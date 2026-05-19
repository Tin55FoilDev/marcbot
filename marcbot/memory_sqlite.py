"""SQLite support for imported MarcBot memory.

The file-based memory store remains the source of truth. This module only
creates and inspects the SQLite schema used for later import/read validation.
"""

from __future__ import annotations

import json
import sqlite3
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from marcbot.memory_store import MEMORY_ROOT, _parse_summary_metadata

DEFAULT_MEMORY_DB_PATH = MEMORY_ROOT / "marcbot-memory.sqlite3"
SCHEMA_VERSION = 1


@dataclass(frozen=True)
class MemorySqliteInitResult:
    """Result of initializing the SQLite memory database."""

    path: Path
    schema_version: int

    @property
    def message(self) -> str:
        return (
            "MarcBot memory SQLite initialized: "
            f"{self.path} (schema version {self.schema_version})"
        )


@dataclass(frozen=True)
class MemorySqliteStatus:
    """Read-only SQLite memory database status."""

    path: Path
    exists: bool
    schema_version: int | None
    table_count: int
    provider_contact: bool = False

    def format_message(self) -> str:
        schema_version = (
            self.schema_version if self.schema_version is not None else "unknown"
        )
        lines = [
            "MarcBot memory SQLite",
            f"Path: {self.path}",
            f"Exists: {'yes' if self.exists else 'no'}",
            f"Schema version: {schema_version}",
            f"Table count: {self.table_count}",
            "Provider contact: no",
        ]
        return "\n".join(lines)


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memory_events (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    type TEXT NOT NULL,
    project TEXT,
    summary TEXT NOT NULL,
    source TEXT NOT NULL,
    confidence TEXT NOT NULL,
    details TEXT,
    cause TEXT,
    resolution TEXT,
    verification TEXT,
    follow_up TEXT,
    related_files_json TEXT NOT NULL DEFAULT '[]',
    related_commands_json TEXT NOT NULL DEFAULT '[]',
    related_artifacts_json TEXT NOT NULL DEFAULT '[]',
    related_commits_json TEXT NOT NULL DEFAULT '[]',
    source_file TEXT NOT NULL,
    source_line INTEGER NOT NULL,
    imported_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memory_events_timestamp
    ON memory_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_memory_events_type
    ON memory_events(type);
CREATE INDEX IF NOT EXISTS idx_memory_events_project
    ON memory_events(project);
CREATE INDEX IF NOT EXISTS idx_memory_events_source
    ON memory_events(source);

CREATE TABLE IF NOT EXISTS memory_facts (
    id TEXT PRIMARY KEY,
    statement TEXT NOT NULL,
    category TEXT NOT NULL,
    project TEXT,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    confidence TEXT NOT NULL,
    status TEXT NOT NULL,
    details TEXT,
    supersedes TEXT,
    superseded_by TEXT,
    superseded_reason TEXT,
    rejected_at TEXT,
    rejected_reason TEXT,
    rejected_source TEXT,
    source_file TEXT NOT NULL,
    imported_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memory_facts_status
    ON memory_facts(status);
CREATE INDEX IF NOT EXISTS idx_memory_facts_category
    ON memory_facts(category);
CREATE INDEX IF NOT EXISTS idx_memory_facts_project
    ON memory_facts(project);
CREATE INDEX IF NOT EXISTS idx_memory_facts_updated_at
    ON memory_facts(updated_at);

CREATE TABLE IF NOT EXISTS memory_summaries (
    name TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    project TEXT,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL,
    body TEXT NOT NULL,
    source_file TEXT NOT NULL,
    imported_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memory_summaries_created_at
    ON memory_summaries(created_at);
CREATE INDEX IF NOT EXISTS idx_memory_summaries_project
    ON memory_summaries(project);

CREATE TABLE IF NOT EXISTS memory_proposals (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    proposed_type TEXT NOT NULL,
    proposed_statement TEXT NOT NULL,
    source TEXT NOT NULL,
    rationale TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    status TEXT NOT NULL,
    project TEXT,
    details TEXT,
    reviewed_at TEXT,
    review_reason TEXT,
    source_file TEXT NOT NULL,
    imported_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memory_proposals_status
    ON memory_proposals(status);
CREATE INDEX IF NOT EXISTS idx_memory_proposals_proposed_type
    ON memory_proposals(proposed_type);
CREATE INDEX IF NOT EXISTS idx_memory_proposals_risk_level
    ON memory_proposals(risk_level);
CREATE INDEX IF NOT EXISTS idx_memory_proposals_project
    ON memory_proposals(project);
CREATE INDEX IF NOT EXISTS idx_memory_proposals_created_at
    ON memory_proposals(created_at);

CREATE TABLE IF NOT EXISTS memory_corrections (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    type TEXT NOT NULL,
    fact_id TEXT,
    old_fact_id TEXT,
    new_fact_id TEXT,
    proposal_id TEXT,
    created_type TEXT,
    created_id TEXT,
    previous_status TEXT,
    reason TEXT,
    source TEXT,
    confidence TEXT,
    raw_json TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_line INTEGER NOT NULL,
    imported_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memory_corrections_timestamp
    ON memory_corrections(timestamp);
CREATE INDEX IF NOT EXISTS idx_memory_corrections_type
    ON memory_corrections(type);
CREATE INDEX IF NOT EXISTS idx_memory_corrections_fact_id
    ON memory_corrections(fact_id);
CREATE INDEX IF NOT EXISTS idx_memory_corrections_proposal_id
    ON memory_corrections(proposal_id);

CREATE TABLE IF NOT EXISTS import_runs (
    id INTEGER PRIMARY KEY,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    source_root TEXT NOT NULL,
    database_path TEXT NOT NULL,
    event_count INTEGER NOT NULL DEFAULT 0,
    fact_count INTEGER NOT NULL DEFAULT 0,
    summary_count INTEGER NOT NULL DEFAULT 0,
    proposal_count INTEGER NOT NULL DEFAULT 0,
    correction_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    message TEXT
);
"""


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_memory_sqlite(
    path: Path = DEFAULT_MEMORY_DB_PATH,
) -> MemorySqliteInitResult:
    """Create the SQLite memory database schema if needed."""
    with _connect(path) as connection:
        connection.executescript(SCHEMA_SQL)
        connection.execute(
            """
            INSERT INTO schema_metadata(key, value)
            VALUES('schema_version', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (str(SCHEMA_VERSION),),
        )
        connection.commit()

    return MemorySqliteInitResult(path=path, schema_version=SCHEMA_VERSION)


def get_memory_sqlite_status(
    path: Path = DEFAULT_MEMORY_DB_PATH,
) -> MemorySqliteStatus:
    """Return read-only SQLite memory database status."""
    if not path.is_file():
        return MemorySqliteStatus(
            path=path,
            exists=False,
            schema_version=None,
            table_count=0,
        )

    with sqlite3.connect(path) as connection:
        table_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchone()[0]

        row = connection.execute(
            """
            SELECT value
            FROM schema_metadata
            WHERE key = 'schema_version'
            """
        ).fetchone()

    schema_version = int(row[0]) if row is not None else None
    return MemorySqliteStatus(
        path=path,
        exists=True,
        schema_version=schema_version,
        table_count=int(table_count),
    )


def format_memory_sqlite_status(
    path: Path = DEFAULT_MEMORY_DB_PATH,
) -> str:
    """Format read-only SQLite memory database status."""
    return get_memory_sqlite_status(path=path).format_message()


@dataclass(frozen=True)
class MemorySqliteImportResult:
    """Result of importing file memory into SQLite."""

    path: Path
    source_root: Path
    event_count: int
    fact_count: int
    summary_count: int
    proposal_count: int
    correction_count: int

    @property
    def message(self) -> str:
        return (
            f"MarcBot memory SQLite import complete: {self.path} "
            f"(events={self.event_count}, facts={self.fact_count}, "
            f"summaries={self.summary_count}, proposals={self.proposal_count}, "
            f"corrections={self.correction_count})"
        )


def _utc_now_text() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _clear_imported_tables(connection: sqlite3.Connection) -> None:
    for table in (
        "memory_events",
        "memory_facts",
        "memory_summaries",
        "memory_proposals",
        "memory_corrections",
    ):
        connection.execute(f"DELETE FROM {table}")


def _json_list(data: dict[str, object], key: str) -> str:
    value = data.get(key, [])
    if isinstance(value, list):
        return json.dumps(value, sort_keys=True)
    return "[]"


def _insert_events(
    connection: sqlite3.Connection,
    *,
    root: Path,
    imported_at: str,
) -> int:
    count = 0
    events_dir = root / "events"

    if not events_dir.is_dir():
        return count

    for path in sorted(events_dir.glob("*.jsonl")):
        with path.open(encoding="utf-8") as file_obj:
            for line_number, line in enumerate(file_obj, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                data = json.loads(stripped)
                connection.execute(
                    """
                    INSERT INTO memory_events(
                        timestamp,
                        type,
                        project,
                        summary,
                        source,
                        confidence,
                        details,
                        cause,
                        resolution,
                        verification,
                        follow_up,
                        related_files_json,
                        related_commands_json,
                        related_artifacts_json,
                        related_commits_json,
                        source_file,
                        source_line,
                        imported_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(data["timestamp"]),
                        str(data["type"]),
                        data.get("project"),
                        str(data["summary"]),
                        str(data["source"]),
                        str(data["confidence"]),
                        data.get("details"),
                        data.get("cause"),
                        data.get("resolution"),
                        data.get("verification"),
                        data.get("follow_up"),
                        _json_list(data, "related_files"),
                        _json_list(data, "related_commands"),
                        _json_list(data, "related_artifacts"),
                        _json_list(data, "related_commits"),
                        str(path),
                        line_number,
                        imported_at,
                    ),
                )
                count += 1

    return count


def _insert_facts(
    connection: sqlite3.Connection,
    *,
    root: Path,
    imported_at: str,
) -> int:
    count = 0
    facts_dir = root / "facts"

    if not facts_dir.is_dir():
        return count

    for path in sorted(facts_dir.glob("*.toml")):
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        connection.execute(
            """
            INSERT INTO memory_facts(
                id,
                statement,
                category,
                project,
                source,
                created_at,
                updated_at,
                confidence,
                status,
                details,
                supersedes,
                superseded_by,
                superseded_reason,
                rejected_at,
                rejected_reason,
                rejected_source,
                source_file,
                imported_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(data["id"]),
                str(data["statement"]),
                str(data["category"]),
                data.get("project"),
                str(data["source"]),
                str(data["created_at"]),
                str(data["updated_at"]),
                str(data["confidence"]),
                str(data["status"]),
                data.get("details"),
                data.get("supersedes"),
                data.get("superseded_by"),
                data.get("superseded_reason"),
                data.get("rejected_at"),
                data.get("rejected_reason"),
                data.get("rejected_source"),
                str(path),
                imported_at,
            ),
        )
        count += 1

    return count


def _summary_body(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + len("\n---\n") :].strip()
    return text.strip()


def _insert_summaries(
    connection: sqlite3.Connection,
    *,
    root: Path,
    imported_at: str,
) -> int:
    count = 0
    summaries_dir = root / "summaries"

    if not summaries_dir.is_dir():
        return count

    for path in sorted(summaries_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        metadata = _parse_summary_metadata(text)
        connection.execute(
            """
            INSERT INTO memory_summaries(
                name,
                title,
                project,
                source,
                created_at,
                body,
                source_file,
                imported_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                path.name,
                metadata.get("title", path.stem),
                metadata.get("project"),
                metadata.get("source", "unknown"),
                metadata.get("created_at", "unknown"),
                _summary_body(text),
                str(path),
                imported_at,
            ),
        )
        count += 1

    return count


def _insert_proposals(
    connection: sqlite3.Connection,
    *,
    root: Path,
    imported_at: str,
) -> int:
    count = 0
    pending_dir = root / "pending"

    if not pending_dir.is_dir():
        return count

    for path in sorted(pending_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        connection.execute(
            """
            INSERT INTO memory_proposals(
                id,
                created_at,
                proposed_type,
                proposed_statement,
                source,
                rationale,
                risk_level,
                status,
                project,
                details,
                reviewed_at,
                review_reason,
                source_file,
                imported_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(data["id"]),
                str(data["created_at"]),
                str(data["proposed_type"]),
                str(data["proposed_statement"]),
                str(data["source"]),
                str(data["rationale"]),
                str(data["risk_level"]),
                str(data["status"]),
                data.get("project"),
                data.get("details"),
                data.get("reviewed_at"),
                data.get("review_reason"),
                str(path),
                imported_at,
            ),
        )
        count += 1

    return count


def _insert_corrections(
    connection: sqlite3.Connection,
    *,
    root: Path,
    imported_at: str,
) -> int:
    count = 0
    corrections_dir = root / "corrections"

    if not corrections_dir.is_dir():
        return count

    for path in sorted(corrections_dir.glob("*.jsonl")):
        with path.open(encoding="utf-8") as file_obj:
            for line_number, line in enumerate(file_obj, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                data = json.loads(stripped)
                connection.execute(
                    """
                    INSERT INTO memory_corrections(
                        timestamp,
                        type,
                        fact_id,
                        old_fact_id,
                        new_fact_id,
                        proposal_id,
                        created_type,
                        created_id,
                        previous_status,
                        reason,
                        source,
                        confidence,
                        raw_json,
                        source_file,
                        source_line,
                        imported_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(data["timestamp"]),
                        str(data["type"]),
                        data.get("fact_id"),
                        data.get("old_fact_id"),
                        data.get("new_fact_id"),
                        data.get("proposal_id"),
                        data.get("created_type"),
                        data.get("created_id"),
                        data.get("previous_status"),
                        data.get("reason"),
                        data.get("source"),
                        data.get("confidence"),
                        stripped,
                        str(path),
                        line_number,
                        imported_at,
                    ),
                )
                count += 1

    return count


def import_file_memory_to_sqlite(
    *,
    source_root: Path = MEMORY_ROOT,
    database_path: Path = DEFAULT_MEMORY_DB_PATH,
) -> MemorySqliteImportResult:
    """Rebuild the SQLite imported view from file memory."""
    initialize_memory_sqlite(path=database_path)

    started_at = _utc_now_text()
    imported_at = started_at

    with _connect(database_path) as connection:
        _clear_imported_tables(connection)

        event_count = _insert_events(connection, root=source_root, imported_at=imported_at)
        fact_count = _insert_facts(connection, root=source_root, imported_at=imported_at)
        summary_count = _insert_summaries(
            connection,
            root=source_root,
            imported_at=imported_at,
        )
        proposal_count = _insert_proposals(
            connection,
            root=source_root,
            imported_at=imported_at,
        )
        correction_count = _insert_corrections(
            connection,
            root=source_root,
            imported_at=imported_at,
        )

        completed_at = _utc_now_text()
        connection.execute(
            """
            INSERT INTO import_runs(
                started_at,
                completed_at,
                source_root,
                database_path,
                event_count,
                fact_count,
                summary_count,
                proposal_count,
                correction_count,
                status,
                message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                started_at,
                completed_at,
                str(source_root),
                str(database_path),
                event_count,
                fact_count,
                summary_count,
                proposal_count,
                correction_count,
                "success",
                "Import completed successfully.",
            ),
        )
        connection.commit()

    return MemorySqliteImportResult(
        path=database_path,
        source_root=source_root,
        event_count=event_count,
        fact_count=fact_count,
        summary_count=summary_count,
        proposal_count=proposal_count,
        correction_count=correction_count,
    )


def get_sqlite_memory_counts(
    path: Path = DEFAULT_MEMORY_DB_PATH,
) -> dict[str, int]:
    """Return row counts for imported memory tables."""
    if not path.is_file():
        return {
            "events": 0,
            "facts": 0,
            "summaries": 0,
            "proposals": 0,
            "corrections": 0,
            "import_runs": 0,
        }

    with sqlite3.connect(path) as connection:
        return {
            "events": int(connection.execute("SELECT COUNT(*) FROM memory_events").fetchone()[0]),
            "facts": int(connection.execute("SELECT COUNT(*) FROM memory_facts").fetchone()[0]),
            "summaries": int(
                connection.execute("SELECT COUNT(*) FROM memory_summaries").fetchone()[0]
            ),
            "proposals": int(
                connection.execute("SELECT COUNT(*) FROM memory_proposals").fetchone()[0]
            ),
            "corrections": int(
                connection.execute("SELECT COUNT(*) FROM memory_corrections").fetchone()[0]
            ),
            "import_runs": int(
                connection.execute("SELECT COUNT(*) FROM import_runs").fetchone()[0]
            ),
        }


def format_memory_sqlite_counts(
    path: Path = DEFAULT_MEMORY_DB_PATH,
) -> str:
    """Format imported SQLite row counts."""
    counts = get_sqlite_memory_counts(path=path)
    return "\n".join(
        [
            "MarcBot memory SQLite counts",
            f"Path: {path}",
            f"- events: {counts['events']}",
            f"- facts: {counts['facts']}",
            f"- summaries: {counts['summaries']}",
            f"- proposals: {counts['proposals']}",
            f"- corrections: {counts['corrections']}",
            f"- import runs: {counts['import_runs']}",
            "Provider contact: no",
        ]
    )
