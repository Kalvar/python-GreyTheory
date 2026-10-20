"""Release metadata must agree before artifacts can be published."""

import io
import tarfile
from zipfile import ZipFile

import pytest

from greytheory import _version
from scripts.check_release import check_distributions, check_tag


def test_source_version_uses_pyproject_even_with_an_older_installed_package(tmp_path, monkeypatch):
    (tmp_path / "greytheory").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "greytheory"\nversion = "2.0.1"\n')
    monkeypatch.setattr(_version, "__file__", str(tmp_path / "greytheory/_version.py"))
    monkeypatch.setattr(_version, "version", lambda name: "0.1")
    assert _version.get_version() == "2.0.1"


def test_installed_version_comes_from_distribution_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(_version, "__file__", str(tmp_path / "greytheory/_version.py"))

    def metadata_version(name):
        assert name == "greytheory"
        return "2.0.1"

    monkeypatch.setattr(_version, "version", metadata_version)
    assert _version.get_version() == "2.0.1"


@pytest.mark.parametrize("tag", ["v2.0.0", "v2.0.1a1", "v0.1"])
def test_wrong_release_tag_is_rejected(tag):
    with pytest.raises(ValueError, match="Release tag"):
        check_tag("2.0.1", tag)


def test_stable_release_tag_and_version_are_required():
    check_tag("2.0.1", "v2.0.1")
    check_tag("2.0.1", "2.0.1")
    with pytest.raises(ValueError, match="stable release"):
        check_tag("2.0.1a1", "v2.0.1a1")


@pytest.mark.parametrize(
    "wheel_version,source_version", [("2.0.1", "2.0.1"), ("0.1", "2.0.1"), ("2.0.1", "2.0.0a1")]
)
def test_wheel_and_sdist_must_both_have_the_release_version(tmp_path, wheel_version, source_version):
    wheel = tmp_path / "greytheory-2.0.1-py3-none-any.whl"
    with ZipFile(wheel, "w") as bundle:
        bundle.writestr(
            "greytheory-2.0.1.dist-info/METADATA", f"Name: greytheory\nVersion: {wheel_version}\n"
        )
    source = tmp_path / "greytheory-2.0.1.tar.gz"
    contents = f"Name: greytheory\nVersion: {source_version}\n".encode()
    with tarfile.open(source, "w:gz") as bundle:
        info = tarfile.TarInfo("greytheory-2.0.1/PKG-INFO")
        info.size = len(contents)
        bundle.addfile(info, io.BytesIO(contents))
    if wheel_version == source_version == "2.0.1":
        assert check_distributions(tmp_path, "2.0.1") == [wheel.name, source.name]
    else:
        with pytest.raises(ValueError, match="expected greytheory"):
            check_distributions(tmp_path, "2.0.1")


def test_release_mismatch_reports_actionable_summary(tmp_path, monkeypatch):
    from scripts.check_release import main

    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    with pytest.raises(SystemExit) as failure:
        main(["--tag", "v0.0.0"])
    assert failure.value.code == 2
    text = summary.read_text(encoding="utf-8")
    assert "v0.0.0" in text
    assert f"Expected release tag: `v{_version.get_version()}`" in text
    assert "original commit" in text


def test_matching_release_summary(tmp_path, monkeypatch):
    from scripts.check_release import main

    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    main(["--tag", f"v{_version.get_version()}"])
    assert "Version check passed" in summary.read_text(encoding="utf-8")
