"""Tests for MarcBot path helpers."""

from pathlib import Path

from marcbot.paths import PROJECT_ROOT, REQUIRED_RUNTIME_DIRS, missing_runtime_dirs


def test_project_root_is_srv_marcbot() -> None:
    assert PROJECT_ROOT == Path("/srv/marcbot")


def test_required_runtime_dirs_include_project_root() -> None:
    assert PROJECT_ROOT in REQUIRED_RUNTIME_DIRS


def test_missing_runtime_dirs_returns_list() -> None:
    missing = missing_runtime_dirs()
    assert isinstance(missing, list)
