"""Reference-only experiments for conservation triage, not restoration certification."""

from collections import defaultdict
from importlib.metadata import version
import hashlib
import json
from pathlib import Path
import platform
from time import perf_counter
import warnings

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from greytheory.analysis import GreyPCA
from greytheory.features import GreyWindowFeatures
from greytheory.io import load_images
from examples.workbench.analysis import spectra_dataset
from examples.workbench.scenarios import art_data
from .artwork import ASSETS, artwork_features
from ._report import write_csv, write_json

METHODS = {
    "pca": {},
    "sparse": {"max_iter": 200, "tol": 1e-6},
    "kernel": {},
    "robust": {"max_iter": 300, "tol": 1e-6},
    "robust_sparse": {"max_iter": 200, "tol": 1e-6},
    "adv": {"max_iter": 200, "inner_max_iter": 200, "tol": 1e-6},
}
DEVELOPMENT_SEEDS = (7, 19)
HELD_OUT_SEEDS = (101, 211)
STRENGTHS = (0.1, 0.2, 0.6)
QUANTILES = (0.95, 0.99)


def paired_review(reference_features, observed_features, *, components=3, budget=12):
    """Rank paired change magnitude, with PCA novelty as a separate clue.

    The budget is the number of regions a reviewer elects to inspect, not a
    statistical threshold, confidence score or validated defect classification.
    Identical descriptors produce no candidates, including high-texture tiles.
    """
    ref, obs = np.asarray(reference_features), np.asarray(observed_features)
    if ref.shape != obs.shape or ref.ndim != 2 or ref.shape[0] < 2:
        raise ValueError("provide matching reference/observed feature matrices")
    if isinstance(budget, bool) or not isinstance(budget, (int, np.integer)) or not 1 <= budget <= len(ref):
        raise ValueError("budget must be between 1 and the number of regions")
    scaler = StandardScaler().fit(ref)
    ref, obs = scaler.transform(ref), scaler.transform(obs)
    model = GreyPCA(components).fit(ref)
    ref_reconstruction = model.inverse_transform(model.transform(ref))
    obs_reconstruction = model.inverse_transform(model.transform(obs))
    change = obs - ref
    explained_change = obs_reconstruction - ref_reconstruction
    novelty = change - explained_change
    total = np.sqrt(np.mean(change**2, axis=1))
    residual = np.sqrt(np.mean(novelty**2, axis=1))
    projected = np.sqrt(np.mean(explained_change**2, axis=1))
    order = np.lexsort((np.arange(len(ref)), -total))
    candidates = [int(i) for i in order if total[i] > 1e-12][:budget]
    return dict(
        budget=int(budget),
        priority=candidates,
        paired_change=total.tolist(),
        pca_novelty=residual.tolist(),
        pca_explained_change=projected.tolist(),
        interpretation="Review priority only; no inferred cause or calibrated probability.",
    )


def _errors(model, values):
    return np.mean((values - model.inverse_transform(model.transform(values))) ** 2, axis=1)


def _fit(reference, method):
    scaler = StandardScaler().fit(reference)
    data = scaler.transform(reference)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        started = perf_counter()
        model = GreyPCA(3, method=method, method_params=METHODS[method]).fit(data)
        seconds = perf_counter() - started
    messages = list(dict.fromkeys(str(item.message) for item in caught))
    return scaler, model, seconds, messages


def _spectral_features(counts, energy, use_windows):
    values = spectra_dataset("synthetic", counts, energy).values
    values /= values.sum(axis=1, keepdims=True)
    if use_windows:
        return GreyWindowFeatures(8, stride=4, normalize=False).fit_transform(values)
    return values


def confusion(flags, truth):
    flags, truth = np.asarray(flags, dtype=bool), np.asarray(truth, dtype=bool)
    if flags.shape != truth.shape or not truth.any() or truth.all():
        raise ValueError("provide matching binary flags with changed and unchanged positions")
    tp, fp = int(np.sum(flags & truth)), int(np.sum(flags & ~truth))
    fn, tn = int(np.sum(~flags & truth)), int(np.sum(~flags & ~truth))
    return dict(
        tp=tp,
        fp=fp,
        fn=fn,
        tn=tn,
        recall=tp / (tp + fn),
        precision=tp / (tp + fp) if tp + fp else 0.0,
        f1=2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
        false_positive_rate=fp / (fp + tn),
    )


