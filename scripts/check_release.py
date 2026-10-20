"""Check the release tag, built metadata, and installed package version."""

import argparse
from email.parser import BytesParser
from importlib.metadata import version as installed_version
from html.parser import HTMLParser
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


def check_readme_links(text):
    """PyPI resolves relative links against its own domain, not the GitHub repo."""
    lines, fence = [], None
    for line in text.splitlines():
        match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if match:
            if fence is None:
                fence = match[1][0]
            elif match[1][0] == fence:
                fence = None
            continue
        if fence is None:
            lines.append(line)
    visible = re.sub(r"`+[^`\n]+`+", "", "\n".join(lines))
    links = re.findall(r"\]\(\s*<?([^\s)>]+)", visible)
    links += re.findall(r"^\s*\[[^]\n]+\]:\s*<?([^\s>]+)", visible, re.MULTILINE)

    class Links(HTMLParser):
        def handle_starttag(self, tag, attrs):
            for name, value in attrs:
                if name in {"href", "src"} and value:
                    links.append(value)

    Links().feed(visible)
    relative = sorted(
        {url for url in links if not url.startswith("#") and not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", url)}
    )
    if relative:
        raise ValueError(
            "README has relative links that break on PyPI: "
            + ", ".join(relative)
            + ". Use absolute URLs for repository files and images."
        )


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
        metadata = [
            member
            for member in source.getmembers()
            if len(Path(member.name).parts) == 2 and member.name.endswith("/PKG-INFO")
        ]
        if len(metadata) != 1:
            raise ValueError("Source distribution must contain one top-level PKG-INFO file")
        with source.extractfile(metadata[0]) as stream:
            source_metadata = BytesParser().parsebytes(stream.read())
    for name, metadata in [(wheels[0].name, wheel_metadata), (sources[0].name, source_metadata)]:
        if metadata["Name"] != "greytheory" or metadata["Version"] != version:
            raise ValueError(
                f"{name}: expected greytheory {version}, got {metadata['Name']} {metadata['Version']}"
            )
        check_readme_links((metadata.get_payload(decode=True) or b"").decode("utf-8"))
    return [path.name for path in wheels + sources]


def write_summary(version, tag, error=None):
    """Expose version mismatches on the Actions run overview, not just in logs."""
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary:
        return
    text = (
        "## Release version check\n\n"
        f"- Package version: `{version}`\n"
        f"- Release tag: `{tag or '(not a release)'}`\n"
        f"- Expected release tag: `v{version}`\n"
    )
    if error:
        text += (
            f"\n**Failed:** {error}\n\n"
            "For README link errors, use absolute repository and image URLs. "
            "For version errors, set the package version in pyproject.toml, commit and push it, then create "
            "the matching release tag at that commit. An existing tag does not follow "
            "updates to master; re-running an old release uses its original commit.\n"
        )
    else:
        text += "\nVersion check passed.\n"
    with Path(summary).open("a", encoding="utf-8") as handle:
        handle.write(text)


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
        check_readme_links((root / "README.md").read_text(encoding="utf-8"))
        result = {"version": version, "tag": args.tag, "status": "PASS"}
        if args.dist is not None:
            result["distributions"] = check_distributions(args.dist, version)
        if args.installed:
            import greytheory

            metadata_version = installed_version("greytheory")
            if metadata_version != version or greytheory.__version__ != version:
                raise ValueError(
                    f"Version mismatch: source={version}, installed={metadata_version}, runtime={greytheory.__version__}"
                )
            result["installed_version"] = metadata_version
            result["package_path"] = greytheory.__file__
    except ValueError as error:
        write_summary(version, args.tag, str(error))
        parser.error(str(error))
    write_summary(version, args.tag)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
