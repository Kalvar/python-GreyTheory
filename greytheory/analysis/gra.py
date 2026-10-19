"""Batch-relative grey relational analysis; scores are not probabilities."""

import numpy as np

from .._validation import array, scalar


def _normalize(rows, mode):
    if mode in {"none", None}:
        return rows.copy()
    if mode in {"minmax", "min-max"}:
        offset = rows.min(axis=1, keepdims=True)
        scale = np.ptp(rows, axis=1, keepdims=True)
    elif mode in {"zscore", "z-score"}:
        offset = rows.mean(axis=1, keepdims=True)
        scale = rows.std(axis=1, keepdims=True)
    elif mode in {"initial", "mean"}:
        offset = 0
        scale = rows[:, :1] if mode == "initial" else rows.mean(axis=1, keepdims=True)
        if np.any(scale == 0):
            raise ValueError(f"{mode} normalization has a zero divisor")
    else:
        raise ValueError("normalize must be none, minmax, zscore, initial or mean")
    return (rows - offset) / np.where(scale == 0, 1, scale)


def grey_relation(
    reference, candidates, rho=0.5, normalize="none", weights=None, *, return_coefficients=False
):
    reference = array(reference, name="reference", ndim=1)
    candidates = array(candidates, name="candidates")
    if candidates.shape[1] != reference.size:
        raise ValueError("reference and candidate sequence lengths must match")
    rho = scalar(rho, "rho", minimum=0, maximum=1)
    if rho == 0:
        raise ValueError("rho must be in (0, 1]")
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            rows = _normalize(np.vstack((reference, candidates)), normalize)
            difference = np.abs(rows[1:] - rows[0])
    except FloatingPointError as exc:
        raise ValueError("GRA arithmetic overflow; rescale the inputs") from exc
    low, high = float(difference.min()), float(difference.max())
    # Ratios avoid overflow in rho*high + difference for large finite values.
    coefficients = np.ones_like(difference) if high == 0 else (low / high + rho) / (difference / high + rho)
    if weights is None:
        w = np.full(reference.size, 1 / reference.size)
    else:
        w = array(weights, name="weights", ndim=1)
        if w.shape != reference.shape or np.any(w < 0) or not np.any(w > 0):
            raise ValueError(
                "weights must be nonnegative, positive in at least one position, and match reference"
            )
        w = w / w.max()
        w = w / w.sum()
    scores = np.where(np.all(coefficients == 1, axis=1), 1.0, coefficients @ w)
    return (scores, coefficients) if return_coefficients else scores


class GreyGRA:
    def score(self, reference, candidates, *, rho=0.5, normalization="none", weights=None):
        return grey_relation(reference, candidates, rho, normalization, weights)

    def rank(self, reference, candidates, **kwargs):
        return np.argsort(-self.score(reference, candidates, **kwargs), kind="stable")
