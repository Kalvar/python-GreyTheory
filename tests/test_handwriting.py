"""The short workflow must preserve reference-only fitting and portable results."""

import csv
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
from PIL import Image
import pytest

from examples.image_files import create_demo_images
from greytheory import compare_handwriting
from greytheory.handwriting import compare_image_files


def test_one_call_preserves_existing_pipeline_and_never_fits_query(tmp_path, monkeypatch):
    from greytheory import handwriting

    paths, query = create_demo_images(tmp_path / "inputs")
    original = handwriting.GreyPCA.fit
    fitted_rows = []

    def fit(self, X, y=None):
        fitted_rows.append(len(X))
        return original(self, X, y)

    monkeypatch.setattr(handwriting.GreyPCA, "fit", fit)
    result = compare_handwriting(query, paths, output=tmp_path / "results", size=(96, 64))
    assert fitted_rows == [8]
    expected = compare_image_files(paths, query)
    assert result.best_match == paths[3]
    assert result.best_distance == pytest.approx(0, abs=1e-5)
    np.testing.assert_array_equal([m.reference for m in result.matches], np.asarray(paths)[expected["ranking"]])
    np.testing.assert_allclose([m.distance for m in result.matches], expected["distances"][expected["ranking"]])
    with (result.output_dir / "ranking.csv").open(newline="", encoding="utf-8") as stream:
        ranking = list(csv.DictReader(stream))
    assert ranking[0]["reference"] == str(paths[3])
    assert len(ranking) == 8


def test_nested_folder_excludes_query_and_duplicate_paths_and_escapes_names(tmp_path):
    paths, query = create_demo_images(tmp_path / "來源 圖片")
    nested = paths[0].parent / "作者 A"
    nested.mkdir()
    renamed = nested / "A & B.PNG"
    paths[0].rename(renamed)
    embedded_query = paths[1].parent / "待比較.png"
    embedded_query.write_bytes(query.read_bytes())
    result = compare_handwriting(embedded_query, paths[1].parent, output=tmp_path / "results")
    assert len(result.matches) == 8
    assert all(item.reference.resolve() != embedded_query.resolve() for item in result.matches)
    assert result.best_match == paths[3]
    assert "A &amp; B.PNG" in result.report.read_text(encoding="utf-8")
    explicit = [renamed, *paths[1:], renamed, embedded_query]
    repeated = compare_handwriting(embedded_query, explicit, output=tmp_path / "second")
    assert len(repeated.matches) == 8


def test_default_handles_different_sizes_and_report_has_embedded_previews(tmp_path):
    paths, query = create_demo_images(tmp_path / "inputs")
    with Image.open(paths[0]) as image:
        image.resize((192, 128)).save(paths[0])
    result = compare_handwriting(query, paths[0].parent, output=tmp_path / "results")
    summary = json.loads((result.output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["size"] == [288, 96]
    assert summary["query_in_fit"] is False
    previews, links = [], []

    class ReportLinks(HTMLParser):
        def handle_starttag(self, tag, attrs):
            attributes = dict(attrs)
            if tag == "img":
                previews.append(attributes["src"])
            if tag == "a":
                links.append(attributes["href"])

    ReportLinks().feed(result.report.read_text(encoding="utf-8"))
    assert len(previews) == 2 and all(value.startswith("data:image/png;base64,") for value in previews)
    assert all((result.output_dir / value).is_file() for value in links)


def test_one_call_accepts_adv_options(tmp_path):
    paths, query = create_demo_images(tmp_path / "inputs")
    result = compare_handwriting(query, paths, output=tmp_path / "results", pca="adv", pca_params={"delta": 0})
    assert result.best_match == paths[3]
    summary = json.loads((result.output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["pca"] == "adv" and summary["pca_params"] == {"delta": 0}


def test_bad_paths_and_too_few_references_do_not_create_results(tmp_path):
    paths, query = create_demo_images(tmp_path / "inputs")
    output = tmp_path / "results"
    with pytest.raises(FileNotFoundError, match="query image"):
        compare_handwriting(tmp_path / "missing.png", paths, output=output)
    with pytest.raises(ValueError, match="reference folder"):
        compare_handwriting(query, tmp_path / "missing", output=output)
    with pytest.raises(ValueError, match="three distinct"):
        compare_handwriting(query, [paths[0], paths[0], paths[1], query], output=output)
    assert not output.exists()


def test_module_cli_handles_paths_with_spaces_and_reports_errors_without_traceback(tmp_path):
    paths, query = create_demo_images(tmp_path / "input pictures")
    output = tmp_path / "output report"
    command = [sys.executable, "-m", "greytheory", "handwriting", str(query), str(paths[0].parent), "--output", str(output)]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    assert "sample_03.png" in result.stdout and str((output / "index.html").resolve()) in result.stdout
    command[4] = str(tmp_path / "missing.png")
    failed = subprocess.run(command, capture_output=True, text=True)
    assert failed.returncode == 2 and "query image does not exist" in failed.stderr
    assert "Traceback" not in failed.stderr


def test_bootstrap_installs_image_extra_once_and_base_run_reuses_environment(tmp_path, monkeypatch):
    import run

    (tmp_path / "pyproject.toml").write_text("project metadata")
    (tmp_path / "setup.py").write_text("setup metadata")
    python = tmp_path / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    python.parent.mkdir(parents=True)
    python.touch()
    calls = []
    monkeypatch.setattr(run.subprocess, "check_call", lambda command, **kwargs: calls.append(command))
    monkeypatch.setattr(run.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0))
    assert run.prepare_environment(tmp_path, extras=("images",)) == python
    assert calls[0][-1] == ".[images]"
    calls.clear()
    run.prepare_environment(tmp_path, extras=("images",))
    run.prepare_environment(tmp_path)
    assert not calls


def test_bootstrap_short_command_forwards_absolute_paths_and_image_extra(tmp_path, monkeypatch):
    import run

    paths, query = create_demo_images(tmp_path / "input pictures")
    output = tmp_path / "output report"
    prepared = []

    def prepare(root, *, extras=()):
        prepared.append(extras)
        return Path(sys.executable)

    monkeypatch.setattr(run, "prepare_environment", prepare)
    assert run.main(["handwriting", str(query), str(paths[0].parent), "--output", str(output)]) == 0
    assert prepared == [("images",)]
    assert (output / "index.html").is_file()
