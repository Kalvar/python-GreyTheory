"""Resampling diagnostics and calibration of externally computed difference scores."""

from dataclasses import dataclass
import math

import numpy as np
from scipy.stats import rankdata
from sklearn.base import BaseEstimator
from sklearn.utils.validation import check_is_fitted

from .._validation import array, integer, scalar
from .selection import GreyFeatureSelector


@dataclass
class RankingStability:
    selection_frequency: np.ndarray
    mean_rank: np.ndarray
    rank_std: np.ndarray
    ranking: np.ndarray
    successful_repeats: int
    skipped_repeats: int
    sample_fraction: float


def _groups(groups, n):
    labels = np.asarray(groups)
    if labels.ndim != 1 or labels.size != n:
        raise ValueError("groups must have one nonmissing label per row")
    # String conversion would silently merge mixed-type identifiers.
    if any(v is None or (isinstance(v, (float, np.floating)) and np.isnan(v)) for v in labels):
        raise ValueError("groups must not contain missing labels")
    try:
        _, codes = np.unique(labels, return_inverse=True)
    except TypeError as exc:
        raise ValueError("group labels must have comparable types") from exc
    return codes


def ranking_stability(
    X,
    y,
    *,
    k=5,
    repeats=100,
    fraction=0.8,
    groups=None,
    rho=0.5,
    normalization="zscore",
    direction="either",
    random_state=0,
):
    """Subsample rows or entire groups without replacement, then repeat GRA.

    Frequencies use successful repeats only; degenerate repeats are reported.
    Tied scores share their average rank and split top-k membership fractionally.
    Constant columns are assigned last-place tied ranks and zero membership.
    This is a sensitivity diagnostic, not a causal or authorship probability.
    """
    X = array(X, min_rows=3)
    y = array(y, name="y", ndim=1)
    if y.size != len(X) or np.ptp(y) == 0:
        raise ValueError("y must match X and vary")
    k = integer(k, "k", maximum=X.shape[1])
    repeats = integer(repeats, "repeats")
    fraction = scalar(fraction, "fraction", minimum=0, maximum=1)
    if not 0 < fraction < 1:
        raise ValueError("fraction must be strictly between zero and one")
    # Validate selector settings even if every resample is degenerate.
    GreyFeatureSelector(None, rho, normalization, direction=direction, constant_policy="exclude").fit(X, y)
    codes = np.arange(len(X)) if groups is None else _groups(groups, len(X))
    units = np.unique(codes)
    if len(units) < 3:
        raise ValueError("at least three independent rows or groups are required")
    count = max(2, min(len(units) - 1, math.ceil(fraction * len(units))))
    generator = np.random.default_rng(random_state)
    ranks, memberships = [], []
    for _ in range(repeats):
        indices = np.flatnonzero(np.isin(codes, generator.choice(units, count, replace=False)))
        eligible = np.any(X[indices] != X[indices[0]], axis=0)
        if np.ptp(y[indices]) == 0 or not eligible.any():
            continue
        model = GreyFeatureSelector(
            None, rho, normalization, direction=direction, constant_policy="exclude"
        ).fit(X[indices], y[indices])
        values = model.scores_[eligible]
        rank = np.full(X.shape[1], (int(eligible.sum()) + 1 + X.shape[1]) / 2)
        rank[eligible] = rankdata(-values, method="average")
        membership = np.zeros(X.shape[1])
        for score in np.unique(values):
            tied = eligible & (model.scores_ == score)
            above = np.count_nonzero(values > score)
            membership[tied] = np.clip((k - above) / tied.sum(), 0, 1)
        ranks.append(rank)
        memberships.append(membership)
    if not ranks:
        raise ValueError("all resamples were degenerate; add independent samples or vary the target")
    mean = np.mean(ranks, axis=0)
    return RankingStability(
        np.mean(memberships, axis=0),
        mean,
        np.std(ranks, axis=0),
        np.argsort(mean, kind="stable"),
        len(ranks),
        repeats - len(ranks),
        fraction,
    )


class DifferenceCalibrator(BaseEstimator):
    """One-sided split-conformal threshold for larger-is-more-unusual scores.

    Fit on independent normal calibration scores from a previously frozen model.
    Marginal false-alarm control requires exchangeable normal calibration/test
    scores; it is not a per-batch, spatial, or distribution-shift guarantee.
    A small calibration set may produce an infinite threshold (no flags).
    """

    def __init__(self, false_alarm_rate=0.05):
        self.false_alarm_rate = false_alarm_rate

    def fit(self, normal_scores):
        scores = array(normal_scores, name="normal_scores", ndim=1)
        alpha = scalar(self.false_alarm_rate, "false_alarm_rate", minimum=0, maximum=1)
        if not 0 < alpha < 1:
            raise ValueError("false_alarm_rate must lie strictly between zero and one")
        order = math.ceil((len(scores) + 1) * (1 - alpha))
        threshold = float(np.sort(scores)[order - 1]) if order <= len(scores) else float("inf")
        self.threshold = threshold
        self.calibration_size = len(scores)
        self.resolution = 1 / (len(scores) + 1)
        return self

    def predict(self, scores):
        check_is_fitted(self, "threshold")
        return array(scores, name="scores", ndim=1) > self.threshold


def reconstruction_scores(model, X):
    """Per-row standardized residual MSE using a fitted GreyPCA's training scaler.

    Scores express reconstruction novelty, not proof of a paired image change.
    """
    check_is_fitted(model, "scaler_")
    X = array(X)
    reconstructed = model.inverse_transform(model.transform(X))
    residual = model.scaler_.transform(X) - model.scaler_.transform(reconstructed)
    return np.mean(residual**2, axis=1)
