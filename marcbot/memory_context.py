from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from marcbot.memory_sqlite import (
    DEFAULT_MEMORY_DB_PATH,
    MemorySqliteEventRow,
    MemorySqliteFactRow,
    MemorySqliteSummaryRow,
    get_memory_sqlite_status,
    query_sqlite_memory_events,
    query_sqlite_memory_facts,
    query_sqlite_memory_summaries,
)


@dataclass(frozen=True)
class MemoryContextProfile:
    name: str
    query: str | None
    project: str | None
    facts_limit: int
    summaries_limit: int
    events_limit: int


DEFAULT_MEMORY_CONTEXT_PROFILES: dict[str, MemoryContextProfile] = {
    "weather-report": MemoryContextProfile(
        name="weather-report",
        query="weather",
        project=None,
        facts_limit=5,
        summaries_limit=2,
        events_limit=5,
    ),
    "source-monitor": MemoryContextProfile(
        name="source-monitor",
        query="source-monitor",
        project="source-monitor",
        facts_limit=5,
        summaries_limit=2,
        events_limit=5,
    ),
}




def memory_context_profiles_to_dict() -> dict[str, object]:
    profiles = []
    for name in sorted(DEFAULT_MEMORY_CONTEXT_PROFILES):
        profile = DEFAULT_MEMORY_CONTEXT_PROFILES[name]
        profiles.append(
            {
                "name": profile.name,
                "query": profile.query,
                "project": profile.project,
                "limits": {
                    "facts": profile.facts_limit,
                    "summaries": profile.summaries_limit,
                    "events": profile.events_limit,
                },
            }
        )

    return {
        "provider_contact": False,
        "profiles": profiles,
    }


def format_memory_context_profiles_json() -> str:
    return json.dumps(memory_context_profiles_to_dict(), indent=2, sort_keys=True)


def format_memory_context_profiles() -> str:
    lines = ["MarcBot memory context profiles", ""]

    for name in sorted(DEFAULT_MEMORY_CONTEXT_PROFILES):
        profile = DEFAULT_MEMORY_CONTEXT_PROFILES[name]
        project = profile.project if profile.project is not None else "none"
        query = profile.query if profile.query is not None else "none"
        lines.append(f"- {profile.name}")
        lines.append(f"  query: {query}")
        lines.append(f"  project: {project}")
        lines.append(
            "  limits: "
            f"facts={profile.facts_limit} "
            f"summaries={profile.summaries_limit} "
            f"events={profile.events_limit}"
        )
        lines.append("")

    lines.append("Provider contact: no")
    return "\n".join(lines)


def get_memory_context_profile(name: str) -> MemoryContextProfile:
    try:
        return DEFAULT_MEMORY_CONTEXT_PROFILES[name]
    except KeyError as exc:
        valid = ", ".join(sorted(DEFAULT_MEMORY_CONTEXT_PROFILES))
        message = f"unknown memory context profile: {name}; valid profiles: {valid}"
        raise ValueError(message) from exc


@dataclass(frozen=True)
class MemoryContextRequest:
    query: str | None
    project: str | None
    facts_limit: int
    summaries_limit: int
    events_limit: int


def resolve_memory_context_request(
    *,
    profile_name: str | None = None,
    query: str | None = None,
    project: str | None = None,
    facts_limit: int = 5,
    summaries_limit: int = 3,
    events_limit: int = 5,
) -> MemoryContextRequest:
    if profile_name:
        profile = get_memory_context_profile(profile_name)
        query = query if query is not None else profile.query
        project = project if project is not None else profile.project
        facts_limit = profile.facts_limit
        summaries_limit = profile.summaries_limit
        events_limit = profile.events_limit

    return MemoryContextRequest(
        query=query,
        project=project,
        facts_limit=facts_limit,
        summaries_limit=summaries_limit,
        events_limit=events_limit,
    )


@dataclass(frozen=True)
class MemoryContextPackage:
    path: Path
    query: str | None
    project: str | None
    facts_limit: int
    summaries_limit: int
    events_limit: int
    facts: list[MemorySqliteFactRow]
    summaries: list[MemorySqliteSummaryRow]
    events: list[MemorySqliteEventRow]


def build_memory_context(
    *,
    path: Path = DEFAULT_MEMORY_DB_PATH,
    query: str | None = None,
    project: str | None = None,
    facts_limit: int = 5,
    summaries_limit: int = 3,
    events_limit: int = 5,
) -> MemoryContextPackage:
    if facts_limit < 1:
        raise ValueError("facts_limit must be 1 or greater")
    if summaries_limit < 1:
        raise ValueError("summaries_limit must be 1 or greater")
    if events_limit < 1:
        raise ValueError("events_limit must be 1 or greater")

    facts = query_sqlite_memory_facts(
        path=path,
        status="active",
        project=project,
        query=query,
        limit=facts_limit,
    )
    summaries = query_sqlite_memory_summaries(
        path=path,
        project=project,
        query=query,
        limit=summaries_limit,
    )
    events = query_sqlite_memory_events(
        path=path,
        project=project,
        query=query,
        limit=events_limit,
    )

    return MemoryContextPackage(
        path=path,
        query=query,
        project=project,
        facts_limit=facts_limit,
        summaries_limit=summaries_limit,
        events_limit=events_limit,
        facts=facts,
        summaries=summaries,
        events=events,
    )


