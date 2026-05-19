from __future__ import annotations

import sqlite3
from pathlib import Path

from marcbot.memory_sqlite import (
    SCHEMA_VERSION,
    format_memory_sqlite_status,
    get_memory_sqlite_status,
    initialize_memory_sqlite,
)


def test_initialize_memory_sqlite_creates_database_and_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.sqlite3"

    result = initialize_memory_sqlite(path=db_path)

    assert result.path == db_path
    assert result.schema_version == SCHEMA_VERSION
    assert db_path.is_file()

    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            )
        }

    assert "schema_metadata" in tables
    assert "memory_events" in tables
    assert "memory_facts" in tables
    assert "memory_summaries" in tables
    assert "memory_proposals" in tables
    assert "memory_corrections" in tables
    assert "import_runs" in tables


def test_initialize_memory_sqlite_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.sqlite3"

    initialize_memory_sqlite(path=db_path)
    initialize_memory_sqlite(path=db_path)

    status = get_memory_sqlite_status(path=db_path)

    assert status.exists is True
    assert status.schema_version == SCHEMA_VERSION
    assert status.table_count >= 7
    assert status.provider_contact is False


def test_get_memory_sqlite_status_reports_missing_database(tmp_path: Path) -> None:
    db_path = tmp_path / "missing.sqlite3"

    status = get_memory_sqlite_status(path=db_path)

    assert status.exists is False
    assert status.schema_version is None
    assert status.table_count == 0


def test_format_memory_sqlite_status(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.sqlite3"
    initialize_memory_sqlite(path=db_path)

    message = format_memory_sqlite_status(path=db_path)

    assert "MarcBot memory SQLite" in message
    assert f"Path: {db_path}" in message
    assert "Exists: yes" in message
    assert f"Schema version: {SCHEMA_VERSION}" in message
    assert "Provider contact: no" in message
