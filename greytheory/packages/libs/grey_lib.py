"""Accumulation and explicitly selected background interpolation."""

import numpy as np

from ..._validation import array, scalar


class GreyLib:
    def __init__(self, alpha=0.5, background_mode="legacy"):
        self._background_mode = "legacy"
        self.alpha = alpha
        self.background_mode = background_mode

    @property
    def alpha(self):
        return self._alpha

    @alpha.setter
    def alpha(self, value):
        self._alpha = scalar(value, "alpha", minimum=0, maximum=1)

    @property
    def background_mode(self):
        return self._background_mode

    @background_mode.setter
    def background_mode(self, value):
        if value not in {"legacy", "corrected", "standard"}:
            raise ValueError("background_mode must be legacy or corrected")
        self._background_mode = "corrected" if value == "standard" else value

    def background(self, accumulated):
        values = array(accumulated, name="accumulated", ndim=1, min_rows=2)
        previous_weight = self.alpha if self.background_mode == "legacy" else 1 - self.alpha
        return self.alpha * values[1:] + previous_weight * values[:-1]

    def accumulate(self, patterns):
        values = array(patterns, name="patterns")
        if values.shape[1] < 2:
            raise ValueError("AGO background requires at least two observations")
        with np.errstate(over="raise", invalid="raise"):
            accumulated = np.cumsum(values, axis=1)
            background = self.background(accumulated[0])
        return accumulated, background

    def ago(self, patterns):
        accumulated, background = self.accumulate(patterns)
        return accumulated.tolist(), background.tolist()
