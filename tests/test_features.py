"""Physical geometry, GM equation checks, boundaries, and complete pipelines."""

import numpy as np
import pytest
from sklearn.base import clone
from sklearn.exceptions import NotFittedError
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline

from greytheory.analysis import GreyPCA
from greytheory.features import GreyWindowFeatures, ImagePatchFeatures, Trajectory, TrajectoryFeatures


def named_features(model, X):
    values = model.fit_transform(X)
    return dict(zip(model.get_feature_names_out(), values[0]))


def test_window_gm_coefficients_match_independent_discrete_equation():
    values = np.array([-2.0, -1.0, 1.0, 3.0, 4.0])
    model = GreyWindowFeatures(5, normalize=False, alpha=0.3, ridge_alpha=0)
    result = named_features(model, values[None])
    accumulated = np.cumsum(values)
    background = 0.3 * accumulated[1:] + 0.7 * accumulated[:-1]
    design = np.column_stack((-background, np.ones(4)))
    expected = np.linalg.lstsq(design, values[1:], rcond=None)[0]
    prefix = "window_0_5.channel_0."
    np.testing.assert_allclose([result[prefix + "gm_a"], result[prefix + "gm_b"]], expected)
    assert result[prefix + "gm_equation_rmse"] == pytest.approx(
        np.sqrt(np.mean((design @ expected - values[1:]) ** 2))
    )
    assert result[prefix + "gm_full_rank_coverage"] == 1
    assert result[prefix + "amplitude"] == 4


def test_windows_cover_tail_without_changing_width_or_input():
    values = np.arange(34.0).reshape(1, 17, 2)
    before = values.copy()
    model = GreyWindowFeatures(6, stride=4).fit(values)
    assert model.windows == ((0, 6), (4, 10), (8, 14), (11, 17))
    result = model.transform(values)
    assert result.shape == (1, 4 * 2 * 9 + 4)
    assert len(model.get_feature_names_out()) == result.shape[1]
    np.testing.assert_array_equal(values, before)
    np.testing.assert_array_equal(result, model.transform(values))
    with pytest.raises(ValueError, match="shape"):
        model.transform(values[:, :-1])
    model.set_params(alpha=0.7)
    with pytest.raises(ValueError, match="fit again"):
        model.transform(values)


def test_windows_do_not_model_pen_up_jump_and_expose_short_segments():
    sequence = np.column_stack(([0, 1, 2, 100, 101, 102], [1, 0, 0, 1, 0, 0]))[None]
    model = GreyWindowFeatures(6, normalize=False, ridge_alpha=0, boundary_channel=-1)
    result = named_features(model, sequence)
    prefix = "window_0_6.channel_0."
    assert result[prefix + "mean_change"] == 1
    assert result[prefix + "gm_coverage"] == 1
    assert result["window_0_6.segment_count"] == 2
    # Only two-point fragments: no invented GM coefficients or full-rank claim.
    sequence[0, :, 1] = [1, 0, 1, 0, 1, 0]
    result = named_features(model, sequence)
    assert result[prefix + "gm_coverage"] == 0
    assert result[prefix + "gm_a"] == result[prefix + "gm_b"] == 0
    assert result[prefix + "gm_full_rank_coverage"] == 0


def test_zero_channels_are_finite_and_report_rank_deficiency():
    model = GreyWindowFeatures(4)
    result = named_features(model, np.zeros((1, 4, 2)))
    assert all(np.isfinite(list(result.values())))
    assert result["window_0_4.channel_0.gm_coverage"] == 1
    assert result["window_0_4.channel_0.gm_full_rank_coverage"] == 0


def test_window_normalization_retains_original_amplitude_separately():
    model = GreyWindowFeatures(4, ridge_alpha=0)
    result = model.fit_transform([[1, 2, 3, 4], [3, 6, 9, 12]])
    names = model.get_feature_names_out().tolist()
    amplitude = names.index("window_0_4.channel_0.amplitude")
    assert result[:, amplitude].tolist() == [4, 12]
    np.testing.assert_allclose(np.delete(result[0], amplitude), np.delete(result[1], amplitude))


