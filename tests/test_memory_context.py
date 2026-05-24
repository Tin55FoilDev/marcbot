from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from marcbot.memory_context import (
    build_memory_context,
    build_memory_context_dict,
    format_memory_context,
    format_memory_context_json,
)
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


def test_format_memory_context_json_is_structured(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.sqlite3"
    initialize_memory_sqlite(path=db_path)
    with sqlite3.connect(db_path) as connection:
        _insert_fact(
            connection,
            fact_id="json-fact",
            statement="JSON context assembly stays structured.",
            project="MarcBot",
        )
        connection.commit()

    payload = json.loads(
        format_memory_context_json(
            path=db_path,
            project="MarcBot",
            query="JSON",
        )
    )

    assert payload["provider_contact"] is False
    assert payload["sqlite"] == {"exists": True, "schema_version": 1}
    assert payload["warnings"] == []
    assert payload["project"] == "MarcBot"
    assert payload["query"] == "JSON"
    assert payload["counts"] == {"events": 0, "facts": 1, "summaries": 0}
    assert payload["facts"][0]["id"] == "json-fact"
    assert payload["summaries"] == []
    assert payload["events"] == []


def test_build_memory_context_dict_is_workflow_facing_contract(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "memory.sqlite3"
    initialize_memory_sqlite(path=db_path)
    with sqlite3.connect(db_path) as connection:
        _insert_fact(
            connection,
            fact_id="contract-fact",
            statement="Workflow code can consume memory context as a dict.",
            project="MarcBot",
        )
        _insert_summary(
            connection,
            name="contract-summary.md",
            title="Contract summary",
            project="MarcBot",
            body="Structured context contract summary body.",
        )
        _insert_event(
            connection,
            timestamp="2026-05-22T10:00:00+00:00",
            event_type="workflow_completed",
            summary="Structured context contract event.",
            project="MarcBot",
        )
        connection.commit()

    payload = build_memory_context_dict(
        path=db_path,
        project="MarcBot",
        query="contract",
        facts_limit=2,
        summaries_limit=2,
        events_limit=2,
    )

    assert payload["provider_contact"] is False
    assert payload["project"] == "MarcBot"
    assert payload["query"] == "contract"
    assert payload["limits"] == {"events": 2, "facts": 2, "summaries": 2}
    assert payload["counts"] == {"events": 1, "facts": 1, "summaries": 1}
    assert payload["facts"][0]["id"] == "contract-fact"
    assert payload["summaries"][0]["name"] == "contract-summary.md"
    assert payload["events"][0]["summary"] == "Structured context contract event."


def test_format_memory_context_json_warns_for_missing_database(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "missing.sqlite3"

    payload = json.loads(format_memory_context_json(path=db_path, query="anything"))

    assert payload["sqlite"] == {"exists": False, "schema_version": None}
    assert "SQLite memory database is missing." in payload["warnings"]
    assert "No matching memory context was found." in payload["warnings"]
    assert payload["counts"] == {"events": 0, "facts": 0, "summaries": 0}


def test_format_memory_context_text_includes_warnings_for_empty_context(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "memory.sqlite3"
    initialize_memory_sqlite(path=db_path)

    message = format_memory_context(path=db_path, query="missing")

    assert "Warnings:" in message
    assert "- No matching memory context was found." in message
    assert "Provider contact: no" in message



def test_get_memory_context_profile_weather_report() -> None:
    from marcbot.memory_context import get_memory_context_profile

    profile = get_memory_context_profile("weather-report")

    assert profile.name == "weather-report"
    assert profile.query == "weather"
    assert profile.project is None
    assert profile.facts_limit == 5
    assert profile.summaries_limit == 2
    assert profile.events_limit == 5


def test_get_memory_context_profile_rejects_unknown_profile() -> None:
    from marcbot.memory_context import get_memory_context_profile

    try:
        get_memory_context_profile("missing")
    except ValueError as exc:
        assert "unknown memory context profile: missing" in str(exc)
        assert "weather-report" in str(exc)
    else:
        raise AssertionError("Expected ValueError")



def test_resolve_memory_context_request_uses_profile_defaults() -> None:
    from marcbot.memory_context import resolve_memory_context_request

    request = resolve_memory_context_request(profile_name="weather-report")

    assert request.query == "weather"
    assert request.project is None
    assert request.facts_limit == 5
    assert request.summaries_limit == 2
    assert request.events_limit == 5


def test_resolve_memory_context_request_allows_query_and_project_overrides() -> None:
    from marcbot.memory_context import resolve_memory_context_request

    request = resolve_memory_context_request(
        profile_name="weather-report",
        query="custom",
        project="weather-report",
        facts_limit=99,
        summaries_limit=99,
        events_limit=99,
    )

    assert request.query == "custom"
    assert request.project == "weather-report"
    assert request.facts_limit == 5
    assert request.summaries_limit == 2
    assert request.events_limit == 5


def test_resolve_memory_context_request_without_profile_preserves_limits() -> None:
    from marcbot.memory_context import resolve_memory_context_request

    request = resolve_memory_context_request(
        query="manual",
        project="manual-project",
        facts_limit=7,
        summaries_limit=4,
        events_limit=2,
    )

    assert request.query == "manual"
    assert request.project == "manual-project"
    assert request.facts_limit == 7
    assert request.summaries_limit == 4
    assert request.events_limit == 2

