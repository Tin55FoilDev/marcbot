"""Allowlisted documentation index for MarcBot."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from marcbot.paths import APP_DIR

DOCS_DIR = APP_DIR / "docs"
MAX_DOC_MESSAGE_CHARS = 3500
MAX_SENDDOC_BYTES = 2_000_000


@dataclass(frozen=True)
class DocEntry:
    """One approved MarcBot documentation entry."""

    name: str
    title: str
    path: Path


@dataclass(frozen=True)
class SendDocResult:
    """Result of validating an approved doc for Telegram file sending."""

    ok: bool
    entry: DocEntry | None
    message: str


APPROVED_DOCS: tuple[DocEntry, ...] = (
    DocEntry("deploy", "Deployment runbook", DOCS_DIR / "DEPLOY.md"),
    DocEntry("roadmap", "Project roadmap", DOCS_DIR / "ROADMAP.md"),
    DocEntry("security", "Security notes", DOCS_DIR / "SECURITY.md"),
    DocEntry("architecture", "Architecture notes", DOCS_DIR / "ARCHITECTURE.md"),
    DocEntry("changelog", "Changelog", DOCS_DIR / "CHANGELOG.md"),
    DocEntry("commands", "Telegram command reference", DOCS_DIR / "COMMANDS.md"),
)


def find_doc_entry(name: str) -> DocEntry | None:
    """Return an approved documentation entry by name."""
    normalized_name = name.strip().lower()

    for entry in APPROVED_DOCS:
        if entry.name == normalized_name:
            return entry

    return None


def approved_doc_names() -> str:
    """Return approved documentation names as a compact string."""
    return ", ".join(entry.name for entry in APPROVED_DOCS)


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
            "Send full file: /senddoc <name>",
        ],
    )

    return "\n".join(lines)


def read_doc_text(entry: DocEntry) -> str:
    """Read an approved documentation file."""
    try:
        return entry.path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"Unable to read doc file: {exc}"


def format_doc_message(name: str) -> str:
    """Format one approved documentation file for Telegram."""
    entry = find_doc_entry(name)
    if entry is None:
        return (
            "🤖 MarcBot doc\n"
            f"Unknown doc name: {name.strip() or '<empty>'}\n"
            f"Available docs: {approved_doc_names()}\n"
            "Use: /doc <name>"
        )

    body = read_doc_text(entry).strip()
    if not body:
        body = "<empty document>"

    message = f"🤖 MarcBot doc: {entry.name}\n{entry.title}\n\n{body}"

    if len(message) <= MAX_DOC_MESSAGE_CHARS:
        return message

    truncated_body = body[:MAX_DOC_MESSAGE_CHARS]
    return (
        f"🤖 MarcBot doc: {entry.name}\n"
        f"{entry.title}\n\n"
        f"{truncated_body}\n\n"
        "[truncated]\n"
        f"Send full file with: /senddoc {entry.name}"
    )


def validate_send_doc(name: str) -> SendDocResult:
    """Validate an approved doc for Telegram file sending."""
    entry = find_doc_entry(name)
    if entry is None:
        return SendDocResult(
            ok=False,
            entry=None,
            message=(
                "🤖 MarcBot senddoc\n"
                f"Unknown doc name: {name.strip() or '<empty>'}\n"
                f"Available docs: {approved_doc_names()}\n"
                "Use: /senddoc <name>"
            ),
        )

    try:
        resolved_docs_dir = DOCS_DIR.resolve(strict=True)
        resolved_path = entry.path.resolve(strict=True)
    except OSError as exc:
        return SendDocResult(
            ok=False,
            entry=entry,
            message=f"🤖 MarcBot senddoc\nUnable to access doc file: {exc}",
        )

    if resolved_docs_dir not in resolved_path.parents:
        return SendDocResult(
            ok=False,
            entry=entry,
            message="🤖 MarcBot senddoc\nRejected doc path outside approved docs directory.",
        )

    if not resolved_path.is_file():
        return SendDocResult(
            ok=False,
            entry=entry,
            message="🤖 MarcBot senddoc\nRejected non-file doc path.",
        )

    size_bytes = resolved_path.stat().st_size
    if size_bytes > MAX_SENDDOC_BYTES:
        return SendDocResult(
            ok=False,
            entry=entry,
            message=(
                "🤖 MarcBot senddoc\n"
                f"Doc file is too large to send: {size_bytes} bytes "
                f"limit={MAX_SENDDOC_BYTES} bytes"
            ),
        )

    return SendDocResult(
        ok=True,
        entry=DocEntry(entry.name, entry.title, resolved_path),
        message=f"Sending doc: {entry.name}",
    )
