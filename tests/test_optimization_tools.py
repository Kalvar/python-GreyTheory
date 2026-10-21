import numpy as np
import pytest
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.decomposition import PCA
from sklearn.exceptions import ConvergenceWarning
from sklearn.model_selection import KFold
import warnings

from greytheory.analysis import (
    DifferenceCalibrator,
    GreyPCA,
    optimize_candidates,
    pareto_front,
    ranking_stability,
    reconstruction_scores,
    search_grey_pca,
)


def dataset():
    generator = np.random.default_rng(42)
    X = generator.normal(size=(60, 5))
    return X, 3 * X[:, 0] + generator.normal(scale=0.02, size=60)


def test_stability_ties_constants_and_repeatability():
    x = np.arange(30.0)
    X = np.column_stack([x, x, np.ones(30)])
    result = ranking_stability(X, x, k=1, repeats=20)
    np.testing.assert_allclose(result.selection_frequency, [0.5, 0.5, 0])
    np.testing.assert_allclose(result.mean_rank, [1.5, 1.5, 3])
    again = ranking_stability(X, x, k=1, repeats=20)
    np.testing.assert_array_equal(result.mean_rank, again.mean_rank)
    assert result.successful_repeats == 20


def test_group_resampling_keeps_complete_groups(monkeypatch):
    from greytheory.analysis.selection import GreyFeatureSelector

    X, y = dataset()
    X[:, -1] = np.repeat(np.arange(20), 3)
    original = GreyFeatureSelector.fit
    sizes = []

    def fit(self, rows, target):
        _, counts = np.unique(rows[:, -1], return_counts=True)
        assert set(counts) == {3}
        sizes.append(len(rows))
        return original(self, rows, target)

    monkeypatch.setattr(GreyFeatureSelector, "fit", fit)
    ranking_stability(X, y, k=2, repeats=10, groups=X[:, -1], fraction=0.5)
    assert sizes == [60] + [30] * 10


def test_degenerate_stability_is_reported():
    X = np.arange(12.0).reshape(6, 2)
    y = np.array([0, 0, 0, 0, 0, 1.0])
    result = ranking_stability(X, y, repeats=50, k=1, fraction=0.4)
    assert result.skipped_repeats > 0
    assert result.successful_repeats + result.skipped_repeats == 50


def test_conformal_order_ties_and_small_samples():
    calibration = DifferenceCalibrator(0.2).fit(np.arange(9.0))
    assert calibration.threshold == 7
    np.testing.assert_array_equal(calibration.predict([7, 8]), [False, True])
    assert np.isinf(DifferenceCalibrator(0.01).fit([1, 2, 3]).threshold)
    # Exhaustive exchangeable leave-one-out test of the marginal rank bound.
    alarms = []
    values = np.arange(20.0)
    for i in range(20):
        model = DifferenceCalibrator(0.1).fit(np.delete(values, i))
        alarms.append(model.predict([values[i]])[0])
    assert sum(alarms) == 2


def test_reconstruction_uses_training_scale():
    X, _ = dataset()
    model = GreyPCA(2, standardize=True).fit(X[:40])
    frozen_mean = model.scaler_.mean_.copy()
    test = X[40:] + 10
    expected = np.mean(
        ((test - model.inverse_transform(model.transform(test))) / model.scaler_.scale_) ** 2, axis=1
    )
    np.testing.assert_allclose(reconstruction_scores(model, test), expected)
    np.testing.assert_array_equal(model.scaler_.mean_, frozen_mean)


def test_search_matches_manual_fold_predictions_and_does_not_mutate_input():
    from sklearn.linear_model import Ridge

    X, y = dataset()
    frozen = X.copy()
    candidate = dict(n_components=2, top_k=1, standardize=True)
    cv = KFold(3, shuffle=True, random_state=0)
    expected = []
    for train, valid in cv.split(X):
        model = GreyPCA(**candidate).fit(X[train], y[train])
        regressor = Ridge().fit(model.transform(X[train]), y[train])
        expected.append(np.sqrt(np.mean((regressor.predict(model.transform(X[valid])) - y[valid]) ** 2)))
    result = search_grey_pca(X, y, candidates=[candidate])
    np.testing.assert_allclose(result.trials[0]["fold_rmse"], expected)
    assert result.predict(X[:4]).shape == (4,)
    np.testing.assert_array_equal(X, frozen)


def test_search_reuses_decomposition_across_gra_parameters(monkeypatch):
    calls = []
    original = PCA.fit

    def fit(self, X, y=None):
        calls.append(len(X))
        return original(self, X, y)

    monkeypatch.setattr(PCA, "fit", fit)
    X, y = dataset()
    result = search_grey_pca(
        X, y, candidates=[dict(n_components=2, rho=r, top_k=k) for r in (0.3, 0.7) for k in (1, 2)]
    )
    assert len(result.trials) == 4
    assert calls == [40, 40, 40, 60]  # three folds + final full-data refit


