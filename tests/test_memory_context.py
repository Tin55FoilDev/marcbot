from __future__ import annotations

import sqlite3
from pathlib import Path

from marcbot.memory_context import build_memory_context, format_memory_context
from marcbot.memory_sqlite import initialize_memory_sqlite


def _insert_fact(
    connection,
    *,
    fact_id: str,
    statement: str,
    project: str | None = None,
    status: str = "active",
) -> None:
    connection.execute(
        (
            "INSERT INTO memory_facts("
            "id, statement, category, project, source, created_at, updated_at, "
            "confidence, status, details, source_file, imported_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        ),
        (
            fact_id,
            statement,
            "workflow",
            project,
            "test",
            "2026-05-22T09:00:00+00:00",
            "2026-05-22T10:00:00+00:00",
            "high",
            status,
            "test details",
            f"/tmp/{fact_id}.toml",
            "2026-05-22T11:00:00+00:00",
        ),
    )


def _insert_summary(
    connection,
    *,
    name: str,
    title: str,
    project: str | None = None,
    body: str = "Summary body.",
) -> None:
    connection.execute(
        (
            "INSERT INTO memory_summaries("
            "name, title, project, source, created_at, body, source_file, imported_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        ),
        (
            name,
            title,
            project,
            "test",
            "2026-05-22T10:00:00+00:00",
            body,
            f"/tmp/{name}",
            "2026-05-22T11:00:00+00:00",
        ),
    )


def _insert_event(
    connection,
    *,
    timestamp: str,
    event_type: str,
    summary: str,
    project: str | None = None,
) -> None:
    connection.execute(
        (
            "INSERT INTO memory_events("
            "timestamp, type, project, summary, source, confidence, details, cause, "
            "resolution, verification, follow_up, related_files_json, "
            "related_commands_json, related_artifacts_json, related_commits_json, "
            "source_file, source_line, imported_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        ),
        (
            timestamp,
            event_type,
            project,
            summary,
            "test",
            "high",
            "event details",
            None,
            None,
            None,
            None,
            "[]",
            "[]",
            "[]",
            "[]",
            "/tmp/events.jsonl",
            1,
            "2026-05-22T11:00:00+00:00",
        ),
    )


def test_build_memory_context_assembles_facts_summaries_and_events(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "memory.sqlite3"
    initialize_memory_sqlite(path=db_path)
    with sqlite3.connect(db_path) as connection:
        _insert_fact(
            connection,
            fact_id="weather-fact",
            statement="Weather reports are sent to Telegram.",
            project="weather-report",
        )
        _insert_fact(
            connection,
            fact_id="rejected-fact",
            statement="Weather rejected fact.",
            project="weather-report",
            status="rejected",
        )
        _insert_summary(
            connection,
            name="weather-summary.md",
            title="Weather summary",
            project="weather-report",
            body="Weather report delivery context.",
        )
        _insert_event(
            connection,
            timestamp="2026-05-22T10:00:00+00:00",
            event_type="workflow_completed",
            summary="Weather report workflow completed.",
            project="weather-report",
        )
        connection.commit()

    context = build_memory_context(
        path=db_path,
        project="weather-report",
        query="weather",
    )

    assert [fact.id for fact in context.facts] == ["weather-fact"]
    assert [summary.name for summary in context.summaries] == ["weather-summary.md"]
    assert [event.summary for event in context.events] == [
        "Weather report workflow completed."
    ]


def test_format_memory_context_reports_provider_contact_no(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "memory.sqlite3"
    initialize_memory_sqlite(path=db_path)
    with sqlite3.connect(db_path) as connection:
        _insert_fact(
            connection,
            fact_id="local-fact",
            statement="Local context assembly stays provider-contact-free.",
            project="MarcBot",
        )
        connection.commit()

    message = format_memory_context(
        path=db_path,
        project="MarcBot",
        query="local",
    )

    assert "MarcBot memory context" in message
    assert "Facts:" in message
    assert "Summaries:" in message
    assert "Recent events:" in message
    assert "local-fact" in message
    assert "Provider contact: no" in message


def test_build_memory_context_validates_limits(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.sqlite3"

    try:
        build_memory_context(path=db_path, facts_limit=0)
    except ValueError as exc:
        assert str(exc) == "facts_limit must be 1 or greater"
    else:
        raise AssertionError("Expected ValueError")
