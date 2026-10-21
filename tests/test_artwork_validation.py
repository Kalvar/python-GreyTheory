"""Change triage must reject identical pairs and keep development selection separate."""

import numpy as np
import pytest

from examples.demos.artwork_validation import confusion, paired_review, select_spectral_configuration


def test_identical_complex_features_produce_no_change_candidates():
    reference = np.random.default_rng(9).normal(size=(24, 8))
    result = paired_review(reference, reference, budget=6)
    assert result["priority"] == []
    np.testing.assert_array_equal(result["paired_change"], 0)
    np.testing.assert_array_equal(result["pca_novelty"], 0)


def test_change_priority_is_paired_and_components_partition_its_energy():
    reference = np.random.default_rng(9).normal(size=(24, 8))
    observed = reference.copy()
    observed[5] += 2
    observed[11] -= 1
    result = paired_review(reference, observed, budget=6)
    assert result["priority"] == [5, 11]
    np.testing.assert_allclose(
        np.square(result["paired_change"]),
        np.square(result["pca_novelty"]) + np.square(result["pca_explained_change"]),
        atol=1e-12,
    )


def test_review_budget_is_not_forced_number_of_damaged_regions():
    reference = np.random.default_rng(9).normal(size=(24, 8))
    observed = reference.copy()
    observed[3] += 0.2
    result = paired_review(reference, observed, budget=12)
    assert result["priority"] == [3]
    with pytest.raises(ValueError, match="budget"):
        paired_review(reference, observed, budget=True)


def test_known_truth_confusion_has_correct_denominators():
    result = confusion([1, 0, 1, 0], [1, 1, 0, 0])
    assert result == dict(tp=1, fp=1, fn=1, tn=1, recall=0.5, precision=0.5, f1=0.5, false_positive_rate=0.5)


def test_selection_excludes_warnings_and_excess_normal_false_flags():
    base = dict(eligible=True, normal_control_fpr=0.02, f1=0.8, false_positive_rate=0.03, fit_seconds=0.1)
    valid = dict(base, method="pca")
    warning = dict(base, method="adv", eligible=False, f1=1)
    excessive = dict(base, method="kernel", normal_control_fpr=0.2, f1=1)
    assert select_spectral_configuration([warning, excessive, valid]) is valid
    assert select_spectral_configuration([warning, excessive]) is None
