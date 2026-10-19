"""Resolve the version from source metadata or the installed distribution."""

from importlib.metadata import version
from pathlib import Path
import tomllib


def get_version():
    project_file = Path(__file__).resolve().parents[1] / "pyproject.toml"
    if project_file.is_file():
        project = tomllib.loads(project_file.read_text(encoding="utf-8")).get("project", {})
        if project.get("name") == "greytheory":
            return project["version"]
    return version("greytheory")
