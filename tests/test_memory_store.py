from __future__ import annotations

from pathlib import Path

from marcbot.memory_store import (
    MEMORY_SUBDIRS,
    format_memory_status_message,
    get_memory_status,
    init_memory_store,
)


def test_init_memory_store_creates_expected_layout(tmp_path: Path) -> None:
    result = init_memory_store(root=tmp_path)

    assert result.root == tmp_path
    assert tmp_path.is_dir()
    assert (tmp_path / "README.md").is_file()
    for name in MEMORY_SUBDIRS:
        assert (tmp_path / name).is_dir()

    assert "MarcBot memory initialized:" in result.message


def test_init_memory_store_is_idempotent(tmp_path: Path) -> None:
    first = init_memory_store(root=tmp_path)
    second = init_memory_store(root=tmp_path)

    assert first.created
    assert second.created == ()
    assert second.message == f"MarcBot memory already initialized: {tmp_path}"


def test_get_memory_status_reports_missing_store(tmp_path: Path) -> None:
    root = tmp_path / "memory"
    status = get_memory_status(root=root)

    assert status.initialized is False
    assert status.readme_exists is False
    assert all(value is False for value in status.directories.values())
    assert status.event_files == 0


def test_get_memory_status_counts_files(tmp_path: Path) -> None:
    init_memory_store(root=tmp_path)

    (tmp_path / "events" / "2026-05.jsonl").write_text("{}", encoding="utf-8")
    (tmp_path / "facts" / "weather.toml").write_text("statement = 'x'", encoding="utf-8")
    (tmp_path / "summaries" / "summary.md").write_text("# Summary", encoding="utf-8")
    (tmp_path / "pending" / "proposal.json").write_text("{}", encoding="utf-8")
    (tmp_path / "corrections" / "corrections.jsonl").write_text("{}", encoding="utf-8")
    (tmp_path / "exports" / "export.txt").write_text("export", encoding="utf-8")

    status = get_memory_status(root=tmp_path)

    assert status.initialized is True
    assert status.event_files == 1
    assert status.fact_files == 1
    assert status.summary_files == 1
    assert status.pending_files == 1
    assert status.correction_files == 1
    assert status.export_files == 1


def test_format_memory_status_message(tmp_path: Path) -> None:
    init_memory_store(root=tmp_path)

    message = format_memory_status_message(root=tmp_path)

    assert "MarcBot memory" in message
    assert f"Root: {tmp_path}" in message
    assert "Initialized: yes" in message
    assert "- events: present" in message
    assert "- pending proposals: 0" in message
    assert "Provider contact: no" in message

def test_add_memory_event_writes_jsonl(tmp_path: Path) -> None:
    import json
    from datetime import UTC, datetime

    from marcbot.memory_store import add_memory_event

    result = add_memory_event(
        root=tmp_path,
        timestamp=datetime(2026, 5, 18, 12, 0, tzinfo=UTC),
        event_type="issue_resolved",
        project="marcbot-operations",
        summary="Fixed backup timer warning.",
        source="manual_debug_session",
        confidence="high",
        details="timer_status showed exit-code status 2.",
        cause="Unreadable root-owned backup files.",
        resolution="Removed stale tuning backup files.",
        verification="Backup service exited success.",
        follow_up="Avoid root-owned runtime config backups.",
        related_commands=("sudo systemctl start marcbot-backup.service",),
    )

    assert result.path == tmp_path / "events" / "2026-05.jsonl"
    data = json.loads(result.path.read_text(encoding="utf-8").strip())

    assert data["type"] == "issue_resolved"
    assert data["project"] == "marcbot-operations"
    assert data["summary"] == "Fixed backup timer warning."
    assert data["cause"] == "Unreadable root-owned backup files."
    assert data["related_commands"] == [
        "sudo systemctl start marcbot-backup.service"
    ]


