"""Synthetic comparisons: python -m examples.research_models --output report.json."""

import argparse
import json
from pathlib import Path
import warnings

import numpy as np

from greytheory import GM11
from greytheory.research import RLFGM, GINN, FGINN, GreyFuzzyGPR, GreyPCAQuality


def _plain(value):
    if isinstance(value, np.ndarray):
        return [_plain(v) for v in value.tolist()]
    if isinstance(value, np.generic):
        return _plain(value.item())
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def make_series(seed=7, kind="smooth"):
    random = np.random.default_rng(seed)
    time = np.arange(48)
    series = 30 * np.exp(0.015 * time)
    if kind == "seasonal":
        series += 2 * np.sin(time * 0.6)
    return series + random.normal(0, 0.15, len(time))


def make_quality(seed=7):
    random = np.random.default_rng(seed)
    features = random.normal(size=(100, 6))
    features[90:] += 2  # ten deliberately out-of-domain tests
    target = 100 + 5 * np.sin(features[:, 0]) + 3 * features[:, 1] ** 2 + 0.5 * features[:, 2]
    target += random.normal(0, 0.4, len(target))
    return features, target


def forecast_comparison(seed=7, kind="smooth", max_iter=500):
    values = make_series(seed, kind)
    training, test = values[:36], values[36:]
    models = {
        "persistence": None,
        "gm11": GM11(correction_mode="none", background_mode="corrected"),
        "rlfgm": RLFGM(),
        "mlp_no_grey": GINN(grey_weight=0, max_iter=max_iter, random_state=seed),
        "ginn_variant": GINN(max_iter=max_iter, random_state=seed),
        "fginn_variant": FGINN(max_iter=max_iter, random_state=seed),
    }
    rows = []
    for name, model in models.items():
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            if model is None:
                prediction = np.full(len(test), training[-1])
                diagnostics = {}
            else:
                model.fit(training)
                prediction = model.predict(len(test))
                diagnostics = getattr(model, "diagnostics", {})
        rows.append(
            dict(
                model=name,
                seed=seed,
                case=kind,
                rmse=float(np.sqrt(np.mean((prediction - test) ** 2))),
                mae=float(np.mean(np.abs(prediction - test))),
                prediction=prediction.tolist(),
                warnings=[str(w.message) for w in caught],
                diagnostics=_plain(diagnostics),
            )
        )
    return dict(training=training.tolist(), test=test.tolist(), models=rows)


def quality_comparison(seed=7, grey_strength=1, *, pca_method=None, n_components=2, method_params=None):
    features, target = make_quality(seed)
    rows = []
    for name, strength in [("uniform_gp", 0), ("grey_fuzzy_gpr_variant", grey_strength)]:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            options = dict(grey_strength=strength, random_state=seed)
            model = (GreyFuzzyGPR(**options) if pca_method is None else GreyPCAQuality(
                pca_method, n_components, pca_params={"method_params": method_params}, model_params=options
            )).fit(features[:60], target[:60])
        gp = model if pca_method is None else model.model
        prediction, std = model.predict(features[60:], return_std=True)
        reliability = model.reliability(features[60:])
        rows.append(
            dict(
                model=name,
                rmse=float(np.sqrt(np.mean((prediction - target[60:]) ** 2))),
                in_domain_rmse=float(np.sqrt(np.mean((prediction[:30] - target[60:90]) ** 2))),
                shifted_domain_rmse=float(np.sqrt(np.mean((prediction[30:] - target[90:]) ** 2))),
                prediction=prediction.tolist(),
                std=std.tolist(),
                heuristic_2std_coverage=float(np.mean(np.abs(prediction - target[60:]) <= 2 * std)),
                reliability={
                    k: v.tolist() if isinstance(v, np.ndarray) else v for k, v in reliability.items()
                },
                feature_scores=gp.feature_scores.tolist(),
                feature_weights=gp.feature_weights.tolist(),
                warnings=[str(w.message) for w in caught],
                diagnostics=model.diagnostics,
            )
        )
    return dict(
        training_rows=60,
        test_rows=40,
        in_domain_test_rows=30,
        shifted_test_rows=10,
        observed=target[60:].tolist(),
        models=rows,
    )


def run_demo():
    forecasts = [forecast_comparison(seed, kind) for seed in (7, 19, 101) for kind in ("smooth", "seasonal")]
    quality = [dict(seed=seed, **quality_comparison(seed)) for seed in (7, 19, 101)]
    summary = []
    for name in [row["model"] for row in forecasts[0]["models"]]:
        rows = [r for case in forecasts for r in case["models"] if r["model"] == name]
        summary.append(
            dict(
                model=name,
                mean_rmse=float(np.mean([r["rmse"] for r in rows])),
                warning_runs=sum(bool(r["warnings"]) for r in rows),
            )
        )
    return dict(
        format="greytheory-research-demo-v1",
        synthetic=True,
        forecast_summary=summary,
        forecasts=forecasts,
        quality=quality,
        notes=[
            "RL core follows published operators; grid/chronological selection differs from paper PSO.",
            "GINN/FGINN are documented engineering variants, not exact paper reproductions.",
            "Grey-Fuzzy GPR is independently designed; reliability is heuristic, not a probability.",
            "Test splits are fixed and not used to choose hyperparameters; no superiority guarantee.",
        ],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/research_models/report.json"))
    args = parser.parse_args()
    report = run_demo()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["forecast_summary"], indent=2))
    print(args.output)


if __name__ == "__main__":
    main()
