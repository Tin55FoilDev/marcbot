from __future__ import annotations

from collections.abc import Callable

from marcbot.source_status import source_monitor_artifact_id
from marcbot.workflow_execution_result import (
    format_workflow_execution_failure,
    format_workflow_execution_success,
)
from marcbot.workflow_runner import SUMMARY_TASK_DEFAULT, WorkflowRunResult, run_workflow

TELEGRAM_SUMMARY_WORKFLOW_ID = "source-monitor-ai-summary"
TELEGRAM_SUMMARY_PROJECT = "ai"
TELEGRAM_SUMMARY_MEMORY_PROFILE = "source-monitor"
TELEGRAM_SUMMARY_MEMORY_FACTS_LIMIT = 0
TELEGRAM_SUMMARY_MEMORY_SUMMARIES_LIMIT = 0
TELEGRAM_SUMMARY_MEMORY_EVENTS_LIMIT = 0
TELEGRAM_SUMMARY_INPUT_LIMIT = 1800


def format_telegram_source_monitor_summary_execution(
    *,
    runner: Callable[..., WorkflowRunResult] = run_workflow,
) -> str:
    result = _run_telegram_source_monitor_summary(runner=runner)
    artifact_path = result.artifact_path
    artifact_id = source_monitor_artifact_id(artifact_path) if artifact_path else None

    if artifact_id is None:
        return format_workflow_execution_failure(
            workflow_id=TELEGRAM_SUMMARY_WORKFLOW_ID,
            provider_contact="yes",
            workflow_ran="yes",
            writes="unknown",
            reason="summary workflow did not return a valid summary artifact id",
        )

    return format_workflow_execution_success(
        workflow_id=TELEGRAM_SUMMARY_WORKFLOW_ID,
        artifact_id=artifact_id,
    )


def format_telegram_source_monitor_summary_failure(error: Exception) -> str:
    return format_workflow_execution_failure(
        workflow_id=TELEGRAM_SUMMARY_WORKFLOW_ID,
        provider_contact="unknown",
        workflow_ran="unknown",
        writes="unknown",
        reason=str(error),
    )


def _run_telegram_source_monitor_summary(
    *,
    runner: Callable[..., WorkflowRunResult],
) -> WorkflowRunResult:
    return runner(
        TELEGRAM_SUMMARY_WORKFLOW_ID,
        project=TELEGRAM_SUMMARY_PROJECT,
        task=SUMMARY_TASK_DEFAULT,
        memory_profile=TELEGRAM_SUMMARY_MEMORY_PROFILE,
        memory_query=None,
        memory_project=None,
        memory_facts_limit=TELEGRAM_SUMMARY_MEMORY_FACTS_LIMIT,
        memory_summaries_limit=TELEGRAM_SUMMARY_MEMORY_SUMMARIES_LIMIT,
        memory_events_limit=TELEGRAM_SUMMARY_MEMORY_EVENTS_LIMIT,
        summary_input_limit=TELEGRAM_SUMMARY_INPUT_LIMIT,
    )
