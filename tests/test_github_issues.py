"""Regressions for the original public GM11 issue reports (#3, #4, #5)."""

import warnings

import numpy as np
import pytest

from greytheory import GM11, GreyTheory
from greytheory.packages.models.grey_gm11 import forecast_values

SERIES = [223.3, 227.3, 230.5, 238.1, 242.9, 251.1]


def loaded_model():
    model = GreyTheory().gm11
    for i, value in enumerate(SERIES):
        model.add_pattern(value, f'a{i + 1}')
    return model


def test_issue_3_original_forecast_argument_and_numeric_results():
    model = loaded_model()
    results = model.forecast(2)
    expected = GM11(horizon=2).fit(SERIES)
    np.testing.assert_allclose([r.forecast_value for r in results],
                               [r.forecast_value for r in expected.analyzed_results])
    assert model.horizon == 2
    np.testing.assert_allclose(model.predict(2), [r.forecast_value for r in results[-2:]])
    assert len(model.forecast(0)) == len(SERIES) - 1
    assert len(model.forecast()) == len(SERIES) - 1


def test_issue_4_original_convolution_entry_point():
    model = loaded_model()
    windows = model.forecast_convolution(1, 4)
    expected = GM11(window_size=4, stride=1).fit(SERIES)
    assert len(windows) == 3
    np.testing.assert_allclose(model.forecasted_outputs, expected.forecasted_outputs)
    np.testing.assert_allclose(model.predict(2), expected.predict(2))
    before = list(model.forecasted_outputs)
    model.forecast_convolution(1, 4)
    np.testing.assert_allclose(model.forecasted_outputs, before)
    model.forecast_convolution(1, 4, period=2)
    assert model.horizon == 2
    assert len([r for r in model.analyzed_results if r.tag == model._TAG_FORECAST_NEXT_MOMENT]) == 2


@pytest.mark.parametrize('values', [[0]*6, [2]*6, [0,0,2,0,1,0], [2,0,0,1,0,3]])
def test_issue_5_zero_coefficients_and_zero_observations(values):
    model = GM11(rank_policy='allow').fit(values)
    assert np.isfinite(model.predict(3)).all()
    assert np.isfinite([model.metrics['mae'],model.metrics['rmse']]).all()
    assert model.metrics['percentage_error_count'] == np.count_nonzero(values[1:])
    for result, actual in zip(model.analyzed_results, values[1:]):
        if actual == 0:
            assert result.error_rate is None
        else:
            assert np.isfinite(result.error_rate)
    if not any(values):
        assert model.metrics['mape'] is None
        np.testing.assert_array_equal(model.predict(3), np.zeros(3))
    # The singular formula in #5 must use its analytic a=0 limit, b.
    np.testing.assert_allclose(forecast_values(values[0], 0, 4, np.arange(1,5)), 4)


@pytest.mark.parametrize('bad', [-1, 1.5, True, float('nan')])
def test_legacy_forecast_arguments_validate_before_changing_configuration(bad):
    model = loaded_model()
    with pytest.raises((ValueError, TypeError)):
        model.forecast(bad)
    assert model.horizon == 1
    with pytest.raises((ValueError, TypeError)):
        model.forecast_convolution(1, 4, period=bad)
    assert model.window_size is None


def test_legacy_convolution_rejects_bad_windows_without_mutating_model():
    model = loaded_model()
    for stride,length in [(0,4),(True,4),(1,2),(1,7)]:
        with pytest.raises((ValueError,TypeError)):
            model.forecast_convolution(stride,length)
        assert model.window_size is None
    with warnings.catch_warnings():
        warnings.simplefilter('error')
        model.forecast(2)
