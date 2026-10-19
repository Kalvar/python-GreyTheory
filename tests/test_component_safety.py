"""Sign ambiguity, inverse consistency, and honest component retention metrics."""

from itertools import product

import numpy as np
import pytest
from sklearn.base import BaseEstimator, TransformerMixin, clone
from sklearn.decomposition import PCA

from greytheory.analysis import AdvPCA, AdversarialPCA, GreyFeatureSelector, GreyPCA, grey_relation


def test_adv_shorthand_and_legacy_import_use_same_backend():
    data = np.random.default_rng(11).normal(size=(12, 4))
    short = GreyPCA(2, method='adv', method_params={'delta': 0}).fit(data)
    legacy = GreyPCA(2, method='adversarial', method_params={'delta': 0}).fit(data)
    assert AdvPCA is AdversarialPCA and isinstance(short.reducer, AdvPCA)
    assert short.reducer.converged and short.reducer.inner_converged
    np.testing.assert_allclose(short.transform(data), legacy.transform(data))


@pytest.mark.parametrize('normalization', ['none', 'zscore', 'minmax'])
def test_component_grades_use_shared_extrema_and_ignore_arbitrary_signs(normalization):
    random = np.random.default_rng(14)
    scores = random.normal(size=(15, 3))
    target = scores[:, 0] - .5 * scores[:, 2] + .1 * random.normal(size=15)
    baseline = GreyFeatureSelector(2, direction='either', normalization=normalization).fit(scores, target)
    both = np.column_stack((scores, -scores)).T
    expected = grey_relation(target, both, normalize=normalization)
    np.testing.assert_allclose(baseline.scores, np.maximum(expected[:3], expected[3:]))
    for signs in product([-1, 1], repeat=3):
        result = clone(baseline).fit(scores * signs, target)
        np.testing.assert_allclose(result.scores, baseline.scores)
        np.testing.assert_array_equal(result.get_support(), baseline.get_support())
    # Original-feature selectors retain the original signed default.
    signed = GreyFeatureSelector(2, normalization=normalization).fit(scores, target)
    np.testing.assert_allclose(signed.scores, grey_relation(target, scores.T, normalize=normalization))


class SignedPCA(TransformerMixin, BaseEstimator):
    def __init__(self, signs=(1, 1, 1)):
        self.signs = signs

    def fit(self, X, y=None):
        self.model_ = PCA(len(self.signs)).fit(X)
        return self

    def transform(self, X):
        return self.model_.transform(X) * self.signs

    def inverse_transform(self, X):
        return self.model_.inverse_transform(X * self.signs)


def test_reference_alignment_is_frozen_and_reversed_for_reconstruction():
    data = np.random.default_rng(9).normal(size=(25, 5))
    target = data[:, 0] - .3 * data[:, 2]
    first = GreyPCA(estimator=SignedPCA(), top_k=2, align_to_target=True).fit(data[:20], target[:20])
    second = GreyPCA(estimator=SignedPCA((-1, 1, -1)), top_k=2, align_to_target=True).fit(data[:20], target[:20])
    np.testing.assert_allclose(first.transform(data[20:]), second.transform(data[20:]))
    np.testing.assert_allclose(
        first.inverse_transform(first.transform(data[20:])),
        second.inverse_transform(second.transform(data[20:])),
    )
    signs = first.component_directions.copy()
    first.transform(data[20:] + 100)
    np.testing.assert_array_equal(first.component_directions, signs)
    raw = first.reducer.transform(data[20:])
    restored = np.zeros_like(raw)
    restored[:, first.selected_components] = raw[:, first.selected_components]
    np.testing.assert_allclose(first.inverse_transform(first.transform(data[20:])), first.reducer.inverse_transform(restored))
    with pytest.raises(ValueError, match='target'):
        GreyPCA(align_to_target=True).fit(data)


def test_constant_component_cannot_win_gra():
    target = np.arange(10.)
    scores = np.column_stack((np.ones(10), -target, np.zeros(10)))
    selector = GreyFeatureSelector(None, direction='either', constant_policy='exclude').fit(scores, target)
    assert selector.get_support(indices=True).tolist() == [1]
    assert np.isnan(selector.scores[[0, 2]]).all()
    assert selector.directions.tolist() == [0, -1, 0]
    with pytest.raises(ValueError):
        GreyFeatureSelector(2, constant_policy='exclude').fit(scores, target)
    with pytest.raises(ValueError, match='nonconstant'):
        GreyFeatureSelector(1, constant_policy='exclude').fit(np.ones((10, 2)), target)


