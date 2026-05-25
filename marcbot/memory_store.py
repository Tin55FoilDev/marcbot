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
    proposal_files: int
    pending_proposals: int
    approved_proposals: int
    rejected_proposals: int
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
                f"- proposal files: {self.proposal_files}",
                f"- pending proposals: {self.pending_proposals}",
                f"- approved proposals: {self.approved_proposals}",
                f"- rejected proposals: {self.rejected_proposals}",
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


def _count_proposals_by_status(path: Path) -> dict[str, int]:
    """Count proposal JSON files by review status."""
    counts = {"pending": 0, "approved": 0, "rejected": 0}

    if not path.is_dir():
        return counts

    for candidate in path.glob("*.json"):
        if not candidate.is_file():
            continue
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        status = data.get("status")
        if isinstance(status, str) and status in counts:
            counts[status] += 1

    return counts


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

    proposal_counts = _count_proposals_by_status(root / "pending")

    return MemoryStatus(
        root=root,
        initialized=initialized,
        readme_exists=readme.is_file(),
        directories=directories,
        event_files=_count_files(root / "events", "*.jsonl"),
        fact_files=_count_files(root / "facts", "*.toml"),
        summary_files=_count_files(root / "summaries", "*.md"),
        proposal_files=_count_files(root / "pending", "*.json"),
        pending_proposals=proposal_counts["pending"],
        approved_proposals=proposal_counts["approved"],
        rejected_proposals=proposal_counts["rejected"],
        correction_files=_count_files(root / "corrections", "*.jsonl"),
        export_files=_count_files(root / "exports"),
    )


def format_memory_status_message(
    root: Path = MEMORY_ROOT,
    include_sqlite: bool = False,
) -> str:
    """Return a Telegram/CLI friendly memory status message."""
    message = get_memory_status(root=root).format_message()

    if not include_sqlite:
        return message

    try:
        from marcbot.memory_sqlite import (
            DEFAULT_MEMORY_DB_PATH,
            get_memory_sqlite_status,
            validate_memory_sqlite_import,
        )

        sqlite_status = get_memory_sqlite_status(path=DEFAULT_MEMORY_DB_PATH)
        if not sqlite_status.exists:
            sqlite_lines = [
                "",
                "SQLite:",
                "- database: missing",
                "- schema version: unknown",
                "- imported view: not available",
            ]
        else:
            validation = validate_memory_sqlite_import(
                source_root=root,
                database_path=DEFAULT_MEMORY_DB_PATH,
            )
            imported_status = "valid" if validation.valid else "invalid"
            sqlite_lines = [
                "",
                "SQLite:",
                "- database: present",
                f"- schema version: {sqlite_status.schema_version}",
                f"- imported view: {imported_status}",
            ]
    except Exception as exc:
        sqlite_lines = [
            "",
            "SQLite:",
            "- status: warning",
            f"- error: {exc}",
        ]

    return message + "\n" + "\n".join(sqlite_lines)

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
    source_line = 1
    if path.is_file():
        with path.open(encoding="utf-8") as existing_file:
            source_line = sum(1 for line in existing_file if line.strip()) + 1

    with path.open("a", encoding="utf-8") as file_obj:
        file_obj.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")

    _sync_memory_event_to_sqlite_if_available(
        event=event,
        source_file=path,
        source_line=source_line,
    )

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

@dataclass(frozen=True)
class MemorySummary:
    # One explicit memory summary.

    path: Path
    title: str
    created_at: str
    project: str | None
    source: str
    body: str

    def format_one_line(self) -> str:
        project = f" [{self.project}]" if self.project else ""
        return f"{self.created_at}{project}: {self.title}"


@dataclass(frozen=True)
class MemorySummaryAddResult:
    # Result of writing one summary.

    path: Path

    @property
    def message(self) -> str:
        return f"Memory summary added: {self.path}"


def _slugify_summary_title(title: str) -> str:
    cleaned = title.lower()
    chars: list[str] = []
    previous_dash = False

    for char in cleaned:
        if char.isalnum():
            chars.append(char)
            previous_dash = False
            continue

        if not previous_dash:
            chars.append("-")
            previous_dash = True

    slug = "".join(chars).strip("-")
    return slug or "summary"


def add_memory_summary(
    *,
    title: str,
    body: str,
    source: str,
    root: Path = MEMORY_ROOT,
    timestamp: datetime | None = None,
    project: str | None = None,
    related_files: tuple[str, ...] = (),
    related_commands: tuple[str, ...] = (),
    related_artifacts: tuple[str, ...] = (),
    related_commits: tuple[str, ...] = (),
) -> MemorySummaryAddResult:
    init_memory_store(root=root)

    current_time = timestamp or datetime.now(UTC)
    created_at = current_time.astimezone(UTC).replace(microsecond=0).isoformat()
    date_prefix = created_at[:10]
    safe_title = _validate_nonempty_text(title, "title")
    safe_body = _validate_nonempty_text(body, "body")
    safe_source = _validate_nonempty_text(source, "source")
    slug = _slugify_summary_title(safe_title)

    path = root / "summaries" / f"{date_prefix}-{slug}.md"
    counter = 2
    while path.exists():
        path = root / "summaries" / f"{date_prefix}-{slug}-{counter}.md"
        counter += 1

    metadata_lines = [
        "---",
        f'title: "{safe_title}"',
        f'created_at: "{created_at}"',
        f'source: "{safe_source}"',
    ]

    if project and project.strip():
        metadata_lines.append(f'project: "{project.strip()}"')

    if related_files:
        metadata_lines.append("related_files:")
        for item in related_files:
            if item.strip():
                metadata_lines.append(f'  - "{item.strip()}"')

    if related_commands:
        metadata_lines.append("related_commands:")
        for item in related_commands:
            if item.strip():
                metadata_lines.append(f'  - "{item.strip()}"')

    if related_artifacts:
        metadata_lines.append("related_artifacts:")
        for item in related_artifacts:
            if item.strip():
                metadata_lines.append(f'  - "{item.strip()}"')

    if related_commits:
        metadata_lines.append("related_commits:")
        for item in related_commits:
            if item.strip():
                metadata_lines.append(f'  - "{item.strip()}"')

    metadata_lines.extend(["---", "", f"# {safe_title}", "", safe_body.rstrip(), ""])

    path.write_text("\n".join(metadata_lines), encoding="utf-8")

    _sync_memory_summary_to_sqlite_if_available(summary_path=path)

    return MemorySummaryAddResult(path=path)


