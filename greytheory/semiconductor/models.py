"""Process analysis estimators. Fit only training lots/time windows."""

import numpy as np
from scipy.special import ndtr
from scipy.stats import qmc
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.cross_decomposition import PLSRegression
from sklearn.decomposition import PCA
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, WhiteKernel
from sklearn.preprocessing import StandardScaler
from sklearn.utils.validation import check_is_fitted

from .._validation import array, integer
from ..analysis.selection import GreyFeatureSelector
from ..analysis.gra import grey_relation


class QualityPLS(RegressorMixin, BaseEstimator):
    def __init__(self, n_components=2):
        self.n_components = n_components

    def fit(self, X, y):
        X = array(X, min_rows=2)
        y = np.asarray(y)
        y = array(y, name="y", ndim=y.ndim)
        if y.ndim not in (1, 2) or y.shape[0] != X.shape[0]:
            raise ValueError("y must have one row per sample")
        integer(self.n_components, "n_components", maximum=min(X.shape[0] - 1, X.shape[1]))
        self.model_ = PLSRegression(self.n_components, scale=True).fit(X, y)
        self.n_features_in_ = X.shape[1]
        self.training_rmse_ = float(np.sqrt(np.mean((self.model_.predict(X) - y) ** 2)))
        return self

    def predict(self, X):
        check_is_fitted(self, "model_")
        X = array(X)
        if X.shape[1] != self.n_features_in_:
            raise ValueError("feature count differs from fit")
        return self.model_.predict(X)


def rank_features(X, y, *, k=None, rho=0.5):
    X = array(X)
    selector = GreyFeatureSelector(X.shape[1] if k is None else k, rho).fit(X, y)
    return dict(scores=selector.scores_, indices=selector.selected_indices_)


class ProcessMonitor(BaseEstimator):
    """PCA residual Q and T2 with empirical training quantile limits.

    Dynamic mode stacks contiguous past lags. Multiway mode flattens each
    batch. Sequences must be passed separately at lot/wafer boundaries.
    """

    def __init__(self, n_components=2, lags=0, quantile=0.99):
        self.n_components = n_components
        self.lags = lags
        self.quantile = quantile

    def _matrix(self, X):
        raw = np.asarray(X)
        if raw.ndim == 3:
            X = array(raw, ndim=3)
            if self.lags:
                raise ValueError("multiway input cannot also use dynamic lags")
            return X.reshape(X.shape[0], -1)
        X = array(raw)
        lags = integer(self.lags, "lags", minimum=0)
        if X.shape[0] <= lags:
            raise ValueError("sequence is shorter than lag window")
        return np.column_stack([X[lags - j : X.shape[0] - j] for j in range(lags + 1)])

    def fit(self, X, y=None):
        raw = np.asarray(X)
        self.input_shape_ = raw.shape[1:]
        data = self._matrix(X)
        if not 0 < self.quantile < 1:
            raise ValueError("quantile must be in (0, 1)")
        integer(self.n_components, "n_components", maximum=min(data.shape[0] - 1, data.shape[1]))
        self.scaler_ = StandardScaler().fit(data)
        scaled = self.scaler_.transform(data)
        self.pca_ = PCA(self.n_components, svd_solver="full").fit(scaled)
        if np.any(self.pca_.explained_variance_ <= np.finfo(float).eps):
            raise ValueError("requested monitoring components include zero-variance directions")
        stats = self.score_samples(X)
        self.q_limit_ = float(np.quantile(stats["q"], self.quantile))
        self.t2_limit_ = float(np.quantile(stats["t2"], self.quantile))
        return self

    def score_samples(self, X):
        check_is_fitted(self, "pca_")
        if np.asarray(X).shape[1:] != self.input_shape_:
            raise ValueError("process shape differs from training")
        scaled = self.scaler_.transform(self._matrix(X))
        Z = self.pca_.transform(scaled)
        return dict(
            q=np.sum((scaled - self.pca_.inverse_transform(Z)) ** 2, axis=1),
            t2=np.sum(Z**2 / self.pca_.explained_variance_, axis=1),
        )

    def predict(self, X):
        stats = self.score_samples(X)
        return (stats["q"] > self.q_limit_) | (stats["t2"] > self.t2_limit_)


def latin_hypercube(bounds, n_points=20, *, random_state=0):
    bounds = array(bounds, name="bounds")
    if bounds.shape[1] != 2 or np.any(bounds[:, 0] >= bounds[:, 1]):
        raise ValueError("bounds must have shape (n_parameters, 2), lower < upper")
    sample = qmc.LatinHypercube(bounds.shape[0], seed=random_state).random(integer(n_points, "n_points"))
    return qmc.scale(sample, bounds[:, 0], bounds[:, 1])


def suggest_parameters(
    X,
    y,
    bounds,
    *,
    n_candidates=512,
    maximize=True,
    random_state=0,
    objective_weights=None,
    objective_directions=None,
):
    """One GP expected-improvement suggestion within user-supplied parameter bounds.

    Multiple quality targets are reduced to training-batch GRA desirability.
    Uncertainty is GP model uncertainty, not an equipment safety guarantee.
    """
    X = array(X, min_rows=3)
    y = np.asarray(y)
    if y.ndim == 2:
        Y = array(y, name="y")
        directions = (
            np.ones(Y.shape[1])
            if objective_directions is None
            else array(objective_directions, name="objective_directions", ndim=1)
        )
        if directions.shape != (Y.shape[1],) or not np.isin(directions, [-1, 1]).all():
            raise ValueError("objective_directions requires one +1/-1 per quality target")
        oriented = Y * directions
        span = np.ptp(oriented, axis=0)
        desired = (oriented - oriented.min(axis=0)) / np.where(span == 0, 1, span)
        y = grey_relation(np.ones(Y.shape[1]), desired, weights=objective_weights)
        maximize = True
    y = array(y, name="y", ndim=1)
    if X.shape[0] != y.size:
        raise ValueError("X and y row counts differ")
    candidates = latin_hypercube(bounds, n_candidates, random_state=random_state)
    if candidates.shape[1] != X.shape[1]:
        raise ValueError("bounds must match parameter count")
    scaler = StandardScaler().fit(X)
    gp = GaussianProcessRegressor(
        kernel=Matern(nu=2.5) + WhiteKernel(1e-6), normalize_y=True, random_state=random_state
    )
    targets = y if maximize else -y
    gp.fit(scaler.transform(X), targets)
    mean, std = gp.predict(scaler.transform(candidates), return_std=True)
    improvement = mean - targets.max()
    z = np.divide(improvement, std, out=np.zeros_like(mean), where=std > 0)
    ei = improvement * ndtr(z) + std * np.exp(-z * z / 2) / np.sqrt(2 * np.pi)
    index = int(np.argmax(ei))
    return dict(
        parameters=candidates[index],
        predicted_quality=float(mean[index] if maximize else -mean[index]),
        model_std=float(std[index]),
        expected_improvement=float(ei[index]),
        model=gp,
    )
