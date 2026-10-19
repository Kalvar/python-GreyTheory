"""Check the release tag, built metadata, and installed package version."""

import argparse
from email.parser import BytesParser
from importlib.metadata import version as installed_version
import json
import os
from pathlib import Path
import re
import tarfile
import tomllib
from zipfile import ZipFile


def check_tag(version, tag):
    if tag:
        if not re.fullmatch(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", version):
            raise ValueError(f"A stable release requires a major.minor.patch version, got {version!r}")
        if tag not in {version, f"v{version}"}:
            raise ValueError(f"Release tag {tag!r} must be {version!r} or 'v{version}'")


def check_distributions(directory, version):
    wheels, sources = sorted(directory.glob("*.whl")), sorted(directory.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sources) != 1:
        raise ValueError("Expected exactly one wheel and one sdist in the distribution directory")
    with ZipFile(wheels[0]) as wheel:
        metadata = [name for name in wheel.namelist() if name.endswith(".dist-info/METADATA")]
        if len(metadata) != 1:
            raise ValueError("Wheel must contain exactly one METADATA file")
        wheel_metadata = BytesParser().parsebytes(wheel.read(metadata[0]))
    with tarfile.open(sources[0], "r:gz") as source:
        metadata = [member for member in source.getmembers()
                    if len(Path(member.name).parts) == 2 and member.name.endswith("/PKG-INFO")]
        if len(metadata) != 1:
            raise ValueError("Source distribution must contain one top-level PKG-INFO file")
        with source.extractfile(metadata[0]) as stream:
            source_metadata = BytesParser().parsebytes(stream.read())
    for name, metadata in [(wheels[0].name, wheel_metadata), (sources[0].name, source_metadata)]:
        if metadata["Name"] != "greytheory" or metadata["Version"] != version:
            raise ValueError(f"{name}: expected greytheory {version}, got {metadata['Name']} {metadata['Version']}")
    return [path.name for path in wheels + sources]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default=os.environ.get("RELEASE_TAG", ""))
    parser.add_argument("--dist", type=Path)
    parser.add_argument("--installed", action="store_true")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    try:
        check_tag(version, args.tag)
        result = {"version": version, "tag": args.tag, "status": "PASS"}
        if args.dist is not None:
            result["distributions"] = check_distributions(args.dist, version)
        if args.installed:
            import greytheory

            metadata_version = installed_version("greytheory")
            if metadata_version != version or greytheory.__version__ != version:
                raise ValueError(f"Version mismatch: source={version}, installed={metadata_version}, runtime={greytheory.__version__}")
            result["installed_version"] = metadata_version
            result["package_path"] = greytheory.__file__
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
