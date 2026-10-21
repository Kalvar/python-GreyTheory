"""Compare aligned display images; RGB differences are not material identification."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.preprocessing import StandardScaler

from greytheory.analysis import GreyPCA
from greytheory.features import GreyWindowFeatures, ImagePatchFeatures
from greytheory.io import load_images
from ._report import write_csv, write_json

ASSETS = Path(__file__).resolve().parents[2] / "data/demo/artwork"


def artwork_features(images):
    """One row per spatial tile: 4x4 patch summaries followed by Grey windows.

    Every tile is described independently. Row-start markers prevent windows
    from interpreting the end of one patch row as the start of the next.
    """
    images = np.asarray(images, dtype=float)
    if images.ndim != 4 or images.shape[-1] != 3 or min(images.shape[1:3]) < 48:
        raise ValueError("Use RGB images at least 48 x 48 pixels.")
    patches = ImagePatchFeatures((48, 48)).fit_transform(images)
    tiles = patches.reshape(len(images), 12, 4, 12, 4, 13).transpose(0, 1, 3, 2, 4, 5)
    tiles = tiles.reshape(len(images), 144, 16, 13).copy()
    tiles[..., -1] = (np.arange(16) % 4 == 0).astype(float)
    windows = GreyWindowFeatures(8, stride=8, normalize=False, boundary_channel=-1)
    windows.fit(tiles[0])
    features = np.stack([windows.transform(tile) for tile in tiles])
    return features, windows.get_feature_names_out().tolist()


def compare_artwork_images(
    reference, observed, *, method="pca", components=3, quantile=0.95, method_params=None
):
    """Fit the reference only and flag observed tiles by reconstruction error.

    Files must already be registered, equally sized, and comparably lit. This
    function does not register images, infer pigments, date art or prove retouching.
    No AI edit mask is used as validated ground truth.
    """
    if isinstance(quantile, bool) or not np.isfinite(quantile) or not 0.8 <= quantile <= 0.999:
        raise ValueError("quantile must be between 0.8 and 0.999")
    images = load_images([reference, observed], mode="RGB")
    features, names = artwork_features(images)
    scaler = StandardScaler().fit(features[0])
    ref, obs = (scaler.transform(row) for row in features)
    model = GreyPCA(components, method=method, method_params=method_params).fit(ref)

    def errors(values):
        return np.mean((values - model.inverse_transform(model.transform(values))) ** 2, axis=1)

    train_error = errors(ref)
    test_error = errors(obs)
    threshold = float(np.quantile(train_error, quantile))
    paired_distance = np.sqrt(np.mean((obs - ref) ** 2, axis=1))
    flags = test_error > threshold
    return dict(
        format="greytheory-artwork-images-v1",
        input_kind="display_rgb_images",
        shape=[12, 12],
        method=method,
        components=int(components),
        quantile=float(quantile),
        threshold=threshold,
        flagged_positions=int(flags.sum()),
        feature_names=names,
        reference_features=features[0].tolist(),
        observed_features=features[1].tolist(),
        reference_errors=train_error.tolist(),
        observed_errors=test_error.tolist(),
        paired_feature_distance=paired_distance.tolist(),
        flags=flags.astype(int).tolist(),
        ground_truth=None,
        provenance={
            "reference_sha256": hashlib.sha256(Path(reference).read_bytes()).hexdigest(),
            "observed_sha256": hashlib.sha256(Path(observed).read_bytes()).hexdigest(),
            "reference_only_fit": True,
            "registered_by_this_function": False,
        },
        limitations=[
            "RGB image features, not XRF spectra or pigment concentrations.",
            "AI editing may alter pixels outside the intended regions; no validated change mask exists.",
            "Reference training errors set an exploratory threshold, not a calibrated confidence level.",
            "Camera, lighting, registration and compression differences can trigger flags.",
        ],
    )


def run_artwork_demo(
    output_dir="artifacts/artwork",
    *,
    reference=None,
    observed=None,
    method="pca",
    components=3,
    quantile=0.95,
):
    """Export a self-contained numeric result and sample-row feature CSVs."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    result = compare_artwork_images(
        reference or ASSETS / "silk_reference.png",
        observed or ASSETS / "silk_observed.png",
        method=method,
        components=components,
        quantile=quantile,
    )
    result["bundled_ai_pair"] = reference is None and observed is None
    write_json(output / "analysis.json", result)
    for split in ("reference", "observed"):
        # Only numeric features: positions and flags are exported separately so
        # they cannot silently become predictors when imported into the GUI.
        write_csv(output / f"{split}_features.csv", result["feature_names"], result[f"{split}_features"])
    write_csv(
        output / "positions.csv",
        ["row", "column", "reference_error", "observed_error", "paired_feature_distance", "flag"],
        [
            (
                i // 12,
                i % 12,
                result["reference_errors"][i],
                result["observed_errors"][i],
                result["paired_feature_distance"][i],
                result["flags"][i],
            )
            for i in range(144)
        ],
    )
    # A concise machine-readable summary is separate from the full descriptor table.
    summary = {
        key: result[key]
        for key in (
            "format",
            "input_kind",
            "shape",
            "method",
            "components",
            "quantile",
            "threshold",
            "flagged_positions",
            "ground_truth",
            "provenance",
            "limitations",
            "bundled_ai_pair",
        )
    }
    write_json(output / "summary.json", summary)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--observed", type=Path)
    parser.add_argument("--output", type=Path, default=Path("artifacts/artwork"))
    parser.add_argument(
        "--pca", choices=["pca", "sparse", "kernel", "robust", "robust_sparse", "adv"], default="pca"
    )
    parser.add_argument("--components", type=int, default=3)
    parser.add_argument("--quantile", type=float, default=0.95)
    args = parser.parse_args(argv)
    if bool(args.reference) != bool(args.observed):
        parser.error("provide both --reference and --observed, or neither for the bundled AI pair")
    result = run_artwork_demo(
        args.output,
        reference=args.reference,
        observed=args.observed,
        method=args.pca,
        components=args.components,
        quantile=args.quantile,
    )
    print(
        json.dumps({"flagged_positions": result["flagged_positions"], "output": str(args.output)}, indent=2)
    )


if __name__ == "__main__":
    main()
