"""Deterministic memory candidate preview helpers for MarcBot."""

from __future__ import annotations

import json
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



@dataclass(frozen=True)
class MemoryProposalPreview:
    """Preview of a pending memory proposal MarcBot could create."""

    would_create_proposal: bool
    proposal_type: str | None
    risk_level: str
    project: str | None
    proposed_statement: str | None
    source: str
    rationale: str
    reason: str
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




def preview_memory_candidate_proposal(
    *,
    text: str,
    project: str | None = None,
) -> MemoryProposalPreview:
    """Preview the proposal MarcBot would create for candidate text."""

    candidate = preview_memory_candidate(text=text, project=project)

    if candidate.action != "propose_fact":
        return MemoryProposalPreview(
            would_create_proposal=False,
            proposal_type=None,
            risk_level=candidate.risk_level,
            project=project,
            proposed_statement=None,
            source="memory_candidate_proposal_preview",
            rationale="Candidate action is not propose_fact.",
            reason=candidate.reason,
        )

    return MemoryProposalPreview(
        would_create_proposal=True,
        proposal_type="fact",
        risk_level=candidate.risk_level,
        project=project,
        proposed_statement=candidate.input_text,
        source="memory_candidate_proposal_preview",
        rationale="Candidate preview classified this text as a durable fact proposal.",
        reason=candidate.reason,
    )


def memory_proposal_preview_to_dict(
    preview: MemoryProposalPreview,
) -> dict[str, object]:
    """Return a structured proposal-preview contract."""

    return {
        "would_create_proposal": preview.would_create_proposal,
        "proposal_type": preview.proposal_type,
        "risk_level": preview.risk_level,
        "project": preview.project,
        "proposed_statement": preview.proposed_statement,
        "source": preview.source,
        "rationale": preview.rationale,
        "reason": preview.reason,
        "provider_contact": preview.provider_contact,
        "writes": preview.writes,
    }


def format_memory_proposal_preview(preview: MemoryProposalPreview) -> str:
    """Format a proposal preview for CLI/Telegram display."""

    project = preview.project if preview.project else "none"
    provider_contact = "yes" if preview.provider_contact else "no"
    writes = "yes" if preview.writes else "no"
    would_create = "yes" if preview.would_create_proposal else "no"
    proposal_type = preview.proposal_type if preview.proposal_type else "none"
    statement = preview.proposed_statement if preview.proposed_statement else "none"

    return "\n".join(
        [
            "MarcBot memory proposal preview",
            f"Would create proposal: {would_create}",
            f"Proposal type: {proposal_type}",
            f"Risk level: {preview.risk_level}",
            f"Project: {project}",
            f"Source: {preview.source}",
            f"Reason: {preview.reason}",
            f"Rationale: {preview.rationale}",
            f"Provider contact: {provider_contact}",
            f"Writes: {writes}",
            "",
            "Proposed statement:",
            statement,
        ]
    )


def format_memory_proposal_preview_json(preview: MemoryProposalPreview) -> str:
    """Format a proposal preview as stable JSON."""

    return json.dumps(
        memory_proposal_preview_to_dict(preview),
        indent=2,
        sort_keys=True,
    )


def memory_candidate_preview_to_dict(
    preview: MemoryCandidatePreview,
) -> dict[str, object]:
    """Return a structured candidate-preview contract."""

    return {
        "action": preview.action,
        "risk_level": preview.risk_level,
        "project": preview.project,
        "reason": preview.reason,
        "input_text": preview.input_text,
        "provider_contact": preview.provider_contact,
        "writes": preview.writes,
    }


def format_memory_candidate_preview_json(preview: MemoryCandidatePreview) -> str:
    """Format a memory candidate preview as stable JSON."""

    return json.dumps(
        memory_candidate_preview_to_dict(preview),
        indent=2,
        sort_keys=True,
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