def _parse_summary_metadata(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}

    end = text.find("\n---\n", 4)
    if end == -1:
        return {}

    metadata: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ": " not in line:
            continue
        key, value = line.split(": ", 1)
        metadata[key.strip()] = value.strip().strip('"')

    return metadata


def list_memory_summaries(
    *,
    root: Path = MEMORY_ROOT,
    limit: int = 10,
) -> tuple[MemorySummary, ...]:
    if limit < 1 or limit > 100:
        raise ValueError("limit must be from 1 to 100")

    summaries_dir = root / "summaries"
    if not summaries_dir.is_dir():
        return ()

    summaries: list[MemorySummary] = []
    for path in sorted(summaries_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        metadata = _parse_summary_metadata(text)
        summaries.append(
            MemorySummary(
                path=path,
                title=metadata.get("title", path.stem),
                created_at=metadata.get("created_at", "unknown"),
                project=metadata.get("project"),
                source=metadata.get("source", "unknown"),
                body=text,
            )
        )

    summaries.sort(key=lambda summary: summary.created_at, reverse=True)
    return tuple(summaries[:limit])


def format_memory_summary_list(
    *,
    root: Path = MEMORY_ROOT,
    limit: int = 10,
) -> str:
    summaries = list_memory_summaries(root=root, limit=limit)

    lines = [
        "MarcBot memory summaries",
        f"Root: {root}",
        f"Limit: {limit}",
    ]

    if not summaries:
        lines.append("No summaries found.")
        lines.append("Provider contact: no")
        return "\n".join(lines)

    for summary in summaries:
        lines.append(f"- {summary.format_one_line()}")
        lines.append(f"  File: {summary.path}")

    lines.append("Provider contact: no")
    return "\n".join(lines)

ALLOWED_FACT_STATUSES: tuple[str, ...] = (
    "active",
    "superseded",
    "rejected",
)


@dataclass(frozen=True)
class MemoryFact:
    # One explicit durable memory fact.

    id: str
    statement: str
    category: str
    source: str
    created_at: str
    updated_at: str
    confidence: str
    status: str
    project: str | None = None
    details: str | None = None
    path: Path | None = None

    def format_one_line(self) -> str:
        project = f" [{self.project}]" if self.project else ""
        return f"{self.id}{project}: {self.statement}"


@dataclass(frozen=True)
class MemoryFactAddResult:
    # Result of writing one fact.

    path: Path
    fact: MemoryFact

    @property
    def message(self) -> str:
        return f"Memory fact added: {self.path}"


def _slugify_fact_id(value: str) -> str:
    cleaned = value.lower()
    chars: list[str] = []
    previous_dash = False

    for char in cleaned:
        if char.isalnum():
            chars.append(char)
            previous_dash = False
            continue

        if not previous_dash:
            chars.append("-")
            previous_dash = True

    slug = "".join(chars).strip("-")
    return slug or "fact"


def _validate_fact_status(status: str) -> str:
    cleaned = _validate_nonempty_text(status, "status")
    if cleaned not in ALLOWED_FACT_STATUSES:
        allowed = ", ".join(ALLOWED_FACT_STATUSES)
        raise ValueError(f"status must be one of: {allowed}")
    return cleaned


def _toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _write_simple_toml(path: Path, values: dict[str, str]) -> None:
    lines = []
    for key, value in values.items():
        lines.append(f'{key} = "{_toml_escape(value)}"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_simple_toml(path: Path) -> dict[str, str]:
    import tomllib

    with path.open("rb") as file_obj:
        data = tomllib.load(file_obj)

    result: dict[str, str] = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = value
    return result


def add_memory_fact(
    *,
    fact_id: str,
    statement: str,
    category: str,
    source: str,
    confidence: str,
    root: Path = MEMORY_ROOT,
    timestamp: datetime | None = None,
    project: str | None = None,
    details: str | None = None,
) -> MemoryFactAddResult:
    init_memory_store(root=root)

    safe_id = _slugify_fact_id(_validate_nonempty_text(fact_id, "id"))
    current_time = timestamp or datetime.now(UTC)
    timestamp_text = current_time.astimezone(UTC).replace(microsecond=0).isoformat()
    path = root / "facts" / f"{safe_id}.toml"

    if path.exists():
        raise ValueError(f"fact already exists: {safe_id}")

    fact = MemoryFact(
        id=safe_id,
        statement=_validate_nonempty_text(statement, "statement"),
        category=_validate_nonempty_text(category, "category"),
        source=_validate_nonempty_text(source, "source"),
        created_at=timestamp_text,
        updated_at=timestamp_text,
        confidence=_validate_confidence(confidence),
        status="active",
        project=project.strip() if project else None,
        details=details.strip() if details else None,
        path=path,
    )

    values = {
        "id": fact.id,
        "statement": fact.statement,
        "category": fact.category,
        "source": fact.source,
        "created_at": fact.created_at,
        "updated_at": fact.updated_at,
        "confidence": fact.confidence,
        "status": fact.status,
    }

    if fact.project:
        values["project"] = fact.project
    if fact.details:
        values["details"] = fact.details

    _write_simple_toml(path, values)
    _sync_memory_fact_to_sqlite_if_available(fact_path=path)
    return MemoryFactAddResult(path=path, fact=fact)


def list_memory_facts(
    *,
    root: Path = MEMORY_ROOT,
    status: str = "active",
    limit: int = 50,
) -> tuple[MemoryFact, ...]:
    if limit < 1 or limit > 200:
        raise ValueError("limit must be from 1 to 200")

    safe_status = _validate_fact_status(status)
    facts_dir = root / "facts"
    if not facts_dir.is_dir():
        return ()

    facts: list[MemoryFact] = []
    for path in sorted(facts_dir.glob("*.toml")):
        data = _read_simple_toml(path)
        if data.get("status", "active") != safe_status:
            continue

        facts.append(
            MemoryFact(
                id=data.get("id", path.stem),
                statement=data.get("statement", ""),
                category=data.get("category", "unknown"),
                source=data.get("source", "unknown"),
                created_at=data.get("created_at", "unknown"),
                updated_at=data.get("updated_at", "unknown"),
                confidence=data.get("confidence", "unknown"),
                status=data.get("status", "active"),
                project=data.get("project"),
                details=data.get("details"),
                path=path,
            )
        )

    facts.sort(key=lambda fact: fact.updated_at, reverse=True)
    return tuple(facts[:limit])


def format_memory_fact_list(
    *,
    root: Path = MEMORY_ROOT,
    status: str = "active",
    limit: int = 50,
) -> str:
    facts = list_memory_facts(root=root, status=status, limit=limit)

    lines = [
        "MarcBot memory facts",
        f"Root: {root}",
        f"Status: {status}",
        f"Limit: {limit}",
    ]

    if not facts:
        lines.append("No facts found.")
        lines.append("Provider contact: no")
        return "\n".join(lines)

    for fact in facts:
        lines.append(f"- {fact.format_one_line()}")
        if fact.details:
            lines.append(f"  Details: {fact.details}")
        if fact.path:
            lines.append(f"  File: {fact.path}")

    lines.append("Provider contact: no")
    return "\n".join(lines)

@dataclass(frozen=True)
class MemoryFactSupersedeResult:
    # Result of superseding one fact with another.

    old_path: Path
    new_path: Path
    correction_path: Path
    old_fact_id: str
    new_fact_id: str

    @property
    def message(self) -> str:
        return (
            f"Memory fact superseded: {self.old_fact_id} -> {self.new_fact_id} "
            f"({self.correction_path})"
        )


def _correction_path_for_timestamp(root: Path, timestamp: str) -> Path:
    return root / "corrections" / f"{timestamp[:7]}.jsonl"


def _append_memory_correction(
    *,
    root: Path,
    timestamp: str,
    correction: dict[str, object],
) -> Path:
    """Append one correction ledger record to file memory."""
    correction_path = _correction_path_for_timestamp(root, timestamp)
    correction_path.parent.mkdir(parents=True, exist_ok=True)

    source_line = 1
    if correction_path.is_file():
        with correction_path.open(encoding="utf-8") as existing_file:
            source_line = sum(1 for line in existing_file if line.strip()) + 1

    with correction_path.open("a", encoding="utf-8") as file_obj:
        file_obj.write(json.dumps(correction, sort_keys=True) + "\n")

    _sync_memory_correction_to_sqlite_if_available(
        correction=correction,
        source_file=correction_path,
        source_line=source_line,
    )

    return correction_path


def _sync_memory_fact_to_sqlite_if_available(*, fact_path: Path) -> None:
    """Sync one real memory fact to SQLite when the database exists."""
    if not _path_is_under(MEMORY_ROOT, fact_path):
        return

    try:
        from marcbot.memory_sqlite import DEFAULT_MEMORY_DB_PATH, upsert_memory_fact_row

        if not DEFAULT_MEMORY_DB_PATH.is_file():
            return

        upsert_memory_fact_row(
            fact_path=fact_path,
            database_path=DEFAULT_MEMORY_DB_PATH,
        )
    except Exception as exc:
        raise RuntimeError(f"SQLite memory fact sync failed: {exc}") from exc


def _memory_fact_from_path(path: Path) -> MemoryFact:
    data = _read_simple_toml(path)
    return MemoryFact(
        id=data.get("id", path.stem),
        statement=data.get("statement", ""),
        category=data.get("category", "unknown"),
        source=data.get("source", "unknown"),
        created_at=data.get("created_at", "unknown"),
        updated_at=data.get("updated_at", "unknown"),
        confidence=data.get("confidence", "unknown"),
        status=data.get("status", "active"),
        project=data.get("project"),
        details=data.get("details"),
        path=path,
    )


def supersede_memory_fact(
    *,
    fact_id: str,
    new_fact_id: str,
    statement: str,
    reason: str,
    source: str,
    confidence: str,
    root: Path = MEMORY_ROOT,
    timestamp: datetime | None = None,
    category: str | None = None,
    project: str | None = None,
    details: str | None = None,
) -> MemoryFactSupersedeResult:
    init_memory_store(root=root)

    old_id = _slugify_fact_id(_validate_nonempty_text(fact_id, "id"))
    safe_new_id = _slugify_fact_id(_validate_nonempty_text(new_fact_id, "new-id"))
    old_path = root / "facts" / f"{old_id}.toml"
    new_path = root / "facts" / f"{safe_new_id}.toml"

    if not old_path.is_file():
        raise ValueError(f"fact does not exist: {old_id}")

    if new_path.exists():
        raise ValueError(f"new fact already exists: {safe_new_id}")

    old_data = _read_simple_toml(old_path)
    old_status = old_data.get("status", "active")
    if old_status != "active":
        raise ValueError(f"fact is not active: {old_id}")

    current_time = timestamp or datetime.now(UTC)
    timestamp_text = current_time.astimezone(UTC).replace(microsecond=0).isoformat()

    new_category = category.strip() if category else old_data.get("category", "unknown")
    new_project = project.strip() if project else old_data.get("project")
    new_details = details.strip() if details else old_data.get("details")

    old_data["status"] = "superseded"
    old_data["updated_at"] = timestamp_text
    old_data["superseded_by"] = safe_new_id
    old_data["superseded_reason"] = _validate_nonempty_text(reason, "reason")
    _write_simple_toml(old_path, old_data)
    _sync_memory_fact_to_sqlite_if_available(fact_path=old_path)

    new_values = {
        "id": safe_new_id,
        "statement": _validate_nonempty_text(statement, "statement"),
        "category": _validate_nonempty_text(new_category, "category"),
        "source": _validate_nonempty_text(source, "source"),
        "created_at": timestamp_text,
        "updated_at": timestamp_text,
        "confidence": _validate_confidence(confidence),
        "status": "active",
        "supersedes": old_id,
        "supersession_reason": _validate_nonempty_text(reason, "reason"),
    }

    if new_project:
        new_values["project"] = new_project
    if new_details:
        new_values["details"] = new_details

    _write_simple_toml(new_path, new_values)
    _sync_memory_fact_to_sqlite_if_available(fact_path=new_path)

    correction = {
        "timestamp": timestamp_text,
        "type": "fact_superseded",
        "old_fact_id": old_id,
        "new_fact_id": safe_new_id,
        "reason": _validate_nonempty_text(reason, "reason"),
        "source": _validate_nonempty_text(source, "source"),
        "confidence": _validate_confidence(confidence),
    }
    correction_path = _append_memory_correction(
        root=root,
        timestamp=timestamp_text,
        correction=correction,
    )

    return MemoryFactSupersedeResult(
        old_path=old_path,
        new_path=new_path,
        correction_path=correction_path,
        old_fact_id=old_id,
        new_fact_id=safe_new_id,
    )

@dataclass(frozen=True)
class MemoryFactRejectResult:
    # Result of rejecting one fact.

    path: Path
    correction_path: Path
    fact_id: str

    @property
    def message(self) -> str:
        return f"Memory fact rejected: {self.fact_id} ({self.correction_path})"


def reject_memory_fact(
    *,
    fact_id: str,
    reason: str,
    source: str,
    confidence: str,
    root: Path = MEMORY_ROOT,
    timestamp: datetime | None = None,
) -> MemoryFactRejectResult:
    init_memory_store(root=root)

    safe_id = _slugify_fact_id(_validate_nonempty_text(fact_id, "id"))
    path = root / "facts" / f"{safe_id}.toml"

    if not path.is_file():
        raise ValueError(f"fact does not exist: {safe_id}")

    data = _read_simple_toml(path)
    current_status = data.get("status", "active")
    if current_status == "rejected":
        raise ValueError(f"fact is already rejected: {safe_id}")

    current_time = timestamp or datetime.now(UTC)
    timestamp_text = current_time.astimezone(UTC).replace(microsecond=0).isoformat()
    safe_reason = _validate_nonempty_text(reason, "reason")
    safe_source = _validate_nonempty_text(source, "source")
    safe_confidence = _validate_confidence(confidence)

    data["status"] = "rejected"
    data["updated_at"] = timestamp_text
    data["rejected_at"] = timestamp_text
    data["rejected_reason"] = safe_reason
    data["rejected_source"] = safe_source
    _write_simple_toml(path, data)
    _sync_memory_fact_to_sqlite_if_available(fact_path=path)

    correction = {
        "timestamp": timestamp_text,
        "type": "fact_rejected",
        "fact_id": safe_id,
        "previous_status": current_status,
        "reason": safe_reason,
        "source": safe_source,
        "confidence": safe_confidence,
    }
    correction_path = _append_memory_correction(
        root=root,
        timestamp=timestamp_text,
        correction=correction,
    )

    return MemoryFactRejectResult(
        path=path,
        correction_path=correction_path,
        fact_id=safe_id,
    )

ALLOWED_PROPOSAL_TYPES: tuple[str, ...] = (
    "event",
    "fact",
    "summary",
)

ALLOWED_PROPOSAL_RISK_LEVELS: tuple[str, ...] = (
    "low",
    "medium",
    "high",
)

ALLOWED_PROPOSAL_STATUSES: tuple[str, ...] = (
    "pending",
    "approved",
    "rejected",
)


@dataclass(frozen=True)
class MemoryProposal:
    # One pending or reviewed memory proposal.

    id: str
    created_at: str
    proposed_type: str
    proposed_statement: str
    source: str
    rationale: str
    risk_level: str
    status: str
    project: str | None = None
    details: str | None = None
    reviewed_at: str | None = None
    review_reason: str | None = None
    path: Path | None = None

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "id": self.id,
            "created_at": self.created_at,
            "proposed_type": self.proposed_type,
            "proposed_statement": self.proposed_statement,
            "source": self.source,
            "rationale": self.rationale,
            "risk_level": self.risk_level,
            "status": self.status,
        }

        optional_values = {
            "project": self.project,
            "details": self.details,
            "reviewed_at": self.reviewed_at,
            "review_reason": self.review_reason,
        }

        for key, value in optional_values.items():
            if value not in (None, ""):
                data[key] = value

        return data

    def format_one_line(self) -> str:
        project = f" [{self.project}]" if self.project else ""
        return (
            f"{self.id}{project}: {self.proposed_type} / {self.risk_level} / "
            f"{self.status}: {self.proposed_statement}"
        )


@dataclass(frozen=True)
class MemoryProposalAddResult:
    # Result of writing one memory proposal.

    path: Path
    proposal: MemoryProposal

    @property
    def message(self) -> str:
        return f"Memory proposal added: {self.path}"


@dataclass(frozen=True)
class MemoryProposalRejectResult:
    # Result of rejecting one memory proposal.

    path: Path
    proposal_id: str

    @property
    def message(self) -> str:
        return f"Memory proposal rejected: {self.proposal_id}"


def _validate_proposal_type(value: str) -> str:
    cleaned = _validate_nonempty_text(value, "proposed-type")
    if cleaned not in ALLOWED_PROPOSAL_TYPES:
        allowed = ", ".join(ALLOWED_PROPOSAL_TYPES)
        raise ValueError(f"proposed-type must be one of: {allowed}")
    return cleaned


def _validate_proposal_risk_level(value: str) -> str:
    cleaned = _validate_nonempty_text(value, "risk-level")
    if cleaned not in ALLOWED_PROPOSAL_RISK_LEVELS:
        allowed = ", ".join(ALLOWED_PROPOSAL_RISK_LEVELS)
        raise ValueError(f"risk-level must be one of: {allowed}")
    return cleaned


def _validate_proposal_status(value: str) -> str:
    cleaned = _validate_nonempty_text(value, "status")
    if cleaned not in ALLOWED_PROPOSAL_STATUSES:
        allowed = ", ".join(ALLOWED_PROPOSAL_STATUSES)
        raise ValueError(f"status must be one of: {allowed}")
    return cleaned


def _proposal_path(root: Path, proposal_id: str) -> Path:
    return root / "pending" / f"{proposal_id}.json"


def _load_memory_proposal(path: Path) -> MemoryProposal:
    data = json.loads(path.read_text(encoding="utf-8"))
    return MemoryProposal(
        id=str(data["id"]),
        created_at=str(data["created_at"]),
        proposed_type=str(data["proposed_type"]),
        proposed_statement=str(data["proposed_statement"]),
        source=str(data["source"]),
        rationale=str(data["rationale"]),
        risk_level=str(data["risk_level"]),
        status=str(data["status"]),
        project=data.get("project"),
        details=data.get("details"),
        reviewed_at=data.get("reviewed_at"),
        review_reason=data.get("review_reason"),
        path=path,
    )


def _write_memory_proposal(path: Path, proposal: MemoryProposal) -> None:
    path.write_text(
        json.dumps(proposal.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sync_memory_proposal_to_sqlite_if_available(*, proposal_path: Path) -> None:
    """Sync one real memory proposal to SQLite when the database exists."""
    if not _path_is_under(MEMORY_ROOT, proposal_path):
        return

    try:
        from marcbot.memory_sqlite import DEFAULT_MEMORY_DB_PATH, upsert_memory_proposal_row

        if not DEFAULT_MEMORY_DB_PATH.is_file():
            return

        upsert_memory_proposal_row(
            proposal_path=proposal_path,
            database_path=DEFAULT_MEMORY_DB_PATH,
        )
    except Exception as exc:
        raise RuntimeError(f"SQLite memory proposal sync failed: {exc}") from exc


def add_memory_proposal(
    *,
    proposal_id: str,
    proposed_type: str,
    proposed_statement: str,
    source: str,
    rationale: str,
    risk_level: str,
    root: Path = MEMORY_ROOT,
    timestamp: datetime | None = None,
    project: str | None = None,
    details: str | None = None,
) -> MemoryProposalAddResult:
    init_memory_store(root=root)

    safe_id = _slugify_fact_id(_validate_nonempty_text(proposal_id, "id"))
    path = _proposal_path(root, safe_id)
    if path.exists():
        raise ValueError(f"proposal already exists: {safe_id}")

    current_time = timestamp or datetime.now(UTC)
    timestamp_text = current_time.astimezone(UTC).replace(microsecond=0).isoformat()

    proposal = MemoryProposal(
        id=safe_id,
        created_at=timestamp_text,
        proposed_type=_validate_proposal_type(proposed_type),
        proposed_statement=_validate_nonempty_text(
            proposed_statement,
            "proposed-statement",
        ),
        source=_validate_nonempty_text(source, "source"),
        rationale=_validate_nonempty_text(rationale, "rationale"),
        risk_level=_validate_proposal_risk_level(risk_level),
        status="pending",
        project=project.strip() if project else None,
        details=details.strip() if details else None,
        path=path,
    )
    _write_memory_proposal(path, proposal)
    _sync_memory_proposal_to_sqlite_if_available(proposal_path=path)

    return MemoryProposalAddResult(path=path, proposal=proposal)


def list_memory_proposals(
    *,
    root: Path = MEMORY_ROOT,
    status: str = "pending",
    limit: int = 50,
) -> tuple[MemoryProposal, ...]:
    if limit < 1 or limit > 200:
        raise ValueError("limit must be from 1 to 200")

    safe_status = _validate_proposal_status(status)
    pending_dir = root / "pending"
    if not pending_dir.is_dir():
        return ()

    proposals: list[MemoryProposal] = []
    for path in sorted(pending_dir.glob("*.json")):
        proposal = _load_memory_proposal(path)
        if proposal.status == safe_status:
            proposals.append(proposal)

    proposals.sort(key=lambda proposal: proposal.created_at, reverse=True)
    return tuple(proposals[:limit])


def format_memory_proposal_list(
    *,
    root: Path = MEMORY_ROOT,
    status: str = "pending",
    limit: int = 50,
) -> str:
    proposals = list_memory_proposals(root=root, status=status, limit=limit)

    lines = [
        "MarcBot memory proposals",
        f"Root: {root}",
        f"Status: {status}",
        f"Limit: {limit}",
    ]

    if not proposals:
        lines.append("No proposals found.")
        lines.append("Provider contact: no")
        return "\n".join(lines)

    for proposal in proposals:
        lines.append(f"- {proposal.format_one_line()}")
        lines.append(f"  Source: {proposal.source}")
        lines.append(f"  Rationale: {proposal.rationale}")
        if proposal.details:
            lines.append(f"  Details: {proposal.details}")
        if proposal.reviewed_at:
            lines.append(f"  Reviewed at: {proposal.reviewed_at}")
        if proposal.review_reason:
            lines.append(f"  Review reason: {proposal.review_reason}")
        if proposal.path:
            lines.append(f"  File: {proposal.path}")

    lines.append("Provider contact: no")
    return "\n".join(lines)


def reject_memory_proposal(
    *,
    proposal_id: str,
    reason: str,
    source: str,
    root: Path = MEMORY_ROOT,
    timestamp: datetime | None = None,
) -> MemoryProposalRejectResult:
    init_memory_store(root=root)

    safe_id = _slugify_fact_id(_validate_nonempty_text(proposal_id, "id"))
    path = _proposal_path(root, safe_id)

    if not path.is_file():
        raise ValueError(f"proposal does not exist: {safe_id}")

    proposal = _load_memory_proposal(path)
    if proposal.status != "pending":
        raise ValueError(f"proposal is not pending: {safe_id}")

    current_time = timestamp or datetime.now(UTC)
    timestamp_text = current_time.astimezone(UTC).replace(microsecond=0).isoformat()

    rejected = MemoryProposal(
        id=proposal.id,
        created_at=proposal.created_at,
        proposed_type=proposal.proposed_type,
        proposed_statement=proposal.proposed_statement,
        source=proposal.source,
        rationale=proposal.rationale,
        risk_level=proposal.risk_level,
        status="rejected",
        project=proposal.project,
        details=proposal.details,
        reviewed_at=timestamp_text,
        review_reason=_validate_nonempty_text(reason, "reason"),
        path=path,
    )
    _write_memory_proposal(path, rejected)
    _sync_memory_proposal_to_sqlite_if_available(proposal_path=path)

    return MemoryProposalRejectResult(path=path, proposal_id=safe_id)

@dataclass(frozen=True)
class MemoryProposalApproveResult:
    # Result of approving one memory proposal.

    proposal_path: Path
    created_path: Path
    proposal_id: str
    created_id: str
    created_type: str

    @property
    def message(self) -> str:
        return (
            f"Memory proposal approved: {self.proposal_id} -> "
            f"{self.created_type} {self.created_id}"
        )


def approve_memory_proposal(
    *,
    proposal_id: str,
    source: str,
    root: Path = MEMORY_ROOT,
    timestamp: datetime | None = None,
    review_reason: str | None = None,
    fact_id: str | None = None,
    category: str = "general",
    confidence: str = "high",
    event_type: str = "workflow_completed",
) -> MemoryProposalApproveResult:
    init_memory_store(root=root)
    safe_id = _slugify_fact_id(_validate_nonempty_text(proposal_id, "id"))
    proposal_path = _proposal_path(root, safe_id)
    if not proposal_path.is_file():
        raise ValueError(f"proposal does not exist: {safe_id}")
    proposal = _load_memory_proposal(proposal_path)
    if proposal.status != "pending":
        raise ValueError(f"proposal is not pending: {safe_id}")
    if proposal.proposed_type not in ("fact", "event", "summary"):
        raise ValueError(
            "only fact, event, and summary proposal approval is supported"
        )

    current_time = timestamp or datetime.now(UTC)
    timestamp_text = current_time.astimezone(UTC).replace(microsecond=0).isoformat()
    safe_source = _validate_nonempty_text(source, "source")
    safe_confidence = _validate_confidence(confidence)
    safe_reason = (
        review_reason.strip()
        if review_reason and review_reason.strip()
        else "Approved after review."
    )

    if proposal.proposed_type == "fact":
        safe_fact_id = _slugify_fact_id(fact_id) if fact_id else proposal.id
        fact_result = add_memory_fact(
            fact_id=safe_fact_id,
            statement=proposal.proposed_statement,
            category=category,
            source=safe_source,
            confidence=safe_confidence,
            root=root,
            timestamp=current_time,
            project=proposal.project,
            details=proposal.details or proposal.rationale,
        )
        created_path = fact_result.path
        created_id = fact_result.fact.id
        created_type = "fact"
    elif proposal.proposed_type == "event":
        event_result = add_memory_event(
            event_type=event_type,
            summary=proposal.proposed_statement,
            source=safe_source,
            confidence=safe_confidence,
            root=root,
            timestamp=current_time,
            project=proposal.project,
            details=proposal.details or proposal.rationale,
        )
        created_path = event_result.path
        created_id = event_result.event.timestamp
        created_type = "event"
    else:
        summary_result = add_memory_summary(
            title=proposal.proposed_statement,
            body=proposal.details or proposal.rationale,
            source=safe_source,
            root=root,
            timestamp=current_time,
            project=proposal.project,
        )
        created_path = summary_result.path
        created_id = summary_result.path.stem
        created_type = "summary"

    approved = MemoryProposal(
        id=proposal.id,
        created_at=proposal.created_at,
        proposed_type=proposal.proposed_type,
        proposed_statement=proposal.proposed_statement,
        source=proposal.source,
        rationale=proposal.rationale,
        risk_level=proposal.risk_level,
        status="approved",
        project=proposal.project,
        details=proposal.details,
        reviewed_at=timestamp_text,
        review_reason=safe_reason,
        path=proposal_path,
    )
    _write_memory_proposal(proposal_path, approved)
    _sync_memory_proposal_to_sqlite_if_available(proposal_path=proposal_path)

    correction = {
        "timestamp": timestamp_text,
        "type": "proposal_approved",
        "proposal_id": proposal.id,
        "created_type": created_type,
        "created_id": created_id,
        "source": safe_source,
        "reason": safe_reason,
        "confidence": safe_confidence,
    }
    _append_memory_correction(
        root=root,
        timestamp=timestamp_text,
        correction=correction,
    )
    return MemoryProposalApproveResult(
        proposal_path=proposal_path,
        created_path=created_path,
        proposal_id=proposal.id,
        created_id=created_id,
        created_type=created_type,
    )
def get_memory_fact(
    *,
    fact_id: str,
    root: Path = MEMORY_ROOT,
) -> MemoryFact:
    safe_id = _slugify_fact_id(_validate_nonempty_text(fact_id, "id"))
    path = root / "facts" / f"{safe_id}.toml"

    if not path.is_file():
        raise ValueError(f"fact does not exist: {safe_id}")

    return _memory_fact_from_path(path)


def format_memory_fact_detail(
    *,
    fact_id: str,
    root: Path = MEMORY_ROOT,
) -> str:
    fact = get_memory_fact(fact_id=fact_id, root=root)

    lines = [
        "MarcBot memory fact",
        f"ID: {fact.id}",
        f"Status: {fact.status}",
        f"Category: {fact.category}",
        f"Project: {fact.project or 'none'}",
        f"Confidence: {fact.confidence}",
        f"Source: {fact.source}",
        f"Created: {fact.created_at}",
        f"Updated: {fact.updated_at}",
        f"Statement: {fact.statement}",
    ]

    if fact.details:
        lines.append(f"Details: {fact.details}")
    if fact.path:
        lines.append(f"File: {fact.path}")

    lines.append("Provider contact: no")
    return "\n".join(lines)


def get_memory_proposal(
    *,
    proposal_id: str,
    root: Path = MEMORY_ROOT,
) -> MemoryProposal:
    safe_id = _slugify_fact_id(_validate_nonempty_text(proposal_id, "id"))
    path = _proposal_path(root, safe_id)

    if not path.is_file():
        raise ValueError(f"proposal does not exist: {safe_id}")

    return _load_memory_proposal(path)


def format_memory_proposal_detail(
    *,
    proposal_id: str,
    root: Path = MEMORY_ROOT,
) -> str:
    proposal = get_memory_proposal(proposal_id=proposal_id, root=root)

    lines = [
        "MarcBot memory proposal",
        f"ID: {proposal.id}",
        f"Status: {proposal.status}",
        f"Proposed type: {proposal.proposed_type}",
        f"Risk level: {proposal.risk_level}",
        f"Project: {proposal.project or 'none'}",
        f"Source: {proposal.source}",
        f"Created: {proposal.created_at}",
        f"Reviewed: {proposal.reviewed_at or 'not reviewed'}",
        f"Proposed statement: {proposal.proposed_statement}",
        f"Rationale: {proposal.rationale}",
    ]

    if proposal.details:
        lines.append(f"Details: {proposal.details}")
    if proposal.review_reason:
        lines.append(f"Review reason: {proposal.review_reason}")
    if proposal.path:
        lines.append(f"File: {proposal.path}")

    lines.append("Provider contact: no")
    return "\n".join(lines)

def format_memory_event_detail(
    *,
    index: int = 1,
    limit: int = 10,
    root: Path = MEMORY_ROOT,
) -> str:
    if index < 1:
        raise ValueError("index must be 1 or greater")

    events = list_memory_events(root=root, limit=limit)
    if index > len(events):
        raise ValueError(f"event index out of range: {index}")

    event = events[index - 1]

    lines = [
        "MarcBot memory event",
        f"Index: {index}",
        f"Timestamp: {event.timestamp}",
        f"Type: {event.type}",
        f"Project: {event.project or 'none'}",
        f"Source: {event.source}",
        f"Confidence: {event.confidence}",
        f"Summary: {event.summary}",
    ]

    optional_fields = [
        ("Details", event.details),
        ("Cause", event.cause),
        ("Resolution", event.resolution),
        ("Verification", event.verification),
        ("Follow-up", event.follow_up),
    ]

    for label, value in optional_fields:
        if value:
            lines.append(f"{label}: {value}")

    list_fields = [
        ("Related files", event.related_files),
        ("Related commands", event.related_commands),
        ("Related artifacts", event.related_artifacts),
        ("Related commits", event.related_commits),
    ]

    for label, values in list_fields:
        if values:
            lines.append(f"{label}:")
            for value in values:
                lines.append(f"- {value}")

    lines.append("Provider contact: no")
    return "\n".join(lines)


def _safe_memory_filename(name: str) -> str:
    cleaned = _validate_nonempty_text(name, "name")
    if Path(cleaned).name != cleaned:
        raise ValueError("name must be a file name, not a path")
    return cleaned


def format_memory_summary_detail(
    *,
    name: str,
    root: Path = MEMORY_ROOT,
) -> str:
    safe_name = _safe_memory_filename(name)
    path = root / "summaries" / safe_name

    if not path.is_file():
        raise ValueError(f"summary does not exist: {safe_name}")

    text = path.read_text(encoding="utf-8")
    metadata = _parse_summary_metadata(text)

    body = text
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            body = text[end + len("\n---\n") :].strip()

    lines = [
        "MarcBot memory summary",
        f"File: {path}",
        f"Title: {metadata.get('title', path.stem)}",
        f"Created: {metadata.get('created_at', 'unknown')}",
        f"Project: {metadata.get('project', 'none')}",
        f"Source: {metadata.get('source', 'unknown')}",
        "Body:",
        body,
        "Provider contact: no",
    ]

    return "\n".join(lines)

SEARCHABLE_MEMORY_SUFFIXES: tuple[str, ...] = (
    ".jsonl",
    ".json",
    ".toml",
    ".md",
)


@dataclass(frozen=True)
class MemorySearchResult:
    # One read-only memory search result.

    path: Path
    line_number: int
    line: str

    def format_one_line(self, root: Path) -> str:
        try:
            relative = self.path.relative_to(root)
        except ValueError:
            relative = self.path

        return f"{relative}:{self.line_number}: {self.line}"


def search_memory(
    query: str,
    *,
    root: Path = MEMORY_ROOT,
    limit: int = 20,
) -> tuple[MemorySearchResult, ...]:
    safe_query = _validate_nonempty_text(query, "query").lower()

    if limit < 1 or limit > 200:
        raise ValueError("limit must be from 1 to 200")

    if not root.is_dir():
        return ()

    results: list[MemorySearchResult] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix not in SEARCHABLE_MEMORY_SUFFIXES:
            continue

        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue

        for line_number, line in enumerate(lines, start=1):
            if safe_query in line.lower():
                excerpt = line.strip()
                if len(excerpt) > 240:
                    excerpt = excerpt[:237] + "..."
                results.append(
                    MemorySearchResult(
                        path=path,
                        line_number=line_number,
                        line=excerpt,
                    )
                )
                if len(results) >= limit:
                    return tuple(results)

    return tuple(results)


def format_memory_search_results(
    query: str,
    *,
    root: Path = MEMORY_ROOT,
    limit: int = 20,
) -> str:
    results = search_memory(query, root=root, limit=limit)

    lines = [
        "MarcBot memory search",
        f"Root: {root}",
        f"Query: {query}",
        f"Limit: {limit}",
    ]

    if not results:
        lines.append("No matches found.")
        lines.append("Provider contact: no")
        return "\n".join(lines)

    for result in results:
        lines.append(f"- {result.format_one_line(root)}")

    lines.append("Provider contact: no")
    return "\n".join(lines)


def _path_is_under(parent: Path, child: Path) -> bool:
    """Return whether child is within parent after path resolution."""
    try:
        child.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _sync_memory_event_to_sqlite_if_available(
    *,
    event: MemoryEvent,
    source_file: Path,
    source_line: int,
) -> None:
    """Sync one appended real memory event to SQLite when the database exists."""
    if not _path_is_under(MEMORY_ROOT, source_file):
        return

    try:
        from marcbot.memory_sqlite import DEFAULT_MEMORY_DB_PATH, insert_memory_event_row

        if not DEFAULT_MEMORY_DB_PATH.is_file():
            return

        insert_memory_event_row(
            event=event,
            source_file=source_file,
            source_line=source_line,
            database_path=DEFAULT_MEMORY_DB_PATH,
        )
    except Exception as exc:
        raise RuntimeError(f"SQLite memory event sync failed: {exc}") from exc


def _sync_memory_summary_to_sqlite_if_available(*, summary_path: Path) -> None:
    """Sync one real memory summary to SQLite when the database exists."""
    if not _path_is_under(MEMORY_ROOT, summary_path):
        return

    try:
        from marcbot.memory_sqlite import DEFAULT_MEMORY_DB_PATH, upsert_memory_summary_row

        if not DEFAULT_MEMORY_DB_PATH.is_file():
            return

        upsert_memory_summary_row(
            summary_path=summary_path,
            database_path=DEFAULT_MEMORY_DB_PATH,
        )
    except Exception as exc:
        raise RuntimeError(f"SQLite memory summary sync failed: {exc}") from exc


def _sync_memory_correction_to_sqlite_if_available(
    *,
    correction: dict[str, object],
    source_file: Path,
    source_line: int,
) -> None:
    """Sync one real memory correction to SQLite when the database exists."""
    if not _path_is_under(MEMORY_ROOT, source_file):
        return

    try:
        from marcbot.memory_sqlite import (
            DEFAULT_MEMORY_DB_PATH,
            insert_memory_correction_row,
        )

        if not DEFAULT_MEMORY_DB_PATH.is_file():
            return

        insert_memory_correction_row(
            correction=correction,
            source_file=source_file,
            source_line=source_line,
            database_path=DEFAULT_MEMORY_DB_PATH,
        )
    except Exception as exc:
        raise RuntimeError(f"SQLite memory correction sync failed: {exc}") from exc

