"""Exercise demo data contracts, real API calculations, and the no-socket boundary."""

import base64
import json

import numpy as np
import pytest

from examples.workbench.analysis import METHODS, analyze, read_csv, read_spectrum_file, spectra_dataset
from examples.workbench.doe import DATA, SPECS, generate
from examples.workbench.backend import Backend
from greytheory.analysis import GreyFeatureSelector


def test_doe_reproducible_design_and_no_response_leakage(tmp_path):
    manifest = generate(tmp_path)
    assert manifest["total_runs"] == 30 and manifest["synthetic"]
    for process, spec in SPECS.items():
        assert (tmp_path / f"{process}_15.csv").read_bytes() == (DATA / f"{process}_15.csv").read_bytes()
        dataset = read_csv((tmp_path / f"{process}_15.csv").read_bytes(), process, spec)
        assert dataset.values.shape == (15, 10)
        np.testing.assert_array_equal(dataset.values[-3:, :6], np.tile(dataset.values[-1, :6], (3, 1)))
        assert not np.array_equal(dataset.values[-1, 6:], dataset.values[-2, 6:])
        assert set(dataset.defaults).isdisjoint(dataset.targets)
        result = analyze(dataset, {"features": dataset.defaults, "target": dataset.targets[0]})
        selector = GreyFeatureSelector(k=None, direction="either", constant_policy="exclude").fit(
            dataset.values[:, :6], dataset.values[:, 6]
        )
        scores = {row["feature"]: row["score"] for row in result["ranking"]}
        np.testing.assert_allclose([scores[n] for n in dataset.defaults], selector.scores)
        with pytest.raises(ValueError, match="目標欄位不能"):
            analyze(
                dataset, {"features": [*dataset.defaults, dataset.targets[0]], "target": dataset.targets[0]}
            )


@pytest.mark.parametrize("method", METHODS)
def test_all_pca_backends_and_target_free_ranking(method):
    dataset = read_csv((DATA / "pvd_15.csv").read_bytes(), "PVD", SPECS["pvd"])
    result = analyze(dataset, {"features": dataset.defaults, "method": method})
    assert np.asarray(result["coordinates"]).shape == (15, 2)
    assert np.isfinite(result["coordinates"]).all()
    assert "非 GRA" in result["ranking_label"]
    assert len(result["ranking"]) == 6
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("data", [b"a,a\n1,2", b"a,b\n1", b"a,b\n", b"a\nx"])
def test_csv_rejects_invalid_structure(data):
    with pytest.raises(ValueError):
        read_csv(data)


def test_csv_handles_missing_and_utf8_labels():
    dataset = read_csv("run_id,a,b,c\n試片一,1,,7\n試片二,2,NaN,7\n試片三,4,8,7".encode())
    assert dataset.columns == ["a", "c"] and dataset.labels[0] == "試片一"
    result = analyze(dataset, {"components": 1})
    assert result["features"] == ["a"] and "常數" in result["warnings"][-1]


def test_spectrum_binning_preserves_counts_and_normalization_ignores_target():
    counts = np.arange(3 * 130).reshape(3, 130) + 1
    dataset = spectra_dataset("counts", counts, np.arange(130) * 0.1)
    np.testing.assert_allclose(dataset.values.sum(axis=1), counts.sum(axis=1))
    assert dataset.values.shape == (3, 64)
    dataset.defaults = dataset.columns.copy()
    target = np.array([1.0, 3.0, 9.0])
    dataset.columns.append("target")
    dataset.values = np.column_stack([dataset.values, target])
    result = analyze(dataset, {"features": dataset.defaults, "target": "target"})
    values = dataset.values[:, :64] / counts.sum(axis=1, keepdims=True)
    selector = GreyFeatureSelector(k=None, direction="either", constant_policy="exclude").fit(values, target)
    scores = {r["feature"]: r["score"] for r in result["ranking"]}
    eligible = np.ptp(values, axis=0) > 0
    np.testing.assert_allclose(
        [scores[n] for n, ok in zip(dataset.defaults, eligible) if ok], selector.scores[eligible]
    )


