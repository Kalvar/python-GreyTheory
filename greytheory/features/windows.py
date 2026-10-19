"""Fixed-size local descriptors using the existing GM discrete equation."""

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_is_fitted

from .._validation import array, integer, scalar
from .._results import result_alias
from ..packages.libs.grey_lib import GreyLib
from ..packages.libs.grey_math import GreyMath


class GreyWindowFeatures(TransformerMixin, BaseEstimator):
    """Convert a batch of numerical sequences to a fixed-width feature matrix.

    X is (samples, points) or (samples, points, channels). Fit records schema
    only; every descriptor is computed independently from its own sample.
    Each complete window supplies amplitude, channel mean/std, mean per-index change,
    GM coefficients, discrete-equation RMSE, full-rank coverage, and GM coverage.
    No time/energy extrapolation or second-level forecast is performed.

    boundary_channel marks segment starts with 1 and other points with 0. It is
    excluded from modeled channels. GM equations and differences never bridge
    segment boundaries. Fragments shorter than three points have zero GM
    coverage and contribute no coefficients; low-rank fits have zero full-rank
    coverage. Coefficients alone are not reliable when coverage is low.
    """

    windows = result_alias("windows_", "Half-open (start, stop) index pairs.")
    channel_indices = result_alias("channel_indices_", "Modeled input channel indices.")

    _STATISTICS = (
        "amplitude",
        "mean",
        "std",
        "mean_change",
        "gm_a",
        "gm_b",
        "gm_equation_rmse",
        "gm_full_rank_coverage",
        "gm_coverage",
    )

    def __init__(
        self, window_size=8, stride=4, *, normalize=True, alpha=0.5, ridge_alpha=1e-6, boundary_channel=None
    ):
        self.window_size = window_size
        self.stride = stride
        self.normalize = normalize
        self.alpha = alpha
        self.ridge_alpha = ridge_alpha
        self.boundary_channel = boundary_channel

    @staticmethod
    def _batch(X):
        raw = np.asarray(X)
        if raw.ndim == 2:
            raw = raw[:, :, None]
        return array(raw, ndim=3)

    def _settings(self, X):
        width = integer(self.window_size, "window_size", minimum=3, maximum=X.shape[1])
        step = integer(self.stride, "stride", maximum=width)
        scalar(self.alpha, "alpha", minimum=0, maximum=1)
        scalar(self.ridge_alpha, "ridge_alpha", minimum=0)
        if not isinstance(self.normalize, (bool, np.bool_)):
            raise TypeError("normalize must be boolean")
        boundary = self.boundary_channel
        if boundary is not None:
            if isinstance(boundary, (bool, np.bool_)) or not isinstance(boundary, (int, np.integer)):
                raise TypeError("boundary_channel must be an integer or None")
            if not -X.shape[2] <= boundary < X.shape[2]:
                raise ValueError("boundary_channel is outside the channel axis")
            boundary %= X.shape[2]
            if not np.isin(X[:, :, boundary], [0, 1]).all():
                raise ValueError("boundary channel must contain only 0 or 1")
        channels = [i for i in range(X.shape[2]) if i != boundary]
        if not channels:
            raise ValueError("need at least one non-boundary channel")
        starts = list(range(0, X.shape[1] - width + 1, step))
        if starts[-1] != X.shape[1] - width:
            starts.append(X.shape[1] - width)
        return [(start, start + width) for start in starts], channels, boundary

    def fit(self, X, y=None):
        X = self._batch(X)
        windows, channels, boundary = self._settings(X)
        self.sample_shape_ = X.shape[1:]
        self.windows_ = tuple(windows)
        self.channel_indices_ = tuple(channels)
        self.boundary_index_ = boundary
        self.settings_ = (
            self.window_size,
            self.stride,
            self.normalize,
            self.alpha,
            self.ridge_alpha,
            self.boundary_channel,
        )
        self.feature_names_ = np.array(
            [
                f"window_{start}_{stop}.channel_{channel}.{stat}"
                for start, stop in windows
                for channel in channels
                for stat in self._STATISTICS
            ]
            + [f"window_{start}_{stop}.segment_count" for start, stop in windows],
            dtype=object,
        )
        return self

    def transform(self, X):
        check_is_fitted(self, "sample_shape_")
        X = self._batch(X)
        if (
            self.window_size,
            self.stride,
            self.normalize,
            self.alpha,
            self.ridge_alpha,
            self.boundary_channel,
        ) != self.settings_:
            raise ValueError("window settings changed; fit again")
        windows, channels, boundary = self._settings(X)
        if X.shape[1:] != self.sample_shape_:
            raise ValueError("sequence point/channel shape differs from fit; resample trajectories first")
        if (
            tuple(windows) != self.windows_
            or tuple(channels) != self.channel_indices_
            or boundary != self.boundary_index_
        ):
            raise ValueError("window settings changed; fit again")
        background = GreyLib(self.alpha, "corrected")
        solver = GreyMath()
        results = []
        try:
            with np.errstate(over="raise", invalid="raise", divide="raise"):
                for sample in X:
                    descriptors, segment_counts = [], []
                    for start, stop in self.windows_:
                        window = sample[start:stop]
                        starts = (
                            np.array([0], dtype=int)
                            if boundary is None
                            else np.unique(np.r_[0, np.flatnonzero(window[:, boundary])])
                        )
                        bounds = list(zip(starts, np.r_[starts[1:], len(window)]))
                        segment_counts.append(len(bounds))
                        for channel in channels:
                            values = window[:, channel]
                            amplitude = float(np.max(np.abs(values)))
                            scale = max(amplitude, np.finfo(float).tiny) if self.normalize else 1.0
                            values = values / scale
                            changes = [
                                np.diff(values[left:right]) for left, right in bounds if right - left >= 2
                            ]
                            mean_change = float(np.mean(np.concatenate(changes))) if changes else 0.0
                            gm = np.zeros(5)
                            for left, right in bounds:
                                part = values[left:right]
                                if len(part) < 3:
                                    continue
                                _, z = background.accumulate([part])
                                design = np.column_stack((-z, np.ones(len(z))))
                                coefficients, diagnostic = solver.solve_equations(
                                    design,
                                    part[1:],
                                    ridge_alpha=self.ridge_alpha,
                                    rank_policy="allow",
                                    penalty_weights=[1, 0],
                                    return_diagnostics=True,
                                )
                                residual = part[1:] - design @ coefficients
                                gm += (
                                    len(part)
                                    / len(values)
                                    * np.r_[
                                        coefficients,
                                        np.sqrt(np.mean(residual**2)),
                                        float(diagnostic["rank"] == 2),
                                        1.0,
                                    ]
                                )
                            # Coefficients/RMSE are averages over modeled points; coverage stays explicit.
                            if gm[-1] > 0:
                                gm[:3] /= gm[-1]
                            descriptors.extend(
                                [amplitude, float(values.mean()), float(values.std()), mean_change, *gm]
                            )
                    results.append(descriptors + segment_counts)
        except FloatingPointError as error:
            raise ValueError("window arithmetic overflow; rescale inputs or use normalize=True") from error
        output = np.asarray(results)
        if not np.isfinite(output).all():
            raise ValueError("nonfinite window descriptor; rescale inputs")
        return output

    def get_feature_names_out(self, input_features=None):
        check_is_fitted(self, "feature_names_")
        return self.feature_names_.copy()
