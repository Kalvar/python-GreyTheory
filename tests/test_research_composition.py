"""Independent composition, chronology and backend compatibility checks."""
import numpy as np
import pytest
from sklearn.decomposition import PCA
from sklearn.exceptions import NotFittedError

from greytheory import forecast_series, predict_quality
from greytheory.analysis import GreyPCA
from greytheory.research import GreyPCAForecast, GreyPCAQuality, GreyFuzzyGPR, RLFGM

METHODS = ['pca', 'sparse', 'kernel', 'robust', 'robust_sparse', 'adv']


def history():
    t = np.arange(24.)
    return np.column_stack([20 + t + np.sin(t), 40 + t*.3 + np.cos(t), 5 + t*.1 + np.sin(t*.4)])


@pytest.mark.parametrize('pca_method', METHODS)
@pytest.mark.parametrize('method', ['rlfgm', 'ginn', 'fginn'])
def test_all_forecast_combinations(pca_method, method):
    model = GreyPCAForecast(method, pca_method, model_params={'order': 1} if method == 'rlfgm' else {})
    model.fit(history())
    result = model.predict(2)
    assert result.shape == (2, 3)
    assert np.isfinite(result).all()
    np.testing.assert_allclose(result[:1], model.predict(1), atol=1e-10)
    scores = model.projection.transform(history())
    assert (scores-model.offsets > 0).all()


@pytest.mark.parametrize('pca_method', METHODS)
def test_all_quality_combinations(pca_method):
    X = np.random.default_rng(19).normal(size=(30,4))
    y = 10 + X[:,0]*2 + X[:,1]**2
    m = GreyPCAQuality(pca_method, model_params={'optimize_kernel': False}).fit(X[:24], y[:24])
    assert np.isfinite(m.predict(X[24:])).all()
    assert m.reliability(X[24:])['grade'].shape == (6,)
    projection = GreyPCA(2, method=pca_method, standardize=True).fit(X[:24], y[:24])
    expected = GreyFuzzyGPR(optimize_kernel=False).fit(projection.transform(X[:24]), y[:24])
    np.testing.assert_allclose(m.predict(X[24:]), expected.predict(projection.transform(X[24:])))


def test_forecast_independent_training_and_reconstruction():
    X = history()
    model = GreyPCAForecast(model_params={'order': 1}).fit(X)
    projection = GreyPCA(2, standardize=True).fit(X)
    Z = projection.transform(X)
    offset = Z.min(axis=0) - np.maximum(Z.std(axis=0), 1e-8)
    future = np.column_stack([RLFGM(1).fit(c).predict(3) for c in (Z-offset).T]) + offset
    np.testing.assert_allclose(model.predict(3), projection.inverse_transform(future))
    before = model.projection.scaler_.mean_.copy()
    model.predict(10)
    np.testing.assert_array_equal(before, model.projection.scaler_.mean_)


def test_custom_estimator_and_supervised_component_selection():
    X = history()
    estimator = PCA(2)
    forecast = GreyPCAForecast(pca_params={'estimator': estimator}, model_params={'order': 1}).fit(X)
    assert forecast.predict(2).shape == (2,3)
    assert not hasattr(estimator, 'components_')
    quality = GreyPCAQuality(pca_params={'top_k':1}, model_params={'optimize_kernel':False}).fit(X, X[:,0])
    assert quality.model.n_features_in_ == 1


def test_quick_functions_and_guards():
    X=history()
    assert forecast_series(X, 2, pca_method='pca', order=1).shape == (2,3)
    result=predict_quality(X, X[:,0], X[:2], pca_method='pca', optimize_kernel=False)
    assert isinstance(result['model'], GreyPCAQuality)
    assert result['std'].shape == (2,)
    with pytest.raises(ValueError, match='pca_method'):
        forecast_series(X[:,0], pca_params={})
    with pytest.raises(ValueError, match='top_k'):
        GreyPCAForecast(pca_params={'top_k':1}).fit(X)
    with pytest.raises(NotFittedError):
        GreyPCAQuality().predict(X)


@pytest.mark.parametrize('pca_method', METHODS)
@pytest.mark.parametrize('method', ['rlfgm', 'ginn', 'fginn', 'grey_fuzzy_gpr'])
def test_workbench_all_compositions(pca_method, method):
    import json
    from examples.workbench.scenarios import run_scenario
    result = run_scenario('research', {'pca_mode':'on', 'method':pca_method, 'tool':method})
    json.dumps(result, allow_nan=False)
    assert result['parameters']['method'] == pca_method
    if method == 'grey_fuzzy_gpr':
        assert result['report']['models'][1]['diagnostics']['pca_method'] == pca_method
    else:
        assert result['diagnostics']['backtest']['latent_components'] == 2
        assert len(result['diagram']['backtest']) == 8


@pytest.mark.parametrize('method', ['rlfgm','ginn','fginn','grey_fuzzy_gpr'])
def test_poisson_counts_composition(method):
    from greytheory.spectroscopy.processing import PoissonPCA
    X = history()
    options = {'estimator':PoissonPCA(2), 'standardize':False}
    if method == 'grey_fuzzy_gpr':
        model = GreyPCAQuality(pca_params=options, model_params={'optimize_kernel':False}).fit(X, X[:,0])
        assert model.predict(X[:2]).shape == (2,)
    else:
        model = GreyPCAForecast(method, pca_params=options).fit(X)
        assert np.isfinite(model.predict(2)).all()
    assert not hasattr(options['estimator'], 'model_')
