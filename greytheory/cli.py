"""Short commands for file-based GreyTheory workflows."""

import argparse
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(prog="greytheory")
    commands = parser.add_subparsers(dest="command", required=True)
    handwriting = commands.add_parser("handwriting", help="compare a query image with a reference folder")
    handwriting.add_argument("query", type=Path)
    handwriting.add_argument("references", type=Path)
    handwriting.add_argument("--output", type=Path, default=Path("artifacts/handwriting"))
    handwriting.add_argument("--pca", choices=("pca", "sparse", "kernel", "robust", "robust_sparse", "adv"), default="pca")
    args = parser.parse_args(argv)
    try:
        from .handwriting import compare_handwriting

        result = compare_handwriting(args.query, args.references, output=args.output, pca=args.pca)
    except (ValueError, OSError, ImportError) as error:
        parser.exit(2, f"greytheory: {error}\n")
    print("Closest image:", result.best_match)
    print("Distance:", f"{result.best_distance:.6g}")
    print("Report:", result.report.resolve())
    return 0
