"""Approved automatic memory helpers for MarcBot workflows."""

from __future__ import annotations

from pathlib import Path

from marcbot.memory_store import MemoryEventAddResult, add_memory_event

APPROVED_AUTOMATIC_EVENT_TYPES: tuple[str, ...] = (
    "workflow_completed",
    "report_generated",
    "report_sent",
    "backup_completed",
    "validation_passed",
    "service_restarted",
)


def _require_nonempty(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must be non-empty")
    return cleaned


def record_approved_workflow_event(
    *,
    event_type: str,
    project: str,
    summary: str,
    source: str,
    details: str,
    verification: str,
    confidence: str = "high",
    follow_up: str | None = None,
    related_files: tuple[str | Path, ...] = (),
    related_commands: tuple[str, ...] = (),
    related_artifacts: tuple[str | Path, ...] = (),
) -> MemoryEventAddResult:
    """Record a low-risk event from an approved workflow.

    This helper is intentionally narrow. It records only approved low-risk event
    types and requires useful operational detail so automatic memory remains
    actionable rather than noisy.
    """
    if event_type not in APPROVED_AUTOMATIC_EVENT_TYPES:
        allowed = ", ".join(APPROVED_AUTOMATIC_EVENT_TYPES)
        raise ValueError(f"event_type must be one of: {allowed}")

    cleaned_related_files = tuple(str(item) for item in related_files)
    cleaned_related_artifacts = tuple(str(item) for item in related_artifacts)

    return add_memory_event(
        event_type=event_type,
        project=_require_nonempty(project, "project"),
        summary=_require_nonempty(summary, "summary"),
        source=_require_nonempty(source, "source"),
        confidence=confidence,
        details=_require_nonempty(details, "details"),
        verification=_require_nonempty(verification, "verification"),
        follow_up=follow_up.strip() if follow_up else None,
        related_files=cleaned_related_files,
        related_commands=related_commands,
        related_artifacts=cleaned_related_artifacts,
    )
