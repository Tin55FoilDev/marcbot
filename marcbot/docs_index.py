"""Allowlisted documentation index for MarcBot."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from marcbot.paths import APP_DIR

DOCS_DIR = APP_DIR / "docs"


@dataclass(frozen=True)
class DocEntry:
    """One approved MarcBot documentation entry."""

    name: str
    title: str
    path: Path


APPROVED_DOCS: tuple[DocEntry, ...] = (
    DocEntry("deploy", "Deployment runbook", DOCS_DIR / "DEPLOY.md"),
    DocEntry("roadmap", "Project roadmap", DOCS_DIR / "ROADMAP.md"),
    DocEntry("security", "Security notes", DOCS_DIR / "SECURITY.md"),
    DocEntry("architecture", "Architecture notes", DOCS_DIR / "ARCHITECTURE.md"),
    DocEntry("changelog", "Changelog", DOCS_DIR / "CHANGELOG.md"),
)


def format_docs_index() -> str:
    """Format the approved documentation list for Telegram."""
    lines = [
        "🤖 MarcBot docs",
        "Available docs:",
    ]

    for entry in APPROVED_DOCS:
        lines.append(f"- {entry.name}: {entry.title}")

    lines.extend(
        [
            "",
            "Use: /doc <name>",
        ],
    )

    return "\n".join(lines)
