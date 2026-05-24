from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from marcbot.memory_sqlite import (
    DEFAULT_MEMORY_DB_PATH,
    MemorySqliteEventRow,
    MemorySqliteFactRow,
    MemorySqliteSummaryRow,
    query_sqlite_memory_events,
    query_sqlite_memory_facts,
    query_sqlite_memory_summaries,
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
    lines.append("Provider contact: no")
    return "\n".join(lines)
