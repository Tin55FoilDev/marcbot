from __future__ import annotations

from pathlib import Path

import pytest

from marcbot.memory_workflows import record_approved_workflow_event


def test_record_approved_workflow_event_writes_event(monkeypatch, tmp_path: Path) -> None:
    import marcbot.memory_workflows as memory_workflows
    from marcbot.memory_store import add_memory_event

    monkeypatch.setattr(
        memory_workflows,
        "add_memory_event",
        lambda **kwargs: add_memory_event(root=tmp_path, **kwargs),
    )

    result = record_approved_workflow_event(
        event_type="workflow_completed",
        project="weather-report",
        summary="Weather report generated and sent.",
        source="weather_report_run_send_text",
        details="Generated artifact and sent Telegram text.",
        verification="Command completed successfully.",
        related_files=(Path("/tmp/weather.md"),),
        related_commands=("python -m marcbot weather-report run-send-text",),
    )

    assert result.path == tmp_path / "events" / f"{result.event.timestamp[:7]}.jsonl"


def test_record_approved_workflow_event_content(monkeypatch, tmp_path: Path) -> None:
    import json

    import marcbot.memory_workflows as memory_workflows
    from marcbot.memory_store import add_memory_event

    monkeypatch.setattr(
        memory_workflows,
        "add_memory_event",
        lambda **kwargs: add_memory_event(root=tmp_path, **kwargs),
    )

    result = record_approved_workflow_event(
        event_type="workflow_completed",
        project="weather-report",
        summary="Weather report generated and sent.",
        source="weather_report_run_send_text",
        details="Generated artifact and sent Telegram text.",
        verification="Command completed successfully.",
        follow_up="Use /weather_status.",
        related_files=("/srv/marcbot/workspace/weather/report.md",),
        related_commands=("python -m marcbot weather-report run-send-text",),
    )

    data = json.loads(result.path.read_text(encoding="utf-8").strip())

    assert data["type"] == "workflow_completed"
    assert data["project"] == "weather-report"
    assert data["summary"] == "Weather report generated and sent."
    assert data["details"] == "Generated artifact and sent Telegram text."
    assert data["verification"] == "Command completed successfully."
    assert data["follow_up"] == "Use /weather_status."
    assert data["related_files"] == ["/srv/marcbot/workspace/weather/report.md"]


def test_record_approved_workflow_event_rejects_unapproved_event_type() -> None:
    with pytest.raises(ValueError, match="event_type must be one of"):
        record_approved_workflow_event(
            event_type="fact_changed",
            project="weather-report",
            summary="Bad event.",
            source="test",
            details="Bad.",
            verification="Bad.",
        )


def test_record_approved_workflow_event_requires_details() -> None:
    with pytest.raises(ValueError, match="details must be non-empty"):
        record_approved_workflow_event(
            event_type="workflow_completed",
            project="weather-report",
            summary="Weather report generated.",
            source="test",
            details="",
            verification="Command completed successfully.",
        )