def spectral_experiments(seeds, progress=print):
    """Train, calibrate, and test on three independently generated maps per seed."""
    rows = []
    for seed in seeds:
        split = "development" if seed in DEVELOPMENT_SEEDS else "held_out"
        energy, train, _, _, _ = art_data(seed)
        calibration = art_data(seed + 10000)[1]
        normal = art_data(seed + 20000)[1]
        for use_windows in (False, True):
            route = "grey_windows" if use_windows else "binned_spectra"
            train_x = _spectral_features(train, energy, use_windows)
            cal_x = _spectral_features(calibration, energy, use_windows)
            normal_x = _spectral_features(normal, energy, use_windows)
            changed = {strength: art_data(seed + 20000, strength) for strength in STRENGTHS}
            for method in METHODS:
                progress(f"{split}: seed={seed} {route}/{method}")
                scaler, model, seconds, messages = _fit(train_x, method)
                cal_error = _errors(model, scaler.transform(cal_x))
                normal_error = _errors(model, scaler.transform(normal_x))
                for strength, (_, _, observed, truth, _) in changed.items():
                    scores = _errors(
                        model, scaler.transform(_spectral_features(observed, energy, use_windows))
                    )
                    for quantile in QUANTILES:
                        threshold = float(np.quantile(cal_error, quantile))
                        row = dict(
                            split=split,
                            seed=seed,
                            route=route,
                            method=method,
                            components=3,
                            quantile=quantile,
                            strength=strength,
                            threshold=threshold,
                            fit_seconds=seconds,
                            normal_control_flags=int(np.sum(normal_error > threshold)),
                            normal_control_fpr=float(np.mean(normal_error > threshold)),
                            roc_auc=float(roc_auc_score(truth, scores)),
                            average_precision=float(average_precision_score(truth, scores)),
                            warnings=messages,
                            eligible=not messages,
                            **confusion(scores > threshold, truth),
                        )
                        rows.append(row)
    return rows


def image_experiments(progress=print):
    images = load_images([ASSETS / "silk_reference.png", ASSETS / "silk_observed.png"])
    # Numerical nuisance controls only: no synthetic UV/XRF imagery or edited files are made.
    controls = np.stack([images[0], images[0] * 0.98, np.roll(images[0], 1, axis=1)])
    features, _ = artwork_features(np.concatenate([images, controls[1:]]))
    reference, observed, exposure, shift = features
    rows, maps = [], {}
    for method in METHODS:
        progress(f"AI image pair: {method}")
        scaler, model, seconds, messages = _fit(reference, method)
        train_error = _errors(model, scaler.transform(reference))
        observed_error = _errors(model, scaler.transform(observed))
        exposure_error = _errors(model, scaler.transform(exposure))
        shift_error = _errors(model, scaler.transform(shift))
        for q in QUANTILES:
            threshold = float(np.quantile(train_error, q))
            rows.append(
                dict(
                    method=method,
                    quantile=q,
                    fit_seconds=seconds,
                    warnings=messages,
                    identical_input_flags=int(np.sum(train_error > threshold)),
                    observed_flags=int(np.sum(observed_error > threshold)),
                    two_percent_exposure_flags=int(np.sum(exposure_error > threshold)),
                    one_pixel_shift_flags=int(np.sum(shift_error > threshold)),
                    ground_truth=None,
                )
            )
        maps[method] = dict(
            errors=observed_error.tolist(),
            flags95=(observed_error > np.quantile(train_error, 0.95)).astype(int).tolist(),
            flags99=(observed_error > np.quantile(train_error, 0.99)).astype(int).tolist(),
        )
    review = paired_review(reference, observed)
    review["same_image_candidates"] = len(paired_review(reference, reference)["priority"])
    review["two_percent_exposure"] = paired_review(reference, exposure)
    review["one_pixel_shift"] = paired_review(reference, shift)
    return rows, maps, review