def _memory_context_warnings(context: MemoryContextPackage) -> list[str]:
    warnings: list[str] = []
    sqlite_status = get_memory_sqlite_status(path=context.path)

    if not sqlite_status.exists:
        warnings.append("SQLite memory database is missing.")
    elif sqlite_status.schema_version is None:
        warnings.append("SQLite memory schema version is unavailable.")

    if not context.facts and not context.summaries and not context.events:
        warnings.append("No matching memory context was found.")

    return warnings


def _memory_context_sqlite_status(context: MemoryContextPackage) -> dict[str, object]:
    sqlite_status = get_memory_sqlite_status(path=context.path)
    return {
        "exists": sqlite_status.exists,
        "schema_version": sqlite_status.schema_version,
    }

def memory_context_to_dict(context: MemoryContextPackage) -> dict[str, object]:
    return {
        "provider_contact": False,
        "path": str(context.path),
        "sqlite": _memory_context_sqlite_status(context),
        "warnings": _memory_context_warnings(context),
        "query": context.query,
        "project": context.project,
        "limits": {
            "facts": context.facts_limit,
            "summaries": context.summaries_limit,
            "events": context.events_limit,
        },
        "counts": {
            "facts": len(context.facts),
            "summaries": len(context.summaries),
            "events": len(context.events),
        },
        "facts": [
            {
                "id": fact.id,
                "statement": fact.statement,
                "category": fact.category,
                "project": fact.project,
                "source": fact.source,
                "created_at": fact.created_at,
                "updated_at": fact.updated_at,
                "confidence": fact.confidence,
                "status": fact.status,
                "details": fact.details,
            }
            for fact in context.facts
        ],
        "summaries": [
            {
                "name": summary.name,
                "title": summary.title,
                "project": summary.project,
                "source": summary.source,
                "created_at": summary.created_at,
                "body": summary.body,
                "preview": _preview(summary.body),
            }
            for summary in context.summaries
        ],
        "events": [
            {
                "id": event.id,
                "timestamp": event.timestamp,
                "type": event.type,
                "project": event.project,
                "summary": event.summary,
                "source": event.source,
                "confidence": event.confidence,
                "details": event.details,
                "source_file": event.source_file,
                "source_line": event.source_line,
            }
            for event in context.events
        ],
    }

def _preview(text: str, *, limit: int = 180) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3].rstrip() + "..."


def format_memory_context(
    *,
    path: Path = DEFAULT_MEMORY_DB_PATH,
    query: str | None = None,
    project: str | None = None,
    facts_limit: int = 5,
    summaries_limit: int = 3,
    events_limit: int = 5,
) -> str:
    context = build_memory_context(
        path=path,
        query=query,
        project=project,
        facts_limit=facts_limit,
        summaries_limit=summaries_limit,
        events_limit=events_limit,
    )

    lines = [
        "MarcBot memory context",
        f"Path: {context.path}",
    ]

    filters = []
    if context.project:
        filters.append(f"project={context.project}")
    if context.query:
        filters.append(f"query={context.query}")
    if filters:
        lines.append("Filters: " + ", ".join(filters))

    lines.append(
        "Limits: "
        f"facts={context.facts_limit}, "
        f"summaries={context.summaries_limit}, "
        f"events={context.events_limit}"
    )
    lines.append("")

    lines.append("Facts:")
    if not context.facts:
        lines.append("- none")
    else:
        for fact in context.facts:
            project_text = fact.project if fact.project else "none"
            lines.append(f"- {fact.id} [{fact.category}; project={project_text}]")
            lines.append(f"  {fact.statement}")

    lines.append("")
    lines.append("Summaries:")
    if not context.summaries:
        lines.append("- none")
    else:
        for summary in context.summaries:
            project_text = summary.project if summary.project else "none"
            lines.append(
                f"- {summary.name} [{summary.created_at}; project={project_text}]"
            )
            lines.append(f"  {summary.title}")
            preview = _preview(summary.body)
            if preview:
                lines.append(f"  {preview}")

    lines.append("")
    lines.append("Recent events:")
    if not context.events:
        lines.append("- none")
    else:
        for event in context.events:
            project_text = event.project if event.project else "none"
            lines.append(
                f"- {event.timestamp} [{event.type}; project={project_text}; "
                f"source={event.source}]"
            )
            lines.append(f"  {event.summary}")

    lines.append("")
    warnings = _memory_context_warnings(context)
    if warnings:
        lines.append("")
        lines.append("Warnings:")
        for warning in warnings:
            lines.append(f"- {warning}")

    lines.append("")
    lines.append("Provider contact: no")
    return "\n".join(lines)


def build_memory_context_dict(
    *,
    path: Path = DEFAULT_MEMORY_DB_PATH,
    query: str | None = None,
    project: str | None = None,
    facts_limit: int = 5,
    summaries_limit: int = 3,
    events_limit: int = 5,
) -> dict[str, object]:
    context = build_memory_context(
        path=path,
        query=query,
        project=project,
        facts_limit=facts_limit,
        summaries_limit=summaries_limit,
        events_limit=events_limit,
    )
    return memory_context_to_dict(context)

def format_memory_context_json(
    *,
    path: Path = DEFAULT_MEMORY_DB_PATH,
    query: str | None = None,
    project: str | None = None,
    facts_limit: int = 5,
    summaries_limit: int = 3,
    events_limit: int = 5,
) -> str:
    payload = build_memory_context_dict(
        path=path,
        query=query,
        project=project,
        facts_limit=facts_limit,
        summaries_limit=summaries_limit,
        events_limit=events_limit,
    )
    return json.dumps(payload, indent=2, sort_keys=True)
