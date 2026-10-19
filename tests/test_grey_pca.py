"""Interchangeable decomposition, training-only selection, and reconstruction."""

import copy

import numpy as np
import pytest
from sklearn.base import BaseEstimator, TransformerMixin, clone
from sklearn.decomposition import PCA, SparsePCA, KernelPCA, TruncatedSVD
from sklearn.exceptions import NotFittedError
from sklearn.preprocessing import StandardScaler

from greytheory.analysis import PCAAdapter, GreyPCA, RobustPCA, RobustSparsePCA, AdvPCA, grey_relation
from greytheory.spectroscopy import PoissonPCA


@pytest.fixture
def data():
    random_generator = np.random.default_rng(27)
    factors = random_generator.normal(size=(48, 3)) @ random_generator.normal(size=(3, 8))
    factors += .03 * random_generator.normal(size=factors.shape)
    targets = factors[:, 0] + .1 * random_generator.normal(size=48)
    return factors[:36], factors[36:], targets[:36]


@pytest.mark.parametrize('method,parameters', [
    ('pca', {'whiten': True}),
    ('sparse', {'alpha': .1, 'max_iter': 2000}),
    ('kernel', {'kernel': 'poly', 'degree': 2, 'gamma': .1}),
    ('robust', {'max_iter': 2000}),
    ('robust_sparse', {'alpha': .1, 'max_iter': 2000}),
    ('adv', {'delta': 0}),
])
@pytest.mark.parametrize('select', [False, True])
def test_named_algorithms_match_independent_training_and_held_out_projection(data, method, parameters, select):
    train, test, targets = data
    model = GreyPCA(3, top_k=2 if select else None, standardize=True,
                    method=method, method_params=parameters).fit(train, targets if select else None)
    scaler = StandardScaler().fit(train)
    training = scaler.transform(train)
    held_out = scaler.transform(test)
    if method == 'robust':
        cleaned = RobustPCA(**parameters).fit(training)
        expected_model = PCA(3, svd_solver='full').fit(cleaned.low_rank)
    else:
        constructors = {
            'pca': lambda: PCA(3, svd_solver='full', **parameters),
            'sparse': lambda: SparsePCA(3, random_state=0, **parameters),
            'kernel': lambda: KernelPCA(3, fit_inverse_transform=True, random_state=0, **parameters),
            'robust_sparse': lambda: RobustSparsePCA(3, **parameters),
            'adv': lambda: AdvPCA(3, **parameters),
        }
        expected_model = constructors[method]().fit(training)
    training_scores = expected_model.transform(training)
    expected_scores = expected_model.transform(held_out)
    if select:
        signed_scores = grey_relation(
            targets, np.vstack((training_scores.T, -training_scores.T)), normalize='zscore'
        )
        ranking_scores = np.maximum(signed_scores[:3], signed_scores[3:])
        selected = np.sort(np.argsort(-ranking_scores, kind='stable')[:2])
        np.testing.assert_allclose(model.component_scores, ranking_scores)
    else:
        selected = np.arange(3)
        assert model.component_scores is None and model.selector is None
    np.testing.assert_array_equal(model.selected_components, selected)
    np.testing.assert_allclose(model.transform(test), expected_scores[:, selected], atol=1e-9)
    scores = model.transform(test)
    zero_filled = np.zeros((len(test), 3))
    zero_filled[:, selected] = scores
    expected_reconstruction = scaler.inverse_transform(expected_model.inverse_transform(zero_filled))
    np.testing.assert_allclose(model.inverse_transform(scores), expected_reconstruction, atol=1e-9)


def test_custom_estimator_is_cloned_and_controls_component_count(data):
    train, test, targets = data
    supplied = TruncatedSVD(4, random_state=4).fit(test)
    original_components = supplied.components_.copy()
    model = GreyPCA(estimator=supplied, top_k=2).fit(train, targets)
    assert model.reducer is not supplied
    assert model.reducer.n_components == 4
    assert model.component_scores.shape == (4,)
    assert model.transform(test).shape == (12, 2)
    np.testing.assert_array_equal(supplied.components_, original_components)
    # Nested parameters remain compatible with sklearn cloning and model search.
    configured = clone(GreyPCA(estimator=AdvPCA(3, delta=0), top_k=2))
    configured.set_params(estimator__n_components=4)
    configured.fit(train, targets)
    assert configured.reducer.n_components == 4


def test_custom_count_model_receives_nonnegative_unscaled_data():
    counts = np.random.default_rng(14).poisson(10, size=(30, 6))
    model = GreyPCA(estimator=PoissonPCA(3)).fit(counts[:20])
    expected = PoissonPCA(3).fit(counts[:20])
    np.testing.assert_allclose(model.transform(counts[20:]), expected.transform(counts[20:]))
    assert not hasattr(model, 'explained_variance_ratio')


def test_copy_false_backend_does_not_change_input_or_double_center_scores(data):
    train, test, _ = data
    train = train + 100
    before = train.copy()
    model = GreyPCA(3, method_params={'copy': False}).fit(train)
    expected = PCA(3, svd_solver='full').fit(before)
    np.testing.assert_array_equal(train, before)
    np.testing.assert_allclose(model.transform(test), expected.transform(test), atol=1e-9)


