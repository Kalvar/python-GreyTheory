"""Same-split synthetic decomposition comparison; no winner is required."""

import json
from pathlib import Path
import sys
import time
import tracemalloc
import warnings

import numpy as np
from sklearn.decomposition import PCA

# Allow direct invocation from a checkout without an editable install.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from greytheory.analysis import PCAAdapter, RobustPCA, RobustSparsePCA, AdvPCA


def main():
    rng = np.random.default_rng(20261019)
    results = []
    for n, p, corrupt in [(80, 16, False), (80, 16, True), (35, 186, True)]:
        loadings = np.zeros((3, p))
        for j in range(3):
            loadings[j, j * 3 : j * 3 + 3] = 1 / np.sqrt(3)
        clean = rng.normal(size=(n, 3)) @ loadings + 0.02 * rng.normal(size=(n, p))
        X = clean.copy()
        if corrupt:
            mask = rng.uniform(size=X.shape) < 0.02
            X[mask] += rng.normal(0, 10, mask.sum())
        split = int(0.8 * n)
        train, test = X[:split], X[split:]
        models = {
            "SVD-PCA": PCAAdapter(3),
            "SparsePCA": PCAAdapter(3, method="sparse", alpha=0.1),
            "PCP_then_PCA": RobustPCA(),
            "HuberRobustSparsePCA": RobustSparsePCA(3, alpha=0.1, max_iter=500),
            "AdvPCA": AdvPCA(3, max_iter=30, inner_max_iter=100),
        }
        for name, model in models.items():
            tracemalloc.start()
            start = time.perf_counter()
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                model.fit(train)
                if name == "PCP_then_PCA":
                    projector = PCA(3).fit(model.low_rank_)
                    reconstructed = projector.inverse_transform(projector.transform(test))
                    weights = projector.components_
                    converged = model.diagnostics_["converged"]
                else:
                    reconstructed = model.inverse_transform(model.transform(test))
                    weights = model.encoder_.T if name == "AdvPCA" else model.components_
                    converged = getattr(
                        model, "converged_", getattr(model, "diagnostics_", {}).get("converged")
                    )
            elapsed = time.perf_counter() - start
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            results.append(
                dict(
                    model=name,
                    n=n,
                    p=p,
                    contaminated=corrupt,
                    train_rows=split,
                    test_rows=n - split,
                    clean_test_mse=float(np.mean((reconstructed - clean[split:]) ** 2)),
                    observed_test_mse=float(np.mean((reconstructed - test) ** 2)),
                    near_zero_loading_fraction=float(np.mean(np.abs(weights) < 1e-6)),
                    seconds=elapsed,
                    python_peak_bytes=peak,
                    converged=converged,
                    warnings=[str(w.message) for w in caught],
                )
            )
    out = Path("artifacts/decomposition_benchmarks.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(results, indent=2) + "\n")
    print(f"{len(results)} same-split measurements: {out}")


if __name__ == "__main__":
    main()
