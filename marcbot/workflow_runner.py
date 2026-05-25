"""Approved MarcBot workflow execution helpers."""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from marcbot.source_config import DEFAULT_SOURCE_PROJECT_NAME
from marcbot.source_monitor import write_source_monitor_report
from marcbot.workflow_registry import get_workflow_definition

SUMMARY_TASK_DEFAULT = "source_monitor_analysis"


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


def _parse_summary_artifact_path(output: str) -> Path | None:
    for line in output.splitlines():
        prefix = "Source monitor summary written: "
        if line.startswith(prefix):
            value = line.removeprefix(prefix).strip()
            if value:
                return Path(value)
    return None


def _run_source_monitor_summary_cli(
    *,
    project: str,
    task: str,
    memory_profile: str | None,
    memory_query: str | None,
    memory_project: str | None,
    memory_facts_limit: int,
    memory_summaries_limit: int,
    memory_events_limit: int,
) -> tuple[str, Path | None]:
    """Run the existing source-monitor summarize-latest CLI path."""
    command = [
        sys.executable,
        "-m",
        "marcbot",
        "source-monitor",
        "summarize-latest",
        project,
        "--task",
        task,
    ]
    if memory_profile:
        command.extend(["--memory-profile", memory_profile])
    if memory_query:
        command.extend(["--memory-query", memory_query])
    if memory_project:
        command.extend(["--memory-project", memory_project])
    command.extend(["--memory-facts-limit", str(memory_facts_limit)])
    command.extend(["--memory-summaries-limit", str(memory_summaries_limit)])
    command.extend(["--memory-events-limit", str(memory_events_limit)])

    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    output = completed.stdout.strip()
    error_output = completed.stderr.strip()
    if completed.returncode != 0:
        detail = error_output or output or "no subprocess output"
        raise RuntimeError(
            "source-monitor summary workflow failed with exit code "
            f"{completed.returncode}: {detail}"
        )
    return output, _parse_summary_artifact_path(output)


def run_workflow(
    workflow_id: str,
    *,
    project: str | None = None,
    task: str = SUMMARY_TASK_DEFAULT,
    memory_profile: str | None = None,
    memory_query: str | None = None,
    memory_project: str | None = None,
    memory_facts_limit: int = 5,
    memory_summaries_limit: int = 3,
    memory_events_limit: int = 5,
) -> WorkflowRunResult:
    """Run one approved workflow through a bounded implementation path."""
    workflow = get_workflow_definition(workflow_id)
    project_name = project or DEFAULT_SOURCE_PROJECT_NAME

    if workflow.workflow_id == "source-monitor-ai-report":
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

    if workflow.workflow_id == "source-monitor-ai-summary":
        output, artifact_path = _run_source_monitor_summary_cli(
            project=project_name,
            task=task,
            memory_profile=memory_profile or workflow.memory_profile,
            memory_query=memory_query,
            memory_project=memory_project,
            memory_facts_limit=memory_facts_limit,
            memory_summaries_limit=memory_summaries_limit,
            memory_events_limit=memory_events_limit,
        )
        return WorkflowRunResult(
            workflow_id=workflow.workflow_id,
            project=project_name,
            message=output,
            artifact_path=artifact_path,
            provider_contact=workflow.provider_contact,
            writes_artifacts=workflow.writes_artifacts,
            writes_memory=workflow.writes_memory,
            state_changing=workflow.state_changing,
        )

    raise ValueError(
        "workflow execution is not implemented for "
        f"{workflow.workflow_id}; valid runnable workflows: "
        "source-monitor-ai-report, source-monitor-ai-summary"
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
    task: str = SUMMARY_TASK_DEFAULT,
    memory_profile: str | None = None,
    memory_query: str | None = None,
    memory_project: str | None = None,
    memory_facts_limit: int = 5,
    memory_summaries_limit: int = 3,
    memory_events_limit: int = 5,
) -> str:
    """Run one workflow and return formatted output."""
    return format_workflow_run_result(
        run_workflow(
            workflow_id,
            project=project,
            task=task,
            memory_profile=memory_profile,
            memory_query=memory_query,
            memory_project=memory_project,
            memory_facts_limit=memory_facts_limit,
            memory_summaries_limit=memory_summaries_limit,
            memory_events_limit=memory_events_limit,
        )
    )
