"""Run all four tools: python -m examples.grey_optimization [--output report.json]."""

import argparse
import json
from pathlib import Path

import numpy as np

from greytheory.analysis import (
    DifferenceCalibrator,
    GreyPCA,
    optimize_candidates,
    ranking_stability,
    reconstruction_scores,
    search_grey_pca,
)
from greytheory.semiconductor import latin_hypercube


def run_demo():
    generator = np.random.default_rng(7)
    # Distinct simulated rows: training, normal calibration, untouched test.
    features = generator.normal(size=(240, 6))
    target = 3 * features[:, 0] - features[:, 1] + generator.normal(scale=0.1, size=240)
    train, calibration, test = features[:120], features[120:180], features[180:]
    stability = ranking_stability(train, target[:120], k=2, repeats=40)

    # Freeze model before seeing calibration/test scores; no threshold tuning on test.
    monitor = GreyPCA(3, standardize=True).fit(train)
    threshold = DifferenceCalibrator(0.05).fit(reconstruction_scores(monitor, calibration))
    flags = threshold.predict(reconstruction_scores(monitor, test))

    search = search_grey_pca(
        train, target[:120], components=(2, 3, 4), top_k=(None, 2), rho=(0.3, 0.5), max_trials=8, cv=3
    )
    test_rmse = float(np.sqrt(np.mean((search.predict(test) - target[180:]) ** 2)))

    parameters = latin_hypercube([[0, 1], [0, 1]], n_points=30, random_state=7)

    def simulated_process(rows):
        # Fictional quality loss / cost, not a PVD/CVD physical model.
        loss = (rows[:, 0] - 0.8) ** 2 + (rows[:, 1] - 0.7) ** 2
        cost = rows[:, 0] + 2 * rows[:, 1]
        return np.column_stack([loss, cost]), (cost - 2.5)[:, None]

    alternatives = optimize_candidates(parameters, simulated_process, ["smaller", "smaller"])
    return dict(
        note="Synthetic workflow only; no real-world accuracy or restoration claim.",
        stability=dict(
            frequency=stability.selection_frequency.tolist(),
            mean_rank=stability.mean_rank.tolist(),
            successful=stability.successful_repeats,
            skipped=stability.skipped_repeats,
        ),
        calibration=dict(
            threshold=threshold.threshold,
            samples=threshold.calibration_size,
            test_flags=int(flags.sum()),
            test_rows=len(test),
        ),
        search=dict(
            parameters=search.best_parameters,
            tuning_rmse=search.validation_rmse,
            independent_test_rmse=test_rmse,
            trials=search.trials,
            elapsed_seconds=search.elapsed_seconds,
            stopped_by_budget=search.stopped_by_budget,
        ),
        pareto=dict(
            candidate_count=len(parameters),
            indices=alternatives["front"].indices.tolist(),
            parameters=alternatives["parameters"].tolist(),
            objectives=alternatives["front"].objectives.tolist(),
        ),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    text = json.dumps(run_demo(), ensure_ascii=False, indent=2, allow_nan=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
