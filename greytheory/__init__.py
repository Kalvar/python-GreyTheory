"""Grey models and batch snapshots. Scientific adapters load on demand."""

from .packages.models.grey_gm0n import GreyGM0N
from .packages.models.grey_gm1n import GreyGM1N
from .packages.models.grey_gm11 import GreyGM11
from .batch import ModelQueue, run_models
from .packages.models.grey_run import GreyRun
from ._version import get_version as _get_version

__version__ = _get_version()
GM0N = GreyGM0N
GM1N = GreyGM1N
GM11 = GreyGM11

__all__ = [
    "GM0N", "GM1N", "GM11", "ModelQueue", "run_models", "analyze_features", "choose_options", "forecast_series", "predict_quality",
    "GreyTheory", "GreyGRA", "GreyGM0N", "GreyGM1N", "GreyGM11", "GreyRun", "compare_handwriting",
]


class GreyTheory:
    def __init__(self):
        self.gm0n = GreyGM0N()
        self.gm1n = GreyGM1N()
        self.gm11 = GreyGM11()
        self.run = GreyRun()
        self._gra = None

    @property
    def gra(self):
        if self._gra is None:
            from .analysis.gra import GreyGRA

            self._gra = GreyGRA()
        return self._gra


def __getattr__(name):
    if name in {"forecast_series", "predict_quality"}:
        from . import research

        return getattr(research, name)
    if name in {"analyze_features", "choose_options"}:
        from .analysis import quick

        return getattr(quick, name)
    if name == "compare_handwriting":
        from .handwriting import compare_handwriting

        return compare_handwriting
    if name == "GreyGRA":
        from .analysis.gra import GreyGRA

        return GreyGRA
    raise AttributeError(name)
