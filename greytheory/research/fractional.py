"""Equal-step RL-FGM core from Xu et al. (2026), independently implemented.

Order selection uses chronological validation and a finite grid instead of the
paper's in-sample MAPE/PSO. No publisher text, figures, data or code are bundled.

Source: Zhenguo Xu, Rui Peng, Mengyi Pang, Jianming Jiang, Rujing Zhang
and Caixia Liu (2026), Science Progress. DOI: 10.1177/00368504261481032.
"""

import numpy as np
from scipy.linalg import solve_triangular, toeplitz
from scipy.special import gamma
from sklearn.base import BaseEstimator
from sklearn.utils.validation import check_is_fitted

from .._validation import array, integer, scalar

MAX_LENGTH = 2048


def _series(values, minimum=4):
    values = array(values, name="series", ndim=1, min_rows=minimum)
    if len(values) > MAX_LENGTH or np.any(values < 0):
        raise ValueError("series must be nonnegative and contain at most 2048 equal-step observations")
    return values


def rl_matrix(length, order):
    """Lower triangular RL accumulation; order=0 is the defined identity limit."""
    length = integer(length, "length", maximum=MAX_LENGTH)
    order = scalar(order, "order", minimum=0, maximum=2)
    if order == 0:
        return np.eye(length)
    j = np.arange(1, length + 1, dtype=float)
    weights = np.empty(length)
    weights[0] = 1 / gamma(order + 1)
    # Stable power differences for small orders and long sequences.
    weights[1:] = j[1:] ** order * -np.expm1(order * np.log1p(-1 / j[1:])) / gamma(order + 1)
    return toeplitz(weights, np.r_[weights[0], np.zeros(length - 1)])


def rl_accumulate(values, order=1):
    values = _series(values, minimum=1)
    return rl_matrix(len(values), order) @ values


def rl_restore(accumulated, order=1):
    values = array(accumulated, name="accumulated", ndim=1)
    return solve_triangular(rl_matrix(len(values), order), values, lower=True)


def _estimate(accumulated, increments=None):
    """Fit derivative + a * midpoint = b via SVD least squares."""
    derivative = np.diff(accumulated)
    if increments is not None:
        derivative = derivative / increments
    background = (accumulated[1:] + accumulated[:-1]) / 2
    design = np.column_stack([-background, np.ones(len(background))])
    coefficients, _, rank, singular = np.linalg.lstsq(design, derivative, rcond=None)
    condition = float(singular[0] / singular[-1]) if rank == 2 else None
    return coefficients, dict(
        rank=int(rank),
        condition_number=condition,
        residual_rmse=float(np.sqrt(np.mean((design @ coefficients - derivative) ** 2))),
    )


def _response(initial, a, b, time):
    time = np.asarray(time, dtype=float)
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            if abs(a) < 1e-10:
                factor = time * (1 - a * time / 2 + (a * time) ** 2 / 6)
            else:
                factor = -np.expm1(-a * time) / a
            result = initial + (b - a * initial) * factor
    except FloatingPointError as exc:
        raise ValueError("grey response overflow; rescale or shorten horizon") from exc
    if not np.isfinite(result).all():
        raise ValueError("grey response must be finite")
    return result


class RLFGM(BaseEstimator):
    """Equal-step RL fractional grey forecast. order='auto' uses a training-only tail.

    Inputs are nonnegative and ordered at equal time intervals. Dates, missing
    intervals and non-equidistant recursive modeling are not implemented here.
    Public fitted results intentionally use readable names without suffixes.
    """

    def __init__(self, order="auto", orders=(0, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 2), validation_size=None):
        self.order = order
        self.orders = orders
        self.validation_size = validation_size

    @staticmethod
    def _fit_fixed(values, order):
        accumulated = rl_accumulate(values, order)
        coefficients, diagnostics = _estimate(accumulated)
        return accumulated[0], coefficients, diagnostics

    @staticmethod
    def _restore_response(initial, coefficients, length, order):
        accumulated = _response(initial, *coefficients, np.arange(length, dtype=float))
        return rl_restore(accumulated, order)

    def fit(self, values, y=None):
        values = _series(values)
        trials = []
        if self.order == "auto":
            if len(values) < 6:
                raise ValueError("automatic order selection needs at least six observations")
            holdout = (
                max(1, len(values) // 5)
                if self.validation_size is None
                else integer(self.validation_size, "validation_size", maximum=len(values) - 4)
            )
            candidates = [scalar(v, "order candidate", minimum=0, maximum=2) for v in self.orders]
            if not candidates:
                raise ValueError("orders must not be empty")
            train = values[:-holdout]
            for order in dict.fromkeys(candidates):
                try:
                    initial, coefficients, _ = self._fit_fixed(train, order)
                    prediction = self._restore_response(initial, coefficients, len(values), order)[-holdout:]
                    error = float(np.sqrt(np.mean((prediction - values[-holdout:]) ** 2)))
                    if not np.isfinite(error):
                        raise ValueError("validation error overflow")
                    trials.append(dict(order=order, validation_rmse=error, status="ok"))
                except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
                    trials.append(dict(order=order, status="failed", error=str(exc)))
            valid = [t for t in trials if t["status"] == "ok"]
            if not valid:
                raise ValueError(f"all order candidates failed: {trials}")
            order = min(valid, key=lambda t: t["validation_rmse"])["order"]
        else:
            order = scalar(self.order, "order", minimum=0, maximum=2)
        initial, coefficients, diagnostics = self._fit_fixed(values, order)
        fitted = self._restore_response(initial, coefficients, len(values), order)
        self.order_selected = order
        self.coefficients = coefficients
        self.initial_accumulated = initial
        self.training_values = values.copy()
        self.fitted_values = fitted
        self.diagnostics = dict(
            **diagnostics,
            order=order,
            order_trials=trials,
            implementation="RL core; chronological grid selection, not paper PSO",
            training_rmse=float(np.sqrt(np.mean((fitted - values) ** 2))),
        )
        return self

    def predict(self, steps=1):
        check_is_fitted(self, "training_values")
        steps = integer(steps, "steps", maximum=MAX_LENGTH - len(self.training_values))
        length = len(self.training_values) + steps
        return self._restore_response(
            self.initial_accumulated, self.coefficients, length, self.order_selected
        )[-steps:]
