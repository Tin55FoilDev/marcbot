from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from marcbot.memory_sqlite import (
    SCHEMA_VERSION,
    format_memory_sqlite_counts,
    format_memory_sqlite_status,
    get_memory_sqlite_status,
    get_sqlite_memory_counts,
    import_file_memory_to_sqlite,
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



def test_import_file_memory_to_sqlite_imports_records(tmp_path: Path) -> None:
    memory_root = tmp_path / "memory"
    db_path = tmp_path / "memory.sqlite3"

    (memory_root / "events").mkdir(parents=True)
    (memory_root / "facts").mkdir()
    (memory_root / "summaries").mkdir()
    (memory_root / "pending").mkdir()
    (memory_root / "corrections").mkdir()

    (memory_root / "events" / "2026-05.jsonl").write_text(
        json.dumps(
            {
                "timestamp": "2026-05-19T00:00:00+00:00",
                "type": "workflow_completed",
                "project": "test",
                "summary": "Workflow completed.",
                "source": "test",
                "confidence": "high",
                "related_files": ["artifact.md"],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    (memory_root / "facts" / "test-fact.toml").write_text(
        '\n'.join(
            [
                'id = "test-fact"',
                'statement = "A test fact."',
                'category = "test"',
                'project = "test"',
                'source = "test"',
                'created_at = "2026-05-19T00:00:00+00:00"',
                'updated_at = "2026-05-19T00:00:00+00:00"',
                'confidence = "high"',
                'status = "active"',
                'details = "Useful detail."',
                "",
            ]
        ),
        encoding="utf-8",
    )

    (memory_root / "summaries" / "test-summary.md").write_text(
        "---\n"
        'title = "Test summary"\n'
        'project = "test"\n'
        'source = "test"\n'
        'created_at = "2026-05-19T00:00:00+00:00"\n'
        "---\n"
        "# Test summary\n\n"
        "Body text.\n",
        encoding="utf-8",
    )

    (memory_root / "pending" / "test-proposal.json").write_text(
        json.dumps(
            {
                "id": "test-proposal",
                "created_at": "2026-05-19T00:00:00+00:00",
                "proposed_type": "fact",
                "proposed_statement": "A proposed fact.",
                "source": "test",
                "rationale": "Test.",
                "risk_level": "low",
                "status": "pending",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    (memory_root / "corrections" / "2026-05.jsonl").write_text(
        json.dumps(
            {
                "timestamp": "2026-05-19T00:00:00+00:00",
                "type": "fact_rejected",
                "fact_id": "old-fact",
                "reason": "Test.",
                "source": "test",
                "confidence": "high",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    result = import_file_memory_to_sqlite(
        source_root=memory_root,
        database_path=db_path,
    )

    assert result.event_count == 1
    assert result.fact_count == 1
    assert result.summary_count == 1
    assert result.proposal_count == 1
    assert result.correction_count == 1

    counts = get_sqlite_memory_counts(path=db_path)

    assert counts["events"] == 1
    assert counts["facts"] == 1
    assert counts["summaries"] == 1
    assert counts["proposals"] == 1
    assert counts["corrections"] == 1
    assert counts["import_runs"] == 1


def test_import_file_memory_to_sqlite_rebuilds_imported_tables(tmp_path: Path) -> None:
    memory_root = tmp_path / "memory"
    db_path = tmp_path / "memory.sqlite3"

    (memory_root / "events").mkdir(parents=True)
    (memory_root / "events" / "2026-05.jsonl").write_text(
        json.dumps(
            {
                "timestamp": "2026-05-19T00:00:00+00:00",
                "type": "workflow_completed",
                "summary": "First.",
                "source": "test",
                "confidence": "high",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    import_file_memory_to_sqlite(source_root=memory_root, database_path=db_path)
    import_file_memory_to_sqlite(source_root=memory_root, database_path=db_path)

    counts = get_sqlite_memory_counts(path=db_path)

    assert counts["events"] == 1
    assert counts["import_runs"] == 2


def test_format_memory_sqlite_counts(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.sqlite3"
    initialize_memory_sqlite(path=db_path)

    message = format_memory_sqlite_counts(path=db_path)

    assert "MarcBot memory SQLite counts" in message
    assert "- events: 0" in message
    assert "Provider contact: no" in message


def test_get_file_memory_record_counts(tmp_path: Path) -> None:
    memory_root = tmp_path / "memory"
    (memory_root / "events").mkdir(parents=True)
    (memory_root / "facts").mkdir()
    (memory_root / "summaries").mkdir()
    (memory_root / "pending").mkdir()
    (memory_root / "corrections").mkdir()

    (memory_root / "events" / "2026-05.jsonl").write_text(
        '{"summary": "one"}\n\n{"summary": "two"}\n',
        encoding="utf-8",
    )
    (memory_root / "facts" / "one.toml").write_text('id = "one"\n', encoding="utf-8")
    (memory_root / "summaries" / "one.md").write_text("# One\n", encoding="utf-8")
    (memory_root / "pending" / "one.json").write_text("{}\n", encoding="utf-8")
    (memory_root / "corrections" / "2026-05.jsonl").write_text(
        '{"type": "one"}\n',
        encoding="utf-8",
    )

    from marcbot.memory_sqlite import get_file_memory_record_counts

    counts = get_file_memory_record_counts(root=memory_root)

    assert counts == {
        "events": 2,
        "facts": 1,
        "summaries": 1,
        "proposals": 1,
        "corrections": 1,
    }


def test_validate_memory_sqlite_import_reports_valid(tmp_path: Path) -> None:
    import json

    from marcbot.memory_sqlite import (
        import_file_memory_to_sqlite,
        validate_memory_sqlite_import,
    )

    memory_root = tmp_path / "memory"
    db_path = tmp_path / "memory.sqlite3"

    (memory_root / "events").mkdir(parents=True)
    (memory_root / "events" / "2026-05.jsonl").write_text(
        json.dumps(
            {
                "timestamp": "2026-05-19T00:00:00+00:00",
                "type": "workflow_completed",
                "summary": "Workflow completed.",
                "source": "test",
                "confidence": "high",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    import_file_memory_to_sqlite(source_root=memory_root, database_path=db_path)

    result = validate_memory_sqlite_import(
        source_root=memory_root,
        database_path=db_path,
    )

    assert result.valid is True
    assert result.file_counts["events"] == 1
    assert result.sqlite_counts["events"] == 1


def test_validate_memory_sqlite_import_reports_invalid(tmp_path: Path) -> None:
    from marcbot.memory_sqlite import (
        initialize_memory_sqlite,
        validate_memory_sqlite_import,
    )

    memory_root = tmp_path / "memory"
    db_path = tmp_path / "memory.sqlite3"

    (memory_root / "events").mkdir(parents=True)
    (memory_root / "events" / "2026-05.jsonl").write_text(
        '{"timestamp": "2026-05-19T00:00:00+00:00"}\n',
        encoding="utf-8",
    )
    initialize_memory_sqlite(path=db_path)

    result = validate_memory_sqlite_import(
        source_root=memory_root,
        database_path=db_path,
    )

    assert result.valid is False
    assert result.file_counts["events"] == 1
    assert result.sqlite_counts["events"] == 0


def test_format_memory_sqlite_validation(tmp_path: Path) -> None:
    from marcbot.memory_sqlite import (
        format_memory_sqlite_validation,
        initialize_memory_sqlite,
    )

    memory_root = tmp_path / "memory"
    db_path = tmp_path / "memory.sqlite3"

    memory_root.mkdir()
    initialize_memory_sqlite(path=db_path)

    message = format_memory_sqlite_validation(
        source_root=memory_root,
        database_path=db_path,
    )

    assert "MarcBot memory SQLite validation" in message
    assert "- events: files=0 sqlite=0 OK" in message
    assert "Overall: valid" in message
    assert "Provider contact: no" in message


def test_insert_memory_event_row_inserts_one_event(tmp_path: Path) -> None:
    import sqlite3

    from marcbot.memory_sqlite import insert_memory_event_row
    from marcbot.memory_store import MemoryEvent

    db_path = tmp_path / "memory.sqlite3"
    event = MemoryEvent(
        timestamp="2026-05-19T01:00:00+00:00",
        type="workflow_completed",
        summary="Workflow completed.",
        source="test",
        confidence="high",
        project="test-project",
        details="Detailed event.",
        verification="Verified.",
        related_files=("artifact.md",),
        related_commands=("python -m marcbot test",),
    )

    inserted = insert_memory_event_row(
        event=event,
        source_file=tmp_path / "events" / "2026-05.jsonl",
        source_line=1,
        database_path=db_path,
        imported_at="2026-05-19T01:01:00+00:00",
    )

    assert inserted is True

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT timestamp, type, project, summary, source, confidence,
                   details, verification, related_files_json,
                   related_commands_json, source_file, source_line
            FROM memory_events
            """
        ).fetchone()

    assert row[0] == "2026-05-19T01:00:00+00:00"
    assert row[1] == "workflow_completed"
    assert row[2] == "test-project"
    assert row[3] == "Workflow completed."
    assert row[4] == "test"
    assert row[5] == "high"
    assert row[6] == "Detailed event."
    assert row[7] == "Verified."
    assert row[8] == '["artifact.md"]'
    assert row[9] == '["python -m marcbot test"]'
    assert row[10].endswith("2026-05.jsonl")
    assert row[11] == 1


def test_insert_memory_event_row_is_duplicate_safe(tmp_path: Path) -> None:
    from marcbot.memory_sqlite import get_sqlite_memory_counts, insert_memory_event_row
    from marcbot.memory_store import MemoryEvent

    db_path = tmp_path / "memory.sqlite3"
    source_file = tmp_path / "events" / "2026-05.jsonl"
    event = MemoryEvent(
        timestamp="2026-05-19T01:00:00+00:00",
        type="workflow_completed",
        summary="Workflow completed.",
        source="test",
        confidence="high",
    )

    first = insert_memory_event_row(
        event=event,
        source_file=source_file,
        source_line=1,
        database_path=db_path,
    )
    second = insert_memory_event_row(
        event=event,
        source_file=source_file,
        source_line=1,
        database_path=db_path,
    )

    counts = get_sqlite_memory_counts(path=db_path)

    assert first is True
    assert second is False
    assert counts["events"] == 1


def test_insert_memory_event_row_rejects_bad_source_line(tmp_path: Path) -> None:
    import pytest

    from marcbot.memory_sqlite import insert_memory_event_row
    from marcbot.memory_store import MemoryEvent

    event = MemoryEvent(
        timestamp="2026-05-19T01:00:00+00:00",
        type="workflow_completed",
        summary="Workflow completed.",
        source="test",
        confidence="high",
    )

    with pytest.raises(ValueError, match="source_line must be 1 or greater"):
        insert_memory_event_row(
            event=event,
            source_file=tmp_path / "events" / "2026-05.jsonl",
            source_line=0,
            database_path=tmp_path / "memory.sqlite3",
        )


def test_upsert_memory_summary_row_inserts_summary(tmp_path: Path) -> None:
    import sqlite3

    from marcbot.memory_sqlite import upsert_memory_summary_row

    db_path = tmp_path / "memory.sqlite3"
    summary_path = tmp_path / "summaries" / "test-summary.md"
    summary_path.parent.mkdir()
    summary_path.write_text(
        "---\n"
        'title: "Test summary"\n'
        'created_at: "2026-05-19T01:30:00+00:00"\n'
        'source: "test"\n'
        'project: "marcbot-memory"\n'
        "---\n"
        "# Test summary\n\n"
        "Body text.\n",
        encoding="utf-8",
    )

    inserted = upsert_memory_summary_row(
        summary_path=summary_path,
        database_path=db_path,
        imported_at="2026-05-19T01:31:00+00:00",
    )

    assert inserted is True

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT name, title, project, source, created_at, body, source_file
            FROM memory_summaries
            """
        ).fetchone()

    assert row[0] == "test-summary.md"
    assert row[1] == "Test summary"
    assert row[2] == "marcbot-memory"
    assert row[3] == "test"
    assert row[4] == "2026-05-19T01:30:00+00:00"
    assert row[5] == "# Test summary\n\nBody text."
    assert row[6].endswith("test-summary.md")


def test_upsert_memory_summary_row_replaces_existing_summary(tmp_path: Path) -> None:
    import sqlite3

    from marcbot.memory_sqlite import upsert_memory_summary_row

    db_path = tmp_path / "memory.sqlite3"
    summary_path = tmp_path / "summaries" / "test-summary.md"
    summary_path.parent.mkdir()
    summary_path.write_text(
        "---\n"
        'title: "Old title"\n'
        'created_at: "2026-05-19T01:30:00+00:00"\n'
        'source: "test"\n'
        "---\n"
        "Old body.\n",
        encoding="utf-8",
    )

    upsert_memory_summary_row(summary_path=summary_path, database_path=db_path)

    summary_path.write_text(
        "---\n"
        'title: "New title"\n'
        'created_at: "2026-05-19T01:30:00+00:00"\n'
        'source: "test"\n'
        "---\n"
        "New body.\n",
        encoding="utf-8",
    )

    upsert_memory_summary_row(summary_path=summary_path, database_path=db_path)

    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT title, body
            FROM memory_summaries
            """
        ).fetchall()

    assert rows == [("New title", "New body.")]


def test_upsert_memory_summary_row_rejects_missing_file(tmp_path: Path) -> None:
    import pytest

    from marcbot.memory_sqlite import upsert_memory_summary_row

    with pytest.raises(FileNotFoundError, match="memory summary file not found"):
        upsert_memory_summary_row(
            summary_path=tmp_path / "missing.md",
            database_path=tmp_path / "memory.sqlite3",
        )
