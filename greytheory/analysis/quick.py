"""Small public entry points for supervised features and named design alternatives."""

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np

from .._validation import array, integer
from .optimization import pareto_front
from .pca import GreyPCA
from .reliability import DifferenceCalibrator, ranking_stability, reconstruction_scores
from .search import _splits, search_grey_pca


class _FixedSplits:
    def __init__(self, splits):
        self.splits = splits

    def split(self, X, y=None, groups=None):
        return iter(self.splits)


def _names(feature_names, width):
    names = [f"feature_{i + 1}" for i in range(width)] if feature_names is None else list(feature_names)
    if len(names) != width or any(not isinstance(n, str) or not n.strip() for n in names):
        raise ValueError("feature_names must contain one nonempty string per feature")
    if len(set(names)) != len(names):
        raise ValueError("feature_names must be unique")
    return names


@dataclass
class FeatureAnalysis:
    """Fitted prediction pipeline, ranking diagnostics and optional calibrated monitor.

    save() writes a JSON report, not a serialized model. Ranking is supervised
    GRA stability on original features, not a PCA loading or causal importance.
    """

    search: object
    stability: object
    feature_names: list
    monitor: object | None
    calibrator: DifferenceCalibrator | None = None

    @property
    def ranking(self):
        return [
            dict(
                feature=self.feature_names[i],
                index=int(i),
                selection_frequency=float(self.stability.selection_frequency[i]),
                mean_rank=float(self.stability.mean_rank[i]),
                rank_std=float(self.stability.rank_std[i]),
            )
            for i in self.stability.ranking
        ]

    @property
    def best_parameters(self):
        return deepcopy(self.search.best_parameters)

    @property
    def validation_rmse(self):
        return self.search.validation_rmse

    def _values(self, features):
        names = getattr(features, "columns", None)
        if names is not None and list(names) != self.feature_names:
            raise ValueError("feature column names and order must match training")
        values = array(features)
        if values.shape[1] != len(self.feature_names):
            raise ValueError("feature count must match training")
        return values

    def predict(self, features):
        return self.search.predict(self._values(features))

    def calibrate(self, normal_data, *, false_alarm_rate=0.05):
        """Use independent normal rows with the training-fitted monitoring model."""
        if self.monitor is None:
            raise ValueError(
                "reconstruction monitoring requires at least two features; prediction still works"
            )
        scores = reconstruction_scores(self.monitor, self._values(normal_data))
        self.calibrator = DifferenceCalibrator(false_alarm_rate).fit(scores)
        return self

    def find_differences(self, features):
        """Return reconstruction-novelty flags; these do not prove paired change."""
        if self.calibrator is None:
            raise ValueError("provide normal_data or call calibrate(normal_data) before finding differences")
        scores = reconstruction_scores(self.monitor, self._values(features))
        return dict(scores=scores, flags=self.calibrator.predict(scores), threshold=self.calibrator.threshold)

    def to_dict(self):
        calibration = None
        if self.calibrator is not None:
            finite = np.isfinite(self.calibrator.threshold)
            calibration = dict(
                threshold=self.calibrator.threshold if finite else None,
                status="ready" if finite else "insufficient_resolution",
                samples=self.calibrator.calibration_size,
                false_alarm_rate=self.calibrator.false_alarm_rate,
                resolution=self.calibrator.resolution,
            )
        return dict(
            format="greytheory-feature-analysis-v1",
            ranking=self.ranking,
            successful_repeats=self.stability.successful_repeats,
            skipped_repeats=self.stability.skipped_repeats,
            best_parameters=self.best_parameters,
            validation_rmse=self.validation_rmse,
            trials=deepcopy(self.search.trials),
            elapsed_seconds=self.search.elapsed_seconds,
            stopped_by_budget=self.search.stopped_by_budget,
            calibration=calibration,
            monitor_parameters=None
            if self.monitor is None
            else dict(method="pca", n_components=self.monitor.n_components, standardize=True),
            notes=[
                "Validation RMSE is a tuning score, not an independent test estimate.",
                "Selection frequency is a resampling diagnostic, not a causal probability.",
                "Calibrated reconstruction novelty is not proof of image change or restoration.",
            ],
        )

    def save(self, path):
        """Write a UTF-8 JSON report; infinite calibration thresholds become null."""

        def convert(value):
            if isinstance(value, np.ndarray):
                return value.tolist()
            if isinstance(value, np.generic):
                return value.item()
            raise TypeError(f"report cannot serialize {type(value).__name__}")

        text = json.dumps(self.to_dict(), ensure_ascii=False, indent=2, allow_nan=False, default=convert)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
        return path


