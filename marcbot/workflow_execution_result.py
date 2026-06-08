from __future__ import annotations

from dataclasses import dataclass

MAX_SAFE_REASON_CHARS = 240
SAFE_FLAG_VALUES = frozenset({"yes", "no", "unknown"})
SAFE_WRITE_VALUES = frozenset({"no", "summary artifact", "unknown"})


@dataclass(frozen=True)
class WorkflowExecutionTelegramResult:
    workflow_id: str
    status: str
    provider_contact: str
    workflow_ran: str
    writes: str
    artifact_id: str | None = None
    reason: str | None = None


def format_workflow_execution_success(
    *,
    workflow_id: str,
    artifact_id: str,
) -> str:
    result = WorkflowExecutionTelegramResult(
        workflow_id=workflow_id,
        status="executed",
        provider_contact="yes",
        workflow_ran="yes",
        writes="summary artifact",
        artifact_id=artifact_id,
    )
    return format_workflow_execution_result(result)


def format_workflow_execution_failure(
    *,
    workflow_id: str,
    provider_contact: str,
    workflow_ran: str,
    writes: str,
    reason: str,
) -> str:
    result = WorkflowExecutionTelegramResult(
        workflow_id=workflow_id,
        status="failed",
        provider_contact=_safe_flag(provider_contact),
        workflow_ran=_safe_flag(workflow_ran),
        writes=_safe_writes(writes),
        reason=_safe_reason(reason),
    )
    return format_workflow_execution_result(result)


def format_workflow_execution_result(result: WorkflowExecutionTelegramResult) -> str:
    lines = [
        "MarcBot workflow confirmation",
        f"Workflow: {result.workflow_id}",
        f"Status: {result.status}",
        f"Provider contact: {_safe_flag(result.provider_contact)}",
        f"Workflow ran: {_safe_flag(result.workflow_ran)}",
        f"Writes: {_safe_writes(result.writes)}",
    ]

    if result.artifact_id is not None:
        lines.append(f"Artifact: {_safe_artifact_id(result.artifact_id)}")

    if result.reason is not None:
        lines.append(f"Reason: {_safe_reason(result.reason)}")

    return "\n".join(lines)


def _safe_flag(value: str) -> str:
    value = value.strip().lower()
    if value in SAFE_FLAG_VALUES:
        return value
    return "unknown"


def _safe_writes(value: str) -> str:
    value = value.strip().lower()
    if value in SAFE_WRITE_VALUES:
        return value
    return "unknown"


def _safe_artifact_id(value: str) -> str:
    value = " ".join(value.strip().split())
    if not value:
        return "unknown"
    if "/" in value or "\\" in value:
        return "unknown"
    if len(value) > 80:
        return value[:80]
    return value


def _safe_reason(value: str) -> str:
    value = " ".join(value.strip().split())
    if not value:
        return "unspecified"
    value = value.replace("/srv/", "[path]/")
    value = value.replace("/home/", "[path]/")
    if len(value) > MAX_SAFE_REASON_CHARS:
        return value[:MAX_SAFE_REASON_CHARS] + "..."
    return value
