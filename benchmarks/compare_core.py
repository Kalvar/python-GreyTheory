"""Measure each design in a separate interpreter; report speed, allocations, RSS.

Usage: python benchmarks/compare_core.py --baseline /path/to/original/snapshot
No assertion that the new solver is universally faster.
"""

import argparse
import json
from pathlib import Path
import resource
import subprocess
import sys
import time
import tracemalloc
import warnings


def measure(root, n, p):
    sys.path.insert(0, root)
    import numpy as np
    from greytheory import GreyTheory

    rng = np.random.default_rng(0)
    X = rng.uniform(0.5, 1.5, (p, n))
    model = GreyTheory().gm0n
    model.add_outputs(rng.uniform(0.5, 1.5, n).tolist(), "output")
    for i, row in enumerate(X):
        model.add_patterns(row.tolist(), f"x{i}")
    model.rank_policy = "allow"
    elapsed = []
    tracemalloc.start()
    status = "PASS"
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for _ in range(5):
                start = time.perf_counter()
                model.analyze()
                elapsed.append(time.perf_counter() - start)
    except Exception as exc:
        status = type(exc).__name__
    _, peak = tracemalloc.get_traced_memory()
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(
        json.dumps(
            dict(
                n=n,
                p=p,
                median_seconds=float(np.median(elapsed)) if elapsed else None,
                python_peak_bytes=peak,
                process_peak_rss_bytes=rss if sys.platform == "darwin" else rss * 1024,
                status=status,
                rank=getattr(model, "diagnostics_", {}).get("rank"),
            )
        )
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline")
    parser.add_argument("--measure", nargs=3)
    parser.add_argument("--output", default="artifacts/benchmarks.json")
    args = parser.parse_args()
    if args.measure:
        root, n, p = args.measure
        measure(root, int(n), int(p))
        return
    roots = {"current": str(Path(__file__).resolve().parents[1])}
    if args.baseline:
        roots["baseline"] = str(Path(args.baseline).resolve())
    results = []
    for name, root in roots.items():
        for n in [20, 100, 1000]:
            for p in [3, 10, 100]:
                process = subprocess.run(
                    [sys.executable, __file__, "--measure", root, str(n), str(p)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                result = json.loads(process.stdout)
                result["implementation"] = name
                results.append(result)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2) + "\n")
    print(f"{len(results)} measured cases: {out}")


if __name__ == "__main__":
    main()
