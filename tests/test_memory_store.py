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
    assert status.proposal_files == 1
    assert status.pending_proposals == 0
    assert status.correction_files == 1
    assert status.export_files == 1


def test_format_memory_status_message(tmp_path: Path) -> None:
    init_memory_store(root=tmp_path)

    message = format_memory_status_message(root=tmp_path)

    assert "MarcBot memory" in message
    assert f"Root: {tmp_path}" in message
    assert "Initialized: yes" in message
    assert "- events: present" in message
    assert "- proposal files: 0" in message
    assert "- pending proposals: 0" in message
    assert "- approved proposals: 0" in message
    assert "- rejected proposals: 0" in message
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

def test_add_memory_fact_writes_toml(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from marcbot.memory_store import add_memory_fact

    result = add_memory_fact(
        root=tmp_path,
        timestamp=datetime(2026, 5, 18, 14, 0, tzinfo=UTC),
        fact_id="Weather Report Schedule",
        statement="The weather report runs daily around 7:15 AM America/New_York.",
        category="schedule",
        project="weather-report",
        source="manual_fact_entry",
        confidence="high",
        details="Defined by marcbot-weather-report.timer.",
    )

    assert result.path == tmp_path / "facts" / "weather-report-schedule.toml"
    text = result.path.read_text(encoding="utf-8")

    assert 'id = "weather-report-schedule"' in text
    assert 'status = "active"' in text
    assert 'category = "schedule"' in text
    assert 'project = "weather-report"' in text
    assert 'Defined by marcbot-weather-report.timer.' in text


def test_add_memory_fact_rejects_duplicate_id(tmp_path: Path) -> None:
    import pytest

    from marcbot.memory_store import add_memory_fact

    kwargs = {
        "root": tmp_path,
        "fact_id": "duplicate",
        "statement": "A fact.",
        "category": "test",
        "source": "test",
        "confidence": "high",
    }

    add_memory_fact(**kwargs)

    with pytest.raises(ValueError, match="fact already exists"):
        add_memory_fact(**kwargs)


def test_list_memory_facts_returns_active_facts(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from marcbot.memory_store import add_memory_fact, list_memory_facts

    add_memory_fact(
        root=tmp_path,
        timestamp=datetime(2026, 5, 18, 14, 0, tzinfo=UTC),
        fact_id="first",
        statement="First fact.",
        category="test",
        source="test",
        confidence="high",
    )
    add_memory_fact(
        root=tmp_path,
        timestamp=datetime(2026, 5, 18, 15, 0, tzinfo=UTC),
        fact_id="second",
        statement="Second fact.",
        category="test",
        source="test",
        confidence="high",
    )

    facts = list_memory_facts(root=tmp_path)

    assert [fact.id for fact in facts] == ["second", "first"]


def test_format_memory_fact_list_reports_no_facts(tmp_path: Path) -> None:
    from marcbot.memory_store import format_memory_fact_list, init_memory_store

    init_memory_store(root=tmp_path)

    message = format_memory_fact_list(root=tmp_path)

    assert "MarcBot memory facts" in message
    assert "No facts found." in message
    assert "Provider contact: no" in message

def test_supersede_memory_fact_marks_old_and_writes_new(tmp_path: Path) -> None:
    import json
    from datetime import UTC, datetime

    from marcbot.memory_store import add_memory_fact, supersede_memory_fact

    add_memory_fact(
        root=tmp_path,
        timestamp=datetime(2026, 5, 18, 14, 0, tzinfo=UTC),
        fact_id="weather-report-schedule",
        statement="Weather report runs at 8 AM.",
        category="schedule",
        project="weather-report",
        source="test",
        confidence="high",
        details="Old schedule.",
    )

    result = supersede_memory_fact(
        root=tmp_path,
        timestamp=datetime(2026, 5, 18, 15, 0, tzinfo=UTC),
        fact_id="weather-report-schedule",
        new_fact_id="weather-report-schedule-715",
        statement="Weather report runs around 7:15 AM America/New_York.",
        reason="Schedule was changed before production deployment.",
        source="test_correction",
        confidence="high",
        details="Defined by marcbot-weather-report.timer.",
    )

    old_text = result.old_path.read_text(encoding="utf-8")
    new_text = result.new_path.read_text(encoding="utf-8")
    correction = json.loads(result.correction_path.read_text(encoding="utf-8").strip())

    assert 'status = "superseded"' in old_text
    assert 'superseded_by = "weather-report-schedule-715"' in old_text
    assert 'id = "weather-report-schedule-715"' in new_text
    assert 'status = "active"' in new_text
    assert 'supersedes = "weather-report-schedule"' in new_text
    assert correction["type"] == "fact_superseded"
    assert correction["old_fact_id"] == "weather-report-schedule"
    assert correction["new_fact_id"] == "weather-report-schedule-715"


def test_supersede_memory_fact_rejects_missing_old_fact(tmp_path: Path) -> None:
    import pytest

    from marcbot.memory_store import supersede_memory_fact

    with pytest.raises(ValueError, match="fact does not exist"):
        supersede_memory_fact(
            root=tmp_path,
            fact_id="missing",
            new_fact_id="new",
            statement="New fact.",
            reason="Correction.",
            source="test",
            confidence="high",
        )


def test_supersede_memory_fact_rejects_non_active_fact(tmp_path: Path) -> None:
    import pytest

    from marcbot.memory_store import add_memory_fact, supersede_memory_fact

    add_memory_fact(
        root=tmp_path,
        fact_id="old",
        statement="Old fact.",
        category="test",
        source="test",
        confidence="high",
    )
    supersede_memory_fact(
        root=tmp_path,
        fact_id="old",
        new_fact_id="new",
        statement="New fact.",
        reason="Correction.",
        source="test",
        confidence="high",
    )

    with pytest.raises(ValueError, match="fact is not active"):
        supersede_memory_fact(
            root=tmp_path,
            fact_id="old",
            new_fact_id="newer",
            statement="Newer fact.",
            reason="Second correction.",
            source="test",
            confidence="high",
        )

def test_reject_memory_fact_marks_fact_rejected(tmp_path: Path) -> None:
    import json
    from datetime import UTC, datetime

    from marcbot.memory_store import add_memory_fact, reject_memory_fact

    add_memory_fact(
        root=tmp_path,
        timestamp=datetime(2026, 5, 18, 14, 0, tzinfo=UTC),
        fact_id="test-fact",
        statement="Temporary test fact.",
        category="test",
        source="test",
        confidence="high",
    )

    result = reject_memory_fact(
        root=tmp_path,
        timestamp=datetime(2026, 5, 18, 15, 0, tzinfo=UTC),
        fact_id="test-fact",
        reason="Temporary fact cleanup.",
        source="test_cleanup",
        confidence="high",
    )

    fact_text = result.path.read_text(encoding="utf-8")
    correction = json.loads(result.correction_path.read_text(encoding="utf-8").strip())

    assert 'status = "rejected"' in fact_text
    assert 'rejected_reason = "Temporary fact cleanup."' in fact_text
    assert correction["type"] == "fact_rejected"
    assert correction["fact_id"] == "test-fact"
    assert correction["previous_status"] == "active"


def test_reject_memory_fact_rejects_missing_fact(tmp_path: Path) -> None:
    import pytest

    from marcbot.memory_store import reject_memory_fact

    with pytest.raises(ValueError, match="fact does not exist"):
        reject_memory_fact(
            root=tmp_path,
            fact_id="missing",
            reason="Cleanup.",
            source="test",
            confidence="high",
        )


def test_reject_memory_fact_rejects_already_rejected_fact(tmp_path: Path) -> None:
    import pytest

    from marcbot.memory_store import add_memory_fact, reject_memory_fact

    add_memory_fact(
        root=tmp_path,
        fact_id="test-fact",
        statement="Temporary test fact.",
        category="test",
        source="test",
        confidence="high",
    )
    reject_memory_fact(
        root=tmp_path,
        fact_id="test-fact",
        reason="Cleanup.",
        source="test",
        confidence="high",
    )

    with pytest.raises(ValueError, match="fact is already rejected"):
        reject_memory_fact(
            root=tmp_path,
            fact_id="test-fact",
            reason="Second cleanup.",
            source="test",
            confidence="high",
        )

def test_add_memory_proposal_writes_json(tmp_path: Path) -> None:
    import json
    from datetime import UTC, datetime

    from marcbot.memory_store import add_memory_proposal

    result = add_memory_proposal(
        root=tmp_path,
        timestamp=datetime(2026, 5, 18, 16, 0, tzinfo=UTC),
        proposal_id="weather-reference-pattern",
        proposed_type="fact",
        proposed_statement="weather-report is the reference pattern for simple workflows.",
        project="marcbot-memory",
        source="manual_proposal",
        rationale="The workflow validated the project lifecycle.",
        risk_level="medium",
        details="Consider approving after review.",
    )

    assert result.path == tmp_path / "pending" / "weather-reference-pattern.json"
    data = json.loads(result.path.read_text(encoding="utf-8"))

    assert data["id"] == "weather-reference-pattern"
    assert data["proposed_type"] == "fact"
    assert data["status"] == "pending"
    assert data["risk_level"] == "medium"
    assert data["project"] == "marcbot-memory"


def test_add_memory_proposal_rejects_invalid_type(tmp_path: Path) -> None:
    import pytest

    from marcbot.memory_store import add_memory_proposal

    with pytest.raises(ValueError, match="proposed-type must be one of"):
        add_memory_proposal(
            root=tmp_path,
            proposal_id="bad",
            proposed_type="bad",
            proposed_statement="Bad.",
            source="test",
            rationale="Test.",
            risk_level="low",
        )


def test_list_memory_proposals_returns_pending_newest_first(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from marcbot.memory_store import add_memory_proposal, list_memory_proposals

    add_memory_proposal(
        root=tmp_path,
        timestamp=datetime(2026, 5, 18, 15, 0, tzinfo=UTC),
        proposal_id="older",
        proposed_type="fact",
        proposed_statement="Older proposal.",
        source="test",
        rationale="Test.",
        risk_level="low",
    )
    add_memory_proposal(
        root=tmp_path,
        timestamp=datetime(2026, 5, 18, 16, 0, tzinfo=UTC),
        proposal_id="newer",
        proposed_type="fact",
        proposed_statement="Newer proposal.",
        source="test",
        rationale="Test.",
        risk_level="low",
    )

    proposals = list_memory_proposals(root=tmp_path)

    assert [proposal.id for proposal in proposals] == ["newer", "older"]


def test_reject_memory_proposal_marks_proposal_rejected(tmp_path: Path) -> None:
    import json
    from datetime import UTC, datetime

    from marcbot.memory_store import add_memory_proposal, reject_memory_proposal

    add_memory_proposal(
        root=tmp_path,
        timestamp=datetime(2026, 5, 18, 16, 0, tzinfo=UTC),
        proposal_id="test-proposal",
        proposed_type="fact",
        proposed_statement="Temporary proposal.",
        source="test",
        rationale="Test.",
        risk_level="low",
    )

    result = reject_memory_proposal(
        root=tmp_path,
        timestamp=datetime(2026, 5, 18, 17, 0, tzinfo=UTC),
        proposal_id="test-proposal",
        reason="Temporary proposal cleanup.",
        source="test_cleanup",
    )

    data = json.loads(result.path.read_text(encoding="utf-8"))

    assert data["status"] == "rejected"
    assert data["reviewed_at"] == "2026-05-18T17:00:00+00:00"
    assert data["review_reason"] == "Temporary proposal cleanup."


def test_format_memory_proposal_list_reports_no_proposals(tmp_path: Path) -> None:
    from marcbot.memory_store import format_memory_proposal_list, init_memory_store

    init_memory_store(root=tmp_path)

    message = format_memory_proposal_list(root=tmp_path)

    assert "MarcBot memory proposals" in message
    assert "No proposals found." in message
    assert "Provider contact: no" in message

def test_approve_memory_proposal_creates_fact_and_marks_approved(tmp_path: Path) -> None:
    import json
    from datetime import UTC, datetime

    from marcbot.memory_store import add_memory_proposal, approve_memory_proposal

    add_memory_proposal(
        root=tmp_path,
        timestamp=datetime(2026, 5, 18, 16, 0, tzinfo=UTC),
        proposal_id="weather-reference-pattern",
        proposed_type="fact",
        proposed_statement="Weather report is the reference pattern.",
        project="marcbot-memory",
        source="test_proposal",
        rationale="It validated the workflow lifecycle.",
        risk_level="medium",
        details="Useful implementation pattern.",
    )

    result = approve_memory_proposal(
        root=tmp_path,
        timestamp=datetime(2026, 5, 18, 17, 0, tzinfo=UTC),
        proposal_id="weather-reference-pattern",
        source="test_approval",
        review_reason="Looks correct.",
        category="project-pattern",
        confidence="high",
    )

    proposal_data = json.loads(result.proposal_path.read_text(encoding="utf-8"))
    fact_text = result.created_path.read_text(encoding="utf-8")
    correction_text = (tmp_path / "corrections" / "2026-05.jsonl").read_text(
        encoding="utf-8"
    )

    assert result.created_id == "weather-reference-pattern"
    assert proposal_data["status"] == "approved"
    assert proposal_data["reviewed_at"] == "2026-05-18T17:00:00+00:00"
    assert proposal_data["review_reason"] == "Looks correct."
    assert 'id = "weather-reference-pattern"' in fact_text
    assert 'category = "project-pattern"' in fact_text
    assert 'project = "marcbot-memory"' in fact_text
    assert "proposal_approved" in correction_text


def test_approve_memory_proposal_rejects_missing_proposal(tmp_path: Path) -> None:
    import pytest

    from marcbot.memory_store import approve_memory_proposal

    with pytest.raises(ValueError, match="proposal does not exist"):
        approve_memory_proposal(
            root=tmp_path,
            proposal_id="missing",
            source="test",
        )


def test_approve_memory_proposal_rejects_non_pending_proposal(tmp_path: Path) -> None:
    import pytest

    from marcbot.memory_store import (
        add_memory_proposal,
        approve_memory_proposal,
        reject_memory_proposal,
    )

    add_memory_proposal(
        root=tmp_path,
        proposal_id="test-proposal",
        proposed_type="fact",
        proposed_statement="A proposal.",
        source="test",
        rationale="Test.",
        risk_level="low",
    )
    reject_memory_proposal(
        root=tmp_path,
        proposal_id="test-proposal",
        reason="Reject.",
        source="test",
    )

    with pytest.raises(ValueError, match="proposal is not pending"):
        approve_memory_proposal(
            root=tmp_path,
            proposal_id="test-proposal",
            source="test",
        )


def test_approve_memory_proposal_rejects_non_fact_proposal(tmp_path: Path) -> None:
    import pytest

    from marcbot.memory_store import add_memory_proposal, approve_memory_proposal

    add_memory_proposal(
        root=tmp_path,
        proposal_id="event-proposal",
        proposed_type="event",
        proposed_statement="An event proposal.",
        source="test",
        rationale="Test.",
        risk_level="low",
    )

    with pytest.raises(ValueError, match="only fact proposal approval is supported"):
        approve_memory_proposal(
            root=tmp_path,
            proposal_id="event-proposal",
            source="test",
        )


def test_get_memory_status_counts_proposals_by_status(tmp_path: Path) -> None:
    from marcbot.memory_store import (
        add_memory_proposal,
        approve_memory_proposal,
        get_memory_status,
        reject_memory_proposal,
    )

    add_memory_proposal(
        root=tmp_path,
        proposal_id="pending-proposal",
        proposed_type="fact",
        proposed_statement="Pending.",
        source="test",
        rationale="Test.",
        risk_level="low",
    )
    add_memory_proposal(
        root=tmp_path,
        proposal_id="approved-proposal",
        proposed_type="fact",
        proposed_statement="Approved.",
        source="test",
        rationale="Test.",
        risk_level="low",
    )
    approve_memory_proposal(
        root=tmp_path,
        proposal_id="approved-proposal",
        source="test",
    )
    add_memory_proposal(
        root=tmp_path,
        proposal_id="rejected-proposal",
        proposed_type="fact",
        proposed_statement="Rejected.",
        source="test",
        rationale="Test.",
        risk_level="low",
    )
    reject_memory_proposal(
        root=tmp_path,
        proposal_id="rejected-proposal",
        reason="Test.",
        source="test",
    )

    status = get_memory_status(root=tmp_path)

    assert status.proposal_files == 3
    assert status.pending_proposals == 1
    assert status.approved_proposals == 1
    assert status.rejected_proposals == 1

def test_format_memory_fact_detail(tmp_path: Path) -> None:
    from marcbot.memory_store import add_memory_fact, format_memory_fact_detail

    add_memory_fact(
        root=tmp_path,
        fact_id="weather-report-schedule",
        statement="Weather report runs at 7:15 AM.",
        category="schedule",
        project="weather-report",
        source="test",
        confidence="high",
        details="Defined by timer.",
    )

    message = format_memory_fact_detail(
        root=tmp_path,
        fact_id="weather-report-schedule",
    )

    assert "MarcBot memory fact" in message
    assert "ID: weather-report-schedule" in message
    assert "Status: active" in message
    assert "Category: schedule" in message
    assert "Project: weather-report" in message
    assert "Statement: Weather report runs at 7:15 AM." in message
    assert "Details: Defined by timer." in message
    assert "Provider contact: no" in message


def test_format_memory_fact_detail_rejects_missing_fact(tmp_path: Path) -> None:
    import pytest

    from marcbot.memory_store import format_memory_fact_detail

    with pytest.raises(ValueError, match="fact does not exist"):
        format_memory_fact_detail(root=tmp_path, fact_id="missing")


def test_format_memory_proposal_detail(tmp_path: Path) -> None:
    from marcbot.memory_store import (
        add_memory_proposal,
        approve_memory_proposal,
        format_memory_proposal_detail,
    )

    add_memory_proposal(
        root=tmp_path,
        proposal_id="weather-reference-pattern",
        proposed_type="fact",
        proposed_statement="Weather is the reference pattern.",
        project="marcbot-memory",
        source="test",
        rationale="It validated the lifecycle.",
        risk_level="medium",
        details="Reviewable proposal.",
    )
    approve_memory_proposal(
        root=tmp_path,
        proposal_id="weather-reference-pattern",
        source="test_approval",
        review_reason="Looks right.",
    )

    message = format_memory_proposal_detail(
        root=tmp_path,
        proposal_id="weather-reference-pattern",
    )

    assert "MarcBot memory proposal" in message
    assert "ID: weather-reference-pattern" in message
    assert "Status: approved" in message
    assert "Proposed type: fact" in message
    assert "Risk level: medium" in message
    assert "Project: marcbot-memory" in message
    assert "Review reason: Looks right." in message
    assert "Provider contact: no" in message


def test_format_memory_proposal_detail_rejects_missing_proposal(tmp_path: Path) -> None:
    import pytest

    from marcbot.memory_store import format_memory_proposal_detail

    with pytest.raises(ValueError, match="proposal does not exist"):
        format_memory_proposal_detail(root=tmp_path, proposal_id="missing")

def test_format_memory_event_detail(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from marcbot.memory_store import add_memory_event, format_memory_event_detail

    add_memory_event(
        root=tmp_path,
        timestamp=datetime(2026, 5, 18, 18, 0, tzinfo=UTC),
        event_type="issue_resolved",
        project="marcbot-operations",
        summary="Fixed backup timer.",
        source="test",
        confidence="high",
        details="Detailed evidence.",
        cause="Root-owned file.",
        resolution="Removed stale file.",
        verification="Backup passed.",
        follow_up="Avoid root-owned backups.",
        related_commands=("sudo systemctl start marcbot-backup.service",),
    )

    message = format_memory_event_detail(root=tmp_path, index=1, limit=10)

    assert "MarcBot memory event" in message
    assert "Index: 1" in message
    assert "Type: issue_resolved" in message
    assert "Project: marcbot-operations" in message
    assert "Summary: Fixed backup timer." in message
    assert "Cause: Root-owned file." in message
    assert "Related commands:" in message
    assert "Provider contact: no" in message


def test_format_memory_event_detail_rejects_out_of_range(tmp_path: Path) -> None:
    import pytest

    from marcbot.memory_store import format_memory_event_detail, init_memory_store

    init_memory_store(root=tmp_path)

    with pytest.raises(ValueError, match="event index out of range"):
        format_memory_event_detail(root=tmp_path, index=1, limit=10)


def test_format_memory_summary_detail(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from marcbot.memory_store import add_memory_summary, format_memory_summary_detail

    add_memory_summary(
        root=tmp_path,
        timestamp=datetime(2026, 5, 18, 18, 0, tzinfo=UTC),
        title="Memory foundation",
        project="marcbot-memory",
        source="test",
        body="Memory foundation body.",
    )

    message = format_memory_summary_detail(
        root=tmp_path,
        name="2026-05-18-memory-foundation.md",
    )

    assert "MarcBot memory summary" in message
    assert "Title: Memory foundation" in message
    assert "Project: marcbot-memory" in message
    assert "Body:" in message
    assert "Memory foundation body." in message
    assert "Provider contact: no" in message


def test_format_memory_summary_detail_rejects_path_name(tmp_path: Path) -> None:
    import pytest

    from marcbot.memory_store import format_memory_summary_detail

    with pytest.raises(ValueError, match="name must be a file name"):
        format_memory_summary_detail(root=tmp_path, name="../bad.md")

def test_search_memory_finds_matches(tmp_path: Path) -> None:
    from marcbot.memory_store import search_memory

    init_root = tmp_path
    (init_root / "facts").mkdir()
    (init_root / "facts" / "weather.toml").write_text(
        'statement = "Weather report runs daily."\n',
        encoding="utf-8",
    )

    results = search_memory("weather", root=init_root)

    assert len(results) == 1
    assert results[0].path.name == "weather.toml"
    assert results[0].line_number == 1
    assert results[0].line == 'statement = "Weather report runs daily."'


def test_search_memory_is_case_insensitive(tmp_path: Path) -> None:
    from marcbot.memory_store import search_memory

    (tmp_path / "summaries").mkdir()
    (tmp_path / "summaries" / "summary.md").write_text(
        "Weather Workflow\n",
        encoding="utf-8",
    )

    results = search_memory("weather workflow", root=tmp_path)

    assert len(results) == 1


def test_search_memory_ignores_unsupported_suffix(tmp_path: Path) -> None:
    from marcbot.memory_store import search_memory

    (tmp_path / "exports").mkdir()
    (tmp_path / "exports" / "secret.txt").write_text(
        "weather",
        encoding="utf-8",
    )

    assert search_memory("weather", root=tmp_path) == ()


def test_format_memory_search_results(tmp_path: Path) -> None:
    from marcbot.memory_store import format_memory_search_results

    (tmp_path / "events").mkdir()
    (tmp_path / "events" / "2026-05.jsonl").write_text(
        '{"summary": "Weather report sent."}\n',
        encoding="utf-8",
    )

    message = format_memory_search_results("weather", root=tmp_path)

    assert "MarcBot memory search" in message
    assert "Query: weather" in message
    assert "events/2026-05.jsonl:1:" in message
    assert "Provider contact: no" in message

def test_format_memory_status_message_omits_sqlite_by_default(tmp_path: Path) -> None:
    from marcbot.memory_store import format_memory_status_message, init_memory_store

    init_memory_store(root=tmp_path)

    message = format_memory_status_message(root=tmp_path)

    assert "MarcBot memory" in message
    assert "SQLite:" not in message


def test_format_memory_status_message_includes_sqlite_section(tmp_path: Path) -> None:
    from marcbot.memory_store import format_memory_status_message, init_memory_store

    init_memory_store(root=tmp_path)

    message = format_memory_status_message(root=tmp_path, include_sqlite=True)

    assert "MarcBot memory" in message
    assert "SQLite:" in message
    assert "- database:" in message
    assert "Provider contact: no" in message



def test_add_memory_event_syncs_sqlite_when_available(monkeypatch, tmp_path: Path) -> None:
    from marcbot.memory_store import add_memory_event

    calls = []

    def fake_sync_memory_event_to_sqlite_if_available(*, event, source_file, source_line):
        calls.append(
            {
                "event": event,
                "source_file": source_file,
                "source_line": source_line,
            }
        )

    import marcbot.memory_store as memory_store

    monkeypatch.setattr(
        memory_store,
        "_sync_memory_event_to_sqlite_if_available",
        fake_sync_memory_event_to_sqlite_if_available,
    )

    result = add_memory_event(
        root=tmp_path,
        event_type="workflow_completed",
        summary="Workflow completed.",
        source="test",
        confidence="high",
    )

    assert len(calls) == 1
    assert calls[0]["event"].summary == "Workflow completed."
    assert calls[0]["source_file"] == result.path
    assert calls[0]["source_line"] == 1


def test_add_memory_event_sqlite_sync_source_line_increments(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from marcbot.memory_store import add_memory_event

    source_lines = []

    def fake_sync_memory_event_to_sqlite_if_available(*, event, source_file, source_line):
        source_lines.append(source_line)

    import marcbot.memory_store as memory_store

    monkeypatch.setattr(
        memory_store,
        "_sync_memory_event_to_sqlite_if_available",
        fake_sync_memory_event_to_sqlite_if_available,
    )

    add_memory_event(
        root=tmp_path,
        event_type="workflow_completed",
        summary="First.",
        source="test",
        confidence="high",
    )
    add_memory_event(
        root=tmp_path,
        event_type="workflow_completed",
        summary="Second.",
        source="test",
        confidence="high",
    )

    assert source_lines == [1, 2]


def test_sqlite_event_sync_skips_when_database_missing(monkeypatch, tmp_path: Path) -> None:
    from marcbot.memory_store import (
        MemoryEvent,
        _sync_memory_event_to_sqlite_if_available,
    )

    class FakePath:
        def is_file(self) -> bool:
            return False

    def fail_insert(**kwargs):
        raise AssertionError("insert should not be called")

    import marcbot.memory_sqlite as memory_sqlite

    monkeypatch.setattr(memory_sqlite, "DEFAULT_MEMORY_DB_PATH", FakePath())
    monkeypatch.setattr(memory_sqlite, "insert_memory_event_row", fail_insert)

    event = MemoryEvent(
        timestamp="2026-05-19T01:30:00+00:00",
        type="workflow_completed",
        summary="Workflow completed.",
        source="test",
        confidence="high",
    )

    _sync_memory_event_to_sqlite_if_available(
        event=event,
        source_file=tmp_path / "events" / "2026-05.jsonl",
        source_line=1,
    )


def test_sqlite_event_sync_raises_clear_error(monkeypatch, tmp_path: Path) -> None:
    import pytest

    from marcbot.memory_store import (
        MemoryEvent,
        _sync_memory_event_to_sqlite_if_available,
    )

    class FakePath:
        def is_file(self) -> bool:
            return True

    def fail_insert(**kwargs):
        raise ValueError("boom")

    import marcbot.memory_sqlite as memory_sqlite

    monkeypatch.setattr(memory_sqlite, "DEFAULT_MEMORY_DB_PATH", FakePath())
    monkeypatch.setattr(memory_sqlite, "insert_memory_event_row", fail_insert)

    event = MemoryEvent(
        timestamp="2026-05-19T01:30:00+00:00",
        type="workflow_completed",
        summary="Workflow completed.",
        source="test",
        confidence="high",
    )

    with pytest.raises(RuntimeError, match="SQLite memory event sync failed: boom"):
        _sync_memory_event_to_sqlite_if_available(
            event=event,
            source_file=Path("/srv/marcbot/memory/events/2026-05.jsonl"),
            source_line=1,
        )


def test_sqlite_event_sync_skips_non_default_memory_root(monkeypatch, tmp_path: Path) -> None:
    from marcbot.memory_store import (
        MemoryEvent,
        _sync_memory_event_to_sqlite_if_available,
    )

    class FakePath:
        def is_file(self) -> bool:
            return True

    def fail_insert(**kwargs):
        raise AssertionError("temporary memory roots must not sync to real SQLite")

    import marcbot.memory_sqlite as memory_sqlite

    monkeypatch.setattr(memory_sqlite, "DEFAULT_MEMORY_DB_PATH", FakePath())
    monkeypatch.setattr(memory_sqlite, "insert_memory_event_row", fail_insert)

    event = MemoryEvent(
        timestamp="2026-05-19T01:30:00+00:00",
        type="workflow_completed",
        summary="Workflow completed.",
        source="test",
        confidence="high",
    )

    _sync_memory_event_to_sqlite_if_available(
        event=event,
        source_file=tmp_path / "events" / "2026-05.jsonl",
        source_line=1,
    )


def test_add_memory_summary_syncs_sqlite_when_available(monkeypatch, tmp_path: Path) -> None:
    from marcbot.memory_store import add_memory_summary

    calls = []

    def fake_sync_memory_summary_to_sqlite_if_available(*, summary_path):
        calls.append(summary_path)

    import marcbot.memory_store as memory_store

    monkeypatch.setattr(
        memory_store,
        "_sync_memory_summary_to_sqlite_if_available",
        fake_sync_memory_summary_to_sqlite_if_available,
    )

    result = add_memory_summary(
        root=tmp_path,
        title="Test summary",
        body="Useful body.",
        source="test",
    )

    assert calls == [result.path]


def test_sqlite_summary_sync_skips_non_default_memory_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from marcbot.memory_store import _sync_memory_summary_to_sqlite_if_available

    class FakePath:
        def is_file(self) -> bool:
            return True

    def fail_upsert(**kwargs):
        raise AssertionError("temporary summary roots must not sync to real SQLite")

    import marcbot.memory_sqlite as memory_sqlite

    monkeypatch.setattr(memory_sqlite, "DEFAULT_MEMORY_DB_PATH", FakePath())
    monkeypatch.setattr(memory_sqlite, "upsert_memory_summary_row", fail_upsert)

    _sync_memory_summary_to_sqlite_if_available(
        summary_path=tmp_path / "summaries" / "test-summary.md",
    )


def test_sqlite_summary_sync_raises_clear_error(monkeypatch) -> None:
    import pytest

    from marcbot.memory_store import _sync_memory_summary_to_sqlite_if_available

    class FakePath:
        def is_file(self) -> bool:
            return True

    def fail_upsert(**kwargs):
        raise ValueError("boom")

    import marcbot.memory_sqlite as memory_sqlite

    monkeypatch.setattr(memory_sqlite, "DEFAULT_MEMORY_DB_PATH", FakePath())
    monkeypatch.setattr(memory_sqlite, "upsert_memory_summary_row", fail_upsert)

    with pytest.raises(RuntimeError, match="SQLite memory summary sync failed: boom"):
        _sync_memory_summary_to_sqlite_if_available(
            summary_path=Path("/srv/marcbot/memory/summaries/test-summary.md"),
        )

def test_append_memory_correction_writes_jsonl(tmp_path: Path) -> None:
    import json

    from marcbot.memory_store import _append_memory_correction

    correction_path = _append_memory_correction(
        root=tmp_path,
        timestamp="2026-05-19T01:30:00+00:00",
        correction={
            "timestamp": "2026-05-19T01:30:00+00:00",
            "type": "test_correction",
            "reason": "Test.",
        },
    )

    assert correction_path == tmp_path / "corrections" / "2026-05.jsonl"

    data = json.loads(correction_path.read_text(encoding="utf-8"))

    assert data["type"] == "test_correction"
    assert data["reason"] == "Test."



def test_append_memory_correction_syncs_sqlite_when_available(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from marcbot.memory_store import _append_memory_correction

    calls = []

    def fake_sync_memory_correction_to_sqlite_if_available(
        *,
        correction,
        source_file,
        source_line,
    ):
        calls.append(
            {
                "correction": correction,
                "source_file": source_file,
                "source_line": source_line,
            }
        )

    import marcbot.memory_store as memory_store

    monkeypatch.setattr(
        memory_store,
        "_sync_memory_correction_to_sqlite_if_available",
        fake_sync_memory_correction_to_sqlite_if_available,
    )

    correction_path = _append_memory_correction(
        root=tmp_path,
        timestamp="2026-05-19T01:45:00+00:00",
        correction={
            "timestamp": "2026-05-19T01:45:00+00:00",
            "type": "test_correction",
        },
    )

    assert len(calls) == 1
    assert calls[0]["correction"]["type"] == "test_correction"
    assert calls[0]["source_file"] == correction_path
    assert calls[0]["source_line"] == 1


def test_append_memory_correction_sync_source_line_increments(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from marcbot.memory_store import _append_memory_correction

    source_lines = []

    def fake_sync_memory_correction_to_sqlite_if_available(
        *,
        correction,
        source_file,
        source_line,
    ):
        source_lines.append(source_line)

    import marcbot.memory_store as memory_store

    monkeypatch.setattr(
        memory_store,
        "_sync_memory_correction_to_sqlite_if_available",
        fake_sync_memory_correction_to_sqlite_if_available,
    )

    _append_memory_correction(
        root=tmp_path,
        timestamp="2026-05-19T01:45:00+00:00",
        correction={
            "timestamp": "2026-05-19T01:45:00+00:00",
            "type": "first",
        },
    )
    _append_memory_correction(
        root=tmp_path,
        timestamp="2026-05-19T01:46:00+00:00",
        correction={
            "timestamp": "2026-05-19T01:46:00+00:00",
            "type": "second",
        },
    )

    assert source_lines == [1, 2]


def test_sqlite_correction_sync_skips_non_default_memory_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from marcbot.memory_store import _sync_memory_correction_to_sqlite_if_available

    class FakePath:
        def is_file(self) -> bool:
            return True

    def fail_insert(**kwargs):
        raise AssertionError("temporary correction roots must not sync to real SQLite")

    import marcbot.memory_sqlite as memory_sqlite

    monkeypatch.setattr(memory_sqlite, "DEFAULT_MEMORY_DB_PATH", FakePath())
    monkeypatch.setattr(memory_sqlite, "insert_memory_correction_row", fail_insert)

    _sync_memory_correction_to_sqlite_if_available(
        correction={
            "timestamp": "2026-05-19T01:45:00+00:00",
            "type": "test_correction",
        },
        source_file=tmp_path / "corrections" / "2026-05.jsonl",
        source_line=1,
    )


def test_sqlite_correction_sync_raises_clear_error(monkeypatch) -> None:
    import pytest

    from marcbot.memory_store import _sync_memory_correction_to_sqlite_if_available

    class FakePath:
        def is_file(self) -> bool:
            return True

    def fail_insert(**kwargs):
        raise ValueError("boom")

    import marcbot.memory_sqlite as memory_sqlite

    monkeypatch.setattr(memory_sqlite, "DEFAULT_MEMORY_DB_PATH", FakePath())
    monkeypatch.setattr(memory_sqlite, "insert_memory_correction_row", fail_insert)

    with pytest.raises(RuntimeError, match="SQLite memory correction sync failed: boom"):
        _sync_memory_correction_to_sqlite_if_available(
            correction={
                "timestamp": "2026-05-19T01:45:00+00:00",
                "type": "test_correction",
            },
            source_file=Path("/srv/marcbot/memory/corrections/2026-05.jsonl"),
            source_line=1,
        )


def test_add_memory_proposal_syncs_sqlite_when_available(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from marcbot.memory_store import add_memory_proposal

    calls = []

    def fake_sync_memory_proposal_to_sqlite_if_available(*, proposal_path):
        calls.append(proposal_path)

    import marcbot.memory_store as memory_store

    monkeypatch.setattr(
        memory_store,
        "_sync_memory_proposal_to_sqlite_if_available",
        fake_sync_memory_proposal_to_sqlite_if_available,
    )

    result = add_memory_proposal(
        root=tmp_path,
        proposal_id="test-proposal",
        proposed_type="fact",
        proposed_statement="A proposed fact.",
        source="test",
        rationale="Test rationale.",
        risk_level="low",
    )

    assert calls == [result.path]


def test_reject_memory_proposal_syncs_sqlite_when_available(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from marcbot.memory_store import add_memory_proposal, reject_memory_proposal

    calls = []

    def fake_sync_memory_proposal_to_sqlite_if_available(*, proposal_path):
        calls.append(proposal_path)

    import marcbot.memory_store as memory_store

    monkeypatch.setattr(
        memory_store,
        "_sync_memory_proposal_to_sqlite_if_available",
        fake_sync_memory_proposal_to_sqlite_if_available,
    )

    added = add_memory_proposal(
        root=tmp_path,
        proposal_id="test-proposal",
        proposed_type="fact",
        proposed_statement="A proposed fact.",
        source="test",
        rationale="Test rationale.",
        risk_level="low",
    )
    reject_memory_proposal(
        root=tmp_path,
        proposal_id="test-proposal",
        source="test",
        reason="Rejected for test.",
    )

    assert calls == [added.path, added.path]


def test_sqlite_proposal_sync_skips_non_default_memory_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from marcbot.memory_store import _sync_memory_proposal_to_sqlite_if_available

    class FakePath:
        def is_file(self) -> bool:
            return True

    def fail_upsert(**kwargs):
        raise AssertionError("temporary proposal roots must not sync to real SQLite")

    import marcbot.memory_sqlite as memory_sqlite

    monkeypatch.setattr(memory_sqlite, "DEFAULT_MEMORY_DB_PATH", FakePath())
    monkeypatch.setattr(memory_sqlite, "upsert_memory_proposal_row", fail_upsert)

    _sync_memory_proposal_to_sqlite_if_available(
        proposal_path=tmp_path / "pending" / "test-proposal.json",
    )


def test_sqlite_proposal_sync_raises_clear_error(monkeypatch) -> None:
    import pytest

    from marcbot.memory_store import _sync_memory_proposal_to_sqlite_if_available

    class FakePath:
        def is_file(self) -> bool:
            return True

    def fail_upsert(**kwargs):
        raise ValueError("boom")

    import marcbot.memory_sqlite as memory_sqlite

    monkeypatch.setattr(memory_sqlite, "DEFAULT_MEMORY_DB_PATH", FakePath())
    monkeypatch.setattr(memory_sqlite, "upsert_memory_proposal_row", fail_upsert)

    with pytest.raises(RuntimeError, match="SQLite memory proposal sync failed: boom"):
        _sync_memory_proposal_to_sqlite_if_available(
            proposal_path=Path("/srv/marcbot/memory/pending/test-proposal.json"),
        )


def test_add_memory_fact_syncs_sqlite_when_available(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from marcbot.memory_store import add_memory_fact

    calls = []

    def fake_sync_memory_fact_to_sqlite_if_available(*, fact_path):
        calls.append(fact_path)

    import marcbot.memory_store as memory_store

    monkeypatch.setattr(
        memory_store,
        "_sync_memory_fact_to_sqlite_if_available",
        fake_sync_memory_fact_to_sqlite_if_available,
    )

    result = add_memory_fact(
        root=tmp_path,
        fact_id="test-fact",
        statement="A test fact.",
        category="test",
        source="test",
        confidence="high",
    )

    assert calls == [result.path]


def test_sqlite_fact_sync_skips_non_default_memory_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from marcbot.memory_store import _sync_memory_fact_to_sqlite_if_available

    class FakePath:
        def is_file(self) -> bool:
            return True

    def fail_upsert(**kwargs):
        raise AssertionError("temporary fact roots must not sync to real SQLite")

    import marcbot.memory_sqlite as memory_sqlite

    monkeypatch.setattr(memory_sqlite, "DEFAULT_MEMORY_DB_PATH", FakePath())
    monkeypatch.setattr(memory_sqlite, "upsert_memory_fact_row", fail_upsert)

    _sync_memory_fact_to_sqlite_if_available(
        fact_path=tmp_path / "facts" / "test-fact.toml",
    )


def test_sqlite_fact_sync_raises_clear_error(monkeypatch) -> None:
    import pytest

    from marcbot.memory_store import _sync_memory_fact_to_sqlite_if_available

    class FakePath:
        def is_file(self) -> bool:
            return True

    def fail_upsert(**kwargs):
        raise ValueError("boom")

    import marcbot.memory_sqlite as memory_sqlite

    monkeypatch.setattr(memory_sqlite, "DEFAULT_MEMORY_DB_PATH", FakePath())
    monkeypatch.setattr(memory_sqlite, "upsert_memory_fact_row", fail_upsert)

    with pytest.raises(RuntimeError, match="SQLite memory fact sync failed: boom"):
        _sync_memory_fact_to_sqlite_if_available(
            fact_path=Path("/srv/marcbot/memory/facts/test-fact.toml"),
        )


def test_reject_memory_fact_syncs_fact_row_before_correction(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from datetime import UTC, datetime

    from marcbot.memory_store import add_memory_fact, reject_memory_fact

    calls = []

    def fake_sync_memory_fact_to_sqlite_if_available(*, fact_path):
        calls.append(("fact", fact_path.name))

    def fake_append_memory_correction(*, root, timestamp, correction):
        calls.append(("correction", correction["type"]))
        return root / "corrections" / "2026-05.jsonl"

    import marcbot.memory_store as memory_store

    monkeypatch.setattr(
        memory_store,
        "_sync_memory_fact_to_sqlite_if_available",
        fake_sync_memory_fact_to_sqlite_if_available,
    )
    monkeypatch.setattr(
        memory_store,
        "_append_memory_correction",
        fake_append_memory_correction,
    )

    add_memory_fact(
        root=tmp_path,
        fact_id="test-fact",
        statement="A test fact.",
        category="test",
        source="test",
        confidence="high",
        timestamp=datetime(2026, 5, 19, 2, 30, tzinfo=UTC),
    )
    calls.clear()

    reject_memory_fact(
        root=tmp_path,
        fact_id="test-fact",
        reason="Rejected for test.",
        source="test",
        confidence="high",
        timestamp=datetime(2026, 5, 19, 2, 35, tzinfo=UTC),
    )

    assert calls == [
        ("fact", "test-fact.toml"),
        ("correction", "fact_rejected"),
    ]


def test_supersede_memory_fact_syncs_old_new_fact_rows_before_correction(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from datetime import UTC, datetime

    from marcbot.memory_store import add_memory_fact, supersede_memory_fact

    calls = []

    def fake_sync_memory_fact_to_sqlite_if_available(*, fact_path):
        calls.append(("fact", fact_path.name))

    def fake_append_memory_correction(*, root, timestamp, correction):
        calls.append(("correction", correction["type"]))
        return root / "corrections" / "2026-05.jsonl"

    import marcbot.memory_store as memory_store

    monkeypatch.setattr(
        memory_store,
        "_sync_memory_fact_to_sqlite_if_available",
        fake_sync_memory_fact_to_sqlite_if_available,
    )
    monkeypatch.setattr(
        memory_store,
        "_append_memory_correction",
        fake_append_memory_correction,
    )

    add_memory_fact(
        root=tmp_path,
        fact_id="old-fact",
        statement="Old fact.",
        category="test",
        source="test",
        confidence="high",
        timestamp=datetime(2026, 5, 19, 2, 40, tzinfo=UTC),
    )
    calls.clear()

    supersede_memory_fact(
        root=tmp_path,
        fact_id="old-fact",
        new_fact_id="new-fact",
        statement="New fact.",
        reason="Updated for test.",
        source="test",
        confidence="high",
        timestamp=datetime(2026, 5, 19, 2, 45, tzinfo=UTC),
    )

    assert calls == [
        ("fact", "old-fact.toml"),
        ("fact", "new-fact.toml"),
        ("correction", "fact_superseded"),
    ]

