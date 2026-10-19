"""AI-generated handwriting STYLE comparison, not human writer attribution."""

import hashlib
from importlib.resources import as_file, files
from pathlib import Path
import shutil

import numpy as np
from scipy.ndimage import zoom
from sklearn.decomposition import PCA
from sklearn.metrics import pairwise_distances
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ..analysis import GreyPCA
from ..features import GreyWindowFeatures, ImagePatchFeatures
from ..io import load_images
from ._report import plotting, report, table, write_csv, write_json

STYLES = ("upright", "flowing", "angular")


def _sheet_cells(path):
    """Extract numeric ROIs from the 3-column, 6-row synthetic sheet."""
    pixels = load_images(path, mode="L")[0]
    if pixels.shape[0] < 192 or pixels.shape[1] < 192:
        raise ValueError("the demo sheet must contain a readable 3-column, 6-row grid")
    ys = np.linspace(0, pixels.shape[0], 7, dtype=int)
    xs = np.linspace(0, pixels.shape[1], 4, dtype=int)
    images, records = [], []
    for row in range(6):
        for column in range(3):
            dy, dx = max(1, (ys[row + 1] - ys[row]) // 25), max(1, (xs[column + 1] - xs[column]) // 25)
            y0, y1 = int(ys[row] + dy), int(ys[row + 1] - dy)
            x0, x1 = int(xs[column] + dx), int(xs[column + 1] - dx)
            region = pixels[y0:y1, x0:x1]
            # Numeric preprocessing only: no derived image assets are written.
            region = zoom(region, (96 / region.shape[0], 288 / region.shape[1]), order=1, prefilter=False)
            images.append(region)
            records.append({"sample": f"row{row + 1}_style{column + 1}", "style": STYLES[column],
                            "row": row, "column": column, "split": "reference" if row < 4 else "query",
                            "y0": y0, "x0": x0, "y1": y1, "x1": x1,
                            "roi_sha256": hashlib.sha256(region.tobytes()).hexdigest()})
    return np.asarray(images), records


def run_handwriting_demo(output_dir="artifacts/synthetic_handwriting", *, sheet_path=None):
    """Compare separate cells of the bundled AI sheet using patch/PCA and Grey/PCA.

    A supplied sheet must follow the same 3-column, 6-row style layout.
    Labels come from the prompt's columns, not verified identities. Class IDs are
    never passed to GRA as numeric regression targets. Query rows are not fitted.
    """
    plt = plotting()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    master = output / "handwriting_sheet.png"
    if sheet_path is None:
        with as_file(files("greytheory.demos").joinpath("assets/handwriting_ai_sheet.png")) as source:
            shutil.copyfile(source, master)
    else:
        source = Path(sheet_path)
        if source.resolve() != master.resolve():
            shutil.copyfile(source, master)
    with as_file(files("greytheory.demos").joinpath("assets/handwriting_ai_sheet.json")) as source:
        shutil.copyfile(source, output / "generation_prompt.json")
    images, records = _sheet_cells(master)
    reference = np.array([row["split"] == "reference" for row in records])
    query = ~reference
    labels = np.array([row["style"] for row in records])
    ids = np.array([row["sample"] for row in records])
    reference_ids, query_ids = np.flatnonzero(reference), np.flatnonzero(query)
    patches = ImagePatchFeatures((4, 8)).fit(images[reference])
    patch_data = patches.transform(images)
    raw = patch_data[:, :, :-1].reshape(len(images), -1)
    windows = GreyWindowFeatures(8, stride=8, boundary_channel=-1).fit(patch_data[reference])
    grey = windows.transform(patch_data)
    methods = [
        ("PCA / patch features", raw, Pipeline([("scale", StandardScaler()),
                                               ("pca", PCA(4, svd_solver="full"))])),
        ("Grey/PCA / window features", grey, GreyPCA(4, standardize=True)),
    ]
    metrics, query_rows, ranking_rows, embedding_rows = [], [], [], []
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)
    for axis, (name, features, model) in zip(axes, methods):
        model.fit(features[reference])
        coordinates = model.transform(features)
        distances = pairwise_distances(coordinates[query], coordinates[reference])
        nearest = reference_ids[distances.argmin(axis=1)]
        correct = labels[nearest] == labels[query]
        metrics.append({"method": name, "style_matches": int(correct.sum()), "queries": int(query.sum()),
                        "synthetic_style_top1": float(correct.mean())})
        for q_index, (sample, row_distances) in enumerate(zip(query_ids, distances)):
            best = int(nearest[q_index])
            query_rows.append((name, ids[sample], labels[sample], ids[best], labels[best],
                               float(row_distances.min()), bool(correct[q_index])))
            for rank, local_index in enumerate(np.argsort(row_distances, kind="stable"), 1):
                candidate = reference_ids[local_index]
                ranking_rows.append((name, ids[sample], rank, ids[candidate], labels[candidate], float(row_distances[local_index])))
        for row, coordinates_row in zip(records, coordinates):
            embedding_rows.append((name, row["sample"], row["style"], row["split"], *coordinates_row))
        for style, color in zip(STYLES, ("#078c86", "#7a4dc4", "#dd7a24")):
            refs = reference & (labels == style)
            queries = query & (labels == style)
            axis.scatter(coordinates[refs, 0], coordinates[refs, 1], c=color, label=f"{style} refs", s=40)
            axis.scatter(coordinates[queries, 0], coordinates[queries, 1], c=color, marker="x", s=90)
        axis.set(title=name, xlabel="PC1", ylabel="PC2")
        axis.legend(fontsize=8)
    fig.savefig(output / "style_embeddings.svg")
    fig.savefig(output / "style_embeddings.png", dpi=160)
    plt.close(fig)
    write_csv(output / "samples.csv", list(records[0]), (row.values() for row in records))
    write_csv(output / "grey_features.csv", ["sample", "style", "split", *windows.get_feature_names_out()],
              ((row["sample"], row["style"], row["split"], *values) for row, values in zip(records, grey)))
    write_csv(output / "components.csv", ["method", "sample", "style", "split", "PC1", "PC2", "PC3", "PC4"], embedding_rows)
    write_csv(output / "queries.csv", ["method", "query", "prompt_style", "nearest_reference", "predicted_style", "distance", "style_match"], query_rows)
    write_csv(output / "ranking.csv", ["method", "query", "rank", "reference", "reference_style", "distance"], ranking_rows)
    summary = {
        "synthetic": True, "source": "AI-generated handwriting contact sheet" if sheet_path is None else "User-supplied sheet following the synthetic layout",
        "sheet_sha256": hashlib.sha256(master.read_bytes()).hexdigest(), "text": "春風明月",
        "labels": "Prompt-assigned styles, not verified human authors",
        "reference_samples": int(reference.sum()), "query_samples": int(query.sum()),
        "reference_rows": [0, 1, 2, 3], "query_rows": [4, 5],
        "unique_normalized_rois": len({row["roi_sha256"] for row in records}),
        "query_in_fit": False, "gra_class_id_target": False,
        "limitations": ["One shared generated sheet, not independent documents or writers",
                        "Scores can reflect AI rendering/layout artifacts", "Distances are not author probabilities or forensic accuracy"],
        "metrics": metrics,
    }
    write_json(output / "summary.json", summary)
    report(output / "index.html", "AI 合成筆跡：Grey/PCA 參考比對",
           "同一張 AI 生成頁的 18 格；12 格作參考、6 格作查詢。只比較人為設定的三種字形風格。",
           [("合成樣本", '<p>每欄一種風格，前四排作參考、後兩排作查詢。沒有真實作者資料，沒有把參考圖直接複製為查詢。</p>'
             '<img src="handwriting_sheet.png" alt="AI-generated fictional handwriting: upright, flowing, angular">'),
            ("參考與查詢的特徵分布", '<p>圓點是參考，叉號是未參與擬合的查詢。每個方法各自擬合，因此兩張圖的座標軸不能直接互比。</p>'
             '<img src="style_embeddings.svg" alt="PCA and Grey window PCA embeddings">' +
             table(["方法", "合成風格命中格數"], [(row["method"], f'{row["style_matches"]}/{row["queries"]}') for row in metrics])),
            ("每格查詢的最近參考", table(["方法", "查詢", "指定風格", "最近參考", "參考風格", "距離", "命中"],
             [(*row[:5], f"{row[5]:.3f}", row[6]) for row in query_rows])),
            ("數據與來源", '<p><a href="samples.csv">樣本與分區座標</a> · <a href="grey_features.csv">Grey 特徵</a> · '
             '<a href="components.csv">PCA 座標</a> · <a href="ranking.csv">完整排名</a> · '
             '<a href="generation_prompt.json">生成提示與配置</a> · <a href="summary.json">設定與限制</a></p>'),
            ("這個 demo 的範圍", '<p>命中率只描述同一張合成頁的字形風格，不能當成真實筆跡作者辨識準確率。'
             '這裡沒有把作者／風格編號當成連續數值送入 GRA；Grey 部分是窗口特徵，PCA 用來整理表示。</p>')])
    return {"report": output / "index.html", "summary": summary}
