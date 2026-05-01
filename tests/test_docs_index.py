"""Tests for MarcBot documentation index helpers."""

from marcbot.docs_index import APPROVED_DOCS, format_docs_index


def test_approved_docs_contains_expected_names() -> None:
    names = {entry.name for entry in APPROVED_DOCS}

    assert names == {
        "deploy",
        "roadmap",
        "security",
        "architecture",
        "changelog",
    }


def test_format_docs_index() -> None:
    message = format_docs_index()

    assert "🤖 MarcBot docs" in message
    assert "- deploy: Deployment runbook" in message
    assert "- roadmap: Project roadmap" in message
    assert "- security: Security notes" in message
    assert "- architecture: Architecture notes" in message
    assert "- changelog: Changelog" in message
    assert "Use: /doc <name>" in message
