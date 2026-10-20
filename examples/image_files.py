"""Read image files, compare Grey/PCA features, and export numeric results.

Run without arguments for generated PNG inputs, or pass --references and --query
to read your own files. No image identity or authenticity decision is made.
"""

import argparse
from pathlib import Path

import numpy as np

# Re-export the existing example helpers for callers using the older interface.
from greytheory.handwriting import (
    compare_image_files as compare_image_files,
    make_image_pipeline as make_image_pipeline,
    write_results as write_results,
)


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
