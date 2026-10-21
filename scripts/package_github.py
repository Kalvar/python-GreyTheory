"""Bundle public source and synthetic demo results: python3 scripts/package_github.py."""

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT_FILES = (
    ".gitignore",
    "LICENSE",
    "MANIFEST.in",
    "README.md",
    "README.zh-TW.md",
    "README.ja.md",
    "THIRD_PARTY_NOTICES.md",
    "pyproject.toml",
    "requirements-dev.txt",
    "setup.py",
    "run.py",
    "example.py",
    ".github/workflows/ci.yml",
    ".github/workflows/publish.yml",
    ".github/workflows/verify.yml",
    "scripts/_synthetic.py",
    "scripts/make_m4_variant.py",
    "scripts/verify_full_install.py",
    "scripts/package_github.py",
    "scripts/check_release.py",
    "tests/fixtures/legacy_golden.json",
    "data/README.md",
    "data/demo/index.html",
    "data/demo/README.md",
    "data/demo/catalog.json",
    "data/demo/handwriting/handwriting_ai_sheet.png",
    "data/demo/handwriting/handwriting_ai_sheet.json",
)
RESULTS = Path("data/demo/results")


def public_files(root):
    """Use an allowlist; never walk local artifacts, environments, or Git metadata."""
    paths = {root / name for name in ROOT_FILES}
    paths.update(
        root / name
        for name in (
            "docs/README.md",
            "docs/README.zh-TW.md",
            "docs/README.ja.md",
            "docs/guide.md",
            "docs/guide.zh-TW.md",
            "docs/guide.ja.md",
            "docs/images/greytheory-banner.svg",
            "docs/images/workbench-research.en.png",
            "docs/images/workbench-research.zh-TW.png",
            "docs/images/workbench-research.ja.png",
            "docs/images/workbench-research-gpr.en.png",
            "docs/images/workbench-research-gpr.zh-TW.png",
            "docs/images/workbench-research-gpr.ja.png",
            "docs/images/workbench-optimization.en.png",
            "docs/images/workbench-optimization.zh-TW.png",
            "docs/images/workbench-optimization.ja.png",
            "docs/images/workbench-doe.en.png",
            "docs/images/workbench-doe.zh-TW.png",
            "docs/images/workbench-doe.ja.png",
            "docs/images/workbench-routes.en.png",
            "docs/images/workbench-routes.zh-TW.png",
            "docs/images/workbench-routes.ja.png",
            "docs/images/workbench-art.en.png",
            "docs/images/workbench-art.zh-TW.png",
            "docs/images/workbench-art.ja.png",
            "docs/images/workbench-handwriting.en.png",
            "docs/images/workbench-handwriting.zh-TW.png",
            "docs/images/workbench-handwriting.ja.png",
            "docs/images/workbench-manual.en.png",
            "docs/images/workbench-manual.zh-TW.png",
            "docs/images/workbench-manual.ja.png",
            "docs/images/workbench-art-image.en.png",
            "docs/images/workbench-art-image.zh-TW.png",
            "docs/images/workbench-art-image.ja.png",
            "docs/images/workbench-art-review.en.png",
            "docs/images/workbench-art-review.zh-TW.png",
            "docs/images/workbench-art-review.ja.png",
            "scripts/capture_docs.py",
        )
    )
    for directory in ("greytheory", "tests", "examples", "benchmarks"):
        for path in (root / directory).rglob("*.py"):
            relative = path.relative_to(root)
            if "__pycache__" not in relative.parts and relative.parts[:3] != (
                "tests",
                "fixtures",
                "external",
            ):
                paths.add(path)
    paths.add(root / "examples/workbench/index.html")
    for pattern in ("*.css", "*.js"):
        paths.update((root / "examples/workbench/static").glob(pattern))
    for pattern in ("*.csv", "*.json"):
        paths.update((root / "data/demo/doe").glob(pattern))
    for pattern in (
        "*.png",
        "*.json",
        "*.html",
        "results/*.json",
        "results/*.csv",
        "review/*.json",
        "review/*.csv",
        "review/*.html",
        "review/*.js",
        "review/*.css",
    ):
        paths.update((root / "data/demo/artwork").glob(pattern))
    paths.update((root / "data/demo/scenarios").glob("*.json"))
    paths.update((root / "benchmarks/results").glob("*.json"))
    results = root / RESULTS
    paths.add(results / "index.html")
    for name in (
        "dataset.npz",
        "spectra.csv",
        "samples.csv",
        "energy_ranking.csv",
        "predictions.csv",
        "summary.json",
        "spectra_and_ranking.svg",
        "spectra_and_ranking.png",
        "held_out_map.svg",
        "held_out_map.png",
        "index.html",
    ):
        paths.add(results / "xrf" / name)
    for map_id in range(4):
        for y in range(6):
            for x in range(6):
                sample = f"map{map_id:02d}_y{y:02d}_x{x:02d}"
                for directory, extension in (("emsa", "msa"), ("spx", "spx")):
                    paths.add(results / "xrf" / directory / f"{sample}.{extension}")
    receipt = results / "xrf/independent_validation.json"
    if receipt.is_file():
        paths.add(receipt)
    for name in (
        "handwriting_sheet.png",
        "generation_prompt.json",
        "samples.csv",
        "grey_features.csv",
        "components.csv",
        "queries.csv",
        "ranking.csv",
        "summary.json",
        "style_embeddings.svg",
        "style_embeddings.png",
        "index.html",
    ):
        paths.add(results / "handwriting" / name)
    missing = [str(path.relative_to(root)) for path in sorted(paths) if not path.is_file()]
    if missing:
        raise ValueError("Missing public files (generate the demos first): " + ", ".join(missing))
    for path in paths:
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Refusing linked or external file: {path}")
    for directory in ("xrf", "handwriting"):
        summary = json.loads((results / directory / "summary.json").read_text(encoding="utf-8"))
        if summary.get("synthetic") is not True:
            raise ValueError(f"Expected synthetic demo results: {directory}")
    return sorted(paths)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/github_upload"))
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    try:
        paths = public_files(root)
    except ValueError as error:
        parser.error(str(error))
    args.output.mkdir(parents=True, exist_ok=True)
    archive = args.output / "greytheory-github-ready.zip"
    records = []
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as bundle:
        for path in paths:
            relative = path.relative_to(root).as_posix()
            data = path.read_bytes()
            bundle.writestr("python-GreyTheory/" + relative, data)
            records.append({"path": relative, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (args.output / "SHA256SUMS.txt").write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    (args.output / "contents.json").write_text(
        json.dumps({"archive": archive.name, "sha256": digest, "files": records}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"GitHub source package: {archive.resolve()} ({len(paths)} files)")


if __name__ == "__main__":
    main()
