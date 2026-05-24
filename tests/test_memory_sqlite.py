from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from marcbot.memory_sqlite import (
    SCHEMA_VERSION,
    format_memory_sqlite_counts,
    format_memory_sqlite_status,
    format_sqlite_memory_fact_list,
    format_sqlite_memory_summary_list,
    get_memory_sqlite_status,
    get_sqlite_memory_counts,
    import_file_memory_to_sqlite,
    initialize_memory_sqlite,
    query_sqlite_memory_facts,
    query_sqlite_memory_summaries,
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


def test_insert_memory_correction_row_inserts_one_correction(tmp_path: Path) -> None:
    import sqlite3

    from marcbot.memory_sqlite import insert_memory_correction_row

    db_path = tmp_path / "memory.sqlite3"
    correction = {
        "timestamp": "2026-05-19T01:45:00+00:00",
        "type": "fact_rejected",
        "fact_id": "old-fact",
        "previous_status": "active",
        "reason": "Test.",
        "source": "test",
        "confidence": "high",
    }

    inserted = insert_memory_correction_row(
        correction=correction,
        source_file=tmp_path / "corrections" / "2026-05.jsonl",
        source_line=1,
        database_path=db_path,
        imported_at="2026-05-19T01:46:00+00:00",
    )

    assert inserted is True

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT timestamp, type, fact_id, previous_status, reason, source,
                   confidence, raw_json, source_file, source_line
            FROM memory_corrections
            """
        ).fetchone()

    assert row[0] == "2026-05-19T01:45:00+00:00"
    assert row[1] == "fact_rejected"
    assert row[2] == "old-fact"
    assert row[3] == "active"
    assert row[4] == "Test."
    assert row[5] == "test"
    assert row[6] == "high"
    assert '"type": "fact_rejected"' in row[7]
    assert row[8].endswith("2026-05.jsonl")
    assert row[9] == 1


def test_insert_memory_correction_row_is_duplicate_safe(tmp_path: Path) -> None:
    from marcbot.memory_sqlite import (
        get_sqlite_memory_counts,
        insert_memory_correction_row,
    )

    db_path = tmp_path / "memory.sqlite3"
    source_file = tmp_path / "corrections" / "2026-05.jsonl"
    correction = {
        "timestamp": "2026-05-19T01:45:00+00:00",
        "type": "fact_rejected",
        "fact_id": "old-fact",
    }

    first = insert_memory_correction_row(
        correction=correction,
        source_file=source_file,
        source_line=1,
        database_path=db_path,
    )
    second = insert_memory_correction_row(
        correction=correction,
        source_file=source_file,
        source_line=1,
        database_path=db_path,
    )

    counts = get_sqlite_memory_counts(path=db_path)

    assert first is True
    assert second is False
    assert counts["corrections"] == 1


def test_insert_memory_correction_row_rejects_bad_source_line(tmp_path: Path) -> None:
    import pytest

    from marcbot.memory_sqlite import insert_memory_correction_row

    with pytest.raises(ValueError, match="source_line must be 1 or greater"):
        insert_memory_correction_row(
            correction={
                "timestamp": "2026-05-19T01:45:00+00:00",
                "type": "fact_rejected",
            },
            source_file=tmp_path / "corrections" / "2026-05.jsonl",
            source_line=0,
            database_path=tmp_path / "memory.sqlite3",
        )


def test_upsert_memory_proposal_row_inserts_proposal(tmp_path: Path) -> None:
    import sqlite3

    from marcbot.memory_sqlite import upsert_memory_proposal_row

    db_path = tmp_path / "memory.sqlite3"
    proposal_path = tmp_path / "pending" / "test-proposal.json"
    proposal_path.parent.mkdir()
    proposal_path.write_text(
        json.dumps(
            {
                "id": "test-proposal",
                "created_at": "2026-05-19T02:00:00+00:00",
                "proposed_type": "fact",
                "proposed_statement": "A proposed fact.",
                "source": "test",
                "rationale": "Test rationale.",
                "risk_level": "low",
                "status": "pending",
                "project": "marcbot-memory",
                "details": "Useful detail.",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    inserted = upsert_memory_proposal_row(
        proposal_path=proposal_path,
        database_path=db_path,
        imported_at="2026-05-19T02:01:00+00:00",
    )

    assert inserted is True

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT id, created_at, proposed_type, proposed_statement, source,
                   rationale, risk_level, status, project, details, source_file
            FROM memory_proposals
            """
        ).fetchone()

    assert row[0] == "test-proposal"
    assert row[1] == "2026-05-19T02:00:00+00:00"
    assert row[2] == "fact"
    assert row[3] == "A proposed fact."
    assert row[4] == "test"
    assert row[5] == "Test rationale."
    assert row[6] == "low"
    assert row[7] == "pending"
    assert row[8] == "marcbot-memory"
    assert row[9] == "Useful detail."
    assert row[10].endswith("test-proposal.json")


