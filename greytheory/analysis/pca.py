"""Decomposition adapters and configurable GRA component selection."""

from collections.abc import Mapping
from dataclasses import dataclass
from numbers import Real, Integral

import numpy as np

from sklearn.base import BaseEstimator, TransformerMixin, clone
from sklearn.decomposition import PCA, SparsePCA, KernelPCA
from sklearn.preprocessing import StandardScaler
from sklearn.utils.validation import check_is_fitted

from .._validation import array, integer, scalar
from .._results import result_alias
from .selection import GreyFeatureSelector


class _SparsePCAProjection(SparsePCA):
    """Keep a sample axis when upstream ridge regression squeezes one row."""

    def transform(self, X):
        scores = super().transform(X)
        return scores.reshape(len(X), -1) if scores.ndim == 1 else scores


class PCAAdapter(TransformerMixin, BaseEstimator):
    components = result_alias("components_", "Fitted principal components, when supported by the method.")
    mean = result_alias("mean_", "Training-data feature means.")
    explained_variance_ratio = result_alias("explained_variance_ratio_", "Explained variance ratios for PCA.")
    singular_values = result_alias("singular_values_", "Singular values for PCA.")

    def __init__(
        self,
        n_components=2,
        *,
        method="pca",
        standardize=False,
        random_state=0,
        alpha=1.0,
        kernel="rbf",
        gamma=None,
    ):
        self.n_components = n_components
        self.method = method
        self.standardize = standardize
        self.random_state = random_state
        self.alpha = alpha
        self.kernel = kernel
        self.gamma = gamma

    def fit(self, X, y=None):
        X = array(X, min_rows=2)
        integer(self.n_components, "n_components", maximum=min(X.shape))
        self.n_features_in_ = X.shape[1]
        self.scaler_ = StandardScaler(with_std=self.standardize).fit(X)
        data = self.scaler_.transform(X)
        if not np.any(data):
            raise ValueError("PCA requires nonzero training variance")
        if self.method == "pca":
            model = PCA(self.n_components, svd_solver="full")
        elif self.method == "sparse":
            model = _SparsePCAProjection(self.n_components, alpha=self.alpha, random_state=self.random_state)
        elif self.method == "kernel":
            model = KernelPCA(
                self.n_components,
                kernel=self.kernel,
                gamma=self.gamma,
                fit_inverse_transform=True,
                random_state=self.random_state,
            )
        else:
            raise ValueError("method must be pca, sparse or kernel")
        self.model_ = model.fit(data)
        return self

    def transform(self, X):
        check_is_fitted(self, "model_")
        X = array(X)
        if X.shape[1] != self.n_features_in_:
            raise ValueError("transform feature count differs from fit")
        return self.model_.transform(self.scaler_.transform(X))

    def inverse_transform(self, Z):
        check_is_fitted(self, "model_")
        Z = array(Z, name="Z")
        if Z.shape[1] != self.n_components:
            raise ValueError("latent feature count differs from fit")
        return self.scaler_.inverse_transform(self.model_.inverse_transform(Z))

    @property
    def components_(self):
        check_is_fitted(self, "model_")
        return self.model_.components_

    @property
    def mean_(self):
        check_is_fitted(self, "model_")
        return self.scaler_.mean_

    @property
    def explained_variance_ratio_(self):
        check_is_fitted(self, "model_")
        return self.model_.explained_variance_ratio_

    @property
    def singular_values_(self):
        check_is_fitted(self, "model_")
        return self.model_.singular_values_


