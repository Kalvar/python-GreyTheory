"""Independent Grey-Fuzzy GPR engineering design, not a paper reproduction.

GRA induces fixed anisotropic RBF length scales. GP amplitude/noise may optimize.
Gaussian input-support and Cauchy uncertainty memberships are combined by min
(fuzzy AND). The result is a declared heuristic grade, never a probability of
correctness or a calibrated coverage statement.
"""

import numpy as np
from scipy.spatial.distance import cdist
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, RBF, WhiteKernel
from sklearn.preprocessing import StandardScaler
from sklearn.utils.validation import check_is_fitted

from .._validation import array, scalar
from ..analysis.selection import GreyFeatureSelector


class GreyFuzzyGPR(RegressorMixin, BaseEstimator):
    """Scalar-response GPR with GRA length scales and fuzzy reliability diagnostics.

    A zero grey_strength recovers the same uniform-RBF GP baseline. Kernel shape
    is deliberately fixed after training-only GRA; this does not reproduce the
    published IGF-GPR kernel optimization or fuzzy rule base. At least two distinct
    training inputs and a varying scalar target are required.
    """

    def __init__(self, rho=0.5, grey_strength=1.0, noise_level=0.01, optimize_kernel=True, random_state=0):
        self.rho = rho
        self.grey_strength = grey_strength
        self.noise_level = noise_level
        self.optimize_kernel = optimize_kernel
        self.random_state = random_state

    def fit(self, X, y):
        X = array(X, min_rows=5)
        y = array(y, name="y", ndim=1)
        if len(y) != len(X) or np.ptp(y) == 0:
            raise ValueError("y must match training rows and vary")
        if len(np.unique(X, axis=0)) < 2:
            raise ValueError("at least two distinct input rows are required")
        strength = scalar(self.grey_strength, "grey_strength", minimum=0, maximum=1)
        noise = scalar(self.noise_level, "noise_level", minimum=1e-12, maximum=1e6)
        if not isinstance(self.optimize_kernel, (bool, np.bool_)):
            raise TypeError("optimize_kernel must be boolean")
        scaler = StandardScaler().fit(X)
        scaled = scaler.transform(X)
        selector = GreyFeatureSelector(None, self.rho, direction="either", constant_policy="exclude").fit(
            X, y
        )
        scores = np.nan_to_num(selector.scores_, nan=0.0)
        span = np.ptp(scores)
        relative = (scores - scores.min()) / span if span else np.ones(X.shape[1])
        weights = (1 - strength) + strength * (0.1 + 0.9 * relative)
        weights /= weights.mean()
        length_scales = 1 / np.sqrt(weights)
        kernel = ConstantKernel(1.0, (1e-3, 1e3)) * RBF(length_scales, length_scale_bounds="fixed")
        kernel += WhiteKernel(noise, (1e-8, 1e2))
        model = GaussianProcessRegressor(
            kernel=kernel,
            alpha=1e-10,
            normalize_y=True,
            optimizer="fmin_l_bfgs_b" if self.optimize_kernel else None,
            random_state=self.random_state,
        ).fit(scaled, y)
        support = scaled / length_scales
        pairwise = cdist(support, support) / np.sqrt(X.shape[1])
        # Duplicate measurements must not collapse the support bandwidth to zero.
        pairwise[pairwise <= 1e-12] = np.inf
        nearest = pairwise.min(axis=1)
        radius = max(float(np.quantile(nearest, 0.9)), 0.05)
        self.scaler = scaler
        self.model = model
        self.feature_scores = scores.copy()
        self.feature_weights = weights.copy()
        self.length_scales = length_scales.copy()
        self.training_support = support.copy()
        self.support_radius = radius
        self.target_scale = float(y.std())
        self.n_features_in_ = X.shape[1]
        self.diagnostics = dict(
            implementation="Independent GRA-RBF GP + min-rule fuzzy memberships",
            kernel=str(model.kernel_),
            grey_strength=strength,
            support_radius=radius,
            calibrated_reliability=False,
        )
        return self

    def _values(self, X):
        check_is_fitted(self, "model")
        X = array(X)
        if X.shape[1] != self.n_features_in_:
            raise ValueError("feature count differs from training")
        return self.scaler.transform(X)

    def predict(self, X, return_std=False):
        values = self._values(X)
        return self.model.predict(values, return_std=return_std)

    def reliability(self, X):
        values = self._values(X)
        _, std = self.model.predict(values, return_std=True)
        distance = cdist(values / self.length_scales, self.training_support).min(axis=1)
        distance /= np.sqrt(self.n_features_in_)
        support = np.exp(-0.5 * (distance / self.support_radius) ** 2)
        precision = 1 / (1 + (std / self.target_scale) ** 2)
        grade = np.minimum(support, precision)
        return dict(
            grade=grade,
            input_support=support,
            precision_membership=precision,
            label=np.where(grade >= 0.75, "high", np.where(grade >= 0.4, "medium", "low")),
            calibrated=False,
        )