@pytest.mark.parametrize("dimensions", [2, 3, 5])
def test_multidimensional_straight_path_has_known_direction_and_speed(dimensions):
    vector = np.arange(1.0, dimensions + 1)
    times = np.array([0.0, 0.4, 1.5, 2.0])
    points = times[:, None] * vector + 20
    model = TrajectoryFeatures(9, include_time=True)
    result = model.fit_transform([Trajectory(points, times)])
    names = model.get_feature_names_out().tolist()
    assert result.shape == (1, 9, 2 * dimensions + 4)
    np.testing.assert_allclose(result[0, :, :dimensions], np.linspace(0, 2, 9)[:, None] * vector)
    np.testing.assert_allclose(
        result[0, 1:, dimensions : 2 * dimensions], np.tile(vector / np.linalg.norm(vector), (8, 1))
    )
    np.testing.assert_allclose(result[0, 1:, names.index("speed")], np.linalg.norm(vector))
    np.testing.assert_allclose(result[0, :, names.index("turn_angle")], 0, atol=3e-8)
    assert result[0, 0, -1] == 1 and result[0, 1:, -1].sum() == 0


def test_pen_up_gaps_are_not_distance_or_speed_and_variable_lengths_resample():
    points = np.array([[0.0, 0], [1, 0], [100, 0], [101, 0]])
    sample = Trajectory(points, timestamps=[0, 1, 20, 21], stroke_ids=[0, 0, 1, 1])
    model = TrajectoryFeatures(8, include_time=True)
    result = model.fit_transform([sample])[0]
    names = model.get_feature_names_out().tolist()
    assert result[:, -1].tolist() == [1, 0, 0, 0, 1, 0, 0, 0]
    np.testing.assert_allclose(result[[0, 4], names.index("step_distance")], 0)
    assert result[:, names.index("step_distance")].sum() == pytest.approx(2.0)
    np.testing.assert_allclose(result[[1, 2, 3, 5, 6, 7], names.index("speed")], 1.0)
    np.testing.assert_array_equal(points, [[0, 0], [1, 0], [100, 0], [101, 0]])
    plain = TrajectoryFeatures(8)
    output = plain.fit_transform([points, np.array([[0, 0], [2, 1], [3, 3.0]])])
    assert output.shape == (2, 8, 7)
    assert np.isfinite(plain.transform([np.zeros((2, 2))])).all()


def test_right_angle_and_translation_are_preserved():
    points = np.array([[0.0, 0], [1, 0], [1, 1]])
    model = TrajectoryFeatures(5)
    result = model.fit_transform([points, points + 100])
    np.testing.assert_allclose(result[0], result[1])
    angle = result[0, :, model.get_feature_names_out().tolist().index("turn_angle")]
    assert angle.max() == pytest.approx(np.pi / 2)
    # Arc-length resampling is insensitive to duplicate stationary measurements.
    repeated = np.insert(points, 1, points[0], axis=0)
    np.testing.assert_allclose(model.transform([repeated])[0], result[0])


def test_image_patches_preserve_channel_values_grid_positions_and_edge_directions():
    ramp = np.tile(np.arange(12.0), (8, 1))
    model = ImagePatchFeatures((2, 3))
    output = model.fit_transform(ramp[None])[0]
    assert output.shape == (6, 5)
    np.testing.assert_allclose(output[:, 0], [1.5, 5.5, 9.5, 1.5, 5.5, 9.5])
    np.testing.assert_allclose(output[:, 2], 1)
    np.testing.assert_allclose(output[:, 3], 0)
    assert output[:, -1].tolist() == [1, 0, 0, 1, 0, 0]
    assert model.patch_bounds[0] == (0, 0, 4, 4)
    assert model.patch_bounds[-1] == (4, 8, 8, 12)
    colors = np.broadcast_to([1.0, 3.0, 7.0], (2, 8, 12, 3))
    output = ImagePatchFeatures((2, 3)).fit_transform(colors)
    np.testing.assert_allclose(output[:, :, [0, 4, 8]], np.broadcast_to([1, 3, 7], (2, 6, 3)))
    assert output.shape == (2, 6, 13)


