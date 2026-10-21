"""Mathematical invariants, independent calculations and leakage boundaries."""

import numpy as np
import pytest
from scipy.optimize import check_grad
from scipy.special import gamma
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, RBF, WhiteKernel
from sklearn.preprocessing import StandardScaler

from greytheory import GM11, forecast_series, predict_quality
from greytheory.research import FGINN, GINN, RLFGM, GreyFuzzyGPR, rl_accumulate, rl_matrix, rl_restore
from greytheory.research.fractional import _response
from greytheory.research.neural import _loss_gradient, _teacher, tm_accumulate, tm_restore


@pytest.mark.parametrize("order", [0, 0.01, 0.5, 1, 1.5, 2])
def test_rl_exact_inverse_and_independent_weights(order):
    x = np.array([2.0, 1.0, 5.0, 3.0])
    accumulated = rl_accumulate(x, order)
    if order == 0:
        np.testing.assert_array_equal(accumulated, x)
    else:
        expected = [
            sum((((k - i + 1) ** order - (k - i) ** order) / gamma(order + 1)) * x[i] for i in range(k + 1))
            for k in range(len(x))
        ]
        np.testing.assert_allclose(accumulated, expected)
    np.testing.assert_allclose(rl_restore(accumulated, order), x, atol=1e-12)


def test_rl_first_state_gamma_factor_and_independent_least_squares():
    x = np.array([2.0, 3.0, 4.0, 6.0, 8.0])
    model = RLFGM(order=0.5).fit(x)
    accumulated = rl_accumulate(x, 0.5)
    design = np.column_stack([-(accumulated[1:] + accumulated[:-1]) / 2, np.ones(4)])
    expected = np.linalg.lstsq(design, np.diff(accumulated), rcond=None)[0]
    assert model.initial_accumulated == pytest.approx(x[0] / gamma(1.5))
    np.testing.assert_allclose(model.coefficients, expected)
    assert model.fitted_values[0] == pytest.approx(x[0])


def test_rl_order_one_matches_existing_unmodified_gm_and_prefix_invariance():
    x = 10 * np.exp(0.04 * np.arange(14))
    reference = GM11(correction_mode="none", background_mode="corrected").fit(x).predict(6)
    model = RLFGM(order=1).fit(x)
    np.testing.assert_allclose(model.predict(6), reference, rtol=1e-10)
    np.testing.assert_allclose(model.predict(3), model.predict(6)[:3])
    scaled = RLFGM(order=1).fit(3 * x)
    np.testing.assert_allclose(scaled.predict(3), 3 * model.predict(3))


def test_rl_auto_order_has_independent_chronological_validation_and_constant_limit():
    x = 10 * np.exp(0.02 * np.arange(20))
    model = RLFGM(orders=[0.5, 1, 1.5], validation_size=4).fit(x)
    for trial in model.diagnostics["order_trials"]:
        independent = RLFGM(order=trial["order"]).fit(x[:-4]).predict(4)
        assert trial["validation_rmse"] == pytest.approx(np.sqrt(np.mean((independent - x[-4:]) ** 2)))
    np.testing.assert_allclose(_response(2, 0, 3, np.arange(4)), [2, 5, 8, 11])
    np.testing.assert_allclose(RLFGM(order=1).fit(np.ones(8) * 5).predict(2), 5, atol=1e-10)
    np.testing.assert_array_equal(RLFGM(order=1).fit(np.zeros(8)).predict(2), [0, 0])


@pytest.mark.parametrize("order,beta", [(1, 1), (0.5, 1), (0.8, 0.3)])
def test_tm_accumulation_difference_are_exact_inverses(order, beta):
    x = np.array([3.0, 6.0, 2.0, 7.0, 9.0])
    np.testing.assert_allclose(tm_restore(tm_accumulate(x, order, beta), order, beta), x)
    if order == beta == 1:
        np.testing.assert_allclose(tm_accumulate(x, order, beta), np.cumsum(x))


def test_neural_analytic_gradient_and_grey_term_actually_depends_on_network():
    random = np.random.default_rng(3)
    X = random.normal(size=(6, 3))
    y = random.normal(size=6)
    prior = random.normal(size=6)
    parameters = random.normal(size=3 * 4 + 4 + 4 + 1)

    def fun(p):
        return _loss_gradient(p, X, y, prior, 4, 0.2, 0.01)

    assert check_grad(lambda p: fun(p)[0], lambda p: fun(p)[1], parameters) < 1e-5
    _, plain = _loss_gradient(parameters, X, y, prior, 4, 0, 0)
    _, guided = _loss_gradient(parameters, X, y, prior, 4, 0.5, 0)
    assert not np.allclose(plain, guided)


def test_ginn_teachers_use_only_past_windows_and_fractional_identity():
    x = 20 * np.exp(0.015 * np.arange(25)) + 0.1 * np.sin(np.arange(25))
    a = GINN(max_iter=800, tol=1e-6).fit(x)
    b = FGINN(order=1, beta=1, max_iter=800, tol=1e-6).fit(x)
    np.testing.assert_allclose(a.predict(4), b.predict(4))
    assert len(a.teacher_values) == len(x) - 3
    for i in range(len(a.teacher_values)):
        assert a.teacher_values[i] == pytest.approx(_teacher(x[i : i + 3], 1, 1))
    np.testing.assert_allclose(a.predict(2), a.predict(4)[:2])
    assert np.isfinite(a.predict(5)).all()
    assert a.diagnostics["loss_history"]


