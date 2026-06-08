from __future__ import annotations

from marcbot.workflow_execution_result import (
    WorkflowExecutionTelegramResult,
    format_workflow_execution_failure,
    format_workflow_execution_result,
    format_workflow_execution_success,
)


def test_format_workflow_execution_success_reports_bounded_artifact_result() -> None:
    message = format_workflow_execution_success(
        workflow_id="source-monitor-ai-summary",
        artifact_id="summary:2026-06-08-010203",
    )

    assert "MarcBot workflow confirmation" in message
    assert "Workflow: source-monitor-ai-summary" in message
    assert "Status: executed" in message
    assert "Provider contact: yes" in message
    assert "Workflow ran: yes" in message
    assert "Writes: summary artifact" in message
    assert "Artifact: summary:2026-06-08-010203" in message


def test_format_workflow_execution_failure_reports_safe_status_fields() -> None:
    message = format_workflow_execution_failure(
        workflow_id="source-monitor-ai-summary",
        provider_contact="yes",
        workflow_ran="yes",
        writes="no",
        reason="provider timeout",
    )

    assert "Status: failed" in message
    assert "Provider contact: yes" in message
    assert "Workflow ran: yes" in message
    assert "Writes: no" in message
    assert "Reason: provider timeout" in message


def test_format_workflow_execution_failure_normalizes_unsafe_status_values() -> None:
    message = format_workflow_execution_failure(
        workflow_id="source-monitor-ai-summary",
        provider_contact="definitely",
        workflow_ran="maybe",
        writes="arbitrary file",
        reason="failed",
    )

    assert "Provider contact: unknown" in message
    assert "Workflow ran: unknown" in message
    assert "Writes: unknown" in message


def test_format_workflow_execution_failure_redacts_common_local_path_prefixes() -> None:
    message = format_workflow_execution_failure(
        workflow_id="source-monitor-ai-summary",
        provider_contact="no",
        workflow_ran="no",
        writes="no",
        reason="failed at /srv/marcbot/app/config and /home/marc/.secret",
    )

    assert "/srv/" not in message
    assert "/home/" not in message
    assert "[path]/marcbot/app/config" in message
    assert "[path]/marc/.secret" in message


def test_format_workflow_execution_failure_bounds_long_reason() -> None:
    message = format_workflow_execution_failure(
        workflow_id="source-monitor-ai-summary",
        provider_contact="unknown",
        workflow_ran="unknown",
        writes="unknown",
        reason="x" * 500,
    )

    reason_line = next(line for line in message.splitlines() if line.startswith("Reason: "))
    assert len(reason_line) <= 252
    assert reason_line.endswith("...")


def test_format_workflow_execution_result_rejects_path_like_artifact_ids() -> None:
    message = format_workflow_execution_result(
        WorkflowExecutionTelegramResult(
            workflow_id="source-monitor-ai-summary",
            status="executed",
            provider_contact="yes",
            workflow_ran="yes",
            writes="summary artifact",
            artifact_id="/srv/marcbot/private.txt",
        )
    )

    assert "Artifact: unknown" in message
    assert "/srv/" not in message
