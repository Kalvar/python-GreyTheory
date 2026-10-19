"""Engineering preferences, fixed-scale grades, and training-only normalization."""

import numpy as np
import pytest
from sklearn.base import clone
from sklearn.exceptions import NotFittedError

from greytheory.analysis import BenefitNormalizer, grade_quality, rank_quality


def test_mixed_directions_and_target_peak_follow_declared_preferences():
    values = np.array([[0, 10, 90], [50, 20, 100], [100, 30, 110], [25, 25, 95.]])
    before = values.copy()
    normalizer = BenefitNormalizer(
        ['smaller', 'larger', 'target'],
        targets=[None, None, 100], bounds=[(0, 100), (10, 30), (90, 110)],
    )
    expected = [[1, 0, 0], [.5, .5, 1], [0, 1, 0], [.75, .75, .5]]
    np.testing.assert_allclose(normalizer.fit_transform(values), expected)
    np.testing.assert_array_equal(values, before)
    fitted = normalizer.fitted_bounds.copy()
    np.testing.assert_allclose(normalizer.transform([[25, 25, 95]]), [[.75, .75, .5]])
    np.testing.assert_array_equal(normalizer.fitted_bounds, fitted)
    # Constructor parameters remain constructor parameters after fitting.
    assert clone(normalizer).bounds == [(0, 100), (10, 30), (90, 110)]


def test_fixed_gra_formula_batch_invariance_and_monotone_dominance():
    benefits = [[0, 0], [1, 1], [.5, .25], [.6, .25]]
    result = grade_quality(benefits, weights=[1, 3])
    expected = np.array([[1/3, 1/3], [1, 1], [.5, .4], [5/9, .4]])
    np.testing.assert_allclose(result.coefficients, expected)
    np.testing.assert_allclose(result.scores, expected @ [.25, .75])
    assert result.ranking.tolist() == [1, 3, 2, 0]
    assert result.scores[3] > result.scores[2]
    separate = grade_quality([benefits[2]], weights=[1, 3])
    assert separate.scores[0] == pytest.approx(result.scores[2])
    combined = grade_quality(benefits + [[.05, .99]], weights=[1, 3])
    np.testing.assert_array_equal(result.scores, combined.scores[:4])
    np.testing.assert_allclose(grade_quality([[1, 1]], weights=[1e308, 1e308]).scores, [1])


def test_fast_quality_call_and_one_row_with_fixed_limits():
    result = rank_quality([[100, 10], [0, 30]], ['smaller', 'larger'])
    np.testing.assert_allclose(result.normalized_values, [[0, 0], [1, 1]])
    assert result.ranking.tolist() == [1, 0]
    assert result.normalizer is not None
    custom = rank_quality([[100, 10], [0, 30]], ['smaller', 'larger'], rho=.7)
    repeated = grade_quality(custom.normalizer.transform([[100, 10]]), weights=custom.weights, rho=custom.rho)
    assert repeated.scores[0] == pytest.approx(custom.scores[0])
    same = rank_quality([[0, 30]], ['smaller', 'larger'], bounds=[(0, 100), (10, 30)])
    assert same.scores[0] == pytest.approx(result.scores[1])


def test_clipping_is_explicit_and_violations_remain_observable():
    normalizer = BenefitNormalizer(['larger']).fit([[0], [10]])
    with pytest.raises(ValueError, match='outside fitted bounds'):
        normalizer.transform([[11]])
    clipped = BenefitNormalizer(['larger'], out_of_range='clip').fit([[0], [10]])
    np.testing.assert_array_equal(clipped.transform([[-1], [11]]), [[0], [1]])
    np.testing.assert_array_equal(clipped.out_of_bounds([[-1], [5], [11]]), [[True], [False], [True]])
    clipped.set_params(out_of_range='raise')
    # Changing constructor parameters does not silently alter fitted behavior.
    np.testing.assert_array_equal(clipped.transform([[11]]), [[1]])


class NamedValues:
    def __init__(self, values, columns):
        self.values = np.asarray(values)
        self.columns = columns

    def __array__(self, dtype=None, copy=None):
        return np.asarray(self.values, dtype=dtype)


def test_named_columns_reject_swapped_or_missing_schema():
    normalizer = BenefitNormalizer(['smaller', 'larger']).fit(
        NamedValues([[1, 10], [2, 20]], ['warpage', 'shear'])
    )
    np.testing.assert_array_equal(
        normalizer.transform(NamedValues([[1, 20]], ['warpage', 'shear'])), [[1, 1]]
    )
    for values in [NamedValues([[20, 1]], ['shear', 'warpage']), [[1, 20]]]:
        with pytest.raises(ValueError, match='names and order'):
            normalizer.transform(values)


@pytest.mark.parametrize('kwargs', [
    {'directions': 'larger'}, {'directions': ['larger', 'smaller']},
    {'directions': ['unknown']}, {'directions': ['larger'], 'bounds': [[1, 1]]},
    {'directions': ['larger'], 'bounds': [[0, 1], [0, 2]]},
    {'directions': ['target']}, {'directions': ['target'], 'targets': [0]},
    {'directions': ['larger'], 'targets': [1]},
    {'directions': ['larger'], 'out_of_range': 'allow'},
])
def test_invalid_quality_configuration_leaves_unfitted_normalizer(kwargs):
    normalizer = BenefitNormalizer(**kwargs)
    with pytest.raises((ValueError, TypeError)):
        normalizer.fit([[0], [1]])
    with pytest.raises(NotFittedError):
        normalizer.transform([[0]])


def test_constant_columns_and_failed_refit():
    normalizer = BenefitNormalizer(['larger'])
    with pytest.raises(ValueError, match='constant'):
        normalizer.fit([[1], [1]])
    fixed = BenefitNormalizer(['larger'], bounds=[(0, 2)]).fit([[1], [1]])
    np.testing.assert_allclose(fixed.transform([[1]]), [[.5]])
    original = BenefitNormalizer(['larger']).fit([[0], [2]])
    with pytest.raises(ValueError):
        original.fit([[3], [3]])
    np.testing.assert_allclose(original.transform([[1]]), [[.5]])


@pytest.mark.parametrize('values,kwargs', [
    ([[np.nan]], {}), ([[1.1]], {}), ([[-.01]], {}),
    ([[.5]], {'rho': 0}), ([[.5]], {'rho': 2}),
    ([[.5]], {'weights': [0]}), ([[.5]], {'weights': [-1]}),
    ([[.5]], {'weights': [1, 1]}),
])
def test_invalid_benefit_grades(values, kwargs):
    with pytest.raises((ValueError, TypeError)):
        grade_quality(values, **kwargs)
