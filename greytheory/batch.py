"""Model snapshots and ordered batch execution."""

from collections.abc import MutableSequence
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import multiprocessing as mp

from ._validation import integer
from .packages.models.grey_gm0n import GreyGM0N
from .packages.models.grey_gm11 import GreyGM11


def _snapshot(model):
    if not isinstance(model, (GreyGM0N, GreyGM11)):
        raise TypeError("expected a GM0N, GM1N or GM11 model")
    return deepcopy(model)


def _execute_model(task):
    model, method = task
    getattr(model, method)()
    return model


def _run_models(models, *, workers, inplace, method=None):
    models = list(models)
    workers = integer(workers, "workers")
    tasks = [
        (_snapshot(model), method or ("forecast" if isinstance(model, GreyGM11) else "analyze"))
        for model in models
    ]
    if not tasks:
        return []
    if workers == 1:
        results = [_execute_model(task) for task in tasks]
    else:
        with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as pool:
            results = list(pool.map(_execute_model, tasks))
    if inplace:
        # Commit only after every job succeeds, including in sequential mode.
        for original, computed in zip(models, results):
            original.__dict__.clear()
            original.__dict__.update(computed.__dict__)
        return models
    return results


def run_models(models, *, workers=1, inplace=True):
    """Compute GM0N/GM1N/GM11 models in input order, including mixed batches.

    Each job runs on a private copy. With inplace=True, input model objects are
    updated only after all jobs succeed; False returns independent fitted copies.
    A plain list keeps its usual reference semantics. Use ModelQueue to snapshot
    models when adding them, before the caller changes or reuses a model.
    """
    return _run_models(models, workers=workers, inplace=inplace)


class ModelQueue(MutableSequence):
    """A model sequence that deep-copies every inserted model.

    append, extend, insert, item/slice assignment, and construction all snapshot
    their inputs. Reading an item returns the stored, editable snapshot. Slicing
    returns an independent ModelQueue. run() computes the stored snapshots.
    """

    def __init__(self, models=()):
        self._models = []
        self.extend(models)

    def __len__(self):
        return len(self._models)

    def __getitem__(self, index):
        value = self._models[index]
        return type(self)(value) if isinstance(index, slice) else value

    def __setitem__(self, index, value):
        self._models[index] = (
            [_snapshot(model) for model in value] if isinstance(index, slice) else _snapshot(value)
        )

    def __delitem__(self, index):
        del self._models[index]

    def insert(self, index, model):
        self._models.insert(index, _snapshot(model))

    def append(self, model):
        self._models.append(_snapshot(model))

    def extend(self, models):
        # Prepare first so a bad item cannot leave a partially extended queue.
        snapshots = [_snapshot(model) for model in models]
        self._models.extend(snapshots)

    def reverse(self):
        self._models.reverse()

    def run(self, *, workers=1, inplace=True):
        return run_models(self, workers=workers, inplace=inplace)
