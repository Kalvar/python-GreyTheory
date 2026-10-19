"""Principal Component Pursuit and an explicitly named composite sparse model."""

import warnings

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.exceptions import ConvergenceWarning
from sklearn.utils.validation import check_is_fitted

from .._validation import array, integer, scalar
from .._results import result_alias


def _soft(X, threshold):
    return np.sign(X) * np.maximum(np.abs(X) - threshold, 0)


def robust_pca(X, *, lambda_=None, tol=1e-7, max_iter=1000):
    """Inexact augmented-Lagrangian PCP: min ||L||_* + lambda ||S||_1, X=L+S.

    Returns (low_rank, sparse_corruption, diagnostics). This is transductive.
    """
    X = array(X)
    tol = scalar(tol, "tol", minimum=0)
    max_iter = integer(max_iter, "max_iter")
    lam = 1 / np.sqrt(max(X.shape)) if lambda_ is None else scalar(lambda_, "lambda_", minimum=0)
    if lam == 0:
        raise ValueError("lambda_ must be positive")
    norm = np.linalg.norm(X, "fro")
    if norm == 0:
        return X.copy(), X.copy(), dict(converged=True, n_iter=0, residual=0.0)
    spectral = np.linalg.norm(X, 2)
    Y = X / max(spectral, np.max(np.abs(X)) / lam)
    mu = 1.25 / spectral
    maximum_mu = mu * 1e7
    S = np.zeros_like(X)
    converged = False
    for iteration in range(1, max_iter + 1):
        U, singular, Vt = np.linalg.svd(X - S + Y / mu, full_matrices=False)
        L = (U * np.maximum(singular - 1 / mu, 0)) @ Vt
        S = _soft(X - L + Y / mu, lam / mu)
        residual = X - L - S
        relative = float(np.linalg.norm(residual, "fro") / norm)
        if relative <= tol:
            converged = True
            break
        Y += mu * residual
        mu = min(mu * 1.5, maximum_mu)
    if not converged:
        warnings.warn("PCP did not converge; inspect residual", ConvergenceWarning, stacklevel=2)
    return L, S, dict(converged=converged, n_iter=iteration, residual=relative)


class RobustPCA(BaseEstimator):
    low_rank = result_alias("low_rank_", "Low-rank part of the fitted data.")
    sparse = result_alias("sparse_", "Sparse contamination in the fitted data.")
    diagnostics = result_alias("diagnostics_", "Optimization convergence diagnostics.")

    def __init__(self, lambda_=None, tol=1e-7, max_iter=1000):
        self.lambda_ = lambda_
        self.tol = tol
        self.max_iter = max_iter

    def fit(self, X, y=None):
        self.low_rank_, self.sparse_, self.diagnostics_ = robust_pca(
            X, lambda_=self.lambda_, tol=self.tol, max_iter=self.max_iter
        )
        self.n_features_in_ = self.low_rank_.shape[1]
        return self

    def fit_transform(self, X, y=None):
        return self.fit(X).low_rank_


def robust_sparse_objective(X, A, B, S, alpha, ridge, kappa):
    residual = X - (X @ B) @ A.T - S
    return float(
        0.5 * np.sum(residual**2)
        + alpha * np.abs(B).sum()
        + 0.5 * ridge * np.sum(B**2)
        + kappa * np.abs(S).sum()
    )


class RobustSparsePCA(TransformerMixin, BaseEstimator):
    """Joint Huber/elastic-net robust SPCA, Erichson et al. (2020), eq. 17.

    Independent Gauss-Seidel proximal solver, not SCRAMBLE. Sparse encoder B,
    orthogonal decoder A, and additive training contamination S are jointly fit.
    Out-of-sample transform is the fitted linear encoder, not outlier removal.
    """

    low_rank = result_alias("low_rank_", "Low-rank reconstruction of the fitted data.")
    sparse = result_alias("sparse_", "Sparse contamination in the fitted data.")
    diagnostics = result_alias("diagnostics_", "Optimization convergence diagnostics.")

    def __init__(self, n_components=2, alpha=1.0, ridge=1e-3, kappa=1.0, max_iter=500, tol=1e-6):
        self.n_components = n_components
        self.alpha = alpha
        self.ridge = ridge
        self.kappa = kappa
        self.max_iter = max_iter
        self.tol = tol

    def fit(self, X, y=None):
        X = array(X, min_rows=2)
        k = integer(self.n_components, "n_components", maximum=min(X.shape))
        alpha = scalar(self.alpha, "alpha", minimum=0)
        ridge = scalar(self.ridge, "ridge", minimum=0)
        kappa = scalar(self.kappa, "kappa", minimum=0)
        if kappa == 0:
            raise ValueError("kappa must be positive")
        max_iter = integer(self.max_iter, "max_iter")
        tol = scalar(self.tol, "tol", minimum=0)
        self.n_features_in_ = X.shape[1]
        self.mean_ = X.mean(axis=0)
        X = X - self.mean_
        _, singular, Vt = np.linalg.svd(X, full_matrices=False)
        A = Vt[:k].T.copy()
        B = A.copy()
        S = np.zeros_like(X)
        norm = float(singular[0] ** 2)
        step = 1 / max(norm, 1)
        previous = robust_sparse_objective(X, A, B, S, alpha, ridge, kappa)
        history = [previous]
        converged = False
        for iteration in range(1, max_iter + 1):
            gradient = X.T @ (X @ B - (X - S) @ A)
            B = _soft(B - step * gradient, step * alpha) / (1 + step * ridge)
            U, _, Vt = np.linalg.svd((X - S).T @ (X @ B), full_matrices=False)
            A = U @ Vt
            S = _soft(X - (X @ B) @ A.T, kappa)
            objective = robust_sparse_objective(X, A, B, S, alpha, ridge, kappa)
            history.append(objective)
            if abs(previous - objective) <= tol * max(1, previous):
                converged = True
                break
            previous = objective
        self.encoder_, self.decoder_, self.sparse_ = B, A, S
        self.components_ = B.T.copy()
        self.low_rank_ = (X @ B) @ A.T + self.mean_
        self.diagnostics_ = dict(
            converged=converged, n_iter=iteration, objective_history=history, objective=history[-1]
        )
        if not converged:
            warnings.warn(
                "RobustSparsePCA reached iteration limit; inspect diagnostics",
                ConvergenceWarning,
                stacklevel=2,
            )
        return self

    def transform(self, X):
        check_is_fitted(self, "encoder_")
        X = array(X)
        if X.shape[1] != self.n_features_in_:
            raise ValueError("transform feature count differs from fit")
        return (X - self.mean_) @ self.encoder_

    def inverse_transform(self, Z):
        check_is_fitted(self, "decoder_")
        Z = array(Z, name="Z")
        if Z.shape[1] != self.n_components:
            raise ValueError("latent feature count differs from fit")
        return Z @ self.decoder_.T + self.mean_
