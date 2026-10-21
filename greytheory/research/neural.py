"""Lightweight GINN/FGINN-inspired forecasts using a grey-teacher penalty.

Independent engineering variants, not exact reproduction of the 2025 paper.
The explicit loss is MSE(prediction, truth) + grey_weight*MAE(prediction, teacher)
+ ridge*mean(weights**2). This makes grey guidance depend on network parameters.
SciPy L-BFGS-B and an analytic gradient avoid an additional deep-learning runtime.
"""

import warnings

import numpy as np
from scipy.optimize import minimize
from scipy.special import gamma
from sklearn.base import BaseEstimator
from sklearn.exceptions import ConvergenceWarning
from sklearn.utils.validation import check_is_fitted

from .._validation import integer, scalar
from .fractional import MAX_LENGTH, _estimate, _response, _series


def tm_weights(length, order=1, beta=1):
    length = integer(length, "length", maximum=MAX_LENGTH)
    order = scalar(order, "order", minimum=0, maximum=1)
    beta = scalar(beta, "beta", minimum=0, maximum=2)
    if order == 0 or beta == 0:
        raise ValueError("tM order and beta must be strictly positive")
    return gamma(beta + 1) * np.arange(1, length + 1, dtype=float) ** (order - 1)


def tm_accumulate(values, order=1, beta=1):
    values = _series(values, minimum=1)
    return np.cumsum(tm_weights(len(values), order, beta) * values)


def tm_restore(accumulated, order=1, beta=1):
    from .._validation import array

    values = array(accumulated, name="accumulated", ndim=1)
    return np.diff(np.r_[0, values]) / tm_weights(len(values), order, beta)


def _teacher(window, order, beta):
    weights = tm_weights(len(window) + 1, order, beta)
    accumulated = np.cumsum(weights[:-1] * window)
    coefficients, _ = _estimate(accumulated, weights[1:-1])
    # Time-warp engineering choice: du/dtau + a*u=b, dtau=weight[k].
    tau = np.r_[0, np.cumsum(weights[1:])]
    response = _response(accumulated[0], *coefficients, tau)
    restored = tm_restore(response, order, beta)
    return float(restored[-1])


def _loss_gradient(parameters, X, y, prior, width, grey_weight, ridge):
    size = X.shape[1] * width
    W = parameters[:size].reshape(X.shape[1], width)
    b = parameters[size : size + width]
    v = parameters[size + width : size + 2 * width]
    c = parameters[-1]
    hidden = np.tanh(X @ W + b)
    prediction = hidden @ v + c
    residual, guide = prediction - y, prediction - prior
    loss = np.mean(residual**2) + grey_weight * np.mean(np.abs(guide))
    loss += ridge * (np.sum(W**2) + np.sum(v**2)) / (W.size + v.size)
    output_gradient = (2 * residual + grey_weight * np.sign(guide)) / len(y)
    hidden_gradient = (output_gradient[:, None] * v) * (1 - hidden**2)
    penalty = 2 * ridge / (W.size + v.size)
    gradient = np.r_[
        (X.T @ hidden_gradient + penalty * W).ravel(),
        hidden_gradient.sum(axis=0),
        hidden.T @ output_gradient + penalty * v,
        output_gradient.sum(),
    ]
    return float(loss), gradient


