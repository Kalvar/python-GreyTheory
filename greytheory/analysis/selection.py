import numpy as np
from sklearn.base import BaseEstimator
from sklearn.feature_selection import SelectorMixin
from sklearn.utils.validation import check_is_fitted

from .._validation import array, integer
from .._results import result_alias
from .gra import grey_relation


class GreyFeatureSelector(SelectorMixin, BaseEstimator):
    """Training-only GRA ranking; either direction compares both signs in one batch."""

    scores = result_alias("scores_", "GRA scores; excluded constant columns have NaN scores.")
    directions = result_alias("directions_", "Preferred comparison signs; excluded columns use zero.")
    direction_ambiguous = result_alias("direction_ambiguous_", "Whether both comparison signs have tied grades.")

    def __init__(self, k=10, rho=0.5, normalization="zscore", *, direction="positive", constant_policy="keep"):
        self.k = k
        self.rho = rho
        self.normalization = normalization
        self.direction = direction
        self.constant_policy = constant_policy

    def fit(self, X, y):
        names = getattr(X, "columns", None)
        X = array(X)
        y = array(y, name="y", ndim=1)
        if X.shape[0] != y.size or y.size < 2:
            raise ValueError("X and y require matching rows and at least two samples")
        if np.ptp(y) == 0:
            raise ValueError("a constant target cannot rank supervised features")
        if self.direction not in {"positive", "either"}:
            raise ValueError("direction must be positive or either")
        if self.constant_policy not in {"keep", "exclude"}:
            raise ValueError("constant_policy must be keep or exclude")
        eligible = np.ones(X.shape[1], dtype=bool)
        if self.constant_policy == "exclude":
            eligible = np.any(X != X[0], axis=0)
        count = int(eligible.sum())
        if not count:
            raise ValueError("no nonconstant candidates remain for GRA")
        k = count if self.k is None else integer(self.k, "k", maximum=count)
        candidates = X[:, eligible].T
        directions = np.zeros(X.shape[1], dtype=int)
        ambiguous = np.zeros(X.shape[1], dtype=bool)
        if self.direction == "either":
            # Shared extrema across both signs make the grades invariant to a
            # component sign flip. Separate GRA calls would change the extrema.
            grades = grey_relation(y, np.vstack((candidates, -candidates)), self.rho, self.normalization)
            positive, negative = grades[:count], grades[count:]
            best = np.maximum(positive, negative)
            directions[eligible] = np.where(negative > positive, -1, 1)
            ambiguous[eligible] = np.isclose(positive, negative, rtol=1e-12, atol=1e-14)
        else:
            best = grey_relation(y, candidates, self.rho, self.normalization)
            directions[eligible] = 1
        scores = np.full(X.shape[1], np.nan)
        scores[eligible] = best
        indices = np.flatnonzero(eligible)
        selected = indices[np.argsort(-best, kind="stable")[:k]]
        self.n_features_in_ = X.shape[1]
        self.scores_ = scores
        self.directions_ = directions
        self.direction_ambiguous_ = ambiguous
        self.selected_indices_ = selected
        self.support_ = np.zeros(X.shape[1], dtype=bool)
        self.support_[self.selected_indices_] = True
        if names is not None:
            self.feature_names_in_ = np.asarray(names, dtype=object)
        else:
            self.__dict__.pop("feature_names_in_", None)
        return self

    def _get_support_mask(self):
        check_is_fitted(self, "support_")
        return self.support_

    def transform(self, X):
        check_is_fitted(self, "support_")
        X = array(X)
        if X.shape[1] != self.n_features_in_:
            raise ValueError("transform feature count differs from fit")
        # As with sklearn selectors, output retains original column order.
        return X[:, self.support_]
