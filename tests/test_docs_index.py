"""Tests for MarcBot documentation index helpers."""

from pathlib import Path

from marcbot.docs_index import (
    APPROVED_DOCS,
    DOCS_DIR,
    DocEntry,
    find_doc_entry,
    format_doc_message,
    format_docs_index,
    read_doc_text,
    validate_send_doc,
)


def test_approved_docs_contains_expected_names() -> None:
    names = {entry.name for entry in APPROVED_DOCS}

    assert names == {
        "deploy",
        "roadmap",
        "security",
        "architecture",
        "changelog",
        "commands",
    }


def test_find_doc_entry_finds_doc_case_insensitively() -> None:
    entry = find_doc_entry("DEPLOY")

    assert entry is not None
    assert entry.name == "deploy"


def test_find_doc_entry_returns_none_for_unknown_doc() -> None:
    assert find_doc_entry("unknown") is None


def test_format_docs_index() -> None:
    message = format_docs_index()

    assert "🤖 MarcBot docs" in message
    assert "- deploy: Deployment runbook" in message
    assert "- roadmap: Project roadmap" in message
    assert "- security: Security notes" in message
    assert "- architecture: Architecture notes" in message
    assert "- changelog: Changelog" in message
    assert "- commands: Telegram command reference" in message
    assert "Use: /doc <name>" in message
    assert "Send full file: /senddoc <name>" in message


def test_read_doc_text(tmp_path: Path) -> None:
    doc_file = tmp_path / "TEST.md"
    doc_file.write_text("# Test\n\nBody\n", encoding="utf-8")
    entry = DocEntry("test", "Test doc", doc_file)

    assert read_doc_text(entry) == "# Test\n\nBody\n"


def test_format_doc_message_unknown_doc() -> None:
    message = format_doc_message("unknown")

    assert "Unknown doc name: unknown" in message
    assert "Available docs:" in message
    assert "Use: /doc <name>" in message


def test_validate_send_doc_unknown_doc() -> None:
    result = validate_send_doc("unknown")

    assert not result.ok
    assert result.entry is None
    assert "Unknown doc name: unknown" in result.message
    assert "Use: /senddoc <name>" in result.message


def test_validate_send_doc_known_doc() -> None:
    # This test uses the real docs directory because approved docs are fixed
    # project files and should exist in every valid MarcBot checkout.
    assert DOCS_DIR.is_dir()

    result = validate_send_doc("commands")

    assert result.ok
    assert result.entry is not None
    assert result.entry.name == "commands"
    assert result.entry.path.is_file()
