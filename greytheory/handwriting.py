"""File-based Grey/PCA comparison; distances do not establish human authorship."""

import base64
import csv
from dataclasses import dataclass
from html import escape
import io
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import pairwise_distances
from sklearn.pipeline import Pipeline

from .analysis import GreyPCA
from .features import GreyWindowFeatures, ImagePatchFeatures
from .io import load_images

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}


@dataclass(frozen=True)
class HandwritingMatch:
    rank: int
    reference: Path
    distance: float


@dataclass(frozen=True)
class HandwritingComparison:
    matches: tuple[HandwritingMatch, ...]
    report: Path
    output_dir: Path

    @property
    def best_match(self):
        return self.matches[0].reference

    @property
    def best_distance(self):
        return self.matches[0].distance


def _reference_paths(references, query):
    if isinstance(references, (str, Path)):
        directory = Path(references)
        if not directory.is_dir():
            raise ValueError(f"reference folder does not exist: {directory}")
        candidates = sorted(path for path in directory.rglob("*")
                            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS)
    else:
        candidates = [Path(path) for path in references]
    paths, seen = [], {query.resolve()}
    for path in candidates:
        resolved = path.resolve()
        if resolved not in seen:
            paths.append(path)
            seen.add(resolved)
    if len(paths) < 3:
        raise ValueError("provide at least three distinct reference images, excluding the query image")
    return paths


def _thumbnail(path):
    from PIL import Image

    pixels = load_images(path, size=(288, 96))[0]
    stream = io.BytesIO()
    Image.fromarray(np.rint(pixels * 255).astype(np.uint8)).save(stream, format="PNG")
    return "data:image/png;base64," + base64.b64encode(stream.getvalue()).decode("ascii")


def _write_report(path, query, matches, pca):
    query_preview = _thumbnail(query)
    best_preview = _thumbnail(matches[0].reference)
    rows = "".join(
        f"<tr><td>{match.rank}</td><td>{escape(str(match.reference))}</td><td>{match.distance:.6g}</td></tr>"
        for match in matches
    )
    path.write_text(f'''<!doctype html>
<html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>筆跡圖片比對</title><style>
:root{{color-scheme:light dark;--bg:#f4f7fb;--panel:white;--text:#19263a;--line:#d9e2ee}}
@media(prefers-color-scheme:dark){{:root{{--bg:#111a29;--panel:#1c293d;--text:#edf3fb;--line:#35465f}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:16px/1.7 system-ui,sans-serif}}
main{{max-width:960px;margin:auto;padding:28px 20px}}h1{{line-height:1.3}}h2{{font-size:1.2rem}}
section{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:22px;margin:18px 0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:24px}}
img{{width:100%;height:auto;background:white;border-radius:8px}}p{{overflow-wrap:anywhere}}
.table{{overflow:auto}}table{{border-collapse:collapse;width:100%}}td,th{{padding:10px;text-align:left;border-bottom:1px solid var(--line)}}
a{{color:#4f8bf0}}.note{{border-left:4px solid #17a09a;padding-left:16px}}
</style><main><h1>筆跡圖片比對</h1>
<p>圖片區塊 → Grey 窗口特徵 → {escape(pca)} → 距離排名。參考圖 {len(matches)} 張；查詢圖不參與擬合。</p>
<section class="grid"><div><h2>待比對圖片</h2><img src="{query_preview}" alt="Query image"><p>{escape(str(query))}</p></div>
<div><h2>最接近的參考圖</h2><img src="{best_preview}" alt="Closest reference image"><p>{escape(str(matches[0].reference))}</p>
<p>距離：{matches[0].distance:.6g}</p></div></section>
<section><h2>完整排名</h2><div class="table"><table><thead><tr><th>排名</th><th>參考圖片</th><th>距離</th></tr></thead>
<tbody>{rows}</tbody></table></div><p class="note">距離越小，表示在這組圖片特徵下越接近。距離不是同一作者的機率，也不直接判定作者身分。</p></section>
<section><h2>數值結果</h2><p><a href="ranking.csv">排名 CSV</a> · <a href="features.csv">Grey 特徵</a> ·
<a href="components.csv">PCA 座標</a> · <a href="summary.json">分析設定</a></p></section></main></html>''', encoding="utf-8")