class GINN(BaseEstimator):
    """Autoregressive, univariate grey-guided MLP; research implementation variant.

    Each training teacher uses only that row's past window, never its next target.
    Normalization uses training data only. Future steps are recursively generated.
    No test-based tuning, clipping, silent fallback, or uncertainty guarantee.
    """

    def __init__(
        self, window=3, hidden=8, grey_weight=0.1, ridge=1e-4, max_iter=500, tol=1e-7, random_state=0
    ):
        self.window = window
        self.hidden = hidden
        self.grey_weight = grey_weight
        self.ridge = ridge
        self.max_iter = max_iter
        self.tol = tol
        self.random_state = random_state

    def _fractional_parameters(self):
        return 1.0, 1.0

    def fit(self, values, y=None):
        window = integer(self.window, "window", minimum=3)
        values = _series(values, minimum=window + 3)
        width = integer(self.hidden, "hidden", maximum=128)
        strength = scalar(self.grey_weight, "grey_weight", minimum=0, maximum=1)
        ridge = scalar(self.ridge, "ridge", minimum=0)
        iterations = integer(self.max_iter, "max_iter")
        tolerance = scalar(self.tol, "tol", minimum=1e-12, maximum=0.1)
        order, beta = self._fractional_parameters()
        tm_weights(1, order, beta)  # validates before training
        windows = np.lib.stride_tricks.sliding_window_view(values, window + 1)
        raw, targets = windows[:, :-1], windows[:, -1]
        teacher = np.array([_teacher(row, order, beta) for row in raw])
        center = float(values.mean())
        scale = float(values.std()) or 1.0
        X, target, prior = (raw - center) / scale, (targets - center) / scale, (teacher - center) / scale
        generator = np.random.default_rng(self.random_state)
        parameters = np.r_[
            generator.normal(0, 1 / np.sqrt(window), window * width),
            np.zeros(width),
            generator.normal(0, 0.1, width),
            0.0,
        ]
        losses = []

        def objective(p):
            return _loss_gradient(p, X, target, prior, width, strength, ridge)

        fitted = minimize(
            objective,
            parameters,
            jac=True,
            method="L-BFGS-B",
            options=dict(maxiter=iterations, ftol=tolerance, gtol=tolerance, maxls=40),
            callback=lambda p: losses.append(objective(p)[0]),
        )
        if not np.isfinite(fitted.fun) or not np.isfinite(fitted.x).all():
            raise ValueError("neural optimization produced nonfinite values")
        self.parameters = fitted.x.copy()
        self.training_values = values.copy()
        self.center = center
        self.scale = scale
        self.width_fitted = width
        self.window_fitted = window
        self.teacher_values = teacher.copy()
        self.diagnostics = dict(
            converged=bool(fitted.success),
            iterations=int(fitted.nit),
            message=str(fitted.message),
            loss=float(fitted.fun),
            loss_history=losses,
            order=order,
            beta=beta,
            implementation="Engineering variant: prediction-to-teacher MAE; one tanh layer; L-BFGS-B",
        )
        if not fitted.success:
            warnings.warn(
                "Grey-guided network did not converge; inspect diagnostics", ConvergenceWarning, stacklevel=2
            )
        return self

    def predict(self, steps=1):
        check_is_fitted(self, "parameters")
        steps = integer(steps, "steps", maximum=MAX_LENGTH - len(self.training_values))
        history = self.training_values.tolist()
        size = self.window_fitted * self.width_fitted
        W = self.parameters[:size].reshape(self.window_fitted, self.width_fitted)
        b = self.parameters[size : size + self.width_fitted]
        v = self.parameters[size + self.width_fitted : -1]
        for _ in range(steps):
            inputs = (np.asarray(history[-self.window_fitted :]) - self.center) / self.scale
            value = float((np.tanh(inputs @ W + b) @ v + self.parameters[-1]) * self.scale + self.center)
            if not np.isfinite(value):
                raise ValueError("recursive forecast overflow; shorten the horizon")
            history.append(value)
        return np.asarray(history[-steps:])


class FGINN(GINN):
    """GINN variant with explicit tM weights and a time-warped grey teacher.

    The accumulation/difference pair follows the public truncated-M definition.
    The weighted-time response resolves ambiguous response notation explicitly;
    this is not a claim of reproducing the author's trained model.
    """

    def __init__(
        self,
        window=3,
        hidden=8,
        grey_weight=0.1,
        ridge=1e-4,
        max_iter=500,
        tol=1e-7,
        random_state=0,
        order=0.5,
        beta=1,
    ):
        super().__init__(window, hidden, grey_weight, ridge, max_iter, tol, random_state)
        self.order = order
        self.beta = beta

    def _fractional_parameters(self):
        return self.order, self.beta
