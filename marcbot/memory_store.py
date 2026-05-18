"""Inspectable local memory store scaffolding for MarcBot."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

MEMORY_ROOT = Path("/srv/marcbot/memory")

MEMORY_SUBDIRS: tuple[str, ...] = (
    "events",
    "facts",
    "summaries",
    "pending",
    "corrections",
    "exports",
)

README_TEXT = """# MarcBot local memory

This directory contains MarcBot local runtime memory.

It is local state and is not committed to Git.

Initial memory classes:

- events: append-only or mostly append-only records of what happened
- facts: durable, correctable statements believed to be currently true
- summaries: milestone, project, or session handoff summaries
- pending: proposed memory updates awaiting review
- corrections: correction records for superseded facts
- exports: future memory exports

Memory must not store secrets such as API keys, Telegram bot tokens, OAuth
tokens, passwords, SSH private keys, raw unrestricted logs, or full local config
files containing secrets.

Memory is helpful context, not final authority. Current repo files, command
output, validation results, Git commits, and Marc's explicit corrections remain
authoritative.
"""


@dataclass(frozen=True)
class MemoryStatus:
    """Read-only status for the local memory store."""

    root: Path
    initialized: bool
    readme_exists: bool
    directories: dict[str, bool]
    event_files: int
    fact_files: int
    summary_files: int
    pending_files: int
    correction_files: int
    export_files: int

    def format_message(self) -> str:
        """Return a compact human-readable memory status message."""
        lines = [
            "MarcBot memory",
            f"Root: {self.root}",
            f"Initialized: {'yes' if self.initialized else 'no'}",
            f"README: {'present' if self.readme_exists else 'missing'}",
            "",
            "Directories:",
        ]

        for name in MEMORY_SUBDIRS:
            status = "present" if self.directories.get(name, False) else "missing"
            lines.append(f"- {name}: {status}")

        lines.extend(
            [
                "",
                "Counts:",
                f"- event files: {self.event_files}",
                f"- fact files: {self.fact_files}",
                f"- summary files: {self.summary_files}",
                f"- pending proposals: {self.pending_files}",
                f"- correction files: {self.correction_files}",
                f"- export files: {self.export_files}",
                "Provider contact: no",
            ]
        )

        return "\n".join(lines)


@dataclass(frozen=True)
class MemoryInitResult:
    """Result of initializing the local memory store."""

    root: Path
    created: tuple[Path, ...]

    @property
    def message(self) -> str:
        """Return a compact CLI success message."""
        if not self.created:
            return f"MarcBot memory already initialized: {self.root}"

        return (
            f"MarcBot memory initialized: {self.root} "
            f"({len(self.created)} item(s) created)"
        )


def _count_files(path: Path, pattern: str = "*") -> int:
    """Count regular files in a directory if it exists."""
    if not path.is_dir():
        return 0

    return sum(1 for candidate in path.glob(pattern) if candidate.is_file())


def init_memory_store(root: Path = MEMORY_ROOT) -> MemoryInitResult:
    """Create the local memory directory skeleton."""
    created: list[Path] = []

    if not root.exists():
        root.mkdir(parents=True)
        created.append(root)

    readme = root / "README.md"
    if not readme.exists():
        readme.write_text(README_TEXT, encoding="utf-8")
        created.append(readme)

    for name in MEMORY_SUBDIRS:
        path = root / name
        if not path.exists():
            path.mkdir()
            created.append(path)

    return MemoryInitResult(root=root, created=tuple(created))


def get_memory_status(root: Path = MEMORY_ROOT) -> MemoryStatus:
    """Return read-only status for the local memory directory."""
    readme = root / "README.md"
    directories = {name: (root / name).is_dir() for name in MEMORY_SUBDIRS}
    initialized = root.is_dir() and readme.is_file() and all(directories.values())

    return MemoryStatus(
        root=root,
        initialized=initialized,
        readme_exists=readme.is_file(),
        directories=directories,
        event_files=_count_files(root / "events", "*.jsonl"),
        fact_files=_count_files(root / "facts", "*.toml"),
        summary_files=_count_files(root / "summaries", "*.md"),
        pending_files=_count_files(root / "pending", "*.json"),
        correction_files=_count_files(root / "corrections", "*.jsonl"),
        export_files=_count_files(root / "exports"),
    )


def format_memory_status_message(root: Path = MEMORY_ROOT) -> str:
    """Return a Telegram/CLI friendly memory status message."""
    return get_memory_status(root=root).format_message()
