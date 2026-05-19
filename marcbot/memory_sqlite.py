"""SQLite support for imported MarcBot memory.

The file-based memory store remains the source of truth. This module only
creates and inspects the SQLite schema used for later import/read validation.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from marcbot.memory_store import MEMORY_ROOT

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