def test_upsert_memory_proposal_row_replaces_existing_proposal(tmp_path: Path) -> None:
    import sqlite3

    from marcbot.memory_sqlite import upsert_memory_proposal_row

    db_path = tmp_path / "memory.sqlite3"
    proposal_path = tmp_path / "pending" / "test-proposal.json"
    proposal_path.parent.mkdir()
    proposal_path.write_text(
        json.dumps(
            {
                "id": "test-proposal",
                "created_at": "2026-05-19T02:00:00+00:00",
                "proposed_type": "fact",
                "proposed_statement": "A proposed fact.",
                "source": "test",
                "rationale": "Test rationale.",
                "risk_level": "low",
                "status": "pending",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    upsert_memory_proposal_row(proposal_path=proposal_path, database_path=db_path)

    proposal_path.write_text(
        json.dumps(
            {
                "id": "test-proposal",
                "created_at": "2026-05-19T02:00:00+00:00",
                "proposed_type": "fact",
                "proposed_statement": "A proposed fact.",
                "source": "test",
                "rationale": "Test rationale.",
                "risk_level": "low",
                "status": "rejected",
                "reviewed_at": "2026-05-19T02:05:00+00:00",
                "review_reason": "Rejected for test.",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    upsert_memory_proposal_row(proposal_path=proposal_path, database_path=db_path)

    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, status, reviewed_at, review_reason
            FROM memory_proposals
            """
        ).fetchall()

    assert rows == [
        (
            "test-proposal",
            "rejected",
            "2026-05-19T02:05:00+00:00",
            "Rejected for test.",
        )
    ]


def test_upsert_memory_proposal_row_rejects_missing_file(tmp_path: Path) -> None:
    import pytest

    from marcbot.memory_sqlite import upsert_memory_proposal_row

    with pytest.raises(FileNotFoundError, match="memory proposal file not found"):
        upsert_memory_proposal_row(
            proposal_path=tmp_path / "missing.json",
            database_path=tmp_path / "memory.sqlite3",
        )


def test_upsert_memory_fact_row_inserts_fact(tmp_path: Path) -> None:
    import sqlite3

    from marcbot.memory_sqlite import upsert_memory_fact_row

    db_path = tmp_path / "memory.sqlite3"
    fact_path = tmp_path / "facts" / "test-fact.toml"
    fact_path.parent.mkdir()
    fact_path.write_text(
        '\n'.join(
            [
                'id = "test-fact"',
                'statement = "A test fact."',
                'category = "test"',
                'project = "marcbot-memory"',
                'source = "test"',
                'created_at = "2026-05-19T02:15:00+00:00"',
                'updated_at = "2026-05-19T02:15:00+00:00"',
                'confidence = "high"',
                'status = "active"',
                'details = "Useful detail."',
                "",
            ]
        ),
        encoding="utf-8",
    )

    inserted = upsert_memory_fact_row(
        fact_path=fact_path,
        database_path=db_path,
        imported_at="2026-05-19T02:16:00+00:00",
    )

    assert inserted is True

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT id, statement, category, project, source, created_at,
                   updated_at, confidence, status, details, source_file
            FROM memory_facts
            """
        ).fetchone()

    assert row[0] == "test-fact"
    assert row[1] == "A test fact."
    assert row[2] == "test"
    assert row[3] == "marcbot-memory"
    assert row[4] == "test"
    assert row[5] == "2026-05-19T02:15:00+00:00"
    assert row[6] == "2026-05-19T02:15:00+00:00"
    assert row[7] == "high"
    assert row[8] == "active"
    assert row[9] == "Useful detail."
    assert row[10].endswith("test-fact.toml")


def test_upsert_memory_fact_row_replaces_existing_fact(tmp_path: Path) -> None:
    import sqlite3

    from marcbot.memory_sqlite import upsert_memory_fact_row

    db_path = tmp_path / "memory.sqlite3"
    fact_path = tmp_path / "facts" / "test-fact.toml"
    fact_path.parent.mkdir()
    fact_path.write_text(
        '\n'.join(
            [
                'id = "test-fact"',
                'statement = "Old fact."',
                'category = "test"',
                'source = "test"',
                'created_at = "2026-05-19T02:15:00+00:00"',
                'updated_at = "2026-05-19T02:15:00+00:00"',
                'confidence = "high"',
                'status = "active"',
                "",
            ]
        ),
        encoding="utf-8",
    )

    upsert_memory_fact_row(fact_path=fact_path, database_path=db_path)

    fact_path.write_text(
        '\n'.join(
            [
                'id = "test-fact"',
                'statement = "Updated fact."',
                'category = "test"',
                'source = "test"',
                'created_at = "2026-05-19T02:15:00+00:00"',
                'updated_at = "2026-05-19T02:20:00+00:00"',
                'confidence = "high"',
                'status = "rejected"',
                'rejected_at = "2026-05-19T02:20:00+00:00"',
                'rejected_reason = "Rejected for test."',
                'rejected_source = "test"',
                "",
            ]
        ),
        encoding="utf-8",
    )

    upsert_memory_fact_row(fact_path=fact_path, database_path=db_path)

    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, statement, status, rejected_reason
            FROM memory_facts
            """
        ).fetchall()

    assert rows == [
        (
            "test-fact",
            "Updated fact.",
            "rejected",
            "Rejected for test.",
        )
    ]


def test_upsert_memory_fact_row_rejects_missing_file(tmp_path: Path) -> None:
    import pytest

    from marcbot.memory_sqlite import upsert_memory_fact_row

    with pytest.raises(FileNotFoundError, match="memory fact file not found"):
        upsert_memory_fact_row(
            fact_path=tmp_path / "missing.toml",
            database_path=tmp_path / "memory.sqlite3",
        )


def _insert_test_sqlite_fact(
    connection,
    *,
    fact_id: str,
    statement: str,
    category: str = "preference",
    project: str | None = None,
    status: str = "active",
    updated_at: str = "2026-05-22T10:00:00+00:00",
) -> None:
    sql = (
        "INSERT INTO memory_facts("
        "id, statement, category, project, source, created_at, updated_at, "
        "confidence, status, details, source_file, imported_at"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    connection.execute(
        sql,
        (
            fact_id,
            statement,
            category,
            project,
            "test",
            "2026-05-22T09:00:00+00:00",
            updated_at,
            "high",
            status,
            "test details",
            f"/tmp/{fact_id}.toml",
            "2026-05-22T11:00:00+00:00",
        ),
    )


def test_query_sqlite_memory_facts_filters_active_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.sqlite3"
    initialize_memory_sqlite(path=db_path)
    with sqlite3.connect(db_path) as connection:
        _insert_test_sqlite_fact(
            connection,
            fact_id="fact-active",
            statement="MarcBot keeps file memory as source of truth.",
            status="active",
        )
        _insert_test_sqlite_fact(
            connection,
            fact_id="fact-rejected",
            statement="Rejected memory fact.",
            status="rejected",
        )
        connection.commit()

    facts = query_sqlite_memory_facts(path=db_path)

    assert [fact.id for fact in facts] == ["fact-active"]


def test_query_sqlite_memory_facts_supports_query_category_and_project(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "memory.sqlite3"
    initialize_memory_sqlite(path=db_path)
    with sqlite3.connect(db_path) as connection:
        _insert_test_sqlite_fact(
            connection,
            fact_id="fact-marcbot",
            statement="SQLite read capability is available.",
            category="architecture",
            project="MarcBot",
        )
        _insert_test_sqlite_fact(
            connection,
            fact_id="fact-other",
            statement="Unrelated active fact.",
            category="preference",
            project="Other",
        )
        connection.commit()

    facts = query_sqlite_memory_facts(
        path=db_path,
        category="architecture",
        project="MarcBot",
        query="read capability",
    )

    assert [fact.id for fact in facts] == ["fact-marcbot"]


def test_format_sqlite_memory_fact_list_includes_provider_contact_no(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "memory.sqlite3"
    initialize_memory_sqlite(path=db_path)
    with sqlite3.connect(db_path) as connection:
        _insert_test_sqlite_fact(
            connection,
            fact_id="fact-format",
            statement="Formatted SQLite facts stay local.",
            category="security",
            project="MarcBot",
        )
        connection.commit()

    message = format_sqlite_memory_fact_list(
        path=db_path,
        category="security",
        project="MarcBot",
        query="local",
    )

    assert "MarcBot memory SQLite facts" in message
    assert "fact-format" in message
    assert "Formatted SQLite facts stay local." in message
    assert "Provider contact: no" in message


def test_query_sqlite_memory_facts_missing_database_returns_empty(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "missing.sqlite3"

    assert query_sqlite_memory_facts(path=db_path) == []


def _insert_test_sqlite_summary(
    connection,
    *,
    name: str,
    title: str,
    project: str | None = None,
    body: str = "Summary body.",
    created_at: str = "2026-05-22T10:00:00+00:00",
) -> None:
    sql = (
        "INSERT INTO memory_summaries("
        "name, title, project, source, created_at, body, source_file, imported_at"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    )
    connection.execute(
        sql,
        (
            name,
            title,
            project,
            "test",
            created_at,
            body,
            f"/tmp/{name}",
            "2026-05-22T11:00:00+00:00",
        ),
    )


def test_query_sqlite_memory_summaries_returns_recent_rows(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "memory.sqlite3"
    initialize_memory_sqlite(path=db_path)
    with sqlite3.connect(db_path) as connection:
        _insert_test_sqlite_summary(
            connection,
            name="older.md",
            title="Older summary",
            created_at="2026-05-21T10:00:00+00:00",
        )
        _insert_test_sqlite_summary(
            connection,
            name="newer.md",
            title="Newer summary",
            created_at="2026-05-22T10:00:00+00:00",
        )
        connection.commit()

    summaries = query_sqlite_memory_summaries(path=db_path, limit=2)

    assert [summary.name for summary in summaries] == ["newer.md", "older.md"]


def test_query_sqlite_memory_summaries_supports_project_and_query(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "memory.sqlite3"
    initialize_memory_sqlite(path=db_path)
    with sqlite3.connect(db_path) as connection:
        _insert_test_sqlite_summary(
            connection,
            name="weather.md",
            title="Weather workflow summary",
            project="weather-report",
            body="Daily weather report delivery workflow notes.",
        )
        _insert_test_sqlite_summary(
            connection,
            name="other.md",
            title="Other workflow summary",
            project="other",
            body="Unrelated notes.",
        )
        connection.commit()

    summaries = query_sqlite_memory_summaries(
        path=db_path,
        project="weather-report",
        query="delivery",
    )

    assert [summary.name for summary in summaries] == ["weather.md"]


def test_format_sqlite_memory_summary_list_includes_provider_contact_no(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "memory.sqlite3"
    initialize_memory_sqlite(path=db_path)
    with sqlite3.connect(db_path) as connection:
        _insert_test_sqlite_summary(
            connection,
            name="summary-format.md",
            title="Formatted summary",
            project="MarcBot",
            body="Formatted SQLite summaries stay local.",
        )
        connection.commit()

    message = format_sqlite_memory_summary_list(
        path=db_path,
        project="MarcBot",
        query="local",
    )

    assert "MarcBot memory SQLite summaries" in message
    assert "summary-format.md" in message
    assert "Formatted summary" in message
    assert "Formatted SQLite summaries stay local." in message
    assert "Provider contact: no" in message


def test_query_sqlite_memory_summaries_missing_database_returns_empty(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "missing.sqlite3"

    assert query_sqlite_memory_summaries(path=db_path) == []
