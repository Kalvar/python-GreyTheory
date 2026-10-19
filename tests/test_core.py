import json
from pathlib import Path
import runpy

import numpy as np
import pytest

from greytheory import GreyTheory
from greytheory.packages.libs.grey_lib import GreyLib
from greytheory.packages.libs.grey_math import GreyMath
from greytheory.packages.models.grey_gm11 import forecast_values

GOLDEN = json.loads((Path(__file__).parent / "fixtures/legacy_golden.json").read_text())
SERIES = [223.3, 227.3, 230.5, 238.1, 242.9, 251.1]


def gm11(convolution=False):
    m = GreyTheory().gm11
    for i, x in enumerate(SERIES):
        m.add_pattern(x, str(i))
    m.convolution = convolution
    return m


def test_example_golden(capsys):
    models = runpy.run_path("example.py")["main"]()
    for name in ("gm0n", "gm1n"):
        result = models[name].analyzed_results
        expected = GOLDEN[name]
        assert [r.name for r in result] == [r["name"] for r in expected]
        np.testing.assert_allclose(
            [r.equation_value for r in result], [r["value"] for r in expected], rtol=1e-9
        )
    np.testing.assert_allclose(models["gm11"].forecasted_outputs, GOLDEN["convolution"]["outputs"], rtol=1e-9)
    assert capsys.readouterr().out


@pytest.mark.parametrize("alpha", [0.5, 0.8])
def test_gm11_golden(alpha):
    m = gm11()
    m.alpha = alpha
    m.period = 2
    result = m.forecast()
    np.testing.assert_allclose([r.forecast_value for r in result], GOLDEN["gm11_" + str(alpha)], rtol=1e-9)


@pytest.mark.parametrize(
    "mode,expected", [("legacy", [5.6, 12]), ("corrected", [4.4, 9]), ("standard", [4.4, 9])]
)
def test_background(mode, expected):
    lib = GreyLib(0.8, mode)
    ago, z = lib.ago([[2, 3, 5]])
    assert ago == [[2, 5, 10]]
    np.testing.assert_allclose(z, expected)


def test_solver_diagnostics_and_ridge():
    B = np.array([[1, 1, 2], [2, 2, 3.0]])
    with pytest.warns(RuntimeWarning):
        beta, d = GreyMath().solve_equations(B, [3, 4], return_diagnostics=True, ridge_alpha=0.1)
    expected = np.linalg.solve(B.T @ B + 0.1 * np.eye(3), B.T @ np.array([3, 4]))
    np.testing.assert_allclose(beta, expected)
    assert d["rank"] == 2 and d["is_rank_deficient"] and np.isinf(d["condition_number"])
    assert d["residual_sum_squares"] == pytest.approx(np.linalg.norm(B @ beta - [3, 4]) ** 2)
    with pytest.raises(ValueError, match="rank"):
        GreyMath().solve_equations(B, [3, 4], rank_policy="raise")


@pytest.mark.parametrize(
    "B,y", [([], []), ([[1], [2]], [1]), ([[np.nan]], [1]), ([[1]], [[1]]), ([[1j]], [1])]
)
def test_invalid_solver(B, y):
    with pytest.raises((ValueError, TypeError)):
        GreyMath().solve_equations(B, y)


def test_keys_order_and_reset():
    m = GreyTheory().gm0n
    m.add_patterns([1, 3, 2, 4], "factor")
    m.add_outputs([2, 5, 4, 7], "target")
    m.analyze()
    assert m.analyzed_results[0].name == "factor"
    assert m.keys == ["target", "factor"]
    m.reset()
    assert len(m.patterns) == 2
    m.reset(True)
    assert not m.patterns


@pytest.mark.parametrize("convolution", [False, True])
def test_repeatability(convolution):
    m = gm11(convolution)
    m.forecast()
    first = m.last_moment
    outputs = list(m.forecasted_outputs)
    m.forecast()
    assert m.last_moment == pytest.approx(first)
    assert m.forecasted_outputs == outputs
    assert m.patterns == SERIES


