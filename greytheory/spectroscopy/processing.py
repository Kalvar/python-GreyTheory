"""Small adapters with explicit measurement assumptions."""

from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.decomposition import NMF, PCA
from sklearn.utils.validation import check_is_fitted

from .._validation import array, integer, scalar


@dataclass
class SpectralDecomposition:
    scores: np.ndarray
    components: np.ndarray
    reconstruction: np.ndarray
    diagnostics: dict
    model: object


def baseline_correct(spectra, *, lam=1e6, p=0.01, x=None):
    """AsLS baseline removal, explicitly opt-in; never implicit for XRF counts."""
    from pybaselines import Baseline

    X = array(spectra)
    lam = scalar(lam, "lam", minimum=0)
    p = scalar(p, "p", minimum=0, maximum=1)
    if lam == 0 or p in (0, 1):
        raise ValueError("lam must be positive and p must be in (0, 1)")
    fitter = Baseline(x_data=x, check_finite=True)
    baselines = np.vstack([fitter.asls(row, lam=lam, p=p)[0] for row in X])
    return X - baselines, baselines


def fit_nmf(X, n_components=2, *, max_iter=500, random_state=0):
    X = array(X)
    if np.any(X < 0):
        raise ValueError("NMF requires nonnegative data")
    integer(n_components, "n_components", maximum=min(X.shape))
    model = NMF(n_components, init="nndsvda", max_iter=max_iter, random_state=random_state)
    scores = model.fit_transform(X)
    return SpectralDecomposition(
        scores,
        model.components_,
        scores @ model.components_,
        dict(reconstruction_error=float(model.reconstruction_err_), n_iter=int(model.n_iter_)),
        model,
    )


def fit_mcr_als(X, initial_spectra, *, max_iter=100):
    """Nonnegative MCR-ALS with NIST pyMCR. Components require reference validation."""
    from pymcr.mcr import McrAR
    from pymcr.regressors import NNLS

    X = array(X)
    initial = array(initial_spectra, name="initial_spectra")
    if initial.shape[1] != X.shape[1] or np.any(X < 0) or np.any(initial < 0):
        raise ValueError("MCR spectra must be nonnegative with matching channel count")
    model = McrAR(
        c_regr=NNLS(),
        st_regr=NNLS(),
        max_iter=integer(max_iter, "max_iter"),
        tol_increase=None,
        tol_err_change=1e-12,
        tol_n_increase=10,
    )
    model.fit(X, ST=initial, verbose=False)
    scores, components = model.C_opt_, model.ST_opt_
    diagnostics = dict(
        mse=float(np.mean((X - scores @ components) ** 2)),
        n_iter=int(model.n_iter),
        errors=list(model.err),
        exit_flags={
            name: bool(getattr(model, name))
            for name in (
                "exit_max_iter_reached",
                "exit_tol_increase",
                "exit_tol_n_increase",
                "exit_tol_err_change",
                "exit_tol_n_above_min",
            )
        },
    )
    return SpectralDecomposition(scores, components, scores @ components, diagnostics, model)


def fit_mnf(cube, n_components=2):
    """Spectral Python MNF with noise estimated from adjacent pixel differences.

    Neighboring pixels must support the stationary-noise assumption.
    """
    import spectral

    X = array(cube, ndim=3, min_rows=2)
    if X.shape[1] < 2:
        raise ValueError("MNF needs at least two columns of pixels")
    integer(n_components, "n_components", maximum=X.shape[2])
    signal = spectral.calc_stats(X)
    noise = spectral.noise_from_diffs(X)
    if np.linalg.matrix_rank(noise.cov) < X.shape[2]:
        raise ValueError("MNF noise covariance is singular; provide more pixels or fewer bands")
    model = spectral.mnf(signal, noise)
    return model.reduce(X, num=n_components), model