def test_multi_spx_selects_requested_spectrum_without_merging(tmp_path):
    path = tmp_path / "multi.spx"
    path.write_text("""<TRTSpectrum><ClassInstance Type="TRTSpectrum" Name="sample">
    <ChannelCount>3</ChannelCount><Channels>1,2,3</Channels><ChildClassInstances>
    <ClassInstance Type="TRTSpectrum" Name="Background"><ChannelCount>3</ChannelCount>
    <Channels>4.5,5,6</Channels></ClassInstance></ChildClassInstances></ClassInstance></TRTSpectrum>""")
    first = read_spectrum_file(path)
    second = read_spectrum_file(path, spectrum_index=1)
    assert first.values.sum() == 6 and second.values.sum() == 15.5
    with pytest.raises(ValueError, match="至少 3"):
        analyze(first, {})
    with pytest.raises(ValueError, match="光譜索引"):
        read_spectrum_file(path, spectrum_index=2)


def test_in_process_backend_has_no_listening_socket(monkeypatch):
    import socket

    monkeypatch.setattr(socket.socket, "bind", lambda *args: pytest.fail("No listening sockets are allowed"))
    backend = Backend()
    assert backend.config()["scenarios"]
    dataset = backend.request("/api/load", {"id": "doe:pvd"})
    result = backend.request(
        "/api/analyze", {"dataset": dataset["id"], "features": dataset["defaults"], "target": "thickness_nm"}
    )
    assert len(result["ranking"]) == 6
    with pytest.raises(ValueError):
        backend.request("/api/load", {"id": "local:../../pyproject.toml"})
    upload = {"name": "example.csv", "data": base64.b64encode(b"x,y\n1,2\n2,4\n3,6").decode()}
    assert backend.request("/api/load", {"upload": upload})["columns"] == ["x", "y"]


def test_one_command_launcher_starts_source_workbench(monkeypatch):
    import run

    calls = []

    def environment(root, *, extras):
        assert extras == ("workbench",)
        return root / ".venv" / "python-for-test"

    monkeypatch.setattr(run, "prepare_environment", environment)
    monkeypatch.setattr(
        run.subprocess, "call", lambda command, **kwargs: calls.append((command, kwargs)) or 0
    )
    assert run.main(["workbench"]) == 0
    command, kwargs = calls[0]
    assert command[1:] == ["-m", "examples.workbench.desktop"]
    assert kwargs["cwd"] == run.Path(run.__file__).resolve().parent


def test_desktop_launcher_uses_file_url_and_disables_http(monkeypatch):
    import sys
    from types import SimpleNamespace
    from examples.workbench import desktop

    calls = {}

    def create_window(*args, **kwargs):
        calls["url"] = kwargs["url"]
        calls["bridge"] = kwargs["js_api"]
        return object()

    fake = SimpleNamespace(
        create_window=create_window, start=lambda **kwargs: calls.update(kwargs), settings={}
    )
    monkeypatch.setitem(sys.modules, "webview", fake)
    assert desktop.main([]) == 0
    assert calls["url"].startswith("file://") and calls["url"].endswith("#desktop")
    assert calls["http_server"] is False


def test_exported_request_roundtrip(tmp_path, monkeypatch):
    import socket
    from examples.workbench.desktop import execute_file

    monkeypatch.setattr(socket.socket, "bind", lambda *args: pytest.fail("No server allowed"))
    path = tmp_path / "request.json"
    path.write_text(
        json.dumps(
            dict(
                format="greytheory-request-v1",
                endpoint="/api/analyze",
                source={"id": "doe:pvd"},
                body={
                    "dataset": "preview:doe:pvd",
                    "features": list(SPECS["pvd"]["features"]),
                    "target": "thickness_nm",
                },
            )
        )
    )
    result = json.loads(execute_file(path).read_text())
    assert result["dataset"]["rows"] == 15 and len(result["result"]["ranking"]) == 6


