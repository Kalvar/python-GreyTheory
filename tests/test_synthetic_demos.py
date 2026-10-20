"""Synthetic truth, file integrity, and reference/query separation."""

import csv
import json

import numpy as np
import pytest

from examples.demos import make_xrf_data, run_handwriting_demo, run_xrf_demo
from examples.demos.handwriting import ASSETS, _sheet_cells
from examples.demos.xrf import _write_emsa, _write_spx
from greytheory.io.bruker import read_spx


def test_xrf_seed_truth_and_known_element_peaks():
    data = make_xrf_data(seed=11, map_shape=(3, 3), n_maps=2, n_channels=512)
    repeated = make_xrf_data(seed=11, map_shape=(3, 3), n_maps=2, n_channels=512)
    assert data.counts.shape == (18, 512)
    assert data.counts.dtype.kind == "u"
    np.testing.assert_array_equal(data.counts, repeated.counts)
    np.testing.assert_allclose(data.mixing_weights.sum(axis=1), 1)
    assert np.all(data.mixing_weights >= 0)
    assert not np.array_equal(data.counts[:9], data.counts[9:])
    copper = np.abs(data.energy_keV - 8.04) < .08
    calcium = np.abs(data.energy_keV - 3.69) < .08
    assert data.counts[data.material_ids == 2][:, copper].mean() > data.counts[data.material_ids == 0][:, copper].mean()
    assert data.counts[data.material_ids == 0][:, calcium].mean() > data.counts[data.material_ids == 2][:, calcium].mean()


def test_synthetic_exchange_files_preserve_counts_and_calibration(tmp_path):
    counts = np.array([0, 2, 41, 1000], dtype=np.uint32)
    _write_spx(tmp_path / "sample.spx", counts, .02)
    result = read_spx(tmp_path / "sample.spx")
    np.testing.assert_array_equal(result.counts, counts)
    np.testing.assert_allclose(result.energy, [0, .02, .04, .06])
    assert result.metadata["Synthetic"] == "true"
    _write_emsa(tmp_path / "sample.msa", counts, .02)
    text = (tmp_path / "sample.msa").read_text()
    assert "SYNTHETIC" in text and "#FORMAT      : EMSA/MAS Spectral Data File" in text
    values = text.split("#SPECTRUM    : Begin synthetic counts\n", 1)[1].split("#ENDOFDATA", 1)[0]
    np.testing.assert_array_equal(np.fromstring(values, sep="\n"), counts)


def test_ai_sheet_has_distinct_reference_and_query_cells():
    asset = ASSETS / "handwriting_ai_sheet.png"
    images, records = _sheet_cells(asset)
    assert images.shape == (18, 96, 288)
    assert sum(row["split"] == "reference" for row in records) == 12
    assert sum(row["split"] == "query" for row in records) == 6
    reference_hashes = {row["roi_sha256"] for row in records if row["split"] == "reference"}
    query_hashes = {row["roi_sha256"] for row in records if row["split"] == "query"}
    assert reference_hashes.isdisjoint(query_hashes)
    assert len(reference_hashes | query_hashes) == 18
    provenance = json.loads((ASSETS / "handwriting_ai_sheet.json").read_text(encoding="utf-8"))
    assert provenance["synthetic"] is True
    assert "not verified" in provenance["labels"]


def test_handwriting_demo_does_not_fit_query_rows_or_use_style_ids_as_targets(tmp_path, monkeypatch):
    from examples.demos import handwriting

    original_fit = handwriting.GreyPCA.fit
    fit_rows = []

    def record_fit(self, X, y=None):
        assert y is None
        fit_rows.append(len(X))
        return original_fit(self, X, y)

    monkeypatch.setattr(handwriting.GreyPCA, "fit", record_fit)
    result = run_handwriting_demo(tmp_path / "writing")
    assert fit_rows == [12]
    assert result["report"].exists()
    assert len(result["summary"]["metrics"]) == 2
    for metric in result["summary"]["metrics"]:
        assert metric["queries"] == 6 and 0 <= metric["synthetic_style_top1"] <= 1
    with (tmp_path / "writing/ranking.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 6 * 12 * 2
    assert all(row["query"] != row["reference"] for row in rows)


def test_xrf_report_holds_out_an_entire_map(tmp_path):
    result = run_xrf_demo(tmp_path / "xrf")
    summary = result["summary"]
    assert set(summary["train_maps"]).isdisjoint(summary["test_maps"])
    assert summary["spectra"] == 144 and summary["channels"] == 1024
    assert all(np.isfinite(metric["held_out_map_mae"]) for metric in summary["metrics"])
    assert len(list((tmp_path / "xrf/emsa").glob("*.msa"))) == 144
    assert len(list((tmp_path / "xrf/spx").glob("*.spx"))) == 144
    with (tmp_path / "xrf/predictions.csv").open(newline="", encoding="utf-8") as stream:
        predictions = list(csv.DictReader(stream))
    assert len(predictions) == 36
    assert all(row["sample"].startswith("map03_") for row in predictions)


@pytest.mark.parametrize("settings", [{"n_maps": 1}, {"n_channels": 128}, {"map_shape": (2, 3)}, {"seed": -1}])
def test_invalid_xrf_generator_settings_are_rejected(settings):
    with pytest.raises(ValueError):
        make_xrf_data(**settings)
