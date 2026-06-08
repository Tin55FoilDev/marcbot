from __future__ import annotations

from pathlib import Path

import pytest

from marcbot.workflow_runner import WorkflowRunResult
from marcbot.workflow_telegram_execution import (
    TELEGRAM_SUMMARY_INPUT_LIMIT,
    TELEGRAM_SUMMARY_MEMORY_EVENTS_LIMIT,
    TELEGRAM_SUMMARY_MEMORY_FACTS_LIMIT,
    TELEGRAM_SUMMARY_MEMORY_PROFILE,
    TELEGRAM_SUMMARY_MEMORY_SUMMARIES_LIMIT,
    TELEGRAM_SUMMARY_PROJECT,
    TELEGRAM_SUMMARY_WORKFLOW_ID,
    format_telegram_source_monitor_summary_execution,
    format_telegram_source_monitor_summary_failure,
)


def test_telegram_summary_execution_adapter_uses_fixed_safe_arguments() -> None:
    calls = []

    def fake_runner(*args, **kwargs):
        calls.append((args, kwargs))
        return WorkflowRunResult(
            workflow_id=TELEGRAM_SUMMARY_WORKFLOW_ID,
            project=TELEGRAM_SUMMARY_PROJECT,
            message="summary written",
            artifact_path=Path("source-monitor-2026-06-08-010203.summary.md"),
            provider_contact=True,
            writes_artifacts=True,
            writes_memory=False,
            state_changing=True,
        )

    message = format_telegram_source_monitor_summary_execution(runner=fake_runner)

    assert calls == [
        (
            (TELEGRAM_SUMMARY_WORKFLOW_ID,),
            {
                "project": TELEGRAM_SUMMARY_PROJECT,
                "task": "source_monitor_analysis",
                "memory_profile": TELEGRAM_SUMMARY_MEMORY_PROFILE,
                "memory_query": None,
                "memory_project": None,
                "memory_facts_limit": TELEGRAM_SUMMARY_MEMORY_FACTS_LIMIT,
                "memory_summaries_limit": TELEGRAM_SUMMARY_MEMORY_SUMMARIES_LIMIT,
                "memory_events_limit": TELEGRAM_SUMMARY_MEMORY_EVENTS_LIMIT,
                "summary_input_limit": TELEGRAM_SUMMARY_INPUT_LIMIT,
            },
        )
    ]
    assert "Status: executed" in message
    assert "Provider contact: yes" in message
    assert "Workflow ran: yes" in message
    assert "Writes: summary artifact" in message
    assert "Artifact: summary:2026-06-08-010203" in message


def test_telegram_summary_execution_adapter_uses_zero_memory_context_limits() -> None:
    assert TELEGRAM_SUMMARY_MEMORY_FACTS_LIMIT == 0
    assert TELEGRAM_SUMMARY_MEMORY_SUMMARIES_LIMIT == 0
    assert TELEGRAM_SUMMARY_MEMORY_EVENTS_LIMIT == 0


def test_telegram_summary_execution_adapter_uses_tighter_summary_input_limit() -> None:
    assert TELEGRAM_SUMMARY_INPUT_LIMIT == 1800


def test_telegram_summary_execution_adapter_rejects_missing_artifact_id() -> None:
    def fake_runner(*args, **kwargs):
        return WorkflowRunResult(
            workflow_id=TELEGRAM_SUMMARY_WORKFLOW_ID,
            project=TELEGRAM_SUMMARY_PROJECT,
            message="summary written",
            artifact_path=Path("not-a-summary.txt"),
            provider_contact=True,
            writes_artifacts=True,
            writes_memory=False,
            state_changing=True,
        )

    message = format_telegram_source_monitor_summary_execution(runner=fake_runner)

    assert "Status: failed" in message
    assert "Provider contact: yes" in message
    assert "Workflow ran: yes" in message
    assert "Writes: unknown" in message
    assert "valid summary artifact id" in message


def test_telegram_summary_failure_formatter_bounds_exception_details() -> None:
    message = format_telegram_source_monitor_summary_failure(
        RuntimeError("failed at /srv/marcbot/app/private-config")
    )

    assert "Status: failed" in message
    assert "Provider contact: unknown" in message
    assert "Workflow ran: unknown" in message
    assert "Writes: unknown" in message
    assert "/srv/" not in message
    assert "[path]/marcbot/app/private-config" in message


def test_telegram_summary_execution_adapter_propagates_runner_failure() -> None:
    def fake_runner(*args, **kwargs):
        raise RuntimeError("provider timeout")

    with pytest.raises(RuntimeError, match="provider timeout"):
        format_telegram_source_monitor_summary_execution(runner=fake_runner)