def test_ai_handwriting_preview_preserves_paper_and_ink_contrast():
    from io import BytesIO
    from PIL import Image

    result = Backend().request("/api/handwriting", {"demo": True, "method": "pca"})
    for data in [result["query"], result["matches"][0]["image"]]:
        pixels = np.asarray(Image.open(BytesIO(base64.b64decode(data.split(",")[1]))).convert("L"))
        assert pixels.max() > 200 and pixels.min() < 100
        assert pixels.mean() > 100


@pytest.mark.parametrize(
    "header, expected",
    [
        (b"AAMVHFSS" + bytes(400), "目前讀取器不支援"),
        (b"not a BCF", "無法辨識"),
    ],
)
def test_bcf_load_error_explains_recognized_and_invalid_headers(tmp_path, header, expected):
    path = tmp_path / "example.bcf"
    path.write_bytes(header)
    with pytest.raises(ValueError, match=expected) as failure:
        read_spectrum_file(path)
    assert failure.value.__cause__ is not None


def test_local_catalog_preflights_files_caches_and_rechecks_changes(tmp_path, monkeypatch):
    import examples.workbench.backend as module
    from scripts._synthetic import make_spx

    folder = tmp_path / "data/test"
    folder.mkdir(parents=True)
    make_spx(folder / "single.spx")
    (folder / "table.csv").write_text("a,b\n1,2\n2,4\n3,5\n")
    invalid = folder / "unsupported.bcf"
    invalid.write_bytes(b"AAMVHFSS" + bytes(400))
    (folder / "bad.csv").write_text("a,b\nnot,numeric\n")
    (folder / "bad.spx").write_text("<broken")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    reader = module.read_spectrum_file
    calls = []

    def counted(path, **kwargs):
        calls.append(path.name)
        return reader(path, **kwargs)

    monkeypatch.setattr(module, "read_spectrum_file", counted)
    backend = module.Backend()
    config = backend.config()
    available = {entry["id"]: entry for entry in config["catalog"]}
    assert "local:table.csv" in available
    assert "單筆光譜 → 多位置分析 ✗" in available["local:single.spx"]["name"]
    assert "多樣本分析 ✓" in available["local:table.csv"]["name"]
    assert {item["name"] for item in config["unavailable"]} == {"unsupported.bcf", "bad.csv", "bad.spx"}
    assert not any("unsupported.bcf" in key for key in available)
    backend.config()
    backend.request("/api/load", {"id": "local:table.csv"})
    assert calls.count("unsupported.bcf") == 1
    assert calls.count("single.spx") == 1
    with pytest.raises(ValueError, match="清單"):
        backend.request("/api/load", {"id": "local:unsupported.bcf"})
    (folder / "table.csv").write_text("bad\ntext\n")
    assert "local:table.csv" not in {item["id"] for item in backend.catalog()}
    (folder / "table.csv").write_text("a,b\n1,2\n2,4\n3,5\n")
    assert "local:table.csv" in {item["id"] for item in backend.catalog()}
    invalid.unlink()
    assert "unsupported.bcf" not in {item["name"] for item in backend.config()["unavailable"]}


def test_public_preview_excludes_private_file_validation(tmp_path, monkeypatch):
    import examples.workbench.backend as module
    from examples.workbench.build_preview import build

    folder = tmp_path / "data/test"
    folder.mkdir(parents=True)
    (folder / "private-customer.bcf").write_bytes(b"not a valid bcf")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    output = build(tmp_path / "preview.js")
    text = output.read_text()
    assert "private-customer" not in text
    payload = json.loads(text.split("window.GREY_PREVIEW=", 1)[1].rstrip(";\n"))
    assert payload["config"]["unavailable"] == []
    assert all(not item["id"].startswith("local:") for item in payload["config"]["catalog"])
