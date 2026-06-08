"""Tests for approved MarcBot workflow execution."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from marcbot.workflow_runner import (
    format_workflow_run,
    format_workflow_status,
    run_workflow,
)


def test_run_workflow_source_monitor_ai_report_calls_report_writer() -> None:
    fake_result = Mock()
    fake_result.path = Path("/srv/marcbot/workspace/source-projects/ai/reports/report.md")
    fake_result.message = "Source monitor report written: /tmp/report.md"

    with patch(
        "marcbot.workflow_runner.write_source_monitor_report",
        return_value=fake_result,
    ) as mock_write:
        result = run_workflow("source-monitor-ai-report", project="ai")

    mock_write.assert_called_once_with(project_name="ai")
    assert result.workflow_id == "source-monitor-ai-report"
    assert result.project == "ai"
    assert result.artifact_path == fake_result.path
    assert result.provider_contact is False
    assert result.writes_artifacts is True
    assert result.writes_memory is False
    assert result.state_changing is True


def test_format_workflow_run_discloses_report_boundaries() -> None:
    fake_result = Mock()
    fake_result.path = Path("/srv/marcbot/workspace/source-projects/ai/reports/report.md")
    fake_result.message = "Source monitor report written: /tmp/report.md"

    with patch(
        "marcbot.workflow_runner.write_source_monitor_report",
        return_value=fake_result,
    ):
        output = format_workflow_run("source-monitor-ai-report", project="ai")

    assert "MarcBot workflow run" in output
    assert "Workflow: source-monitor-ai-report" in output
    assert "Project: ai" in output
    assert "State changing: yes" in output
    assert "Writes artifacts: yes" in output
    assert "Writes memory: no" in output
    assert "Provider contact: no" in output
    assert "Artifact: /srv/marcbot/workspace/source-projects/ai/reports/report.md" in output


def test_run_workflow_source_monitor_ai_summary_uses_existing_cli_path() -> None:
    completed = subprocess.CompletedProcess(
        args=["python"],
        returncode=0,
        stdout=(
            "Using latest source monitor report: /tmp/report.md\n"
            "Source monitor summary written: "
            "/srv/marcbot/workspace/source-projects/ai/summaries/report.summary.md\n"
        ),
        stderr="",
    )

    with patch("marcbot.workflow_runner.subprocess.run", return_value=completed) as run:
        result = run_workflow(
            "source-monitor-ai-summary",
            project="ai",
            task="source_monitor_analysis",
            memory_profile="source-monitor",
            memory_query="source monitor",
            memory_project="source-monitor",
            memory_facts_limit=4,
            memory_summaries_limit=2,
            memory_events_limit=6,
        )

    command = run.call_args.args[0]
    assert command[2:6] == ["marcbot", "source-monitor", "summarize-latest", "ai"]
    assert "--task" in command
    assert "source_monitor_analysis" in command
    assert "--memory-profile" in command
    assert "source-monitor" in command
    assert "--memory-query" in command
    assert "source monitor" in command
    assert "--memory-project" in command
    assert "--memory-facts-limit" in command
    assert "4" in command
    assert result.workflow_id == "source-monitor-ai-summary"
    assert result.project == "ai"
    assert result.provider_contact is True
    assert result.writes_artifacts is True
    assert result.writes_memory is False
    assert result.artifact_path == Path(
        "/srv/marcbot/workspace/source-projects/ai/summaries/report.summary.md"
    )


def test_run_workflow_source_monitor_ai_summary_empty_memory_profile_disables_default() -> None:
    completed = subprocess.CompletedProcess(
        args=["python"],
        returncode=0,
        stdout="Source monitor summary written: /tmp/report.summary.md\n",
        stderr="",
    )

    with patch("marcbot.workflow_runner.subprocess.run", return_value=completed) as run:
        run_workflow(
            "source-monitor-ai-summary",
            project="ai",
            memory_profile="",
            memory_facts_limit=0,
            memory_summaries_limit=0,
            memory_events_limit=0,
        )

    command = run.call_args.args[0]
    assert "--memory-profile" not in command
    assert "--memory-facts-limit" in command
    assert "0" in command


def test_run_workflow_source_monitor_ai_summary_accepts_summary_input_limit() -> None:
    completed = subprocess.CompletedProcess(
        args=["python"],
        returncode=0,
        stdout="Source monitor summary written: /tmp/report.summary.md\n",
        stderr="",
    )

    with patch("marcbot.workflow_runner.subprocess.run", return_value=completed) as run:
        result = run_workflow(
            "source-monitor-ai-summary",
            project="ai",
            summary_input_limit=1800,
        )

    command = run.call_args.args[0]
    assert "--summary-input-limit" in command
    assert "1800" in command
    assert result.workflow_id == "source-monitor-ai-summary"


def test_format_workflow_run_discloses_summary_provider_contact() -> None:
    completed = subprocess.CompletedProcess(
        args=["python"],
        returncode=0,
        stdout="Source monitor summary written: /tmp/report.summary.md\n",
        stderr="",
    )

    with patch("marcbot.workflow_runner.subprocess.run", return_value=completed):
        output = format_workflow_run("source-monitor-ai-summary", project="ai")

    assert "Workflow: source-monitor-ai-summary" in output
    assert "Project: ai" in output
    assert "State changing: yes" in output
    assert "Writes artifacts: yes" in output
    assert "Writes memory: no" in output
    assert "Provider contact: yes" in output
    assert "Artifact: /tmp/report.summary.md" in output


def test_run_workflow_summary_reports_subprocess_failure() -> None:
    completed = subprocess.CompletedProcess(
        args=["python"],
        returncode=2,
        stdout="",
        stderr="summary failed",
    )

    with patch("marcbot.workflow_runner.subprocess.run", return_value=completed):
        with pytest.raises(RuntimeError, match="summary failed"):
            run_workflow("source-monitor-ai-summary", project="ai")

def test_format_workflow_status_reuses_source_monitor_status() -> None:
    with patch(
        "marcbot.workflow_runner.format_source_monitor_cli_status",
        return_value="MarcBot source monitor status\nLatest report: report.md",
    ) as mock_status:
        output = format_workflow_status(
            "source-monitor-ai-summary",
            project="ai",
        )

    mock_status.assert_called_once_with(project_name="ai")
    assert "MarcBot workflow status" in output
    assert "Workflow: source-monitor-ai-summary" in output
    assert "Project: ai" in output
    assert "Provider contact for status: no" in output
    assert "Provider contact when run: yes" in output
    assert "Writes artifacts when run: yes" in output
    assert "Writes memory when run: no" in output
    assert "Underlying source-monitor status:" in output
    assert "Latest report: report.md" in output


def test_format_workflow_status_reports_report_workflow_boundaries() -> None:
    with patch(
        "marcbot.workflow_runner.format_source_monitor_cli_status",
        return_value="MarcBot source monitor status",
    ):
        output = format_workflow_status("source-monitor-ai-report", project="ai")

    assert "Workflow: source-monitor-ai-report" in output
    assert "Provider contact for status: no" in output
    assert "Provider contact when run: no" in output
    assert "Writes artifacts when run: yes" in output
    assert "Telegram executable: no" in output


def test_format_workflow_artifacts_lists_recent_report_artifacts(tmp_path: Path) -> None:
    from marcbot.workflow_runner import format_workflow_artifacts

    reports_dir = tmp_path / "reports"
    summaries_dir = tmp_path / "summaries"
    reports_dir.mkdir()
    summaries_dir.mkdir()

    newest = reports_dir / "source-monitor-2026-05-03-120000.md"
    older = reports_dir / "source-monitor-2026-05-02-120000.md"
    newest.write_text("# newest\n", encoding="utf-8")
    older.write_text("# older\n", encoding="utf-8")

    output = format_workflow_artifacts(
        "source-monitor-ai-report",
        project="ai",
        reports_dir=reports_dir,
        summaries_dir=summaries_dir,
    )

    assert "MarcBot workflow artifacts" in output
    assert "Workflow: source-monitor-ai-report" in output
    assert "Project: ai" in output
    assert "Provider contact: no" in output
    assert "Writes memory when run: no" in output
    assert "Telegram executable: no" in output
    assert "Recent report artifacts:" in output
    assert "report:2026-05-03-120000" in output
    assert "source-monitor-2026-05-03-120000.md" in output
    assert "Recent summary artifacts:" not in output


def test_format_workflow_artifacts_lists_recent_summary_artifacts(tmp_path: Path) -> None:
    from marcbot.workflow_runner import format_workflow_artifacts

    reports_dir = tmp_path / "reports"
    summaries_dir = tmp_path / "summaries"
    reports_dir.mkdir()
    summaries_dir.mkdir()

    newest = summaries_dir / "source-monitor-2026-05-03-120000.summary.md"
    older = summaries_dir / "source-monitor-2026-05-02-120000.summary.md"
    newest.write_text("# newest\n", encoding="utf-8")
    older.write_text("# older\n", encoding="utf-8")

    output = format_workflow_artifacts(
        "source-monitor-ai-summary",
        project="ai",
        reports_dir=reports_dir,
        summaries_dir=summaries_dir,
    )

    assert "MarcBot workflow artifacts" in output
    assert "Workflow: source-monitor-ai-summary" in output
    assert "Project: ai" in output
    assert "Provider contact: no" in output
    assert "Writes memory when run: no" in output
    assert "Telegram executable: no" in output
    assert "Recent summary artifacts:" in output
    assert "summary:2026-05-03-120000" in output
    assert "source-monitor-2026-05-03-120000.summary.md" in output
    assert "Recent report artifacts:" not in output


def test_format_workflow_artifacts_handles_empty_artifact_list(tmp_path: Path) -> None:
    from marcbot.workflow_runner import format_workflow_artifacts

    reports_dir = tmp_path / "reports"
    summaries_dir = tmp_path / "summaries"
    reports_dir.mkdir()
    summaries_dir.mkdir()

    output = format_workflow_artifacts(
        "source-monitor-ai-report",
        project="ai",
        reports_dir=reports_dir,
        summaries_dir=summaries_dir,
    )

    assert "Recent report artifacts:" in output
    assert "- none" in output


def test_resolve_workflow_artifact_accepts_report_for_report_workflow(
    tmp_path: Path,
) -> None:
    from marcbot.workflow_runner import resolve_workflow_artifact

    reports_dir = tmp_path / "reports"
    summaries_dir = tmp_path / "summaries"
    reports_dir.mkdir()
    summaries_dir.mkdir()

    report = reports_dir / "source-monitor-2026-05-26-113618.md"
    report.write_text("# report\n", encoding="utf-8")

    resolved = resolve_workflow_artifact(
        "source-monitor-ai-report",
        "report:2026-05-26-113618",
        project="ai",
        reports_dir=reports_dir,
        summaries_dir=summaries_dir,
    )

    assert resolved == report


def test_resolve_workflow_artifact_rejects_summary_for_report_workflow(
    tmp_path: Path,
) -> None:
    from marcbot.workflow_runner import resolve_workflow_artifact

    reports_dir = tmp_path / "reports"
    summaries_dir = tmp_path / "summaries"
    reports_dir.mkdir()
    summaries_dir.mkdir()

    summary = summaries_dir / "source-monitor-2026-05-26-113618.summary.md"
    summary.write_text("# summary\n", encoding="utf-8")

    resolved = resolve_workflow_artifact(
        "source-monitor-ai-report",
        "summary:2026-05-26-113618",
        project="ai",
        reports_dir=reports_dir,
        summaries_dir=summaries_dir,
    )

    assert resolved is None


def test_resolve_workflow_artifact_accepts_summary_for_summary_workflow(
    tmp_path: Path,
) -> None:
    from marcbot.workflow_runner import resolve_workflow_artifact

    reports_dir = tmp_path / "reports"
    summaries_dir = tmp_path / "summaries"
    reports_dir.mkdir()
    summaries_dir.mkdir()

    summary = summaries_dir / "source-monitor-2026-05-26-113618.summary.md"
    summary.write_text("# summary\n", encoding="utf-8")

    resolved = resolve_workflow_artifact(
        "source-monitor-ai-summary",
        "summary:2026-05-26-113618",
        project="ai",
        reports_dir=reports_dir,
        summaries_dir=summaries_dir,
    )

    assert resolved == summary


def test_resolve_workflow_artifact_rejects_report_for_summary_workflow(
    tmp_path: Path,
) -> None:
    from marcbot.workflow_runner import resolve_workflow_artifact

    reports_dir = tmp_path / "reports"
    summaries_dir = tmp_path / "summaries"
    reports_dir.mkdir()
    summaries_dir.mkdir()

    report = reports_dir / "source-monitor-2026-05-26-113618.md"
    report.write_text("# report\n", encoding="utf-8")

    resolved = resolve_workflow_artifact(
        "source-monitor-ai-summary",
        "report:2026-05-26-113618",
        project="ai",
        reports_dir=reports_dir,
        summaries_dir=summaries_dir,
    )

    assert resolved is None


def test_resolve_workflow_artifact_rejects_invalid_artifact_id(
    tmp_path: Path,
) -> None:
    from marcbot.workflow_runner import resolve_workflow_artifact

    reports_dir = tmp_path / "reports"
    summaries_dir = tmp_path / "summaries"
    reports_dir.mkdir()
    summaries_dir.mkdir()

    resolved = resolve_workflow_artifact(
        "source-monitor-ai-report",
        "../source-monitor-2026-05-26-113618.md",
        project="ai",
        reports_dir=reports_dir,
        summaries_dir=summaries_dir,
    )

    assert resolved is None


def test_resolve_workflow_artifact_rejects_missing_artifact(
    tmp_path: Path,
) -> None:
    from marcbot.workflow_runner import resolve_workflow_artifact

    reports_dir = tmp_path / "reports"
    summaries_dir = tmp_path / "summaries"
    reports_dir.mkdir()
    summaries_dir.mkdir()

    resolved = resolve_workflow_artifact(
        "source-monitor-ai-report",
        "report:2026-05-26-113618",
        project="ai",
        reports_dir=reports_dir,
        summaries_dir=summaries_dir,
    )

    assert resolved is None
