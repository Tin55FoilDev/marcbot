"""Tests for local MarcBot chat context loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from marcbot.chat_context import CHAT_CONTEXT_FILENAMES, load_chat_context
from marcbot.errors import MarcBotError


def test_load_chat_context_all_missing_returns_empty_bundle(tmp_path: Path) -> None:
    bundle = load_chat_context(context_dir=tmp_path)

    assert bundle.files == ()
    assert bundle.loaded_names == ()
    assert bundle.total_chars == 0
    status = bundle.format_status()
    assert "MarcBot chat context" in status
    assert "Loaded files: 0" in status
    assert "- system.md: missing" in status


def test_load_chat_context_loads_approved_files_in_prompt_order(tmp_path: Path) -> None:
    (tmp_path / "project.md").write_text("Project context", encoding="utf-8")
    (tmp_path / "agent.md").write_text("Agent context", encoding="utf-8")
    (tmp_path / "ignored.md").write_text("Ignored context", encoding="utf-8")
    (tmp_path / "system.md").write_text("System context", encoding="utf-8")

    bundle = load_chat_context(context_dir=tmp_path)

    assert bundle.loaded_names == ("system.md", "agent.md", "project.md")
    assert [item.content for item in bundle.files] == [
        "System context",
        "Agent context",
        "Project context",
    ]

    assembled = bundle.assemble_text()
    assert "## Local chat context: system.md" in assembled
    assert "System context" in assembled
    assert "Agent context" in assembled
    assert "Project context" in assembled
    assert "Ignored context" not in assembled


def test_load_chat_context_status_does_not_expose_contents(tmp_path: Path) -> None:
    (tmp_path / "system.md").write_text("Private local context", encoding="utf-8")

    bundle = load_chat_context(context_dir=tmp_path)
    status = bundle.format_status()

    assert "- system.md: loaded" in status
    assert "Private local context" not in status


def test_load_chat_context_rejects_oversized_file(tmp_path: Path) -> None:
    (tmp_path / "system.md").write_text("abcd", encoding="utf-8")

    with pytest.raises(MarcBotError) as excinfo:
        load_chat_context(context_dir=tmp_path, max_file_chars=3)

    assert excinfo.value.code == "MBOT-CHATCTX-002"
    assert "system.md" in excinfo.value.message


def test_load_chat_context_rejects_oversized_combined_context(
    tmp_path: Path,
) -> None:
    (tmp_path / "system.md").write_text("abc", encoding="utf-8")
    (tmp_path / "agent.md").write_text("def", encoding="utf-8")

    with pytest.raises(MarcBotError) as excinfo:
        load_chat_context(context_dir=tmp_path, max_total_chars=5)

    assert excinfo.value.code == "MBOT-CHATCTX-003"


def test_load_chat_context_rejects_directory_at_context_file_path(
    tmp_path: Path,
) -> None:
    (tmp_path / "system.md").mkdir()

    with pytest.raises(MarcBotError) as excinfo:
        load_chat_context(context_dir=tmp_path)

    assert excinfo.value.code == "MBOT-CHATCTX-001"


def test_load_chat_context_rejects_invalid_limits(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="max_file_chars"):
        load_chat_context(context_dir=tmp_path, max_file_chars=0)

    with pytest.raises(ValueError, match="max_total_chars"):
        load_chat_context(context_dir=tmp_path, max_total_chars=0)


def test_chat_context_filename_order_is_stable() -> None:
    assert CHAT_CONTEXT_FILENAMES == (
        "system.md",
        "agent.md",
        "user.md",
        "project.md",
    )