def test_add_memory_event_rejects_unknown_type(tmp_path: Path) -> None:
    import pytest

    from marcbot.memory_store import add_memory_event

    with pytest.raises(ValueError, match="type must be one of"):
        add_memory_event(
            root=tmp_path,
            event_type="unknown",
            summary="Something happened.",
            source="test",
            confidence="high",
        )


def test_list_memory_events_returns_newest_first(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from marcbot.memory_store import add_memory_event, list_memory_events

    add_memory_event(
        root=tmp_path,
        timestamp=datetime(2026, 5, 17, 12, 0, tzinfo=UTC),
        event_type="report_sent",
        summary="Older report sent.",
        source="test",
        confidence="high",
    )
    add_memory_event(
        root=tmp_path,
        timestamp=datetime(2026, 5, 18, 12, 0, tzinfo=UTC),
        event_type="report_sent",
        summary="Newer report sent.",
        source="test",
        confidence="high",
    )

    events = list_memory_events(root=tmp_path, limit=2)

    assert [event.summary for event in events] == [
        "Newer report sent.",
        "Older report sent.",
    ]


def test_format_memory_event_list_reports_no_events(tmp_path: Path) -> None:
    from marcbot.memory_store import format_memory_event_list, init_memory_store

    init_memory_store(root=tmp_path)

    message = format_memory_event_list(root=tmp_path)

    assert "MarcBot memory events" in message
    assert "No events found." in message
    assert "Provider contact: no" in message

def test_add_memory_summary_writes_markdown(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from marcbot.memory_store import add_memory_summary

    result = add_memory_summary(
        root=tmp_path,
        timestamp=datetime(2026, 5, 18, 13, 0, tzinfo=UTC),
        title="Weather workflow completed",
        project="weather-report",
        source="manual_milestone_summary",
        body="The weather workflow is production validated.",
        related_commands=("python -m marcbot weather-report run-send-text",),
        related_commits=("abc1234",),
    )

    assert result.path == tmp_path / "summaries" / "2026-05-18-weather-workflow-completed.md"
    text = result.path.read_text(encoding="utf-8")

    assert 'title: "Weather workflow completed"' in text
    assert 'created_at: "2026-05-18T13:00:00+00:00"' in text
    assert 'project: "weather-report"' in text
    assert "The weather workflow is production validated." in text
    assert "python -m marcbot weather-report run-send-text" in text
    assert "abc1234" in text


def test_add_memory_summary_uses_unique_filename(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from marcbot.memory_store import add_memory_summary

    first = add_memory_summary(
        root=tmp_path,
        timestamp=datetime(2026, 5, 18, 13, 0, tzinfo=UTC),
        title="Same title",
        source="test",
        body="First.",
    )
    second = add_memory_summary(
        root=tmp_path,
        timestamp=datetime(2026, 5, 18, 13, 1, tzinfo=UTC),
        title="Same title",
        source="test",
        body="Second.",
    )

    assert first.path.name == "2026-05-18-same-title.md"
    assert second.path.name == "2026-05-18-same-title-2.md"


def test_list_memory_summaries_returns_newest_first(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from marcbot.memory_store import add_memory_summary, list_memory_summaries

    add_memory_summary(
        root=tmp_path,
        timestamp=datetime(2026, 5, 17, 12, 0, tzinfo=UTC),
        title="Older summary",
        source="test",
        body="Older.",
    )
    add_memory_summary(
        root=tmp_path,
        timestamp=datetime(2026, 5, 18, 12, 0, tzinfo=UTC),
        title="Newer summary",
        source="test",
        body="Newer.",
    )

    summaries = list_memory_summaries(root=tmp_path, limit=2)

    assert [summary.title for summary in summaries] == [
        "Newer summary",
        "Older summary",
    ]


def test_format_memory_summary_list_reports_no_summaries(tmp_path: Path) -> None:
    from marcbot.memory_store import format_memory_summary_list, init_memory_store

    init_memory_store(root=tmp_path)

    message = format_memory_summary_list(root=tmp_path)

    assert "MarcBot memory summaries" in message
    assert "No summaries found." in message
    assert "Provider contact: no" in message
