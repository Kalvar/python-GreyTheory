"""Normalize quality responses and compare them with a fixed ideal sequence.

These scores express a declared engineering preference, not process capability,
yield, or evidence that a part passes specifications.
"""

from dataclasses import dataclass

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_is_fitted

from .._results import result_alias
from .._validation import array, scalar


class BenefitNormalizer(TransformerMixin, BaseEstimator):
    """Map larger/smaller/target responses to benefits in [0, 1].

    Fit bounds on training rows, or supply per-column (lower, upper) bounds.
    New rows reuse those bounds. Out-of-range values raise unless clipping was
    explicitly selected. A target response uses a piecewise linear peak at its
    target; bounds are normalization limits, not automatic acceptance criteria.
    """

    fitted_bounds = result_alias("bounds_", "Fitted lower/upper normalization bounds.")

    def __init__(self, directions, *, targets=None, bounds=None, out_of_range="raise"):
        self.directions = directions
        self.targets = targets
        self.bounds = bounds
        self.out_of_range = out_of_range

    def fit(self, X, y=None):
        names = getattr(X, "columns", None)
        values = array(X)
        if isinstance(self.directions, str):
            raise ValueError("directions must provide one larger, smaller, or target entry per column")
        directions = tuple(self.directions)
        if len(directions) != values.shape[1] or any(d not in {"larger", "smaller", "target"} for d in directions):
            raise ValueError("directions must match columns and contain only larger, smaller, or target")
        if self.out_of_range not in {"raise", "clip"}:
            raise ValueError("out_of_range must be raise or clip")
        if self.bounds is None:
            bounds = np.column_stack((values.min(axis=0), values.max(axis=0)))
        else:
            bounds = array(self.bounds, name="bounds")
            if bounds.shape != (values.shape[1], 2):
                raise ValueError("bounds must contain one (lower, upper) pair per column")
        if np.any(bounds[:, 1] <= bounds[:, 0]):
            raise ValueError("bounds need upper > lower; constant columns require explicit engineering bounds")
        raw_targets = [None] * values.shape[1] if self.targets is None else list(self.targets)
        if len(raw_targets) != values.shape[1]:
            raise ValueError("targets must match the number of columns")
        targets = np.full(values.shape[1], np.nan)
        for i, direction in enumerate(directions):
            if direction == "target":
                if raw_targets[i] is None:
                    raise ValueError("target-direction columns require a numeric target value")
                targets[i] = scalar(raw_targets[i], f"targets[{i}]")
                if not bounds[i, 0] < targets[i] < bounds[i, 1]:
                    raise ValueError("each target must lie strictly inside its normalization bounds")
            elif raw_targets[i] is not None:
                raise ValueError("only target-direction columns accept a target value")
        schema = None if names is None else tuple(names)
        if schema is not None and len(set(schema)) != len(schema):
            raise ValueError("quality column names must be unique")
        # Validate arithmetic and ranges before publishing fitted state.
        self._normalize(values, bounds, directions, targets, self.out_of_range)
        self.bounds_ = bounds.copy()
        self.directions_ = directions
        self.targets_ = targets
        self.out_of_range_ = self.out_of_range
        self.column_names_ = schema
        self.n_features_in_ = values.shape[1]
        return self

    @staticmethod
    def _normalize(values, bounds, directions, targets, out_of_range):
        outside = (values < bounds[:, 0]) | (values > bounds[:, 1])
        if np.any(outside) and out_of_range == "raise":
            raise ValueError("quality values lie outside fitted bounds; use out_of_range='clip' to saturate explicitly")
        values = np.clip(values, bounds[:, 0], bounds[:, 1])
        try:
            with np.errstate(over="raise", invalid="raise", divide="raise"):
                result = (values - bounds[:, 0]) / (bounds[:, 1] - bounds[:, 0])
                for i, direction in enumerate(directions):
                    if direction == "smaller":
                        result[:, i] = 1 - result[:, i]
                    elif direction == "target":
                        target = targets[i]
                        result[:, i] = np.where(
                            values[:, i] <= target,
                            (values[:, i] - bounds[i, 0]) / (target - bounds[i, 0]),
                            (bounds[i, 1] - values[:, i]) / (bounds[i, 1] - target),
                        )
        except FloatingPointError as exc:
            raise ValueError("normalization arithmetic overflow; rescale quality values and bounds") from exc
        return np.clip(result, 0, 1)

    def _values(self, X):
        check_is_fitted(self, "bounds_")
        names = getattr(X, "columns", None)
        if self.column_names_ is not None and (names is None or tuple(names) != self.column_names_):
            raise ValueError("quality column names and order must match fit")
        values = array(X)
        if values.shape[1] != self.n_features_in_:
            raise ValueError("quality column count must match fit")
        return values

    def transform(self, X):
        return self._normalize(
            self._values(X), self.bounds_, self.directions_, self.targets_, self.out_of_range_
        )

    def out_of_bounds(self, X):
        """Return a per-cell mask, including violations hidden by explicit clipping."""
        values = self._values(X)
        return (values < self.bounds_[:, 0]) | (values > self.bounds_[:, 1])


@dataclass
class QualityRanking:
    normalized_values: np.ndarray
    coefficients: np.ndarray
    scores: np.ndarray
    ranking: np.ndarray
    weights: np.ndarray
    rho: float = 0.5
    normalizer: BenefitNormalizer | None = None


def grade_quality(benefits, *, weights=None, rho=0.5):
    """GRA grades of benefit rows against all ones, with fixed differences 0..1.

    Coefficients are rho / (1 - benefit + rho). Fixed extrema keep a row's grade
    independent of the other rows being scored. Larger grades mean closer to the
    declared ideal; a weighted mean can compensate one weak response with others.
    """
    values = array(benefits, name="benefits")
    if np.any((values < 0) | (values > 1)):
        raise ValueError("benefits must lie in [0, 1]; normalize quality responses first")
    rho = scalar(rho, "rho", minimum=0, maximum=1)
    if rho == 0:
        raise ValueError("rho must be in (0, 1]")
    if weights is None:
        weights = np.full(values.shape[1], 1 / values.shape[1])
    else:
        weights = array(weights, name="weights", ndim=1)
        if weights.size != values.shape[1] or np.any(weights < 0) or not np.any(weights > 0):
            raise ValueError("weights must match quality columns, be nonnegative, and have a positive entry")
        weights = weights / weights.max()
        weights = weights / weights.sum()
    coefficients = rho / (1 - values + rho)
    scores = coefficients @ weights
    return QualityRanking(
        values.copy(), coefficients, scores, np.argsort(-scores, kind="stable"), weights.copy(), rho=rho
    )


def rank_quality(values, directions, *, bounds=None, targets=None, weights=None, rho=0.5, out_of_range="raise"):
    """Normalize raw responses and return GRA grades, ranks, and the fitted normalizer."""
    normalizer = BenefitNormalizer(directions, bounds=bounds, targets=targets, out_of_range=out_of_range)
    result = grade_quality(normalizer.fit_transform(values), weights=weights, rho=rho)
    result.normalizer = normalizer
    return result