def analyze_features(
    features,
    target,
    *,
    feature_names=None,
    groups=None,
    normal_data=None,
    top=5,
    repeats=40,
    false_alarm_rate=0.05,
    monitor_components=None,
    cv=3,
    random_state=0,
    search_options=None,
):
    """One call for GRA stability + supervised GreyPCA/Ridge selection.

    features: numeric rows of samples; target: one numeric response per row.
    Optional normal_data must be separate, representative normal calibration
    measurements. It is never passed to ranking/search; test rows stay external.
    Monitoring uses a separate ordinary PCA fitted on training rows only, with
    min(3, n_features - 1) components by default. It is not selected by prediction
    RMSE. One-feature input supports prediction but not reconstruction monitoring.
    For dependent observations pass groups or an appropriate cv splitter. Group
    subsampling is supported; ranking subsampling is not time-block bootstrap.

    Defaults search up to eight ordinary-PCA settings with at most six components,
    including the largest allowed count. Pass search_options for the lower-level
    search controls, e.g. methods, candidates, memory, max_trials or time_budget.
    Feature extraction/window settings are not automatically searched.
    """
    columns = getattr(features, "columns", None)
    if feature_names is None and columns is not None:
        feature_names = columns
    elif isinstance(feature_names, str):
        raise ValueError("feature_names must be a sequence, not one string")
    values = array(features, min_rows=4)
    names = _names(feature_names, values.shape[1])
    if columns is not None and list(columns) != names:
        raise ValueError("feature_names must match feature column names and order")
    top = min(integer(top, "top"), values.shape[1])
    splits = _splits(values, target, cv, groups, random_state)
    maximum = min(values.shape[1], min(len(train) - 1 for train, _ in splits), 6)
    components = sorted({1, min(2, maximum), min(3, maximum), maximum})
    options = dict(components=components, top_k=(None, top), max_trials=8)
    if search_options is not None:
        if not isinstance(search_options, Mapping):
            raise TypeError("search_options must be a mapping")
        if set(search_options) & {"X", "y", "groups", "cv", "random_state"}:
            raise ValueError(
                "pass groups, cv and random_state directly, and features/target as the first arguments"
            )
        options.update(search_options)
    stability = ranking_stability(
        values, target, k=top, repeats=repeats, groups=groups, random_state=random_state
    )
    search = search_grey_pca(
        values, target, cv=_FixedSplits(splits), groups=groups, random_state=random_state, **options
    )
    monitor = None
    if values.shape[1] > 1:
        count = (
            min(3, values.shape[1] - 1, len(values) - 1)
            if monitor_components is None
            else integer(
                monitor_components, "monitor_components", maximum=min(values.shape[1] - 1, len(values) - 1)
            )
        )
        monitor = GreyPCA(count, standardize=True).fit(values)
    elif monitor_components is not None:
        raise ValueError("reconstruction monitoring requires at least two features")
    result = FeatureAnalysis(search, stability, names, monitor)
    if normal_data is not None:
        result.calibrate(normal_data, false_alarm_rate=false_alarm_rate)
    return result


def choose_options(options, *, smaller=(), larger=(), limits=None):
    """Return nondominated named option dictionaries within optional inclusive limits.

    Example: choose_options(rows, smaller=['cost'], larger=['quality'],
                            limits={'days': (None, 4)}).
    Only named numeric fields are compared; other fields (e.g. name) are retained.
    Results are deep copies in input order. This screens supplied candidates,
    without aggregating unlike units or inferring global optimality.
    """
    rows = list(options)
    if not rows or any(not isinstance(row, Mapping) for row in rows):
        raise ValueError("options must be a nonempty sequence of dictionaries")
    if isinstance(smaller, str) or isinstance(larger, str):
        raise ValueError("smaller and larger must be sequences of field names")
    smaller, larger = list(smaller), list(larger)
    fields = smaller + larger
    if not fields or any(not isinstance(f, str) or not f for f in fields) or len(set(fields)) != len(fields):
        raise ValueError("objective names must be nonempty, unique and have only one direction")
    if limits is None:
        limits = {}
    if not isinstance(limits, Mapping):
        raise TypeError("limits must map field names to (lower, upper)")

    def column(field):
        try:
            return array([row[field] for row in rows], name=field, ndim=1)
        except KeyError as exc:
            raise ValueError(f"every option must provide numeric field {field!r}") from exc

    objectives = np.column_stack([column(field) for field in fields])
    violations = []
    for field, bounds in limits.items():
        if not isinstance(bounds, (tuple, list)) or len(bounds) != 2 or all(b is None for b in bounds):
            raise ValueError("each limit needs (lower, upper), with at least one finite bound")
        low, high = bounds
        finite = array([b for b in bounds if b is not None], name="limit bounds", ndim=1)
        if len(finite) == 2 and low > high:
            raise ValueError("limit lower bound must not exceed upper bound")
        values = column(field)
        if low is not None:
            violations.append(low - values)
        if high is not None:
            violations.append(values - high)
    constraints = None if not violations else np.column_stack(violations)
    front = pareto_front(
        objectives, ["smaller"] * len(smaller) + ["larger"] * len(larger), constraints=constraints
    )
    return [deepcopy(dict(rows[i])) for i in front.indices]
