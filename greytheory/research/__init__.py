"""Experimental research models. Importing the package does not train any model."""

from importlib import import_module

_EXPORTS = {
    "GreyPCAForecast": ("composition", "GreyPCAForecast"),
    "GreyPCAQuality": ("composition", "GreyPCAQuality"),
    "RLFGM": ("fractional", "RLFGM"),
    "rl_matrix": ("fractional", "rl_matrix"),
    "rl_accumulate": ("fractional", "rl_accumulate"),
    "rl_restore": ("fractional", "rl_restore"),
    "GINN": ("neural", "GINN"),
    "FGINN": ("neural", "FGINN"),
    "tm_accumulate": ("neural", "tm_accumulate"),
    "tm_restore": ("neural", "tm_restore"),
    "GreyFuzzyGPR": ("gpr", "GreyFuzzyGPR"),
}
__all__ = list(_EXPORTS) + ["forecast_series", "predict_quality"]


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(name)
    module, attribute = _EXPORTS[name]
    result = getattr(import_module(f"{__name__}.{module}"), attribute)
    globals()[name] = result
    return result


def forecast_series(values, steps=3, *, method="rlfgm", pca_method=None,
                    n_components=2, pca_params=None, **parameters):
    """Quick equal-step forecast: rlfgm, ginn or fginn; parameters configure the model."""
    if pca_method is not None:
        return __getattr__("GreyPCAForecast")(
            method, pca_method, n_components, pca_params, parameters
        ).fit(values).predict(steps)
    if pca_params is not None:
        raise ValueError("pca_params requires pca_method")
    methods = {key.lower(): key for key in ("RLFGM", "GINN", "FGINN")}
    if method not in methods:
        raise ValueError("method must be rlfgm, ginn or fginn")
    model = __getattr__(methods[method])(**parameters).fit(values)
    return model.predict(steps)


def predict_quality(features, target, new_features, *, pca_method=None,
                    n_components=2, pca_params=None, **parameters):
    """Return predictions, GP standard deviations and heuristic reliability grades."""
    if pca_method is not None:
        model = __getattr__("GreyPCAQuality")(
            pca_method, n_components, pca_params, parameters
        ).fit(features, target)
    else:
        if pca_params is not None:
            raise ValueError("pca_params requires pca_method")
        model = __getattr__("GreyFuzzyGPR")(**parameters).fit(features, target)
    values, std = model.predict(new_features, return_std=True)
    return dict(prediction=values, std=std, reliability=model.reliability(new_features), model=model)
