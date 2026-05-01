"""Tests for safe workspace listing helpers."""

from pathlib import Path

from marcbot.workspace_list import (
    MAX_LIST_ENTRIES,
    WorkspaceEntry,
    format_workspace_ls_message,
    list_workspace_root,
)


def test_list_workspace_root_lists_visible_entries(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    report = tmp_path / "daily.txt"
    report.write_text("hello", encoding="utf-8")
    hidden = tmp_path / ".hidden"
    hidden.write_text("secret", encoding="utf-8")

    entries = list_workspace_root(tmp_path)
    names = [entry.name for entry in entries]

    assert names == ["reports", "daily.txt"]
    assert ".hidden" not in names


def test_list_workspace_root_sorts_directories_before_files(tmp_path: Path) -> None:
    (tmp_path / "z-file.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "a-dir").mkdir()

    entries = list_workspace_root(tmp_path)

    assert [entry.name for entry in entries] == ["a-dir", "z-file.txt"]


def test_format_workspace_ls_message_empty(tmp_path: Path) -> None:
    message = format_workspace_ls_message(tuple(), workspace_dir=tmp_path)

    assert "🤖 MarcBot workspace" in message
    assert "<empty>" in message
    assert "/send <workspace-relative-path>" in message


def test_format_workspace_ls_message_with_entries(tmp_path: Path) -> None:
    entries = (
        WorkspaceEntry(
            name="reports",
            path=tmp_path / "reports",
            is_dir=True,
            is_file=False,
            size_bytes=None,
        ),
        WorkspaceEntry(
            name="daily.txt",
            path=tmp_path / "daily.txt",
            is_dir=False,
            is_file=True,
            size_bytes=5,
        ),
    )

    message = format_workspace_ls_message(entries, workspace_dir=tmp_path)

    assert "📁 reports/" in message
    assert "📄 daily.txt (5 B)" in message


def test_format_workspace_ls_message_truncates_entry_count(tmp_path: Path) -> None:
    entries = tuple(
        WorkspaceEntry(
            name=f"file-{number}.txt",
            path=tmp_path / f"file-{number}.txt",
            is_dir=False,
            is_file=True,
            size_bytes=1,
        )
        for number in range(MAX_LIST_ENTRIES + 2)
    )

    message = format_workspace_ls_message(entries, workspace_dir=tmp_path)

    assert f"showing {MAX_LIST_ENTRIES} of {MAX_LIST_ENTRIES + 2}" in message


def test_format_workspace_ls_message_missing_workspace(tmp_path: Path) -> None:
    missing = tmp_path / "missing"

    message = format_workspace_ls_message(workspace_dir=missing)

    assert "🤖 MarcBot ls" in message
    assert "workspace directory not found" in message