class _RobustPCAProjection(TransformerMixin, BaseEstimator):
    """Fit a linear PCA projection on the PCP low-rank training matrix.

    New rows are projected directly; they are not independently PCP-cleaned.
    """

    def __init__(self, n_components=2, lambda_=None, tol=1e-7, max_iter=1000):
        self.n_components = n_components
        self.lambda_ = lambda_
        self.tol = tol
        self.max_iter = max_iter

    def fit(self, X, y=None):
        from .robust import RobustPCA

        self.decomposition_ = RobustPCA(self.lambda_, self.tol, self.max_iter).fit(X)
        if not np.any(np.ptp(self.decomposition_.low_rank, axis=0)):
            raise ValueError("PCP low-rank training data have no variance for PCA")
        self.projector_ = PCA(self.n_components, svd_solver="full").fit(self.decomposition_.low_rank)
        return self

    def transform(self, X):
        check_is_fitted(self, "projector_")
        return self.projector_.transform(X)

    def inverse_transform(self, Z):
        check_is_fitted(self, "projector_")
        return self.projector_.inverse_transform(Z)

    @property
    def explained_variance_ratio_(self):
        return self.projector_.explained_variance_ratio_

    @property
    def low_rank(self):
        return self.decomposition_.low_rank

    @property
    def sparse(self):
        return self.decomposition_.sparse

    @property
    def diagnostics(self):
        return self.decomposition_.diagnostics


@dataclass
class ReconstructionReport:
    """Measured reconstruction coverage, not an additive variance decomposition."""

    prefix_coverage: np.ndarray
    selected_coverage: float
    threshold: float
    first_prefix_at_threshold: int | None
    monotonic: bool
    space: str

    @property
    def full_coverage(self):
        return float(self.prefix_coverage[-1])


