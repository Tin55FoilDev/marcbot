"""Approved MarcBot workflow execution helpers."""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from marcbot.source_config import DEFAULT_SOURCE_PROJECT_NAME
from marcbot.source_monitor import write_source_monitor_report
from marcbot.source_status import (
    find_recent_source_monitor_reports,
    find_recent_source_monitor_summaries,
    format_source_monitor_cli_status,
    resolve_source_monitor_artifact,
    source_monitor_artifact_id,
)
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
    summary_input_limit: int | None,
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
    if summary_input_limit is not None:
        command.extend(["--summary-input-limit", str(summary_input_limit)])

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
    summary_input_limit: int | None = None,
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
            memory_profile=(
                workflow.memory_profile if memory_profile is None else memory_profile
            ),
            memory_query=memory_query,
            memory_project=memory_project,
            memory_facts_limit=memory_facts_limit,
            memory_summaries_limit=memory_summaries_limit,
            memory_events_limit=memory_events_limit,
            summary_input_limit=summary_input_limit,
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


def format_workflow_status(
    workflow_id: str,
    *,
    project: str | None = None,
) -> str:
    """Return read-only workflow status and artifact visibility."""
    workflow = get_workflow_definition(workflow_id)
    project_name = project or DEFAULT_SOURCE_PROJECT_NAME

    if workflow.workflow_id not in (
        "source-monitor-ai-report",
        "source-monitor-ai-summary",
    ):
        raise ValueError(
            "workflow status is not implemented for "
            f"{workflow.workflow_id}; valid workflows: "
            "source-monitor-ai-report, source-monitor-ai-summary"
        )

    source_status = format_source_monitor_cli_status(project_name=project_name)
    lines = [
        "MarcBot workflow status",
        f"Workflow: {workflow.workflow_id}",
        f"Project: {project_name}",
        f"Status: {workflow.status}",
        "Provider contact for status: no",
        f"Provider contact when run: {_yes_no(workflow.provider_contact)}",
        f"Writes artifacts when run: {_yes_no(workflow.writes_artifacts)}",
        f"Writes memory when run: {_yes_no(workflow.writes_memory)}",
        f"Telegram executable: {_yes_no(workflow.telegram_executable)}",
        "",
        "Underlying source-monitor status:",
        source_status,
    ]
    return "\n".join(lines)


def resolve_workflow_artifact(
    workflow_id: str,
    artifact_id: str,
    *,
    project: str | None = None,
    reports_dir: Path | None = None,
    summaries_dir: Path | None = None,
) -> Path | None:
    """Resolve a workflow artifact ID through workflow-specific safety gates."""
    workflow = get_workflow_definition(workflow_id)
    project_name = project or DEFAULT_SOURCE_PROJECT_NAME
    normalized_artifact_id = artifact_id.strip()

    if workflow.workflow_id == "source-monitor-ai-report":
        if not normalized_artifact_id.startswith("report:"):
            return None
    elif workflow.workflow_id == "source-monitor-ai-summary":
        if not normalized_artifact_id.startswith("summary:"):
            return None
    else:
        return None

    return resolve_source_monitor_artifact(
        normalized_artifact_id,
        project_name=project_name,
        reports_dir=reports_dir,
        summaries_dir=summaries_dir,
    )


def _format_workflow_artifact_lines(label: str, paths: list[Path]) -> list[str]:
    """Return human-readable artifact lines for workflow artifact output."""
    lines = [f"{label}:"]
    if not paths:
        lines.append("- none")
        return lines

    for path in paths:
        artifact_id = source_monitor_artifact_id(path)
        if artifact_id is not None:
            lines.append(f"- {artifact_id} — {path.name}")

    if len(lines) == 1:
        lines.append("- none")

    return lines


def format_workflow_artifacts(
    workflow_id: str,
    *,
    project: str | None = None,
    reports_dir: Path | None = None,
    summaries_dir: Path | None = None,
    limit: int = 3,
) -> str:
    """Return read-only artifact visibility for a registered workflow."""
    workflow = get_workflow_definition(workflow_id)
    project_name = project or DEFAULT_SOURCE_PROJECT_NAME

    if workflow.workflow_id not in (
        "source-monitor-ai-report",
        "source-monitor-ai-summary",
    ):
        valid_ids = "source-monitor-ai-report, source-monitor-ai-summary"
        raise ValueError(
            "workflow artifact visibility is not implemented for "
            f"{workflow.workflow_id}; valid workflows: {valid_ids}"
        )

    reports = find_recent_source_monitor_reports(
        project_name=project_name,
        reports_dir=reports_dir,
        limit=limit,
    )
    summaries = find_recent_source_monitor_summaries(
        project_name=project_name,
        summaries_dir=summaries_dir,
        limit=limit,
    )

    lines = [
        "MarcBot workflow artifacts",
        f"Workflow: {workflow.workflow_id}",
        f"Project: {project_name}",
        "Provider contact: no",
        f"Writes artifacts when run: {_yes_no(workflow.writes_artifacts)}",
        f"Writes memory when run: {_yes_no(workflow.writes_memory)}",
        f"Telegram executable: {_yes_no(workflow.telegram_executable)}",
        "",
    ]

    if workflow.workflow_id == "source-monitor-ai-report":
        lines.extend(_format_workflow_artifact_lines("Recent report artifacts", reports))
    else:
        lines.extend(_format_workflow_artifact_lines("Recent summary artifacts", summaries))

    return "\n".join(lines)

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
    summary_input_limit: int | None = None,
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
            summary_input_limit=summary_input_limit,
        )
    )