def test_fractional_component_count_is_exact_for_conventional_pca():
    data = np.random.default_rng(33).normal(size=(30, 6)) * [10, 3, 1, .5, .1, .05]
    model = GreyPCA(.85).fit(data)
    expected = PCA(.85, svd_solver='full').fit(data)
    assert model.n_components_fitted == expected.n_components_
    np.testing.assert_allclose(model.explained_variance_ratio, expected.explained_variance_ratio_)
    report = model.reconstruction_report(data)
    np.testing.assert_allclose(report.prefix_coverage, np.cumsum(expected.explained_variance_ratio_))
    assert report.full_coverage >= .85 and report.monotonic
    for method in ['adv', 'sparse', 'robust', 'kernel']:
        with pytest.raises(ValueError, match='fractional'):
            GreyPCA(.85, method=method).fit(data)


def test_quality_relevant_low_variance_component_can_reduce_retained_variance():
    # Orthogonal, centered columns with a quality target on the smallest axis.
    data = np.array([[10, 0, 0], [-10, 0, 0], [0, 3, 0], [0, -3, 0], [0, 0, 1], [0, 0, -1.]])
    model = GreyPCA(3, top_k=1).fit(data, data[:, 2])
    report = model.reconstruction_report(data, threshold=.85)
    np.testing.assert_allclose(report.prefix_coverage, [100/110, 109/110, 1])
    assert model.selected_components.tolist() == [2]
    assert report.selected_coverage == pytest.approx(1/110)
    assert report.first_prefix_at_threshold == 1
    assert report.full_coverage > report.selected_coverage


class NonorthogonalProjection(TransformerMixin, BaseEstimator):
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return X.copy()

    def inverse_transform(self, Z):
        return np.column_stack((Z[:, 0] - 10 * Z[:, 1], np.zeros(len(Z))))


def test_reconstruction_coverage_can_be_negative_and_nonmonotone():
    data = np.array([[1, 1], [-1, -1], [2, 2], [-2, -2.]])
    model = GreyPCA(estimator=NonorthogonalProjection()).fit(data)
    report = model.reconstruction_report(data)
    assert report.prefix_coverage[0] == pytest.approx(.5)
    assert report.prefix_coverage[1] < 0
    assert not report.monotonic and report.first_prefix_at_threshold is None
    assert report.full_coverage == pytest.approx(report.selected_coverage)
    with pytest.raises(AttributeError):
        _ = model.explained_variance_ratio
    with pytest.raises(ValueError, match='variance'):
        model.reconstruction_report(np.ones((3, 2)))


def test_adv_zero_radius_reconstruction_coverage_agrees_with_pca():
    data = np.random.default_rng(42).normal(size=(22, 5))
    model = GreyPCA(4, method='adv', method_params={'delta': 0}).fit(data)
    report = model.reconstruction_report(data)
    expected = PCA(4).fit(data)
    np.testing.assert_allclose(report.prefix_coverage, np.cumsum(expected.explained_variance_ratio_), atol=1e-12)


class IdentityProjection(TransformerMixin, BaseEstimator):
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return X.copy()


def test_ambiguous_direction_cannot_be_presented_as_target_alignment():
    target = np.array([-1., 0, 1, 0])
    scores = np.array([0., 1, 0, -1])[:, None]
    selector = GreyFeatureSelector(1, direction='either').fit(scores, target)
    assert selector.direction_ambiguous.tolist() == [True]
    with pytest.raises(ValueError, match='tied component directions'):
        GreyPCA(estimator=IdentityProjection(), align_to_target=True).fit(scores, target)
    model = GreyPCA(estimator=IdentityProjection()).fit(scores, target)
    assert model.component_direction_ambiguous.tolist() == [True]
    for normalization in ['initial', 'mean']:
        with pytest.raises(ValueError, match='erase signs'):
            GreyPCA(align_to_target=True, normalization=normalization).fit(scores, target)
    with pytest.raises(ValueError, match='component_direction'):
        GreyPCA(align_to_target=True, component_direction='positive').fit(scores, target)


def test_standardized_whitened_pca_coverage_is_in_analysis_space():
    data = np.random.default_rng(77).normal(size=(30, 5)) * [1, 3, 4, 8, 20]
    model = GreyPCA(4, standardize=True, method_params={'whiten': True}).fit(data)
    report = model.reconstruction_report(data)
    assert report.space == 'standardized'
    np.testing.assert_allclose(report.prefix_coverage, np.cumsum(model.explained_variance_ratio))