def test_training_statistics_and_gra_scores_stay_fixed_for_new_data(data):
    train, test, targets = data
    model = GreyPCA(3, top_k=2, method='kernel', standardize=True).fit(train, targets)
    mean = model.scaler_.mean_.copy()
    scores = model.component_scores.copy()
    selected = model.selected_components.copy()
    baseline = model.transform(test)
    model.transform(test + 1000)
    np.testing.assert_array_equal(model.scaler_.mean_, mean)
    np.testing.assert_array_equal(model.component_scores, scores)
    np.testing.assert_array_equal(model.selected_components, selected)
    np.testing.assert_array_equal(model.transform(test), baseline)


def test_failed_refit_keeps_the_previous_complete_fit(data):
    train, test, targets = data
    model = GreyPCA(3, top_k=2).fit(train, targets)
    expected = model.transform(test)
    model.set_params(top_k=100)
    with pytest.raises(ValueError):
        model.fit(train * 10, targets)
    np.testing.assert_array_equal(model.transform(test), expected)
    model.set_params(top_k=None, method='sparse', method_params={'alpha': .1})
    model.fit(train)
    assert model.selector is None and model.component_scores is None
    assert model.transform(test).shape == (12, 3)
    assert not hasattr(model, 'explained_variance_ratio')


class BadShape(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        self.training_rows_ = X.shape[0]
        return self

    def transform(self, X):
        return np.zeros((len(X) + 1, 2))


class NoInverse(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        self.n_features_in_ = X.shape[1]
        return self

    def transform(self, X):
        return X[:, :2]


class SharedClone(NoInverse):
    def __sklearn_clone__(self):
        return self


def test_estimator_capabilities_and_bad_output_shapes(data):
    train, test, _ = data
    with pytest.raises(TypeError, match='fit and transform'):
        GreyPCA(estimator=RobustPCA()).fit(train)
    shared = SharedClone()
    with pytest.raises(TypeError, match='independent'):
        GreyPCA(estimator=shared).fit(train)
    assert not hasattr(shared, 'n_features_in_')
    with pytest.raises(ValueError, match='row'):
        GreyPCA(estimator=BadShape()).fit(train)
    model = GreyPCA(estimator=NoInverse()).fit(train)
    assert model.transform(test).shape == (12, 2)
    with pytest.raises(NotImplementedError, match='inverse_transform'):
        model.inverse_transform(model.transform(test))


@pytest.mark.parametrize('kwargs', [
    {'method': 'unknown'}, {'method_params': []}, {'method_params': {'n_components': 3}},
    {'method_params': {'not_a_parameter': 1}}, {'estimator': PCA(2), 'method': 'sparse'},
    {'estimator': PCA(2), 'method_params': {'whiten': True}}, {'top_k': 0}, {'n_components': 0},
])
def test_bad_configuration_does_not_leave_a_partial_fit(data, kwargs):
    train, test, targets = data
    model = GreyPCA(**kwargs)
    with pytest.raises((ValueError, TypeError)):
        model.fit(train, targets)
    with pytest.raises(NotFittedError):
        model.transform(test)


def test_validation_and_variance_reporting(data):
    train, test, targets = data
    with pytest.raises(ValueError, match='target'):
        GreyPCA(3, top_k=2).fit(train)
    with pytest.raises(ValueError, match='constant'):
        GreyPCA(3).fit(train, np.ones(len(train)))
    with pytest.raises(ValueError, match='observation'):
        GreyPCA(3).fit(train, targets[:-1])
    with pytest.raises(ValueError, match='variance'):
        GreyPCA(3).fit(np.ones_like(train))
    model = GreyPCA(3).fit(train)
    np.testing.assert_allclose(model.explained_variance_ratio, PCA(3).fit(train).explained_variance_ratio_)
    with pytest.raises(ValueError, match='feature count'):
        model.transform(test[:, :-1])
    with pytest.raises(ValueError, match='component count'):
        model.inverse_transform(np.ones((2, 2)))
    restored = copy.deepcopy(model)
    np.testing.assert_allclose(restored.transform(test), model.transform(test))


def test_kernel_uses_actual_output_dimension_after_zero_eigenvalues_are_removed():
    factors = np.arange(15., dtype=float).reshape(-1, 1)
    targets = factors[:, 0] ** 2
    model = GreyPCA(4, method='kernel', method_params={'kernel': 'linear', 'remove_zero_eig': True})
    model.fit(factors, targets)
    assert model.component_scores.shape == (1,)
    assert model.transform(factors[:3]).shape == (3, 1)


@pytest.mark.parametrize('adapter', [GreyPCA, PCAAdapter])
@pytest.mark.parametrize('components', [1, 3])
def test_sparse_single_pixel_matches_batch_projection_and_reconstruction(data, adapter, components):
    train, test, _ = data
    model = adapter(components, method='sparse').fit(train)
    single = model.transform(test[:1])
    batch = model.transform(test)
    assert single.shape == (1, components)
    np.testing.assert_allclose(single, batch[:1], atol=1e-10)
    np.testing.assert_allclose(model.inverse_transform(single), model.inverse_transform(batch)[:1], atol=1e-10)