def test_search_groups_and_invalid_candidates():
    X, y = dataset()
    groups = np.repeat(np.arange(20), 3)
    result = search_grey_pca(X, y, groups=groups, candidates=[dict(n_components=999), dict(n_components=2)])
    assert sorted(t["status"] for t in result.trials) == ["failed", "ok"]
    assert result.best_parameters["n_components"] == 2
    with pytest.raises(ValueError, match="group"):
        search_grey_pca(X, y, groups=groups, cv=KFold(3, shuffle=True))


class WarningRegressor(RegressorMixin, BaseEstimator):
    def fit(self, X, y):
        warnings.warn("unfinished", ConvergenceWarning)
        return self

    def predict(self, X):
        return np.zeros(len(X))


def test_unconverged_search_cannot_win():
    X, y = dataset()
    with pytest.raises(ValueError, match="not_converged"):
        search_grey_pca(X, y, predictor=WarningRegressor(), candidates=[dict(n_components=1)])


def test_pareto_mixed_directions_feasibility_and_duplicates():
    values = [[1, 5], [2, 4], [3, 8], [1, 5], [0, 9]]
    result = pareto_front(values, ["smaller", "larger"], constraints=[[-1], [0], [-2], [0], [1]])
    np.testing.assert_array_equal(result.indices, [0, 2, 3])
    empty = pareto_front(values, ["smaller", "larger"], constraints=np.ones((5, 1)))
    assert empty.indices.size == 0
    flipped = pareto_front(-np.array(values), ["larger", "smaller"])
    assert flipped.indices.tolist() == [4]


def test_candidate_evaluation_and_constraint_boundary():
    parameters = np.array([[0.0], [1.0], [2.0]])
    original = parameters.copy()

    def evaluate(rows):
        objectives = np.column_stack([rows[:, 0] ** 2, (rows[:, 0] - 2) ** 2])
        rows[:] = 99  # callback cannot mutate caller data
        return objectives, np.array([[-1], [0], [1]])

    result = optimize_candidates(parameters, evaluate, ["smaller", "smaller"])
    np.testing.assert_array_equal(result["front"].indices, [0, 1])
    np.testing.assert_array_equal(parameters, original)


@pytest.mark.parametrize(
    "operation",
    [
        lambda: DifferenceCalibrator(0).fit([1, 2]),
        lambda: DifferenceCalibrator().fit([np.nan]),
        lambda: ranking_stability([[1], [2], [3]], [1, 2, 3], k=1, groups=[1, None, 2]),
        lambda: pareto_front([[1, 2]], ["smaller"]),
        lambda: optimize_candidates([[1]], lambda x: [[1], [2]], ["smaller"]),
    ],
)
def test_invalid_inputs(operation):
    with pytest.raises((ValueError, TypeError)):
        operation()


def test_cached_convergence_warning_is_not_lost(monkeypatch):
    original = PCA.fit

    def fit(self, X, y=None):
        warnings.warn("unfinished decomposition", ConvergenceWarning)
        return original(self, X, y)

    monkeypatch.setattr(PCA, "fit", fit)
    X, y = dataset()
    with pytest.raises(ValueError, match="no valid converged trial") as error:
        search_grey_pca(X, y, candidates=[dict(n_components=2, rho=0.3), dict(n_components=2, rho=0.7)])
    assert str(error.value).count("'status': 'not_converged'") == 2


def test_search_budget_stops_between_trials(monkeypatch):
    from greytheory.analysis import search as module

    clock = iter([0, 0, 0, 0, 10, 10])
    monkeypatch.setattr(module, "perf_counter", lambda: next(clock))
    X, y = dataset()
    result = search_grey_pca(X, y, components=(1, 2, 3), time_budget=1)
    assert result.stopped_by_budget
    assert len(result.trials) == 1


def test_search_pipeline_survives_cache_cleanup_and_pickle(tmp_path):
    import pickle

    X, y = dataset()
    result = search_grey_pca(X, y, components=(2,), memory=str(tmp_path / "cache"))
    import shutil

    shutil.rmtree(tmp_path / "cache")
    restored = pickle.loads(pickle.dumps(result))
    np.testing.assert_allclose(result.predict(X[:4]), restored.predict(X[:4]))


def test_simple_launcher_uses_project_environment(monkeypatch, tmp_path):
    import run

    calls = []
    monkeypatch.setattr(run, "prepare_environment", lambda root: tmp_path / "python")
    monkeypatch.setattr(run.subprocess, "call", lambda command, **kwargs: calls.append(command) or 0)
    output = tmp_path / "results with spaces.json"
    assert run.main(["optimize", "--output", str(output)]) == 0
    assert calls == [[str(tmp_path / "python"), "-m", "examples.grey_optimization", "--output", str(output)]]
