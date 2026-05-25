"""Tests for approved MarcBot workflow execution."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from marcbot.workflow_runner import format_workflow_run, run_workflow


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


def test_format_workflow_run_discloses_boundaries() -> None:
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


def test_run_workflow_rejects_unimplemented_workflow() -> None:
    with pytest.raises(
        ValueError,
        match="workflow execution is not implemented for source-monitor-ai-summary",
    ):
        run_workflow("source-monitor-ai-summary", project="ai")
