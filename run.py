"""Prepare the local environment and run the example: python3 run.py."""

import hashlib
from pathlib import Path
import subprocess
import sys
import venv


def prepare_environment(root):
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
    stamp = environment / ".greytheory-install"
    configured = stamp.is_file() and stamp.read_text().strip() == fingerprint
    if configured:
        installed = subprocess.run(
            [str(python), "-c", "from importlib.metadata import distribution; distribution('greytheory')"],
            cwd=root, capture_output=True,
        ).returncode == 0
        healthy = installed and subprocess.run(
            [str(python), "-m", "pip", "check"], cwd=root, capture_output=True,
        ).returncode == 0
    else:
        healthy = False

    if not healthy:
        print("Installing project dependencies (internet access may be needed)...", flush=True)
        subprocess.check_call([str(python), "-m", "pip", "install", "-e", "."], cwd=root)
        subprocess.check_call([str(python), "-m", "pip", "check"], cwd=root)
        stamp.write_text(fingerprint + "\n")
    return python


def main():
    if sys.version_info < (3, 11):
        print("GreyTheory needs Python 3.11 or later.", file=sys.stderr)
        return 1
    root = Path(__file__).resolve().parent
    try:
        python = prepare_environment(root)
        return subprocess.call([str(python), str(root / "example.py")], cwd=root)
    except subprocess.CalledProcessError as error:
        print("Setup failed. Check the installation error above, then run this command again.", file=sys.stderr)
        return error.returncode


if __name__ == "__main__":
    raise SystemExit(main())