def test_neural_failed_convergence_is_visible():
    with pytest.warns(ConvergenceWarning):
        model = GINN(max_iter=1).fit(np.arange(1.0, 20.0))
    assert not model.diagnostics["converged"]
    assert model.diagnostics["iterations"] == 1


def dataset():
    random = np.random.default_rng(7)
    X = random.normal(size=(35, 4))
    y = np.sin(X[:, 0]) + X[:, 1] ** 2
    return X, y


def test_gpr_zero_grey_strength_matches_independent_gp():
    X, y = dataset()
    model = GreyFuzzyGPR(grey_strength=0, optimize_kernel=False).fit(X, y)
    scaler = StandardScaler().fit(X)
    kernel = ConstantKernel(1.0, (1e-3, 1e3)) * RBF(np.ones(4), length_scale_bounds="fixed") + WhiteKernel(
        0.01, (1e-8, 1e2)
    )
    reference = GaussianProcessRegressor(kernel=kernel, alpha=1e-10, normalize_y=True, optimizer=None).fit(
        scaler.transform(X), y
    )
    for actual, expected in zip(
        model.predict(X[:4], return_std=True), reference.predict(scaler.transform(X[:4]), return_std=True)
    ):
        np.testing.assert_allclose(actual, expected)


def test_gpr_scores_are_training_only_and_fuzzy_support_falls_outside_data():
    X, y = dataset()
    model = GreyFuzzyGPR(optimize_kernel=False).fit(X, y)
    scores = model.feature_scores.copy()
    mean = model.scaler.mean_.copy()
    inside = model.reliability(X[:4])
    outside = model.reliability(np.ones((4, 4)) * 100)
    assert np.all((inside["grade"] >= 0) & (inside["grade"] <= 1))
    assert np.all(outside["grade"] < inside["grade"])
    assert not inside["calibrated"]
    np.testing.assert_allclose(
        inside["grade"], np.minimum(inside["input_support"], inside["precision_membership"])
    )
    np.testing.assert_array_equal(model.feature_scores, scores)
    np.testing.assert_array_equal(model.scaler.mean_, mean)
    kernel = model.model.kernel_(model.scaler.transform(X))
    assert np.linalg.eigvalsh(kernel).min() > 0


def test_gpr_duplicates_constants_and_readable_quick_functions():
    X, y = dataset()
    X[:4] = X[4]
    X[:, -1] = 1
    model = GreyFuzzyGPR(optimize_kernel=False).fit(X, y)
    assert model.feature_scores[-1] == 0
    assert model.support_radius > 0
    values = predict_quality(X, y, X[:2], optimize_kernel=False)
    assert values["prediction"].shape == values["std"].shape == (2,)
    assert forecast_series(np.arange(1.0, 12.0), steps=2, method="rlfgm", order=1).shape == (2,)


@pytest.mark.parametrize(
    "operation",
    [
        lambda: rl_matrix(3, -1),
        lambda: rl_accumulate([1, np.nan]),
        lambda: RLFGM().fit([1, 2, 3, 4]),
        lambda: RLFGM(order=1).fit([1, -2, 3, 4]),
        lambda: RLFGM(order=1).fit([1, 2, 3, 4]).predict(0),
        lambda: FGINN(order=0).fit(np.arange(1.0, 12.0)),
        lambda: GreyFuzzyGPR().fit(np.ones((5, 2)), np.arange(5.0)),
        lambda: GreyFuzzyGPR().fit(np.arange(10.0).reshape(5, 2), np.ones(5)),
        lambda: forecast_series([1, 2, 3, 4], method="unknown"),
    ],
)
def test_research_input_guard(operation):
    with pytest.raises((ValueError, TypeError)):
        operation()


@pytest.mark.parametrize("tool", ["rlfgm", "ginn", "fginn", "grey_fuzzy_gpr"])
def test_research_workbench_has_real_numeric_outputs(tool):
    import json
    from examples.workbench.backend import Backend

    result = Backend().request("/api/scenario", {"scenario": "research", "parameters": {"tool": tool}})
    assert result["tables"] and result["warnings"]
    assert result["inputs"]["synthetic"]
    assert result["parameters"]["tool"] == tool
    if tool == "grey_fuzzy_gpr":
        assert len(result["diagram"]["observed"]) == 40
        assert len(result["diagram"]["models"]) == 2
        assert result["diagram"]["models"][1]["reliability"]["calibrated"] is False
    else:
        assert len(result["diagram"]["forecast"]) == 4
        assert len(result["diagram"]["backtest"]) == 8
    json.dumps(result, allow_nan=False)


def test_research_launcher_dispatches_to_project_python(monkeypatch, tmp_path):
    import run

    calls = []
    monkeypatch.setattr(run, "prepare_environment", lambda root: tmp_path / "python")
    monkeypatch.setattr(run.subprocess, "call", lambda command, **kwargs: calls.append(command) or 0)
    assert run.main(["research", "--output", str(tmp_path / "report.json")]) == 0
    assert calls[0][1:3] == ["-m", "examples.research_models"]
