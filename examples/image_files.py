"""Read image files, compare Grey/PCA features, and export numeric results.

Run without arguments for generated PNG inputs, or pass --references and --query
to read your own files. No image identity or authenticity decision is made.
"""

import argparse
import csv
from pathlib import Path

import numpy as np
from sklearn.metrics import pairwise_distances
from sklearn.pipeline import Pipeline

from greytheory.analysis import GreyPCA
from greytheory.features import GreyWindowFeatures, ImagePatchFeatures
from greytheory.io import load_images


def make_image_pipeline():
    return Pipeline([
        ("patches", ImagePatchFeatures(grid_shape=(4, 8))),
        ("windows", GreyWindowFeatures(8, stride=8, boundary_channel=-1)),
        ("pca", GreyPCA(2, standardize=True)),
    ])


def compare_image_files(reference_paths, query_path, *, size=None):
    """Fit on reference files only and rank their distance to one query file."""
    reference_paths = list(reference_paths)
    if len(reference_paths) < 3:
        raise ValueError("provide at least three reference images for this two-component example")
    references = load_images(reference_paths, size=size)
    query = load_images(query_path, size=size)
    pipeline = make_image_pipeline()
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


def create_demo_images(folder):
    """Generate small display images so the example needs no external dataset."""
    from PIL import Image

    folder = Path(folder)
    reference_folder = folder / "reference"
    reference_folder.mkdir(parents=True, exist_ok=True)
    y, x = np.mgrid[:64, :96]
    paths = []
    for index in range(8):
        center = 18 + 8 * index
        pixels = 255 - 180 * np.exp(-((x - center) / 9) ** 2 - ((y - 32) / 18) ** 2)
        pixels -= 30 * np.sin((index + 1) * x / 96) ** 2
        path = reference_folder / f"sample_{index:02d}.png"
        Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8)).save(path)
        paths.append(path)
    query_path = folder / "query.png"
    query_path.write_bytes(paths[3].read_bytes())
    return paths, query_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--references", type=Path, help="directory containing at least three reference images")
    parser.add_argument("--query", type=Path, help="image to compare with the references")
    parser.add_argument("--size", type=int, nargs=2, metavar=("WIDTH", "HEIGHT"),
                        help="resize with preserved aspect ratio and white padding")
    parser.add_argument("--output", type=Path, default=Path("artifacts/image_files"))
    args = parser.parse_args(argv)
    if (args.references is None) != (args.query is None):
        parser.error("supply both --references and --query, or omit both for generated inputs")
    if args.references is None:
        reference_paths, query_path = create_demo_images(args.output / "inputs")
        print("Generated PNG inputs; query is an exact copy of sample_03.png.")
    else:
        if not args.references.is_dir():
            parser.error("--references must be an existing directory")
        extensions = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
        reference_paths = sorted(path for path in args.references.iterdir()
                                 if path.is_file() and path.suffix.lower() in extensions)
        query_path = args.query
    result = compare_image_files(reference_paths, query_path, size=args.size)
    write_results(args.output, reference_paths, query_path, result)
    for rank, index in enumerate(result["ranking"], 1):
        print(rank, reference_paths[index].name, f"distance={result['distances'][index]:.6f}")
    print("Results:", args.output.resolve())
    return result


if __name__ == "__main__":
    main()