def compare_handwriting(query, references, *, output="artifacts/handwriting", pca="pca", pca_params=None, size=(288, 96)):
    """Rank reference images and write a visual report plus numeric exports.

    references accepts a folder (including subfolders) or an ordered path list.
    The query path and repeated reference paths are excluded before fitting.
    The default size preserves aspect ratio with white padding. Crop and align
    the same text/signature beforehand. This compares image features, not identities.
    """
    query = Path(query)
    if not query.is_file():
        raise FileNotFoundError(f"query image does not exist: {query}")
    reference_paths = _reference_paths(references, query)
    analysis = compare_image_files(reference_paths, query, size=size, pca=pca, pca_params=pca_params)
    matches = tuple(HandwritingMatch(rank, reference_paths[index], float(analysis["distances"][index]))
                    for rank, index in enumerate(analysis["ranking"], 1))
    output = Path(output)
    write_results(output, reference_paths, query, analysis)
    report = output / "index.html"
    _write_report(report, query, matches, pca)
    (output / "summary.json").write_text(json.dumps({
        "query": str(query), "reference_count": len(reference_paths), "pca": pca,
        "pca_params": pca_params, "size": size, "query_in_fit": False,
        "interpretation": "Feature-space distance, not an author probability",
        "matches": [{"rank": item.rank, "reference": str(item.reference), "distance": item.distance}
                    for item in matches],
    }, ensure_ascii=False, indent=2,
        default=lambda value: value.tolist() if hasattr(value, "tolist") else str(value)) + "\n", encoding="utf-8")
    return HandwritingComparison(matches, report, output)


def make_image_pipeline(*, pca="pca", pca_params=None):
    return Pipeline([
        ("patches", ImagePatchFeatures(grid_shape=(4, 8))),
        ("windows", GreyWindowFeatures(8, stride=8, boundary_channel=-1)),
        ("pca", GreyPCA(2, standardize=True, method=pca, method_params=pca_params)),
    ])


def compare_image_files(reference_paths, query_path, *, size=None, pca="pca", pca_params=None):
    """Fit on reference files only and rank their distance to one query file."""
    reference_paths = list(reference_paths)
    if len(reference_paths) < 3:
        raise ValueError("provide at least three reference images for two-component PCA")
    references = load_images(reference_paths, size=size)
    query = load_images(query_path, size=size)
    pipeline = make_image_pipeline(pca=pca, pca_params=pca_params)
    reference_components = pipeline.fit_transform(references)
    query_components = pipeline.transform(query)
    distances = pairwise_distances(query_components, reference_components)[0]
    return {
        "pipeline": pipeline,
        "distances": distances,
        "ranking": np.argsort(distances, kind="stable"),
        "components": np.vstack((reference_components, query_components)),
        "features": np.vstack((pipeline[:-1].transform(references), pipeline[:-1].transform(query))),
    }


def write_results(output, reference_paths, query_path, result):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows = [("reference", path) for path in reference_paths] + [("query", query_path)]
    feature_names = result["pipeline"].named_steps["windows"].get_feature_names_out()
    for filename, names, values in [
        ("features.csv", feature_names, result["features"]),
        ("components.csv", ["PC1", "PC2"], result["components"]),
    ]:
        with (output / filename).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["role", "path", *names])
            for (role, path), row in zip(rows, values):
                writer.writerow([role, str(path), *row])
    with (output / "ranking.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["rank", "reference", "distance"])
        for rank, index in enumerate(result["ranking"], 1):
            writer.writerow([rank, str(reference_paths[index]), float(result["distances"][index])])
