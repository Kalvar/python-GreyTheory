"""Round-trip and provenance checks for local, source-derived BCF simulations."""

import hashlib
import json

import numpy as np
import pytest

from scripts.make_m4_variant import generate, write_demo_bcf
from greytheory.io.bruker import read_bcf
from examples.workbench.analysis import analyze, read_spectrum_file


def test_variant_roundtrip_reproducibility_and_source_preservation(tmp_path):
    axis = np.linspace(-1, 20, 1024)
    counts = np.full((3, 3, 1024), 8, dtype=np.uint64)
    source = tmp_path / "source.bcf"
    write_demo_bcf(source, {0: counts, 1: counts + 2}, {0: axis, 1: axis + 0.001})
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    output = tmp_path / "simulated.bcf"
    other = tmp_path / "repeat.bcf"
    manifest = generate(source, output)
    generate(source, other)
    assert output.read_bytes() == other.read_bytes()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
    assert manifest["simulated"] and manifest["source_sha256"] == source_hash
    assert manifest["shape"] == [3, 3, 1024]
    actual = read_bcf(output)
    assert actual.detectors == (0, 1)
    assert not np.array_equal(actual.energy_axes[0], actual.energy_axes[1])
    assert not np.array_equal(actual.get_spectra(detector=0), counts)
    metadata = json.loads(output.with_suffix(".simulation.json").read_text(encoding="utf-8"))
    assert metadata["output_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert "0.9–1.1" in metadata["changes"]
    dataset = read_spectrum_file(output)
    result = analyze(dataset, {"method": "pca", "components": 2})
    assert np.asarray(result["coordinates"]).shape == (9, 2)
    assert np.isfinite(result["coordinates"]).all()
    with pytest.raises(ValueError, match="differ"):
        generate(source, source)


def test_demo_writer_preserves_counts_above_one_byte(tmp_path):
    counts = np.array([[[0, 15, 255, 256, 65535]]], dtype=np.uint64)
    axis = np.arange(5) * 0.01
    path = tmp_path / "counts.bcf"
    write_demo_bcf(path, {0: counts}, {0: axis})
    np.testing.assert_array_equal(read_bcf(path).get_spectra(), counts)
