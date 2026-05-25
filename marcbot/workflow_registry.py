"""Approved MarcBot workflow registry."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowDefinition:
    """Static metadata for one approved MarcBot workflow."""

    workflow_id: str
    title: str
    description: str
    status: str
    cli_only: bool
    telegram_visible: bool
    telegram_executable: bool
    provider_contact: bool
    writes_artifacts: bool
    writes_memory: bool
    state_changing: bool
    allowed_arguments: tuple[str, ...]
    artifact_roots: tuple[str, ...]
    memory_profile: str | None = None
    implementation_note: str = ""


WORKFLOW_REGISTRY: tuple[WorkflowDefinition, ...] = (
    WorkflowDefinition(
        workflow_id="source-monitor-ai-report",
        title="Source monitor AI report",
        description="Generate a bounded source-monitor report for the AI source project.",
        status="runnable",
        cli_only=True,
        telegram_visible=False,
        telegram_executable=False,
        provider_contact=False,
        writes_artifacts=True,
        writes_memory=False,
        state_changing=True,
        allowed_arguments=("project",),
        artifact_roots=("workspace/source-projects/<project>/reports",),
        memory_profile="source-monitor",
        implementation_note="CLI workflow run v1 executes this workflow.",
    ),
    WorkflowDefinition(
        workflow_id="source-monitor-ai-summary",
        title="Source monitor AI summary",
        description=(
            "Summarize the latest source-monitor report through the configured "
            "LLM task route."
        ),
        status="registered",
        cli_only=True,
        telegram_visible=False,
        telegram_executable=False,
        provider_contact=True,
        writes_artifacts=True,
        writes_memory=False,
        state_changing=True,
        allowed_arguments=("project", "memory-profile"),
        artifact_roots=("workspace/source-projects/<project>/summaries",),
        memory_profile="source-monitor",
        implementation_note="Execution is intentionally deferred until workflow run v1.",
    ),
)


def list_workflow_definitions() -> tuple[WorkflowDefinition, ...]:
    """Return approved workflow definitions sorted by workflow id."""
    return tuple(sorted(WORKFLOW_REGISTRY, key=lambda workflow: workflow.workflow_id))


def get_workflow_definition(workflow_id: str) -> WorkflowDefinition:
    """Return one approved workflow definition by id."""
    normalized = workflow_id.strip()
    if not normalized:
        raise ValueError("workflow id is required")
    for workflow in WORKFLOW_REGISTRY:
        if workflow.workflow_id == normalized:
            return workflow
    valid = ", ".join(workflow.workflow_id for workflow in list_workflow_definitions())
    raise ValueError(f"unknown workflow: {normalized}; valid workflows: {valid}")


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def format_workflow_list() -> str:
    """Return a human-readable approved workflow list."""
    lines = [
        "MarcBot approved workflows",
        f"Count: {len(WORKFLOW_REGISTRY)}",
        "",
    ]
    for workflow in list_workflow_definitions():
        lines.extend(
            [
                f"- {workflow.workflow_id}",
                f"  Title: {workflow.title}",
                f"  Status: {workflow.status}",
                f"  Provider contact: {_yes_no(workflow.provider_contact)}",
                f"  Writes artifacts: {_yes_no(workflow.writes_artifacts)}",
                f"  Writes memory: {_yes_no(workflow.writes_memory)}",
                f"  Telegram executable: {_yes_no(workflow.telegram_executable)}",
            ]
        )
    lines.append("")
    lines.append("Registry provider contact: no")
    return "\n".join(lines)


def format_workflow_detail(workflow_id: str) -> str:
    """Return a human-readable approved workflow detail view."""
    workflow = get_workflow_definition(workflow_id)
    lines = [
        "MarcBot approved workflow",
        f"ID: {workflow.workflow_id}",
        f"Title: {workflow.title}",
        f"Status: {workflow.status}",
        f"Description: {workflow.description}",
        f"CLI only: {_yes_no(workflow.cli_only)}",
        f"Telegram visible: {_yes_no(workflow.telegram_visible)}",
        f"Telegram executable: {_yes_no(workflow.telegram_executable)}",
        f"Provider contact when run: {_yes_no(workflow.provider_contact)}",
        f"Writes artifacts when run: {_yes_no(workflow.writes_artifacts)}",
        f"Writes memory when run: {_yes_no(workflow.writes_memory)}",
        f"State changing when run: {_yes_no(workflow.state_changing)}",
        f"Allowed arguments: {', '.join(workflow.allowed_arguments) or 'none'}",
        f"Artifact roots: {', '.join(workflow.artifact_roots) or 'none'}",
        f"Memory profile: {workflow.memory_profile or 'none'}",
        f"Implementation note: {workflow.implementation_note or 'none'}",
        "Registry provider contact: no",
    ]
    return "\n".join(lines)
