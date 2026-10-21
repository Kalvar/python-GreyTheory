import json

import numpy as np
import pytest
from sklearn.model_selection import TimeSeriesSplit

from greytheory import analyze_features, choose_options
from greytheory.analysis import DifferenceCalibrator, ranking_stability, reconstruction_scores


@pytest.fixture
def data():
    generator = np.random.default_rng(9)
    features = generator.normal(size=(90, 3))
    target = 2 * features[:, 0] + 0.3 * features[:, 1]
    return features, target


def quick(features, target, **kwargs):
    return analyze_features(
        features,
        target,
        repeats=8,
        search_options={"candidates": [dict(n_components=2, standardize=True)]},
        **kwargs,
    )


def test_quick_matches_low_level_steps_and_root_exports(data):
    from greytheory.analysis import analyze_features as exported

    assert exported is analyze_features
    features, target = data
    result = quick(features[:50], target[:50], normal_data=features[50:70], feature_names=["a", "b", "c"])
    expected = ranking_stability(features[:50], target[:50], k=3, repeats=8)
    np.testing.assert_allclose(result.stability.selection_frequency, expected.selection_frequency)
    model = result.monitor
    calibration = DifferenceCalibrator().fit(reconstruction_scores(model, features[50:70]))
    differences = result.find_differences(features[70:])
    assert differences["threshold"] == calibration.threshold
    np.testing.assert_array_equal(differences["flags"], calibration.predict(differences["scores"]))
    assert result.predict(features[70:]).shape == (20,)
    assert set(row["feature"] for row in result.ranking) == {"a", "b", "c"}
    parameters = result.best_parameters
    parameters["n_components"] = 99
    assert result.best_parameters["n_components"] == 2


def test_normal_data_never_enters_training_and_predictions_stay_frozen(data):
    features, target = data
    result = quick(features[:50], target[:50])
    before = result.predict(features[70:])
    result.calibrate(features[50:70] + 100)
    np.testing.assert_array_equal(result.predict(features[70:]), before)
    np.testing.assert_allclose(
        result.search.model.named_steps["grey"].scaler_.mean_, features[:50].mean(axis=0)
    )


def test_uncalibrated_result_and_report(data, tmp_path):
    features, target = data
    result = quick(features, target)
    with pytest.raises(ValueError, match="normal_data"):
        result.find_differences(features[:2])
    assert result.to_dict()["calibration"] is None
    result.calibrate(features[:2], false_alarm_rate=0.01)
    report = result.save(tmp_path / "報告" / "result.json")
    parsed = json.loads(report.read_text(encoding="utf-8"))
    assert parsed["calibration"]["threshold"] is None
    assert parsed["calibration"]["status"] == "insufficient_resolution"
    assert "Infinity" not in report.read_text(encoding="utf-8")
    assert not result.find_differences(features[:2])["flags"].any()


def test_groups_and_time_splits_are_supported(data):
    features, target = data
    groups = np.repeat(np.arange(30), 3)
    grouped = quick(features, target, groups=groups)
    assert grouped.stability.successful_repeats == 8
    chronological = quick(features, target, cv=TimeSeriesSplit(n_splits=3, gap=2))
    assert len(chronological.search.trials[0]["fold_rmse"]) == 3


def test_small_feature_count_works_with_defaults(data):
    features, target = data
    result = analyze_features(features[:, :1], target, repeats=4)
    assert result.ranking[0]["feature"] == "feature_1"
    assert result.predict(features[:2, :1]).shape == (2,)


def test_named_columns_cannot_be_silently_reordered(data):
    class NamedArray(np.ndarray):
        pass

    features, target = data
    named = features.view(NamedArray)
    named.columns = ["a", "b", "c"]
    result = quick(named, target)
    swapped = named[:, ::-1]
    swapped.columns = ["c", "b", "a"]
    with pytest.raises(ValueError, match="order"):
        result.predict(swapped)
    with pytest.raises(ValueError, match="order"):
        result.calibrate(swapped)


def test_choose_options_names_limits_duplicates_and_snapshot():
    rows = [
        dict(name="A", cost=10, quality=5, days=3, notes=["original"]),
        dict(name="B", cost=12, quality=4, days=2),
        dict(name="C", cost=15, quality=8, days=4),
        dict(name="D", cost=5, quality=9, days=8),
        dict(name="E", cost=10, quality=5, days=3),
    ]
    result = choose_options(rows, smaller=["cost"], larger=["quality"], limits={"days": (None, 4)})
    assert [r["name"] for r in result] == ["A", "C", "E"]
    result[0]["notes"].append("changed")
    assert rows[0]["notes"] == ["original"]
    assert choose_options(rows, smaller=["cost"], limits={"days": (0, 1)}) == []


@pytest.mark.parametrize(
    "call",
    [
        lambda x, y: quick(x, y, feature_names="abc"),
        lambda x, y: quick(x, y, feature_names=["a", "a", "b"]),
        lambda x, y: quick(x, y, normal_data=x[:, :1]),
        lambda x, y: analyze_features(x, y, search_options={"groups": [1]}),
        lambda x, y: choose_options([{"cost": 2}], smaller="cost"),
        lambda x, y: choose_options([{"cost": 2}], smaller=["missing"]),
        lambda x, y: choose_options([{"cost": 2}], smaller=["cost"], larger=["cost"]),
        lambda x, y: choose_options([{"cost": 2}], smaller=["cost"], limits={"cost": (5, 3)}),
        lambda x, y: choose_options([{"cost": 2}], smaller=["cost"], limits={"cost": (None, None)}),
        lambda x, y: choose_options([{"cost": float("nan")}], smaller=["cost"]),
    ],
)
def test_quick_validation(data, call):
    with pytest.raises((ValueError, TypeError)):
        call(*data)


def test_monitor_is_separate_from_full_rank_prediction_search(data):
    features, target = data
    result = analyze_features(
        features[:50],
        target[:50],
        normal_data=features[50:70],
        repeats=4,
        search_options={"candidates": [dict(n_components=3, standardize=True)]},
    )
    assert result.best_parameters["n_components"] == 3
    assert result.monitor.n_components == 2
    np.testing.assert_allclose(result.monitor.scaler_.mean_, features[:50].mean(axis=0))
    assert result.to_dict()["monitor_parameters"]["n_components"] == 2
    with pytest.raises(ValueError, match="monitor_components"):
        analyze_features(features[:50], target[:50], repeats=4, monitor_components=3)
    one = analyze_features(features[:50, :1], target[:50], repeats=4)
    with pytest.raises(ValueError, match="at least two features"):
        one.calibrate(features[50:70, :1])