class PoissonPCA(TransformerMixin, BaseEstimator):
    """Approximate Poisson-aware PCA using the Anscombe transform.

    Not an exact Poisson likelihood fit. Assumes nonnegative raw counts;
    low-count bias remains. Inverse uses the simple algebraic approximation.
    """

    def __init__(self, n_components=2):
        self.n_components = n_components

    def fit(self, X, y=None):
        X = array(X, min_rows=2)
        if np.any(X < 0):
            raise ValueError("PoissonPCA requires nonnegative counts")
        integer(self.n_components, "n_components", maximum=min(X.shape))
        self.n_features_in_ = X.shape[1]
        self.model_ = PCA(self.n_components, svd_solver="full").fit(2 * np.sqrt(X + 3 / 8))
        return self

    def transform(self, X):
        check_is_fitted(self, "model_")
        X = array(X)
        if X.shape[1] != self.n_features_in_ or np.any(X < 0):
            raise ValueError("counts must be nonnegative and match fitted channels")
        return self.model_.transform(2 * np.sqrt(X + 3 / 8))

    def inverse_transform(self, scores):
        check_is_fitted(self, "model_")
        scores = array(scores, name="scores")
        if scores.shape[1] != self.n_components:
            raise ValueError("latent dimensions differ from fit")
        stabilized = self.model_.inverse_transform(scores)
        return np.maximum(np.maximum(stabilized, 0) ** 2 / 4 - 3 / 8, 0)


def fit_mlpca(X, variances, n_components=2, *, max_iter=100, tol=1e-7):
    """Weighted low-rank ML fit for independent Gaussian errors with known variances.

    Fixed variance weights, not an exact Poisson model. For count-based variance
    estimates, users must explicitly specify how zero variances are regularized.
    """
    X = array(X, min_rows=2)
    V = array(variances, name="variances")
    if V.shape != X.shape or np.any(V <= 0):
        raise ValueError("variances must be positive and match X")
    k = integer(n_components, "n_components", maximum=min(X.shape))
    max_iter = integer(max_iter, "max_iter")
    tol = scalar(tol, "tol", minimum=0)
    U, s, H = np.linalg.svd(X, full_matrices=False)
    scores, components = U[:, :k] * s[:k], H[:k].copy()
    previous = np.inf
    history = []
    converged = False
    for iteration in range(1, max_iter + 1):
        for i in range(X.shape[0]):
            weight = 1 / np.sqrt(V[i])
            scores[i] = np.linalg.lstsq(components.T * weight[:, None], X[i] * weight, rcond=None)[0]
        for j in range(X.shape[1]):
            weight = 1 / np.sqrt(V[:, j])
            components[:, j] = np.linalg.lstsq(scores * weight[:, None], X[:, j] * weight, rcond=None)[0]
        objective = float(np.sum((X - scores @ components) ** 2 / V))
        history.append(objective)
        if np.isfinite(previous) and abs(previous - objective) <= tol * max(1, previous):
            converged = True
            break
        previous = objective
    return SpectralDecomposition(
        scores,
        components,
        scores @ components,
        dict(objective_history=history, converged=converged, n_iter=iteration),
        None,
    )


def element_lines(atomic_number, *, energy_range=(0, float("inf"))):
    """xraylib characteristic line energies/rates; no concentration inference."""
    import xraylib

    Z = integer(atomic_number, "atomic_number", maximum=98)
    lower, upper = energy_range
    if not 0 <= lower < upper:
        raise ValueError("energy_range must be increasing and nonnegative")
    result = []
    for name in ("KA1_LINE", "KA2_LINE", "KB1_LINE", "LA1_LINE", "LB1_LINE", "MA1_LINE"):
        code = getattr(xraylib, name)
        try:
            energy = xraylib.LineEnergy(Z, code)
            rate = xraylib.RadRate(Z, code)
        except ValueError:
            continue
        if lower <= energy <= upper:
            result.append(dict(line=name, energy_keV=energy, relative_rate=rate))
    return result


def fit_peaks(energy, counts, centers, *, sigma=0.05):
    """Bounded Gaussian peak amplitudes + constant background, Poisson-weighted.

    Centers/widths are fixed inputs. Detector response and matrix corrections
    are not modeled; amplitudes are not elemental concentrations.
    """
    energy = array(energy, name="energy", ndim=1)
    counts = array(counts, name="counts", ndim=1)
    centers = array(centers, name="centers", ndim=1)
    sigma = scalar(sigma, "sigma", minimum=0)
    if energy.shape != counts.shape or np.any(counts < 0) or sigma == 0 or np.any(np.diff(energy) <= 0):
        raise ValueError("require increasing energy, matching nonnegative counts and positive sigma")
    design = np.column_stack(
        (np.exp(-0.5 * ((energy[:, None] - centers) / sigma) ** 2), np.ones(energy.size))
    )
    result = least_squares(
        lambda beta: (design @ beta - counts) / np.sqrt(np.maximum(counts, 1)),
        np.ones(centers.size + 1),
        bounds=(0, np.inf),
    )
    return dict(
        amplitudes=result.x[:-1],
        background=float(result.x[-1]),
        fitted_counts=design @ result.x,
        success=bool(result.success),
    )
