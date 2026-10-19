"""Compatibility entry points for model batch execution."""

import multiprocessing as mp

from ...batch import _run_models, run_models


class GreyRun:
    def __init__(self, workers=1):
        self.cpu_count = mp.cpu_count()
        self.workers = workers

    def __call__(self, models, *, workers=None, inplace=True):
        return run_models(models, workers=self.workers if workers is None else workers, inplace=inplace)

    def _execute_models(self, gmnn_queue=None, is_gm11=False, *, workers=None, inplace=True):
        return _run_models(
            () if gmnn_queue is None else gmnn_queue,
            workers=self.workers if workers is None else workers,
            inplace=inplace,
            method="forecast" if is_gm11 else "analyze",
        )

    def gm0n(self, queue, **kwargs):
        return self._execute_models(queue, **kwargs)

    def gm1n(self, queue, **kwargs):
        return self._execute_models(queue, **kwargs)

    def gm11(self, queue, **kwargs):
        return self._execute_models(queue, True, **kwargs)