class GreyPCA(TransformerMixin, BaseEstimator):
    """Choose a decomposition and optionally select its components with GRA.

    method selects pca, sparse, kernel, robust, robust_sparse, or adv.
    method_params configures that backend; n_components belongs on GreyPCA.
    Alternatively, estimator supplies a cloneable fit/transform model and owns
    its component-count settings. The supplied instance is never fitted in place.

    Without y, no GRA is applied. With y, top_k selects how many components to
    retain (None retains all nonconstant components). By default both signs are
    compared in a shared GRA batch. Optional target alignment applies those signs
    to the output and is reversed during reconstruction. This does not make
    components physically monotone quality indicators. Output follows original
    component order, not GRA rank order. Scaling, decomposition,
    and selection use training data only. standardize=False preserves raw input
    before the backend's own preprocessing, including for custom count models.
    """

    reducer = result_alias("reducer_", "Fitted decomposition model.")
    selector = result_alias("selector_", "Fitted GRA selector, or None when no target was supplied.")
    component_scores = result_alias("component_scores_", "GRA scores for all components, or None without a target.")
    selected_components = result_alias("selected_components_", "Selected zero-based indices in output order.")
    component_directions = result_alias("component_directions_", "Reference comparison signs, or None without y.")
    component_direction_ambiguous = result_alias("component_direction_ambiguous_", "Tied comparison signs, or None without y.")
    n_components_fitted = result_alias("n_components_fit_", "Actual number of components before GRA selection.")
    explained_variance_ratio = result_alias("explained_variance_ratio_", "Explained variance ratios before selection.")

    def __init__(
        self, n_components=2, top_k=None, standardize=False, rho=0.5,
        *, method="pca", method_params=None, estimator=None, normalization="zscore",
        component_direction="either", align_to_target=False,
    ):
        self.n_components = n_components
        self.top_k = top_k
        self.standardize = standardize
        self.rho = rho
        self.method = method
        self.method_params = method_params
        self.estimator = estimator
        self.normalization = normalization
        self.component_direction = component_direction
        self.align_to_target = align_to_target

    def _make_reducer(self):
        if self.estimator is not None:
            if self.method != "pca" or self.method_params is not None:
                raise ValueError("use either method/method_params or estimator, not both")
            if not all(callable(getattr(self.estimator, name, None)) for name in ("fit", "transform")):
                raise TypeError("estimator must implement fit and transform; use method='robust' for PCP")
            model = clone(self.estimator)
            if model is self.estimator:
                raise TypeError("estimator must clone to an independent trainable model")
            return model

        parameters = {} if self.method_params is None else self.method_params
        if not isinstance(parameters, Mapping):
            raise TypeError("method_params must be a mapping of backend parameter names to values")
        if "n_components" in parameters:
            raise ValueError("set n_components on GreyPCA, not inside method_params")
        fractional = isinstance(self.n_components, Real) and not isinstance(self.n_components, Integral)
        if fractional:
            if self.method != "pca" or not 0 < self.n_components < 1:
                raise ValueError("fractional n_components requires method='pca' and a threshold strictly between 0 and 1")
            count = float(self.n_components)
        else:
            count = integer(self.n_components, "n_components")
        if self.method == "pca":
            model = PCA(count, svd_solver="full")
        elif self.method == "sparse":
            model = _SparsePCAProjection(count, random_state=0)
        elif self.method == "kernel":
            model = KernelPCA(count, kernel="rbf", fit_inverse_transform=True, random_state=0)
        elif self.method == "robust":
            model = _RobustPCAProjection(count)
        elif self.method == "robust_sparse":
            from .robust import RobustSparsePCA

            model = RobustSparsePCA(count)
        elif self.method in {"adv", "adversarial"}:
            from .adversarial import AdvPCA

            model = AdvPCA(count)
        else:
            raise ValueError("method must be pca, sparse, kernel, robust, robust_sparse, or adv")
        return clone(model.set_params(**dict(parameters)))

    def fit(self, X, y=None):
        X = array(X, min_rows=2)
        if not np.any(np.ptp(X, axis=0)):
            raise ValueError("GreyPCA requires nonzero training variance")
        if self.component_direction not in {"positive", "either"}:
            raise ValueError("component_direction must be positive or either")
        if not isinstance(self.align_to_target, (bool, np.bool_)):
            raise TypeError("align_to_target must be a boolean")
        if self.align_to_target and y is None:
            raise ValueError("align_to_target requires a supervised target y")
        if self.align_to_target and self.component_direction != "either":
            raise ValueError("align_to_target requires component_direction='either'")
        if self.align_to_target and self.normalization in {"initial", "mean"}:
            raise ValueError("target alignment requires none, minmax, or zscore normalization; initial/mean erase signs")
        if self.top_k is not None:
            integer(self.top_k, "top_k")
            if y is None:
                raise ValueError("top_k requires a supervised target y")
        if y is not None:
            y = array(y, name="y", ndim=1, min_rows=2)
            if y.size != X.shape[0]:
                raise ValueError("X and y must have the same observation count")
            if np.ptp(y) == 0:
                raise ValueError("a constant target cannot rank supervised components")
        reducer = self._make_reducer()
        scaler = StandardScaler(with_mean=self.standardize, with_std=self.standardize).fit(X)
        data = scaler.transform(X)
        # Some backends support copy=False and may modify their fitting input.
        reducer.fit(data.copy())
        scores = array(reducer.transform(data), name="component scores", min_rows=X.shape[0])
        if scores.shape[0] != X.shape[0]:
            raise ValueError("estimator must return one component-score row per observation")
        selector = None
        selected = np.arange(scores.shape[1])
        component_scores = None
        component_directions = None
        component_direction_ambiguous = None
        alignment = np.ones(scores.shape[1])
        if y is not None:
            selector = GreyFeatureSelector(
                self.top_k, self.rho, self.normalization,
                direction=self.component_direction, constant_policy="exclude",
            ).fit(scores, y)
            selected = selector.get_support(indices=True)
            component_scores = selector.scores_.copy()
            component_directions = selector.directions_.copy()
            component_direction_ambiguous = selector.direction_ambiguous_.copy()
            if self.align_to_target:
                if np.any(component_direction_ambiguous[selected]):
                    raise ValueError("reference gives tied component directions; keep align_to_target=False or use a more informative reference")
                alignment = component_directions.copy()

        # Publish a complete fit only after preprocessing, reduction, and GRA succeed.
        self.scaler_ = scaler
        self.reducer_ = reducer
        self.pca_ = reducer  # Compatibility with the earlier PCA-only pipeline.
        self.selector_ = selector
        self.selected_components_ = selected
        self.component_scores_ = component_scores
        self.component_directions_ = component_directions
        self.component_direction_ambiguous_ = component_direction_ambiguous
        self.alignment_ = alignment
        self.n_components_fit_ = scores.shape[1]
        self.n_features_in_ = X.shape[1]
        return self

    def transform(self, X):
        check_is_fitted(self, "reducer_")
        X = array(X)
        if X.shape[1] != self.n_features_in_:
            raise ValueError("transform feature count differs from fit")
        scores = array(self.reducer_.transform(self.scaler_.transform(X)), name="component scores")
        if scores.shape != (X.shape[0], self.n_components_fit_):
            raise ValueError("estimator component-score shape differs from fit")
        return scores[:, self.selected_components_] * self.alignment_[self.selected_components_]

    def inverse_transform(self, Z):
        """Reconstruct data when supported, filling unselected components with zeros."""
        check_is_fitted(self, "reducer_")
        Z = array(Z, name="Z")
        if Z.shape[1] != self.selected_components_.size:
            raise ValueError("latent feature count differs from selected component count")
        inverse = getattr(self.reducer_, "inverse_transform", None)
        if not callable(inverse):
            raise NotImplementedError("the selected estimator does not provide inverse_transform")
        scores = np.zeros((Z.shape[0], self.n_components_fit_))
        scores[:, self.selected_components_] = Z * self.alignment_[self.selected_components_]
        reconstructed = array(inverse(scores), name="reconstruction")
        if reconstructed.shape != (Z.shape[0], self.n_features_in_):
            raise ValueError("estimator reconstruction shape differs from fit")
        return self.scaler_.inverse_transform(reconstructed)

    def reconstruction_report(self, X, *, threshold=0.85):
        """Evaluate all prefixes and the GRA-selected set in the fitted input space.

        Coverage is 1 - squared reconstruction error / centered sum of squares.
        It can be negative or nonmonotone for non-PCA models. A prefix uses one
        fitted model with later scores zeroed; refitting fewer components may
        produce a different result. No model is refitted here.
        """
        check_is_fitted(self, "reducer_")
        threshold = scalar(threshold, "threshold", minimum=0, maximum=1)
        if threshold == 0:
            raise ValueError("threshold must be in (0, 1]")
        values = array(X, min_rows=2)
        if values.shape[1] != self.n_features_in_:
            raise ValueError("feature count differs from fit")
        inverse = getattr(self.reducer_, "inverse_transform", None)
        if not callable(inverse):
            raise NotImplementedError("the selected estimator does not provide inverse_transform")
        data = self.scaler_.transform(values)
        scores = array(self.reducer_.transform(data.copy()), name="component scores")
        if scores.shape != (len(data), self.n_components_fit_):
            raise ValueError("estimator component-score shape differs from fit")
        total = float(np.sum((data - data.mean(axis=0)) ** 2))
        if not np.isfinite(total) or total == 0:
            raise ValueError("reconstruction coverage requires finite, nonzero evaluation variance")

        def coverage(latent):
            reconstructed = array(inverse(latent.copy()), name="reconstruction")
            if reconstructed.shape != data.shape:
                raise ValueError("estimator reconstruction shape differs from input")
            error = float(np.sum((data - reconstructed) ** 2))
            if not np.isfinite(error):
                raise ValueError("reconstruction error overflow; rescale the inputs")
            return 1 - error / total

        prefix = []
        latent = np.zeros_like(scores)
        for j in range(scores.shape[1]):
            latent[:, j] = scores[:, j]
            prefix.append(coverage(latent))
        latent.fill(0)
        latent[:, self.selected_components_] = scores[:, self.selected_components_]
        prefix = np.asarray(prefix)
        reached = np.flatnonzero(prefix >= threshold)
        return ReconstructionReport(
            prefix, coverage(latent), threshold,
            int(reached[0] + 1) if reached.size else None,
            bool(np.all(np.diff(prefix) >= -1e-12)),
            "standardized" if self.scaler_.with_std else "input",
        )

    @property
    def explained_variance_ratio_(self):
        check_is_fitted(self, "reducer_")
        if not hasattr(self.reducer_, "explained_variance_ratio_"):
            raise AttributeError("the selected estimator does not provide explained variance ratios")
        return self.reducer_.explained_variance_ratio_
