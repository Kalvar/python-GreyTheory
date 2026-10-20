"""Run examples, compare handwriting, or open the local analysis workbench."""

import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import venv


def prepare_environment(root, *, extras=()):
    environment = root / ".venv"
    python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if not python.is_file():
        print("Creating the project environment...", flush=True)
        venv.EnvBuilder(with_pip=True).create(environment)

    # Editable installs pick up code edits immediately. Reinstall only when the
    # package configuration changes or the installed dependencies are incomplete.
    digest = hashlib.sha256()
    for filename in ("pyproject.toml", "setup.py"):
        digest.update((root / filename).read_bytes())
    fingerprint = digest.hexdigest()
    base_stamp = environment / ".greytheory-install"
    stamp = environment / (f".greytheory-{'-'.join(extras)}-install" if extras else ".greytheory-install")
    configured = stamp.is_file() and stamp.read_text().strip() == fingerprint
    if configured:
        check = "from importlib.metadata import distribution; distribution('greytheory')"
        if "images" in extras or "workbench" in extras:
            check += "; distribution('Pillow')"
        if "workbench" in extras:
            check += "; distribution('pywebview')"
        installed = subprocess.run(
            [str(python), "-c", check],
            cwd=root, capture_output=True,
        ).returncode == 0
        healthy = installed and subprocess.run(
            [str(python), "-m", "pip", "check"], cwd=root, capture_output=True,
        ).returncode == 0
    else:
        healthy = False

    if not healthy:
        print("Installing project dependencies (internet access may be needed)...", flush=True)
        project = f".[{','.join(extras)}]" if extras else "."
        subprocess.check_call([str(python), "-m", "pip", "install", "-e", project], cwd=root)
        subprocess.check_call([str(python), "-m", "pip", "check"], cwd=root)
        stamp.write_text(fingerprint + "\n")
        base_stamp.write_text(fingerprint + "\n")
    return python


def main(argv=None):
    if sys.version_info < (3, 11):
        print("GreyTheory needs Python 3.11 or later.", file=sys.stderr)
        return 1
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command")
    workbench = commands.add_parser("workbench", help="open the local analysis interface")
    workbench.add_argument("--request", type=Path)
    workbench.add_argument("--output", type=Path)
    handwriting = commands.add_parser("handwriting", help="compare one image with a reference folder")
    handwriting.add_argument("query", type=Path)
    handwriting.add_argument("references", type=Path)
    handwriting.add_argument("--output", type=Path, default=root / "artifacts/handwriting")
    handwriting.add_argument("--pca", choices=("pca", "sparse", "kernel", "robust", "robust_sparse", "adv"), default="pca")
    args = parser.parse_args(argv)
    if args.command == "handwriting":
        if not args.query.is_file():
            parser.error(f"query image does not exist: {args.query}")
        if not args.references.is_dir():
            parser.error(f"reference folder does not exist: {args.references}")
    if args.command == "workbench" and args.output and not args.request:
        parser.error("--output requires --request")
    try:
        if args.command == "workbench":
            extras = ("images",) if args.request else ("workbench",)
            python = prepare_environment(root, extras=extras)
            command = [str(python), "-m", "examples.workbench.desktop"]
            if args.request:
                command.extend(["--request", str(args.request.resolve())])
            if args.output:
                command.extend(["--output", str(args.output.resolve())])
            return subprocess.call(command, cwd=root)
        if args.command == "handwriting":
            python = prepare_environment(root, extras=("images",))
            return subprocess.call([
                str(python), "-m", "greytheory", "handwriting", str(args.query.resolve()),
                str(args.references.resolve()), "--output", str(args.output.resolve()), "--pca", args.pca,
            ])
        python = prepare_environment(root)
        return subprocess.call([str(python), str(root / "example.py")], cwd=root)
    except subprocess.CalledProcessError as error:
        print("Setup failed. Check the installation error above, then run this command again.", file=sys.stderr)
        return error.returncode


if __name__ == "__main__":
    raise SystemExit(main())
