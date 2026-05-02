"""Tests for MarcBot version metadata consistency."""

import tomllib
from pathlib import Path

from marcbot import __version__


def test_package_version_matches_pyproject() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["version"] == __version__