def test_image_schema_and_binary_masks_work_with_clone_and_grey_windows():
    images = np.tile(np.arange(16) % 2 == 0, (2, 8, 1))
    patches = clone(ImagePatchFeatures((2, 4)))
    sequences = patches.fit_transform(images)
    windows = GreyWindowFeatures(4, stride=4, boundary_channel=-1)
    described = windows.fit_transform(sequences)
    assert described.shape == (2, 2 * 4 * 9 + 2)
    np.testing.assert_allclose(described[0], described[1])
    with pytest.raises(ValueError, match="shape/grid"):
        patches.transform(np.zeros((1, 4, 8)))


def test_scaled_trajectory_uses_normalized_distance_and_rejects_changed_schema():
    model = TrajectoryFeatures(5, scale=True)
    result = model.fit_transform([[[0, 0], [3, 4]]])[0]
    index = model.get_feature_names_out().tolist().index("step_distance")
    assert result[:, index].sum() == pytest.approx(1.0)
    with pytest.raises(ValueError, match="dimensions"):
        model.transform([[[0, 0, 0], [1, 2, 3]]])
    model.set_params(n_points=10)
    with pytest.raises(ValueError, match="fit again"):
        model.transform([[[0, 0], [3, 4]]])


def test_trajectory_window_pca_regression_is_a_cloneable_training_only_pipeline():
    # Dyadic, axis-aligned paths have exactly zero turning angles. Oblique
    # straight lines can produce arccos roundoff that standardization amplifies,
    # making this test measure BLAS-dependent noise instead of scale prediction.
    times = np.arange(9) / 8
    scales = np.arange(4, 36) / 8
    paths = [Trajectory(np.column_stack((s * times, np.zeros_like(times))), timestamps=times) for s in scales]
    supplied = Pipeline(
        [
            ("trajectory", TrajectoryFeatures(17, include_time=True)),
            ("windows", GreyWindowFeatures(8, stride=4, boundary_channel=-1)),
            ("reducer", GreyPCA(1, top_k=1, standardize=True)),
            ("model", Ridge(alpha=1)),
        ]
    )
    model = clone(supplied).fit(paths[:24], scales[:24])
    predicted = model.predict(paths[24:])
    error = np.sqrt(np.mean((predicted - scales[24:]) ** 2))
    baseline = np.sqrt(np.mean((scales[:24].mean() - scales[24:]) ** 2))
    assert error < baseline * 0.2
    scaler = model.named_steps["reducer"].scaler_
    before = scaler.mean_.copy()
    model.predict(paths[-1:])
    np.testing.assert_array_equal(scaler.mean_, before)
    assert not hasattr(supplied.named_steps["trajectory"], "dimensions")


@pytest.mark.parametrize(
    "model,X",
    [
        (GreyWindowFeatures(), np.zeros((1, 8))),
        (TrajectoryFeatures(), [np.zeros((3, 2))]),
        (ImagePatchFeatures(), np.zeros((1, 8, 8))),
    ],
)
def test_feature_extractors_require_fit(model, X):
    with pytest.raises(NotFittedError):
        model.transform(X)


@pytest.mark.parametrize(
    "model,X",
    [
        (GreyWindowFeatures(2), np.ones((1, 4))),
        (GreyWindowFeatures(4, stride=5), np.ones((1, 8))),
        (GreyWindowFeatures(4, boundary_channel=0), np.ones((1, 4, 1))),
        (GreyWindowFeatures(4, boundary_channel=1), np.full((1, 4, 2), 0.5)),
        (GreyWindowFeatures(4), np.full((1, 4), np.nan)),
        (TrajectoryFeatures(include_time=True), [np.ones((4, 2))]),
        (TrajectoryFeatures(), [Trajectory(np.ones((4, 2)), [0, 1, 1, 2])]),
        (TrajectoryFeatures(), [Trajectory(np.ones((4, 2)), stroke_ids=[0, 1, 1, 1])]),
        (TrajectoryFeatures(), [np.ones((4, 2)), np.ones((4, 3))]),
        (TrajectoryFeatures(), np.ones((4, 2))),
        (ImagePatchFeatures((3, 3)), np.ones((1, 2, 2))),
    ],
)
def test_invalid_data_is_explicitly_rejected(model, X):
    with pytest.raises((ValueError, TypeError)):
        model.fit_transform(X)
