"""GM(1,1), including the original two-level sliding-window method."""

import numpy as np

from ..._validation import array, integer, scalar
from .grey_class import GreyClass
from .grey_forecast import GreyForecast


def forecast_values(x1, a, b, k):
    """k=1 is the second observation. Analytic limit at a=0 is b."""
    a = scalar(a, "a")
    b = scalar(b, "b")
    k = np.asarray(k, dtype=float)
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            ratio = 1 + a / 2 + a * a / 6 + a**3 / 24 if abs(a) < 1e-5 else np.expm1(a) / a
            result = (-np.expm1(a) * x1 + b * ratio) * np.exp(-a * k)
    except FloatingPointError as exc:
        raise ValueError("GM11 forecast overflow; shorten horizon or rescale input") from exc
    if not np.isfinite(result).all():
        raise ValueError("GM11 produced a nonfinite forecast")
    return result


class GreyGM11(GreyClass):
    def __init__(self, *, horizon=1, window_size=None, stride=1, correction_mode="legacy", **kwargs):
        super().__init__(**kwargs)
        self.forecasted_outputs = []
        self._continuation = []
        self.stride = integer(stride, "stride")
        self.length = 4
        self.period = integer(horizon, "horizon", minimum=0)
        self.convolution = False
        self.window_size = window_size
        if correction_mode not in {"legacy", "none"}:
            raise ValueError("correction_mode must be legacy or none")
        self.correction_mode = correction_mode

    @property
    def horizon(self):
        return self.period

    @horizon.setter
    def horizon(self, value):
        self.period = integer(value, "horizon", minimum=0)

    @property
    def window_size(self):
        return self.length if self.convolution else None

    @window_size.setter
    def window_size(self, value):
        if value is None:
            self.convolution = False
        else:
            self.length = integer(value, "window_size", minimum=3)
            self.convolution = True

    def add_pattern(self, pattern, pattern_key):
        self._add_patterns(scalar(pattern, "pattern"), pattern_key)

    def _forecast(self, patterns, period):
        values = array(patterns, name="series", ndim=1, min_rows=3)
        self.remove_all_analysis()
        _, background = self._ago_arrays([values])
        a, b = self._solve(
            np.column_stack((-background, np.ones(values.size - 1))),
            values[1:],
            penalty_weights=[1, 0],
        )
        predicted = forecast_values(values[0], a, b, np.arange(1, values.size + period))
        residual = values[1:] - predicted[: values.size - 1]
        valid = values[1:] != 0
        errors = np.abs(residual[valid] / values[1:][valid])
        average = float(errors.mean()) if errors.size else None
        self.metrics_ = dict(
            mae=float(np.mean(np.abs(residual))),
            rmse=float(np.sqrt(np.mean(residual**2))),
            mape=average,
            percentage_error_count=int(valid.sum()),
        )
        results = []
        for k, value in enumerate(predicted, 1):
            historical = k < values.size
            original = float(values[k]) if historical else 0.0
            error = float(abs((original - value) / original)) if historical and original != 0 else None
            results.append(
                GreyForecast(
                    self._TAG_FORECAST_HISTORY if historical else self._TAG_FORECAST_NEXT_MOMENT,
                    k,
                    original,
                    float(value),
                    error,
                    average,
                )
            )
        self.analyzed_results = results
        return results

    def forecast(self):
        period = integer(self.period, "period", minimum=0)
        values = array(self.patterns, name="series", ndim=1, min_rows=3)
        if not self.convolution:
            return self._forecast(values, period)
        stride = integer(self.stride, "stride")
        length = integer(self.length, "length", minimum=3, maximum=values.size)
        if self.correction_mode not in {"legacy", "none"}:
            raise ValueError("correction_mode must be legacy or none")
        self.forecasted_outputs = list(self._continuation)
        starts = list(range(0, values.size - length + 1, stride))
        windows = []
        for i, start in enumerate(starts):
            # Preserve the historical final-window tail policy.
            stop = values.size if i == len(starts) - 1 else start + length
            result = self._forecast(values[start:stop], 1)
            windows.append(result)
            value = result[-1].forecast_value
            if self.correction_mode == "legacy":
                value *= 1 + (result[-1].average_error_rate or 0)
            self.forecasted_outputs.append(value)
        if len(self.forecasted_outputs) >= 3:
            self._forecast(self.forecasted_outputs, period)
            if period:
                self.forecasted_outputs.append(self.last_moment)
        elif len(starts) > 1:
            raise ValueError("second-level GM11 requires at least three window predictions")
        elif period != 1:
            self._forecast(values, period)
        return windows

    def set_data(self, series):
        """Store a private copy of a series without fitting it."""
        values = array(series, name="series", ndim=1, min_rows=3)
        self.reset(clear_data=True)
        for i, value in enumerate(values):
            self.add_pattern(value, f"t{i}")
        return self

    def fit(self, series):
        self.set_data(series)
        self.forecast()
        return self

    def predict(self, steps=1):
        steps = integer(steps, "steps", minimum=0)
        if not hasattr(self, "coefficients_"):
            raise ValueError("fit or forecast must be called before predict")
        a, b = self.coefficients_
        if self.convolution:
            # Reuse the complete two-level forecast, including its tail policy,
            # without changing the fitted model's horizon or results.
            if steps == 0:
                return np.empty(0)
            model = self.deepcopy()
            model.horizon = steps
            model.forecast()
            return np.array([
                result.forecast_value for result in model.analyzed_results
                if result.tag == self._TAG_FORECAST_NEXT_MOMENT
            ])
        return forecast_values(
            self.patterns[0], a, b, np.arange(len(self.patterns), len(self.patterns) + steps)
        )

    def continue_forecasting(self, last_forecasted_outputs=None):
        if last_forecasted_outputs is not None:
            values = array(last_forecasted_outputs, name="last_forecasted_outputs", ndim=1)
            self._continuation.extend(values.tolist())

    def clean_forecasted(self):
        self.forecasted_outputs = []
        self._continuation = []

    @property
    def last_moment(self):
        if not self.analyzed_results:
            raise ValueError("forecast must be called first")
        return self.analyzed_results[-1].forecast_value
