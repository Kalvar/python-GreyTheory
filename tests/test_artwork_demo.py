"""Image comparisons must preserve reference-only fitting and avoid invented truth."""

import csv
import json

import numpy as np
import pytest

from examples.demos import artwork
from greytheory.analysis import GreyPCA


def image_pair():
    y, x = np.mgrid[:96, :96] / 96
    reference = np.stack([0.1 + 0.7 * x, 0.2 + 0.5 * y, 0.2 + 0.3 * x * y], axis=-1)
    observed = reference.copy()
    observed[24:48, 48:72, 2] += 0.15
    return np.stack([reference, observed])


@pytest.fixture
def pair(tmp_path, monkeypatch):
    reference, observed = tmp_path / "reference.png", tmp_path / "observed.png"
    reference.write_bytes(b"reference-test-hash")
    observed.write_bytes(b"observed-test-hash")
    monkeypatch.setattr(artwork, "load_images", lambda paths, **kwargs: image_pair())
    return reference, observed


def test_features_are_local_and_fit_no_observation_statistics():
    pair = image_pair()
    features, names = artwork.artwork_features(pair)
    assert features.shape == (2, 144, 218)
    assert len(names) == 218 and np.isfinite(features).all()
    independent, _ = artwork.artwork_features(pair[:1])
    np.testing.assert_array_equal(features[0], independent[0])
    assert not np.array_equal(features[0], features[1])


def test_only_reference_tiles_fit_pca_and_no_ground_truth_is_claimed(pair, monkeypatch):
    fitted = []
    original = GreyPCA.fit

    def fit(self, values, y=None):
        assert y is None
        fitted.append(values.copy())
        return original(self, values, y)

    monkeypatch.setattr(GreyPCA, "fit", fit)
    first = artwork.compare_artwork_images(*pair)
    changed = image_pair()
    changed[1] *= 0.7
    monkeypatch.setattr(artwork, "load_images", lambda *args, **kwargs: changed)
    second = artwork.compare_artwork_images(*pair)
    assert len(fitted) == 2 and fitted[0].shape == (144, 218)
    np.testing.assert_array_equal(fitted[0], fitted[1])
    np.testing.assert_array_equal(first["reference_errors"], second["reference_errors"])
    assert first["ground_truth"] is None
    assert first["provenance"]["reference_only_fit"] is True
    assert first["flagged_positions"] == sum(first["flags"])
    assert first["provenance"]["reference_sha256"] != first["provenance"]["observed_sha256"]


def test_stricter_threshold_keeps_a_subset_of_flags(pair):
    loose = artwork.compare_artwork_images(*pair, quantile=0.8)
    strict = artwork.compare_artwork_images(*pair, quantile=0.99)
    assert strict["threshold"] >= loose["threshold"]
    assert np.all(np.asarray(strict["flags"]) <= loose["flags"])


def test_exports_are_reimportable_features_without_coordinate_leakage(pair, tmp_path):
    from examples.workbench.analysis import read_csv

    output = tmp_path / "results"
    artwork.run_artwork_demo(output, reference=pair[0], observed=pair[1])
    dataset = read_csv((output / "observed_features.csv").read_bytes(), "features")
    assert dataset.values.shape == (144, 218)
    assert not {"row", "column", "flag"} & set(dataset.columns)
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["bundled_ai_pair"] is False and summary["ground_truth"] is None
    with (output / "positions.csv").open(encoding="utf-8", newline="") as stream:
        assert len(list(csv.DictReader(stream))) == 144


@pytest.mark.parametrize("quantile", [True, 0.5, 1, float("nan")])
def test_invalid_threshold_is_rejected(pair, quantile):
    with pytest.raises(ValueError, match="quantile"):
        artwork.compare_artwork_images(*pair, quantile=quantile)
