"""Approved MarcBot workflow execution helpers."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from marcbot.source_config import DEFAULT_SOURCE_PROJECT_NAME
from marcbot.source_monitor import write_source_monitor_report
from marcbot.workflow_registry import get_workflow_definition


@dataclass(frozen=True)
class WorkflowRunResult:
    """Result of running one approved MarcBot workflow."""

    workflow_id: str
    project: str
    message: str
    artifact_path: Path | None
    provider_contact: bool
    writes_artifacts: bool
    writes_memory: bool
    state_changing: bool


def run_workflow(
    workflow_id: str,
    *,
    project: str | None = None,
) -> WorkflowRunResult:
    """Run one approved workflow through a bounded implementation path."""
    workflow = get_workflow_definition(workflow_id)

    if workflow.workflow_id != "source-monitor-ai-report":
        raise ValueError(
            "workflow execution is not implemented for "
            f"{workflow.workflow_id}; valid runnable workflow: "
            "source-monitor-ai-report"
        )

    project_name = project or DEFAULT_SOURCE_PROJECT_NAME
    result = write_source_monitor_report(project_name=project_name)
    return WorkflowRunResult(
        workflow_id=workflow.workflow_id,
        project=project_name,
        message=result.message,
        artifact_path=result.path,
        provider_contact=workflow.provider_contact,
        writes_artifacts=workflow.writes_artifacts,
        writes_memory=workflow.writes_memory,
        state_changing=workflow.state_changing,
    )


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def format_workflow_run_result(result: WorkflowRunResult) -> str:
    """Return a human-readable workflow run result."""
    artifact_text = str(result.artifact_path) if result.artifact_path else "none"
    lines = [
        "MarcBot workflow run",
        f"Workflow: {result.workflow_id}",
        f"Project: {result.project}",
        f"State changing: {_yes_no(result.state_changing)}",
        f"Writes artifacts: {_yes_no(result.writes_artifacts)}",
        f"Writes memory: {_yes_no(result.writes_memory)}",
        f"Provider contact: {_yes_no(result.provider_contact)}",
        f"Artifact: {artifact_text}",
        f"Message: {result.message}",
    ]
    return "\n".join(lines)


def format_workflow_run(
    workflow_id: str,
    *,
    project: str | None = None,
) -> str:
    """Run one workflow and return formatted output."""
    return format_workflow_run_result(run_workflow(workflow_id, project=project))
