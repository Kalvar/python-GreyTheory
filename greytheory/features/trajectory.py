"""Resample ordered paths without connecting pen-up gaps."""

from dataclasses import dataclass

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_is_fitted

from .._validation import array, integer
from .._results import result_alias


@dataclass(frozen=True)
class Trajectory:
    """One ordered path. Time units and spatial units are supplied by the caller.

    Consecutive changes in stroke_ids mark pen-up boundaries. Without IDs the
    path is treated as one stroke. Timestamps, when supplied, must increase.
    """

    points: object
    timestamps: object = None
    stroke_ids: object = None


class TrajectoryFeatures(TransformerMixin, BaseEstimator):
    """Turn paths of arbitrary lengths and D>=2 dimensions into fixed sequences.

    Supply a list of Trajectory objects or (points, dimensions) arrays, or a 3D
    array of equal-length paths. Each stroke receives at least two output points.
    Default resampling is by arc length; include_time=True uses time per stroke
    and additionally emits speed. No pressure or timing is inferred from images.
    Output channels: positions, step directions, step distance, turn angle,
    optional speed, then stroke_start. Use boundary_channel=-1 downstream.
    """

    dimensions = result_alias("dimensions_", "Number of spatial coordinate dimensions.")
    boundary_channel = result_alias("boundary_channel_", "Output stroke-start channel index.")

    def __init__(self, n_points=64, *, center=True, scale=False, include_time=False):
        self.n_points = n_points
        self.center = center
        self.scale = scale
        self.include_time = include_time

    def _samples(self, X):
        integer(self.n_points, "n_points", minimum=3)
        for name in ("center", "scale", "include_time"):
            if not isinstance(getattr(self, name), (bool, np.bool_)):
                raise TypeError(f"{name} must be boolean")
        if isinstance(X, np.ndarray) and X.ndim != 3:
            raise ValueError("use a batch: [points] for one trajectory, not a single 2D array")
        samples = list(X)
        if not samples:
            raise ValueError("need at least one trajectory")
        validated = []
        for sample in samples:
            sample = sample if isinstance(sample, Trajectory) else Trajectory(sample)
            points = array(sample.points, name="points", min_rows=2)
            if points.shape[1] < 2:
                raise ValueError("trajectories need at least two spatial dimensions")
            times = None
            if sample.timestamps is not None:
                times = array(sample.timestamps, name="timestamps", ndim=1)
                if len(times) != len(points) or np.any(np.diff(times) <= 0):
                    raise ValueError("timestamps must match points and increase strictly")
            if self.include_time and times is None:
                raise ValueError("include_time=True requires recorded timestamps for every trajectory")
            if sample.stroke_ids is None:
                starts = np.array([0])
            else:
                ids = np.asarray(sample.stroke_ids)
                if ids.ndim != 1 or len(ids) != len(points) or ids.dtype.kind not in "iu":
                    raise ValueError("stroke_ids must be one integer per point")
                starts = np.r_[0, np.flatnonzero(ids[1:] != ids[:-1]) + 1]
            bounds = list(zip(starts, np.r_[starts[1:], len(points)]))
            if any(right - left < 2 for left, right in bounds):
                raise ValueError("each stroke needs at least two recorded points")
            if 2 * len(bounds) > self.n_points:
                raise ValueError("n_points must allow at least two output points per stroke")
            validated.append((points, times, bounds))
        if len({sample[0].shape[1] for sample in validated}) != 1:
            raise ValueError("all trajectories must have the same spatial dimensions")
        return validated

    def fit(self, X, y=None):
        samples = self._samples(X)
        dimensions = samples[0][0].shape[1]
        names = [f"position_{i}" for i in range(dimensions)]
        names += [f"direction_{i}" for i in range(dimensions)]
        names += ["step_distance", "turn_angle"]
        if self.include_time:
            names += ["speed"]
        names += ["stroke_start"]
        self.dimensions_ = dimensions
        self.feature_names_ = np.array(names, dtype=object)
        self.boundary_channel_ = len(names) - 1
        self.schema_ = (self.n_points, self.center, self.scale, self.include_time)
        return self

    def transform(self, X):
        check_is_fitted(self, "dimensions_")
        samples = self._samples(X)
        if (self.n_points, self.center, self.scale, self.include_time) != self.schema_:
            raise ValueError("trajectory settings changed; fit again")
        if samples[0][0].shape[1] != self.dimensions_:
            raise ValueError("trajectory dimensions differ from fit")
        try:
            with np.errstate(over="raise", invalid="raise", divide="raise"):
                return np.stack([self._describe(*sample) for sample in samples])
        except FloatingPointError as error:
            raise ValueError("trajectory arithmetic overflow; rescale coordinates/timestamps") from error

    def _describe(self, points, times, bounds):
        points = points.copy()
        if self.center:
            points -= points[0]
        if self.scale:
            extent = np.linalg.norm(np.ptp(points, axis=0))
            if extent > 0:
                points /= extent
        parameters, weights = [], []
        for left, right in bounds:
            part = points[left:right]
            axis = (
                times[left:right] - times[left]
                if self.include_time
                else np.r_[0, np.cumsum(np.linalg.norm(np.diff(part, axis=0), axis=1))]
            )
            weights.append(axis[-1])
            # A stationary path still has a defined shape and two endpoints.
            parameters.append(axis if axis[-1] > 0 else np.linspace(0, 1, len(part)))
        weights = np.asarray(weights)
        if not weights.any():
            weights = np.ones(len(bounds))
        quota = (self.n_points - 2 * len(bounds)) * weights / weights.sum()
        allocation = np.floor(quota).astype(int) + 2
        remaining = self.n_points - int(allocation.sum())
        allocation[np.argsort(-(quota - np.floor(quota)), kind="stable")[:remaining]] += 1
        features = []
        for (left, right), axis, count in zip(bounds, parameters, allocation):
            positions = points[left:right]
            unique, indices = np.unique(axis, return_index=True)
            grid = np.linspace(unique[0], unique[-1], count)
            resampled = np.column_stack(
                [np.interp(grid, unique, positions[indices, i]) for i in range(self.dimensions_)]
            )
            displacement = np.vstack((np.zeros(self.dimensions_), np.diff(resampled, axis=0)))
            distance = np.linalg.norm(displacement, axis=1)
            direction = np.divide(
                displacement, distance[:, None], out=np.zeros_like(displacement), where=distance[:, None] > 0
            )
            angle = np.zeros(count)
            valid = (distance[1:] > 0) & (distance[:-1] > 0)
            dots = np.sum(direction[1:] * direction[:-1], axis=1)
            angle[1:][valid] = np.arccos(np.clip(dots[valid], -1, 1))
            columns = [resampled, direction, distance[:, None], angle[:, None]]
            if self.include_time:
                speed = np.r_[0, distance[1:] / np.diff(grid)]
                columns.append(speed[:, None])
            columns.append(np.r_[1.0, np.zeros(count - 1)][:, None])
            features.append(np.column_stack(columns))
        return np.vstack(features)

    def get_feature_names_out(self, input_features=None):
        check_is_fitted(self, "feature_names_")
        return self.feature_names_.copy()
