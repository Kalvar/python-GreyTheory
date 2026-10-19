"""Spectroscopy operations; no automatic preprocessing of XRF counts."""

from .processing import (
    baseline_correct,
    fit_nmf,
    fit_mcr_als,
    fit_mnf,
    PoissonPCA,
    fit_mlpca,
    element_lines,
    fit_peaks,
)

__all__ = [
    "baseline_correct",
    "fit_nmf",
    "fit_mcr_als",
    "fit_mnf",
    "PoissonPCA",
    "fit_mlpca",
    "element_lines",
    "fit_peaks",
]
