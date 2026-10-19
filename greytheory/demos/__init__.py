"""Reproducible synthetic demos; outputs are not instrument or forensic evidence."""

from importlib import import_module

_EXPORTS = {
    "make_xrf_data": ("xrf", "make_xrf_data"),
    "run_xrf_demo": ("xrf", "run_xrf_demo"),
    "run_handwriting_demo": ("handwriting", "run_handwriting_demo"),
}
__all__ = list(_EXPORTS)


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(name)
    module, symbol = _EXPORTS[name]
    value = getattr(import_module(f"{__name__}.{module}"), symbol)
    globals()[name] = value
    return value
