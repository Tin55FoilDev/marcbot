"""Deterministic memory candidate preview helpers for MarcBot."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryCandidatePreview:
    """Preview of how MarcBot would treat possible memory text."""

    action: str
    risk_level: str
    project: str | None
    reason: str
    input_text: str
    provider_contact: bool = False
    writes: bool = False


_HIGH_RISK_TERMS = (
    "password",
    "token",
    "api key",
    "apikey",
    "secret",
    "credential",
    "private key",
    "ssh key",
    "bot token",
)

_EVENT_TERMS = (
    "completed",
    "generated",
    "sent",
    "backed up",
    "backup completed",
    "failed",
    "recovered",
    "restarted",
    "validated",
)

_DURABLE_FACT_TERMS = (
    "remember",
    "from now on",
    "going forward",
    "always",
    "prefer",
    "preference",
    "should",
    "must",
    "use",
)


def preview_memory_candidate(
    *,
    text: str,
    project: str | None = None,
) -> MemoryCandidatePreview:
    """Classify text as a possible memory candidate without writing memory."""

    cleaned_text = text.strip()
    if not cleaned_text:
        return MemoryCandidatePreview(
            action="ignore",
            risk_level="low",
            project=project,
            reason="empty input",
            input_text=cleaned_text,
        )

    lowered = cleaned_text.lower()

    if any(term in lowered for term in _HIGH_RISK_TERMS):
        return MemoryCandidatePreview(
            action="manual_review",
            risk_level="high",
            project=project,
            reason="text appears to mention secrets or credentials",
            input_text=cleaned_text,
        )

    if any(term in lowered for term in _DURABLE_FACT_TERMS):
        return MemoryCandidatePreview(
            action="propose_fact",
            risk_level="medium",
            project=project,
            reason="text looks like a durable instruction, preference, or policy",
            input_text=cleaned_text,
        )

    if any(term in lowered for term in _EVENT_TERMS):
        return MemoryCandidatePreview(
            action="record_event",
            risk_level="low",
            project=project,
            reason="text looks like a low-risk operational event",
            input_text=cleaned_text,
        )

    return MemoryCandidatePreview(
        action="ignore",
        risk_level="low",
        project=project,
        reason="no durable memory signal detected",
        input_text=cleaned_text,
    )


def format_memory_candidate_preview(preview: MemoryCandidatePreview) -> str:
    """Format a memory candidate preview for CLI/Telegram display."""

    project = preview.project if preview.project else "none"
    provider_contact = "yes" if preview.provider_contact else "no"
    writes = "yes" if preview.writes else "no"

    return "\n".join(
        [
            "MarcBot memory candidate preview",
            f"Action: {preview.action}",
            f"Risk level: {preview.risk_level}",
            f"Project: {project}",
            f"Reason: {preview.reason}",
            f"Provider contact: {provider_contact}",
            f"Writes: {writes}",
            "",
            "Input:",
            preview.input_text,
        ]
    )