def summarize(rows, split):
    groups = defaultdict(list)
    for row in rows:
        if row["split"] == split:
            groups[(row["route"], row["method"], row["quantile"])].append(row)
    summary = []
    for (route, method, q), values in groups.items():
        item = dict(
            route=route,
            method=method,
            quantile=q,
            components=3,
            eligible=all(v["eligible"] for v in values),
            warning_runs=sum(bool(v["warnings"]) for v in values),
            trials=len(values),
        )
        for metric in (
            "recall",
            "precision",
            "f1",
            "false_positive_rate",
            "normal_control_fpr",
            "roc_auc",
            "fit_seconds",
        ):
            item[metric] = float(np.mean([v[metric] for v in values]))
        summary.append(item)
    return summary


def select_spectral_configuration(development):
    """Select from development runs only; held-out metrics never choose parameters."""
    valid = [row for row in development if row["eligible"] and row["normal_control_fpr"] <= 0.05]
    if not valid:
        return None
    return sorted(
        valid,
        key=lambda row: (
            -row["f1"],
            row["false_positive_rate"],
            row["normal_control_fpr"],
            row["fit_seconds"],
        ),
    )[0]


def run_validation(output=None, *, progress=print):
    output = Path(output or ASSETS / "review")
    output.mkdir(parents=True, exist_ok=True)
    with threadpool_limits(limits=1):
        images, maps, review = image_experiments(progress)
        spectral = spectral_experiments(DEVELOPMENT_SEEDS + HELD_OUT_SEEDS, progress)
    development = summarize(spectral, "development")
    held_out = summarize(spectral, "held_out")
    selected = select_spectral_configuration(development)
    selection_test = next(
        (
            row
            for row in held_out
            if selected and all(row[key] == selected[key] for key in ("route", "method", "quantile"))
        ),
        None,
    )
    report = dict(
        format="greytheory-artwork-review-v1",
        synthetic=True,
        image_ground_truth=None,
        image_inputs={
            name: hashlib.sha256((ASSETS / name).read_bytes()).hexdigest()
            for name in ("silk_reference.png", "silk_observed.png")
        },
        professional_review_status="Illustrative reasoning from public guidance; not reviewed by a conservator.",
        image_results=images,
        image_maps=maps,
        paired_review=review,
        spectral_trials=spectral,
        development=development,
        held_out=held_out,
        selected_on_development=selected,
        selected_held_out=selection_test,
        protocol=dict(
            development_seeds=DEVELOPMENT_SEEDS,
            held_out_seeds=HELD_OUT_SEEDS,
            strengths=STRENGTHS,
            quantiles=QUANTILES,
            method_parameters=METHODS,
            independent_calibration_seed_offset=10000,
            independent_test_seed_offset=20000,
            selection_rule="Warning-free fits, mean normal-control FPR <= 5%, then development F1, FPR, runtime.",
            calibration="Independent normal spectral map; image legacy thresholds still use reference training errors.",
            scope="Same toy peak family and fixed anomaly geometry; not independent real artworks or pigments.",
            image_control_scope="Synthetic exposure / pixel-shift arrays, not independently photographed controls.",
            seed_groups_are_independent_objects=False,
        ),
        environment=dict(
            python=platform.python_version(),
            numpy=version("numpy"),
            sklearn=version("scikit-learn"),
            machine=platform.machine(),
            blas_threads=1,
        ),
    )
    write_json(output / "validation.json", report)
    for name, values in (
        ("spectral_trials", spectral),
        ("image_trials", images),
        ("spectral_development", development),
        ("spectral_held_out", held_out),
    ):
        headers = list(values[0])
        write_csv(
            output / f"{name}.csv",
            headers,
            [
                [
                    json.dumps(row[key], ensure_ascii=False) if isinstance(row[key], list) else row[key]
                    for key in headers
                ]
                for row in values
            ],
        )
    (output / "review-data.js").write_text(
        "// Computed by examples.demos.artwork_validation; synthetic data only.\nwindow.ART_REVIEW="
        + json.dumps(report, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c")
        + ";\n",
        encoding="utf-8",
    )
    return report


if __name__ == "__main__":
    result = run_validation(progress=lambda line: print(line, flush=True))
    print(
        json.dumps(
            {"selected": result["selected_on_development"], "held_out": result["selected_held_out"]}, indent=2
        )
    )
