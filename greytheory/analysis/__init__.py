"""Public analysis API; adapters are imported only when requested."""

from importlib import import_module

_EXPORTS = {
    "grey_relation": ("gra", "grey_relation"),
    "GreyGRA": ("gra", "GreyGRA"),
    "GreyFeatureSelector": ("selection", "GreyFeatureSelector"),
    "PCAAdapter": ("pca", "PCAAdapter"),
    "GreyPCA": ("pca", "GreyPCA"),
    "ReconstructionReport": ("pca", "ReconstructionReport"),
    "RobustPCA": ("robust", "RobustPCA"),
    "robust_pca": ("robust", "robust_pca"),
    "RobustSparsePCA": ("robust", "RobustSparsePCA"),
    "AdversarialPCA": ("adversarial", "AdversarialPCA"),
    "AdvPCA": ("adversarial", "AdvPCA"),
    "BenefitNormalizer": ("quality", "BenefitNormalizer"),
    "QualityRanking": ("quality", "QualityRanking"),
    "grade_quality": ("quality", "grade_quality"),
    "rank_quality": ("quality", "rank_quality"),
}
__all__ = list(_EXPORTS)


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(name)
    module, symbol = _EXPORTS[name]
    value = getattr(import_module(f"{__name__}.{module}"), symbol)
    globals()[name] = value
    return value
