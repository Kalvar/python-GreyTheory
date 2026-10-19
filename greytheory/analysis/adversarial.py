"""AdvPCA, arXiv:2606.03553 Algorithms 1/2; no runtime convex package."""

import warnings

import numpy as np
from scipy.linalg import cho_factor, cho_solve, lstsq
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.exceptions import ConvergenceWarning
from sklearn.utils.validation import check_is_fitted

from .._validation import array, integer, scalar
from .._results import result_alias


def adversarial_objective(X, A, B, delta):
    orthogonal_residual = X - (X @ A) @ A.T
    penalty = np.abs(X @ (B - A)) + delta * np.abs(B).sum(axis=0)
    return float(np.sum(orthogonal_residual**2) + np.sum(penalty**2))


def eta_regression(X, alpha, delta, *, max_iter=500, tol=1e-8, smoothing=1e-10):
    """Stabilized eta-trick weighted ridge. Returns beta and convergence diagnostics."""
    y = X @ alpha
    if delta == 0:
        return lstsq(X, y, lapack_driver="gelsd")[0], dict(n_iter=0, converged=True)
    if np.linalg.norm(y, 1) == 0 or delta >= np.max(np.abs(X.T @ y)) / np.linalg.norm(y, 1):
        return np.zeros(X.shape[1]), dict(n_iter=0, converged=True)
    w = np.ones(X.shape[0])
    gamma = np.ones(X.shape[1])
    previous = np.inf
    converged = False
    for iteration in range(1, max_iter + 1):
        # Equivalent weighted ridge; positive diagonal permits a small dual solve
        # for n << d. No inverse is formed. Otherwise use augmented QR/SVD.
        if X.shape[0] < X.shape[1]:
            root_gamma = np.sqrt(gamma)
            C = X * np.sqrt(w)[:, None] / root_gamma
            rhs = y * np.sqrt(w)
            factor = cho_factor(C @ C.T + np.eye(X.shape[0]), lower=True)
            beta = (C.T @ cho_solve(factor, rhs)) / root_gamma
        else:
            B = np.vstack((X * np.sqrt(w)[:, None], np.diag(np.sqrt(gamma))))
            beta = lstsq(B, np.r_[np.sqrt(w) * y, np.zeros(X.shape[1])], lapack_driver="gelsy")[0]
        residual = np.abs(y - X @ beta)
        absolute_beta = np.abs(beta)
        objective = float(np.sum((residual + delta * absolute_beta.sum()) ** 2))
        if np.isfinite(previous) and abs(previous - objective) <= tol * max(1, previous):
            converged = True
            break
        previous = objective
        total = residual + delta * absolute_beta.sum()
        # Algebraically identical to Algorithm 2's eta weights away from zeros.
        w = np.maximum(total, smoothing) / np.maximum(residual, smoothing)
        gamma = delta * np.maximum(total.sum(), smoothing) / np.maximum(absolute_beta, smoothing)
        normalizer = max(float(w.max()), float(gamma.max()), 1)
        w = w / normalizer
        gamma = gamma / normalizer
    return beta, dict(n_iter=iteration, converged=converged, objective=objective)


def _polar(matrix):
    U, _, Vt = np.linalg.svd(matrix, full_matrices=False)
    return U @ Vt


