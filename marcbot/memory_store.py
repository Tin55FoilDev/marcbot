"""Inspectable local memory store scaffolding for MarcBot."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
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

ALLOWED_EVENT_TYPES: tuple[str, ...] = (
    "validation_passed",
    "report_generated",
    "report_sent",
    "timer_validated",
    "service_restarted",
    "backup_completed",
    "issue_detected",
    "issue_resolved",
    "commit_pushed",
    "workflow_completed",
    "design_decision",
)

ALLOWED_CONFIDENCE_VALUES: tuple[str, ...] = (
    "low",
    "medium",
    "high",
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

@dataclass(frozen=True)
class MemoryEvent:
    # One explicit memory event.

    timestamp: str
    type: str
    summary: str
    source: str
    confidence: str
    project: str | None = None
    details: str | None = None
    cause: str | None = None
    resolution: str | None = None
    verification: str | None = None
    follow_up: str | None = None
    related_files: tuple[str, ...] = ()
    related_commands: tuple[str, ...] = ()
    related_artifacts: tuple[str, ...] = ()
    related_commits: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "timestamp": self.timestamp,
            "type": self.type,
            "summary": self.summary,
            "source": self.source,
            "confidence": self.confidence,
        }

        optional_values: dict[str, object | None] = {
            "project": self.project,
            "details": self.details,
            "cause": self.cause,
            "resolution": self.resolution,
            "verification": self.verification,
            "follow_up": self.follow_up,
            "related_files": list(self.related_files) if self.related_files else None,
            "related_commands": list(self.related_commands) if self.related_commands else None,
            "related_artifacts": list(self.related_artifacts) if self.related_artifacts else None,
            "related_commits": list(self.related_commits) if self.related_commits else None,
        }

        for key, value in optional_values.items():
            if value not in (None, "", [], ()):
                data[key] = value

        return data

    def format_one_line(self) -> str:
        project = f" [{self.project}]" if self.project else ""
        return f"{self.timestamp} {self.type}{project}: {self.summary}"


@dataclass(frozen=True)
class MemoryEventAddResult:
    # Result of appending one event.

    path: Path
    event: MemoryEvent

    @property
    def message(self) -> str:
        return f"Memory event added: {self.path}"


def _validate_nonempty_text(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must be non-empty")
    return cleaned


def _validate_event_type(event_type: str) -> str:
    cleaned = _validate_nonempty_text(event_type, "type")
    if cleaned not in ALLOWED_EVENT_TYPES:
        allowed = ", ".join(ALLOWED_EVENT_TYPES)
        raise ValueError(f"type must be one of: {allowed}")
    return cleaned


def _validate_confidence(confidence: str) -> str:
    cleaned = _validate_nonempty_text(confidence, "confidence")
    if cleaned not in ALLOWED_CONFIDENCE_VALUES:
        allowed = ", ".join(ALLOWED_CONFIDENCE_VALUES)
        raise ValueError(f"confidence must be one of: {allowed}")
    return cleaned


def _event_path_for_timestamp(root: Path, timestamp: str) -> Path:
    return root / "events" / f"{timestamp[:7]}.jsonl"


def add_memory_event(
    *,
    event_type: str,
    summary: str,
    source: str,
    confidence: str,
    root: Path = MEMORY_ROOT,
    timestamp: datetime | None = None,
    project: str | None = None,
    details: str | None = None,
    cause: str | None = None,
    resolution: str | None = None,
    verification: str | None = None,
    follow_up: str | None = None,
    related_files: tuple[str, ...] = (),
    related_commands: tuple[str, ...] = (),
    related_artifacts: tuple[str, ...] = (),
    related_commits: tuple[str, ...] = (),
) -> MemoryEventAddResult:
    init_memory_store(root=root)

    current_time = timestamp or datetime.now(UTC)
    timestamp_text = current_time.astimezone(UTC).replace(microsecond=0).isoformat()

    event = MemoryEvent(
        timestamp=timestamp_text,
        type=_validate_event_type(event_type),
        summary=_validate_nonempty_text(summary, "summary"),
        source=_validate_nonempty_text(source, "source"),
        confidence=_validate_confidence(confidence),
        project=project.strip() if project else None,
        details=details.strip() if details else None,
        cause=cause.strip() if cause else None,
        resolution=resolution.strip() if resolution else None,
        verification=verification.strip() if verification else None,
        follow_up=follow_up.strip() if follow_up else None,
        related_files=tuple(item.strip() for item in related_files if item.strip()),
        related_commands=tuple(item.strip() for item in related_commands if item.strip()),
        related_artifacts=tuple(item.strip() for item in related_artifacts if item.strip()),
        related_commits=tuple(item.strip() for item in related_commits if item.strip()),
    )

    path = _event_path_for_timestamp(root, event.timestamp)
    with path.open("a", encoding="utf-8") as file_obj:
        file_obj.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")

    return MemoryEventAddResult(path=path, event=event)


def list_memory_events(
    *,
    root: Path = MEMORY_ROOT,
    limit: int = 10,
) -> tuple[MemoryEvent, ...]:
    if limit < 1 or limit > 100:
        raise ValueError("limit must be from 1 to 100")

    events_dir = root / "events"
    if not events_dir.is_dir():
        return ()

    events: list[MemoryEvent] = []
    for path in sorted(events_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            events.append(
                MemoryEvent(
                    timestamp=str(data["timestamp"]),
                    type=str(data["type"]),
                    summary=str(data["summary"]),
                    source=str(data["source"]),
                    confidence=str(data["confidence"]),
                    project=data.get("project"),
                    details=data.get("details"),
                    cause=data.get("cause"),
                    resolution=data.get("resolution"),
                    verification=data.get("verification"),
                    follow_up=data.get("follow_up"),
                    related_files=tuple(data.get("related_files", ())),
                    related_commands=tuple(data.get("related_commands", ())),
                    related_artifacts=tuple(data.get("related_artifacts", ())),
                    related_commits=tuple(data.get("related_commits", ())),
                )
            )

    events.sort(key=lambda event: event.timestamp, reverse=True)
    return tuple(events[:limit])


def format_memory_event_list(
    *,
    root: Path = MEMORY_ROOT,
    limit: int = 10,
) -> str:
    events = list_memory_events(root=root, limit=limit)

    lines = [
        "MarcBot memory events",
        f"Root: {root}",
        f"Limit: {limit}",
    ]

    if not events:
        lines.append("No events found.")
        lines.append("Provider contact: no")
        return "\n".join(lines)

    for event in events:
        lines.append(f"- {event.format_one_line()}")

    lines.append("Provider contact: no")
    return "\n".join(lines)

