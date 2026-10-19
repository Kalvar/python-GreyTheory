"""Local image summaries from arrays, without pretrained models or image I/O."""

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_is_fitted

from .._validation import array, integer
from .._results import result_alias


class ImagePatchFeatures(TransformerMixin, BaseEstimator):
    """Describe a fixed grid of patches, preserving channels and grid positions.

    Input: (samples, height, width) or (samples, height, width, channels).
    Output: (samples, grid_rows*grid_columns, 4*channels+1). For each channel,
    retain mean, std and mean absolute horizontal/vertical pixel differences.
    The last channel marks row starts; use boundary_channel=-1 for Grey windows
    to avoid modeling an artificial transition across patch-grid rows.
    This is a simple intensity/edge baseline, not handwriting recognition.
    """

    patch_bounds = result_alias("patch_bounds_", "Half-open (y0, x0, y1, x1) patch bounds.")
    boundary_channel = result_alias("boundary_channel_", "Output row-start channel index.")

    def __init__(self, grid_shape=(4, 4)):
        self.grid_shape = grid_shape

    @staticmethod
    def _images(X):
        raw = np.asarray(X)
        if raw.dtype.kind == "b":
            raw = raw.astype(float)
        if raw.ndim == 3:
            raw = raw[:, :, :, None]
        data = array(raw, name="images", ndim=4)
        if min(data.shape[1:]) < 1:
            raise ValueError("image axes must be nonempty")
        return data

    def fit(self, X, y=None):
        X = self._images(X)
        if len(self.grid_shape) != 2:
            raise ValueError("grid_shape must contain rows and columns")
        rows = integer(self.grid_shape[0], "grid rows", maximum=X.shape[1])
        columns = integer(self.grid_shape[1], "grid columns", maximum=X.shape[2])
        ys = np.linspace(0, X.shape[1], rows + 1, dtype=int)
        xs = np.linspace(0, X.shape[2], columns + 1, dtype=int)
        bounds = [(ys[y], xs[x], ys[y + 1], xs[x + 1]) for y in range(rows) for x in range(columns)]
        self.image_shape_ = X.shape[1:]
        self.grid_shape_ = tuple(self.grid_shape)
        self.patch_bounds_ = tuple(bounds)
        self.feature_names_ = np.array(
            [
                f"channel_{i}.{stat}"
                for i in range(X.shape[3])
                for stat in ("mean", "std", "horizontal_change", "vertical_change")
            ]
            + ["row_start"],
            dtype=object,
        )
        self.boundary_channel_ = len(self.feature_names_) - 1
        return self

    def transform(self, X):
        check_is_fitted(self, "image_shape_")
        X = self._images(X)
        if X.shape[1:] != self.image_shape_ or tuple(self.grid_shape) != self.grid_shape_:
            raise ValueError("image shape/grid differs from fit")
        patches = []
        try:
            with np.errstate(over="raise", invalid="raise"):
                for index, (y0, x0, y1, x1) in enumerate(self.patch_bounds_):
                    patch = X[:, y0:y1, x0:x1]
                    horizontal = (
                        np.mean(np.abs(np.diff(patch, axis=2)), axis=(1, 2))
                        if x1 - x0 > 1
                        else np.zeros((len(X), X.shape[3]))
                    )
                    vertical = (
                        np.mean(np.abs(np.diff(patch, axis=1)), axis=(1, 2))
                        if y1 - y0 > 1
                        else np.zeros((len(X), X.shape[3]))
                    )
                    summary = np.stack(
                        [patch.mean(axis=(1, 2)), patch.std(axis=(1, 2)), horizontal, vertical], axis=2
                    )
                    marker = np.full((len(X), 1), float(index % self.grid_shape_[1] == 0))
                    patches.append(np.column_stack((summary.reshape(len(X), -1), marker)))
        except FloatingPointError as error:
            raise ValueError("image arithmetic overflow; rescale pixel values") from error
        return np.stack(patches, axis=1)

    def get_feature_names_out(self, input_features=None):
        check_is_fitted(self, "feature_names_")
        return self.feature_names_.copy()