class AdvPCA(TransformerMixin, BaseEstimator):
    converged = result_alias("converged_", "Whether the outer optimization converged.")
    reconstruction_error = result_alias("reconstruction_error_", "Mean squared training reconstruction error.")
    sparsity = result_alias("sparsity_", "Fraction of encoder entries close to zero.")

    def __init__(
        self,
        n_components=2,
        delta="adaptive",
        max_iter=200,
        tol=1e-6,
        inner_max_iter=500,
        inner_tol=1e-8,
        smoothing=0.5,
    ):
        self.n_components = n_components
        self.delta = delta
        self.max_iter = max_iter
        self.tol = tol
        self.inner_max_iter = inner_max_iter
        self.inner_tol = inner_tol
        self.smoothing = smoothing

    def fit(self, X, y=None):
        X = array(X, min_rows=2)
        k = integer(self.n_components, "n_components", maximum=min(X.shape))
        max_iter = integer(self.max_iter, "max_iter")
        inner_max_iter = integer(self.inner_max_iter, "inner_max_iter")
        tol = scalar(self.tol, "tol", minimum=0)
        inner_tol = scalar(self.inner_tol, "inner_tol", minimum=0)
        smooth = scalar(self.smoothing, "smoothing", minimum=0, maximum=1)
        if smooth == 1:
            raise ValueError("smoothing must be below 1 to permit decoder updates")
        self.n_features_in_ = X.shape[1]
        self.mean_ = X.mean(axis=0)
        X = X - self.mean_
        _, _, Vt = np.linalg.svd(X, full_matrices=False)
        A = Vt[:k].T
        denom = np.abs(X @ A).sum(axis=0)
        threshold = np.divide(np.abs(X.T @ (X @ A)).max(axis=0), denom, out=np.zeros(k), where=denom > 0)
        if isinstance(self.delta, str):
            if self.delta != "adaptive":
                raise ValueError("delta must be adaptive, a nonnegative scalar, or length-k vector")
            # Paper Section 7, fixed from initialization. Degenerate cases yield zero.
            fraction = np.sqrt(np.log(X.shape[1]) / X.shape[0])
            if fraction >= 1:
                warnings.warn(
                    "adaptive radius reaches zero-encoder regime; provide delta explicitly",
                    RuntimeWarning,
                    stacklevel=2,
                )
            delta = threshold * fraction
        else:
            raw = np.asarray(self.delta)
            if raw.ndim == 0:
                delta = np.full(k, scalar(self.delta, "delta", minimum=0))
            else:
                delta = array(self.delta, name="delta", ndim=1)
                if delta.shape != (k,) or np.any(delta < 0):
                    raise ValueError("delta vector must be nonnegative with length n_components")
        self.delta_ = delta
        self.delta_max_ = threshold
        self.objective_history_ = []
        self.inner_diagnostics_ = []
        self.converged_ = False
        if not np.any(delta):
            B = A.copy()
            self.objective_history_ = [adversarial_objective(X, A, B, delta)]
            self.n_iter_ = 0
            self.converged_ = True
        else:
            previous = np.inf
            for iteration in range(1, max_iter + 1):
                solutions = [
                    eta_regression(X, A[:, j], delta[j], max_iter=inner_max_iter, tol=inner_tol)
                    for j in range(k)
                ]
                B = np.column_stack([result[0] for result in solutions])
                self.inner_diagnostics_.append([result[1] for result in solutions])
                R = np.sign(X @ (B - A)) * (delta * np.abs(B).sum(axis=0))
                updated = _polar(X.T @ (X @ B + R))
                new_A = _polar(smooth * A + (1 - smooth) * updated)
                objective = adversarial_objective(X, new_A, B, delta)
                self.objective_history_.append(objective)
                change = np.linalg.norm(new_A - A)
                A = new_A
                if (
                    np.isfinite(previous)
                    and abs(previous - objective) <= tol * max(1, previous)
                    and change <= np.sqrt(max(tol, np.finfo(float).eps))
                ):
                    self.converged_ = True
                    break
                previous = objective
            self.n_iter_ = iteration
            # Synchronize encoder with the final decoder, including the last iteration.
            solutions = [
                eta_regression(X, A[:, j], delta[j], max_iter=inner_max_iter, tol=inner_tol) for j in range(k)
            ]
            B = np.column_stack([result[0] for result in solutions])
            self.inner_diagnostics_.append([result[1] for result in solutions])
            self.objective_history_.append(adversarial_objective(X, A, B, delta))
            if not self.converged_ or not all(d["converged"] for d in self.inner_diagnostics_[-1]):
                warnings.warn(
                    "AdvPCA reached iteration limits; inspect convergence diagnostics",
                    ConvergenceWarning,
                    stacklevel=2,
                )
        self.encoder_, self.decoder_ = B, A
        self.sparsity_ = float(np.mean(np.abs(B) < 1e-6))
        self.reconstruction_error_ = float(np.mean((X - (X @ B) @ A.T) ** 2))
        return self

    def transform(self, X):
        check_is_fitted(self, "encoder_")
        X = array(X)
        if X.shape[1] != self.n_features_in_:
            raise ValueError("transform feature count differs from fit")
        return (X - self.mean_) @ self.encoder_

    @property
    def inner_converged(self):
        """Whether all final inner regressions converged (also true for delta=0)."""
        check_is_fitted(self, "encoder_")
        return not self.inner_diagnostics_ or all(d["converged"] for d in self.inner_diagnostics_[-1])

    def inverse_transform(self, Z):
        check_is_fitted(self, "decoder_")
        Z = array(Z, name="Z")
        if Z.shape[1] != self.n_components:
            raise ValueError("latent feature count differs from fit")
        return Z @ self.decoder_.T + self.mean_


# Retain imports made before the public shorthand was introduced.
AdversarialPCA = AdvPCA
