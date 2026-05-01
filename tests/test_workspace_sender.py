"""Tests for safe workspace file sending validation."""

from pathlib import Path

import pytest

from marcbot import workspace_sender


def test_validate_workspace_send_rejects_empty_path() -> None:
    result = workspace_sender.validate_workspace_send("")

    assert not result.ok
    assert result.path is None
    assert "Missing file path" in result.message


def test_validate_workspace_send_rejects_absolute_path() -> None:
    result = workspace_sender.validate_workspace_send("/etc/passwd")

    assert not result.ok
    assert result.path is None
    assert "Absolute paths are not allowed" in result.message


def test_validate_workspace_send_rejects_parent_traversal() -> None:
    result = workspace_sender.validate_workspace_send("../config/marcbot.toml")

    assert not result.ok
    assert result.path is None
    assert "Parent-directory traversal is not allowed" in result.message


def test_validate_workspace_send_rejects_missing_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(workspace_sender, "WORKSPACE_DIR", tmp_path)

    result = workspace_sender.validate_workspace_send("reports/missing.txt")

    assert not result.ok
    assert result.path is None
    assert "Unable to access file" in result.message


def test_validate_workspace_send_rejects_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    monkeypatch.setattr(workspace_sender, "WORKSPACE_DIR", tmp_path)

    result = workspace_sender.validate_workspace_send("reports")

    assert not result.ok
    assert result.path is None
    assert "not a regular file" in result.message


def test_validate_workspace_send_accepts_workspace_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    report_file = reports_dir / "latest.txt"
    report_file.write_text("hello\n", encoding="utf-8")
    monkeypatch.setattr(workspace_sender, "WORKSPACE_DIR", tmp_path)

    result = workspace_sender.validate_workspace_send("reports/latest.txt")

    assert result.ok
    assert result.path == report_file.resolve()
    assert "Sending workspace file" in result.message


def test_validate_workspace_send_rejects_escaped_symlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outside_file = tmp_path.parent / "outside-secret.txt"
    outside_file.write_text("secret\n", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to(outside_file)
    monkeypatch.setattr(workspace_sender, "WORKSPACE_DIR", tmp_path)

    result = workspace_sender.validate_workspace_send("link.txt")

    assert not result.ok
    assert result.path is None
    assert "outside the workspace" in result.message
