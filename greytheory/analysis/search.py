"""Budgeted supervised GreyPCA search with fold-local preprocessing and caching."""

from dataclasses import dataclass
from itertools import product
from tempfile import TemporaryDirectory
from time import perf_counter
import warnings

from joblib import Memory
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin, clone
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold, KFold
from sklearn.pipeline import Pipeline

from .._validation import array, integer, scalar
from .pca import GreyPCA
from .reliability import _groups


def _fit_decomposition(estimator, X):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fitted = clone(estimator).fit(X)
    return fitted, [(str(w.message), w.category) for w in caught]


class _CachedDecomposition(TransformerMixin, BaseEstimator):
    """Cache only the unsupervised backend; GRA still fits on each training y."""

    def __init__(self, estimator, location):
        self.estimator = estimator
        self.location = location

    def fit(self, X, y=None):
        self.model_, messages = Memory(self.location, verbose=0).cache(_fit_decomposition)(self.estimator, X)
        # Cached unconverged fits must remain ineligible on every cache hit.
        for message, category in messages:
            warnings.warn(message, category, stacklevel=2)
        return self

    def transform(self, X):
        return self.model_.transform(X)

    def inverse_transform(self, X):
        return self.model_.inverse_transform(X)

    @property
    def explained_variance_ratio_(self):
        return self.model_.explained_variance_ratio_


@dataclass
class GreyPCASearchResult:
    model: Pipeline
    best_parameters: dict
    validation_rmse: float
    trials: list
    elapsed_seconds: float
    stopped_by_budget: bool

    def predict(self, X):
        return self.model.predict(X)


def _splits(X, y, cv, groups, random_state):
    codes = None if groups is None else _groups(groups, len(X))
    if isinstance(cv, (int, np.integer)) and not isinstance(cv, (bool, np.bool_)):
        folds = integer(cv, "cv", minimum=2)
        splitter = (
            GroupKFold(folds) if codes is not None else KFold(folds, shuffle=True, random_state=random_state)
        )
        splits = splitter.split(X, y, codes)
    elif hasattr(cv, "split"):
        splits = cv.split(X, y, codes)
    else:
        raise TypeError("cv must be an integer or a splitter with split()")
    result = []
    for train, valid in splits:
        train, valid = np.asarray(train), np.asarray(valid)
        for indices in (train, valid):
            if indices.ndim != 1 or indices.dtype.kind not in "iu" or not len(indices):
                raise ValueError("CV indices must be nonempty integer vectors")
            if indices.min() < 0 or indices.max() >= len(X) or len(np.unique(indices)) != len(indices):
                raise ValueError("CV indices must be unique and within X")
        if len(train) < 2 or np.intersect1d(train, valid).size:
            raise ValueError("CV needs at least two training rows and disjoint validation rows")
        if codes is not None and np.intersect1d(codes[train], codes[valid]).size:
            raise ValueError("CV must keep each group entirely in training or validation")
        result.append((train, valid))
    if len(result) < 2:
        raise ValueError("at least two validation splits are required")
    return result