def test_zero_and_near_zero():
    np.testing.assert_allclose(forecast_values(3, 0, 4, np.arange(1, 5)), 4)
    np.testing.assert_allclose(forecast_values(3, 1e-14, 4, np.arange(1, 5)), 4)
    m = GreyTheory().gm11
    with pytest.warns(RuntimeWarning):
        m.fit([0, 0, 0, 0])
    assert m.last_moment == 0 and m.metrics_["mape"] is None
    assert all(r.error_rate is None for r in m.analyzed_results)
    m = GreyTheory().gm11.fit([2, 2, 2, 2])
    np.testing.assert_allclose(m.predict(2), 2, atol=1e-12)
    m.period = 0
    assert len(m.forecast()) == 3
    with pytest.raises(ValueError, match="overflow"):
        forecast_values(1, -100, 1, [100])


def test_parallel_inplace_and_failure():
    runner = GreyTheory().run
    a, b = gm11(), gm11()
    results = runner.gm11([a, b], workers=2)
    assert results[0] is a and results[1] is b
    assert a.last_moment == pytest.approx(b.last_moment)
    c = gm11()
    runner.gm11([c], workers=1)
    assert c.last_moment == pytest.approx(a.last_moment)
    bad = GreyTheory().gm11
    with pytest.raises(ValueError):
        runner.gm11([a, bad], workers=2)


@pytest.mark.parametrize("value", [-0.1, 1.1, float("nan"), float("inf")])
def test_alpha_invalid(value):
    with pytest.raises(ValueError):
        GreyLib(value)


@pytest.mark.parametrize("period", [-1, 1.2, True])
def test_period_invalid(period):
    m = gm11()
    m.period = period
    with pytest.raises((TypeError, ValueError)):
        m.forecast()


@pytest.mark.parametrize("B,y", [(np.eye(3), [1, 2, 3]), ([[1, 1], [1, 2], [1, 3]], [1, 2, 2])])
def test_full_rank_solver(B, y):
    result = GreyMath().solve_equations(B, y)
    np.testing.assert_allclose(result, np.linalg.lstsq(B, y, rcond=None)[0])


def test_ridge_intercept_and_invalid_parameters():
    B = np.column_stack((np.arange(5), np.ones(5)))
    y = 3 * np.arange(5) + 10
    beta = GreyMath().solve_equations(B, y, ridge_alpha=2, penalty_weights=[1, 0])
    expected = np.linalg.solve(B.T @ B + np.diag([2, 0]), B.T @ y)
    np.testing.assert_allclose(beta, expected)
    for value in [-1, float("inf"), float("nan")]:
        with pytest.raises(ValueError):
            GreyMath().solve_equations(B, y, ridge_alpha=value)


def test_gm1n_design_known_equation():
    from greytheory.packages.libs.grey_lib import GreyLib

    factor = np.array([1, 2, 4, 3, 6, 8.0])
    target = np.array([2, 4, 5, 7, 8, 11.0])
    m = GreyTheory().gm1n
    m.add_patterns(factor, "driver")
    m.add_outputs(target, "output")
    m.background_mode = "corrected"
    m.alpha = 0.8
    m.analyze()
    ago, z = GreyLib(0.8, "corrected").ago([target, factor])
    B = np.column_stack((-np.array(z), np.array(ago[1])[1:]))
    expected = np.linalg.lstsq(B, target[1:], rcond=None)[0]
    np.testing.assert_allclose(m.coefficients_, expected)
    assert m.development_coefficient_ == expected[0]
    m.analyze()
    assert len(m.influence_degrees) == 1


def test_state_keys_and_copy_independence():
    m = gm11()
    m.forecast()
    copy = m.deepcopy()
    copy.patterns[0] = 999
    assert m.patterns[0] == SERIES[0]
    with pytest.raises(ValueError, match="duplicate"):
        m.add_pattern(5, "0")
    m.continue_forecasting([1, 2, 3])
    m.clean_forecasted()
    assert m._continuation == []


@pytest.mark.parametrize("stride,length", [(0, 4), (1, 2), (1, 20), (1.5, 4)])
def test_convolution_boundaries(stride, length):
    m = gm11(True)
    m.stride = stride
    m.length = length
    with pytest.raises((ValueError, TypeError)):
        m.forecast()
