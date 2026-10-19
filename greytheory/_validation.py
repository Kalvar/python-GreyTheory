"""Shared finite-real array and scalar validation."""

from numbers import Integral, Real

import numpy as np


def array(value, *, name="X", ndim=2, min_rows=1):
    raw = np.asarray(value)
    if raw.dtype.kind not in "iuf":
        raise TypeError(f"{name} must contain real numbers")
    out = np.asarray(raw, dtype=np.float64)
    if out.ndim != ndim or not out.size or out.shape[0] < min_rows:
        raise ValueError(f"{name} must be nonempty {ndim}D data with >= {min_rows} rows")
    if not np.isfinite(out).all():
        raise ValueError(f"{name} must contain only finite values")
    return out


def integer(value, name, minimum=1, maximum=None):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral):
        raise TypeError(f"{name} must be an integer")
    if value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f"{name} must be in [{minimum}, {maximum or 'infinity'}]")
    return int(value)


def scalar(value, name, minimum=None, maximum=None):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number")
    value = float(value)
    if (
        not np.isfinite(value)
        or (minimum is not None and value < minimum)
        or (maximum is not None and value > maximum)
    ):
        raise ValueError(f"{name} must be finite and in [{minimum}, {maximum}]")
    return value