def search_grey_pca(
    X,
    y,
    *,
    candidates=None,
    methods=("pca",),
    components=(1, 2, 3),
    top_k=(None,),
    rho=(0.5,),
    max_trials=12,
    cv=3,
    groups=None,
    predictor=None,
    memory=None,
    time_budget=None,
    random_state=0,
):
    """Find a low validation-RMSE regression pipeline within a finite candidate budget.

    Default: ordinary PCA with GRA (y supplied), standardization and Ridge(alpha=1).
    Pass candidates as GreyPCA keyword dictionaries for conditional backend settings.
    A seeded random subset is evaluated on identical folds. Unsupervised backend
    fits are cached across GRA settings; an optional directory persists caches.
    Backend settings and training data are part of joblib's cache key.

    Convergence warnings disqualify a trial. The budget is checked between trials,
    not inside a fit; final refitting also takes time. Validation RMSE is a tuning
    score, not an independent test estimate. Keep test data outside this function.
    No TPE, successive halving or global-optimum guarantee is implied.
    """
    X = array(X, min_rows=4)
    y = array(y, name="y", ndim=1)
    if len(X) != len(y) or np.ptp(y) == 0:
        raise ValueError("y must match X and vary")
    max_trials = integer(max_trials, "max_trials")
    if time_budget is not None:
        time_budget = scalar(time_budget, "time_budget", minimum=0)
        if time_budget == 0:
            raise ValueError("time_budget must be positive")
    splits = _splits(X, y, cv, groups, random_state)
    if candidates is None:
        candidates = [
            dict(method=m, n_components=n, top_k=k, rho=r, standardize=True)
            for m, n, k, r in product(methods, components, top_k, rho)
        ]
    else:
        candidates = [dict(c) for c in candidates]
    if not candidates:
        raise ValueError("at least one candidate is required")
    predictor = Ridge(alpha=1) if predictor is None else predictor
    if not callable(getattr(predictor, "predict", None)):
        raise TypeError("predictor must implement fit and predict")
    generator = np.random.default_rng(random_state)
    order = generator.permutation(len(candidates))[:max_trials]
    started = perf_counter()
    records, valid_trials = [], []
    stopped = False
    with TemporaryDirectory(prefix="greytheory-search-") as temporary:
        cache = Memory(temporary if memory is None else memory, verbose=0)

        def make_model(parameters):
            prototype = GreyPCA(**parameters)
            backend = prototype._make_reducer()
            options = prototype.get_params(deep=False)
            options.update(
                method="pca", method_params=None, estimator=_CachedDecomposition(backend, cache.location)
            )
            return Pipeline([("grey", GreyPCA(**options)), ("predictor", clone(predictor))])

        for index in order:
            if time_budget is not None and perf_counter() - started >= time_budget:
                stopped = True
                break
            parameters = candidates[index]
            trial_start = perf_counter()
            record = dict(parameters=parameters, fold_rmse=[], warnings=[], status="failed")
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                try:
                    for train, valid in splits:
                        pipeline = make_model(parameters).fit(X[train], y[train])
                        prediction = array(pipeline.predict(X[valid]), name="prediction", ndim=1)
                        if prediction.shape != y[valid].shape:
                            raise ValueError("predictor must return one scalar per validation row")
                        rmse = float(np.sqrt(np.mean((prediction - y[valid]) ** 2)))
                        if not np.isfinite(rmse):
                            raise ValueError("validation error overflowed; rescale the target")
                        record["fold_rmse"].append(rmse)
                    record["mean_rmse"] = float(np.mean(record["fold_rmse"]))
                    record["status"] = "ok"
                except (ValueError, TypeError, np.linalg.LinAlgError, FloatingPointError) as exc:
                    record["error"] = str(exc)
                record["warnings"] = [str(w.message) for w in caught]
                if any(issubclass(w.category, ConvergenceWarning) for w in caught):
                    record["status"] = "not_converged"
            record["seconds"] = perf_counter() - trial_start
            records.append(record)
            if record["status"] == "ok":
                valid_trials.append(record)
        if not valid_trials:
            raise ValueError(f"no valid converged trial; diagnostics: {records}")
        for best in sorted(valid_trials, key=lambda trial: trial["mean_rmse"]):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                try:
                    model = make_model(best["parameters"]).fit(X, y)
                except (ValueError, TypeError, np.linalg.LinAlgError, FloatingPointError) as exc:
                    best["refit_error"] = str(exc)
                    continue
            best["refit_warnings"] = [str(w.message) for w in caught]
            if any(issubclass(w.category, ConvergenceWarning) for w in caught):
                best["refit_error"] = "full-data fit did not converge"
                continue
            # The returned model does not depend on an ephemeral cache directory.
            model.memory = None
            return GreyPCASearchResult(
                model, dict(best["parameters"]), best["mean_rmse"], records, perf_counter() - started, stopped
            )
    raise ValueError(f"all final refits failed; diagnostics: {records}")
