"""Training-only PCA composition for research forecasts and quality regression."""

import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.utils.validation import check_is_fitted

from .._validation import array
from ..analysis import GreyPCA
from .fractional import RLFGM
from .neural import GINN, FGINN
from .gpr import GreyFuzzyGPR


def _projection(method, count, parameters):
    parameters = {} if parameters is None else dict(parameters)
    if 'method' in parameters or 'n_components' in parameters:
        raise ValueError('use pca_method and n_components, not duplicate pca_params entries')
    parameters.setdefault('standardize', True)
    return GreyPCA(count, method=method, **parameters)


class GreyPCAForecast(BaseEstimator):
    """Forecast each latent series, then reconstruct the original feature space.

    Rows are equally spaced observations; columns are measured channels. PCA and
    positive offsets use the training history only. Grey models are not translation
    invariant: the declared offset changes the model, not just display coordinates.
    Kernel inverse reconstruction is approximate. No forecast clipping is applied.
    """

    def __init__(self, method='rlfgm', pca_method='pca', n_components=2,
                 pca_params=None, model_params=None):
        self.method = method
        self.pca_method = pca_method
        self.n_components = n_components
        self.pca_params = pca_params
        self.model_params = model_params

    def fit(self, X, y=None):
        X = array(X, min_rows=4)
        constructor = {'rlfgm': RLFGM, 'ginn': GINN, 'fginn': FGINN}.get(self.method)
        if constructor is None:
            raise ValueError('method must be rlfgm, ginn or fginn')
        projection = _projection(self.pca_method, self.n_components, self.pca_params).fit(X)
        scores = projection.transform(X)
        # Require inverse support now, rather than fail only when forecasting.
        projection.inverse_transform(scores[:1])
        offsets = scores.min(axis=0) - np.maximum(scores.std(axis=0), 1e-8)
        models = [constructor(**(self.model_params or {})).fit(column)
                  for column in (scores - offsets).T]
        self.projection = projection
        self.models = models
        self.offsets = offsets
        self.n_features_in_ = X.shape[1]
        self.diagnostics = dict(
            implementation="GreyPCA -> shifted component " + self.method + " -> inverse reconstruction",
            converged=all(model.diagnostics.get("converged", True) for model in models),
            pca_method=self.pca_method,
            latent_components=scores.shape[1],
            offset_rule='training minimum minus max(training std, 1e-8)',
            offsets=offsets.tolist(),
            components=[model.diagnostics for model in models],
            inverse_is_approximate=True,
        )
        return self

    def predict_components(self, steps=3):
        check_is_fitted(self, 'models')
        return np.column_stack([model.predict(steps) for model in self.models]) + self.offsets

    def predict(self, steps=3):
        scores = self.predict_components(steps)
        return self.projection.inverse_transform(scores)


class GreyPCAQuality(RegressorMixin, BaseEstimator):
    """GreyPCA -> Grey-Fuzzy GPR; fit preprocessing and GRA on training rows only.

    Optional top_k ranks latent components against the training target. Reliability
    is measured in retained PCA space, and cannot detect discarded-space changes.
    """

    def __init__(self, pca_method='pca', n_components=2, pca_params=None, model_params=None):
        self.pca_method = pca_method
        self.n_components = n_components
        self.pca_params = pca_params
        self.model_params = model_params

    def fit(self, X, y):
        projection = _projection(self.pca_method, self.n_components, self.pca_params).fit(X, y)
        scores = projection.transform(X)
        model = GreyFuzzyGPR(**(self.model_params or {})).fit(scores, y)
        self.projection = projection
        self.model = model
        self.n_features_in_ = projection.n_features_in_
        self.diagnostics = dict(
            pca_method=self.pca_method, latent_components=scores.shape[1],
            reliability_space='retained PCA components only', **model.diagnostics,
        )
        return self

    def predict(self, X, return_std=False):
        check_is_fitted(self, 'model')
        return self.model.predict(self.projection.transform(X), return_std=return_std)

    def reliability(self, X):
        check_is_fitted(self, 'model')
        return self.model.reliability(self.projection.transform(X))
