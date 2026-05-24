"""MarcBot command-line interface."""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from marcbot import __version__
from marcbot.config import DEFAULT_CONFIG_PATH, load_config
from marcbot.errors import MarcBotError
from marcbot.llm_client import (
    format_llm_completion_result,
    format_llm_health_result,
    format_llm_models,
    list_openai_compatible_models,
    run_openai_compatible_completion,
    run_openai_compatible_health_check,
)
from marcbot.llm_config import format_llm_profile_detail, format_llm_profiles, load_llm_config
from marcbot.llm_file_summary import (
    WorkspaceSummaryInput,
    build_summary_prompt,
    load_workspace_summary_input,
    resolve_workspace_summary_output_path,
    write_workspace_summary_output,
)
from marcbot.llm_status import load_llm_env
from marcbot.llm_tasks import format_llm_task_detail, format_llm_tasks, load_llm_task_config
from marcbot.logging_setup import configure_logging
from marcbot.memory_context import (
    format_memory_context,
    format_memory_context_json,
    get_memory_context_profile,
)
from marcbot.memory_sqlite import (
    format_memory_sqlite_counts,
    format_memory_sqlite_status,
    format_memory_sqlite_validation,
    format_sqlite_memory_event_list,
    format_sqlite_memory_fact_list,
    format_sqlite_memory_summary_list,
    import_file_memory_to_sqlite,
    initialize_memory_sqlite,
)
from marcbot.memory_store import (
    add_memory_event,
    add_memory_fact,
    add_memory_proposal,
    add_memory_summary,
    approve_memory_proposal,
    format_memory_event_detail,
    format_memory_event_list,
    format_memory_fact_detail,
    format_memory_fact_list,
    format_memory_proposal_detail,
    format_memory_proposal_list,
    format_memory_search_results,
    format_memory_status_message,
    format_memory_summary_detail,
    format_memory_summary_list,
    init_memory_store,
    reject_memory_fact,
    reject_memory_proposal,
    supersede_memory_fact,
)
from marcbot.memory_workflows import record_approved_workflow_event
from marcbot.paths import LOG_DIR, WORKSPACE_DIR, missing_runtime_dirs
from marcbot.report_sender import (
    send_latest_report,
    send_latest_weather_report,
    send_latest_weather_report_text,
)
from marcbot.reports import write_daily_status_report
from marcbot.source_config import format_source_config_summary, load_source_config
from marcbot.source_monitor import write_source_monitor_report
from marcbot.source_status import (
    find_latest_source_monitor_report,
    format_source_monitor_cli_status,
    resolve_source_monitor_artifact,
)
from marcbot.telegram_bot import run_foreground_bot
from marcbot.weather_report import (
    find_latest_weather_report,
    write_weather_report,
)

LOGGER = logging.getLogger(__name__)

SUMMARY_COMPLETION_ATTEMPTS = 2
SOURCE_MONITOR_SUMMARY_INPUT_LIMIT = 3000
SOURCE_MONITOR_SUMMARY_WITH_MEMORY_INPUT_LIMIT = 2000


def _save_prompt_preview(prompt: str, output_path: str) -> Path:
    resolved_output = resolve_workspace_summary_output_path(output_path)
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    resolved_output.write_text(prompt, encoding="utf-8")
    return resolved_output

def _load_llm_env_for_provider_contact() -> None:
    values = load_llm_env()
    for name, value in values.items():
        os.environ[name] = value

def _build_optional_memory_context_for_prompt(args: argparse.Namespace) -> str:
    memory_query = getattr(args, "memory_query", None)
    memory_project = getattr(args, "memory_project", None)
    if not memory_query and not memory_project:
        return ""

    return format_memory_context(
        query=memory_query,
        project=memory_project,
        facts_limit=getattr(args, "memory_facts_limit", 5),
        summaries_limit=getattr(args, "memory_summaries_limit", 3),
        events_limit=getattr(args, "memory_events_limit", 5),
    )


def _append_optional_memory_context_to_prompt(
    prompt: str,
    args: argparse.Namespace,
) -> str:
    memory_context = _build_optional_memory_context_for_prompt(args)
    if not memory_context:
        return prompt

    memory_instructions = "\n".join(
        [
            "## Local MarcBot memory context",
            "",
            "The following memory context was retrieved locally by MarcBot before this",
            "LLM request. Use it only if it is relevant to the requested task.",
            "",
            "Memory-use rules:",
            "- Prefer active facts over summaries and recent events if they conflict.",
            "- Treat warnings from the memory context as important.",
            "- Do not invent memory that is not present in the supplied context.",
            "- Do not treat recent events as durable facts unless supported by facts",
            "  or summaries.",
            "- Memory retrieval was local; provider contact begins with this explicit",
            "  LLM command.",
            "",
            "Retrieved memory context:",
            "",
        ]
    )

    return prompt.rstrip() + "\n\n" + memory_instructions + memory_context + "\n"

def _build_source_monitor_summary_input(
    report_path: Path,
    requested_path: Path,
    *,
    input_limit: int = SOURCE_MONITOR_SUMMARY_INPUT_LIMIT,
) -> WorkspaceSummaryInput:
    """Build a bounded source-monitor summary input from a generated report."""

    report_text = report_path.read_text(encoding="utf-8")
    if len(report_text) <= input_limit:
        return WorkspaceSummaryInput(
            requested_path=str(requested_path),
            resolved_path=report_path,
            text=report_text,
        )

    lines = report_text.splitlines()
    kept_lines: list[str] = []
    in_fetch_results = False
    fetch_items_kept = 0
    max_fetch_items = 8

    for line in lines:
        if line == "## Fetch results":
            in_fetch_results = True
            kept_lines.append(line)
            continue

        if not in_fetch_results:
            kept_lines.append(line)
            continue

        if line.startswith("- "):
            if fetch_items_kept >= max_fetch_items:
                continue
            fetch_items_kept += 1
            kept_lines.append(line)
            continue

        if fetch_items_kept <= max_fetch_items and (
            line.startswith("  - kind:")
            or line.startswith("  - fetched:")
            or line.startswith("  - status:")
            or line.startswith("  - title:")
            or line.startswith("  - feed_title:")
            or line.startswith("  - latest_item_title:")
            or line.startswith("  - latest_item_link:")
            or line.startswith("  - latest_item_published:")
            or line.startswith("  - change:")
            or line.startswith("  - error:")
        ):
            kept_lines.append(line)

    compact_text = "\n".join(kept_lines).strip()
    suffix = (
        "\n\nNote: This is a compacted source-monitor report input. "
        "The original full report remains saved on disk."
    )
    if len(compact_text) + len(suffix) > input_limit:
        compact_text = compact_text[: input_limit - len(suffix)].rstrip()

    return WorkspaceSummaryInput(
        requested_path=str(requested_path),
        resolved_path=report_path,
        text=compact_text + suffix,
    )


def _write_source_monitor_summary_for_report(
    *,
    project_name: str,
    report_path: Path,
    task_name: str,
    memory_args: argparse.Namespace | None = None,
) -> Path:
    """Summarize an existing source-monitor report and save the summary artifact."""
    input_path = report_path.relative_to(WORKSPACE_DIR)
    output_path = input_path.parent.parent / "summaries" / f"{input_path.stem}.summary.md"

    uses_memory_context = bool(
        memory_args is not None
        and (
            getattr(memory_args, "memory_query", None)
            or getattr(memory_args, "memory_project", None)
        )
    )
    input_limit = (
        SOURCE_MONITOR_SUMMARY_WITH_MEMORY_INPUT_LIMIT
        if uses_memory_context
        else SOURCE_MONITOR_SUMMARY_INPUT_LIMIT
    )
    summary_input = _build_source_monitor_summary_input(
        report_path,
        input_path,
        input_limit=input_limit,
    )
    prompt = build_summary_prompt(summary_input)
    if memory_args is not None:
        prompt = _append_optional_memory_context_to_prompt(prompt, memory_args)
    resolve_workspace_summary_output_path(str(output_path))

    task_config = load_llm_task_config()
    task = task_config.tasks.get(task_name)
    if task is None:
        raise MarcBotError(
            "MBOT-LLM-046",
            f"Unknown LLM task: {task_name}",
        )

    _load_llm_env_for_provider_contact()
    llm_config = load_llm_config()
    profile = llm_config.profiles.get(task.profile)
    if profile is None:
        raise MarcBotError(
            "MBOT-LLM-047",
            f"Unknown LLM profile for task {task_name}: {task.profile}",
        )

    provider = llm_config.providers[profile.provider]
    summary = _run_summary_completion_with_retry(
        provider=provider,
        profile_name=profile.name,
        model=profile.model,
        prompt=prompt,
        temperature=profile.temperature,
        max_tokens=profile.max_tokens,
    )
    written_summary_path = write_workspace_summary_output(
        str(output_path),
        summary.response_text,
    )
    LOGGER.info(
        "Source monitor report summarized: project=%s report=%s summary=%s task=%s",
        project_name,
        report_path,
        written_summary_path,
        task_name,
    )
    return written_summary_path


def _format_llm_status(llm_config, task_config, *, verbose: bool = False) -> str:
    """Format a read-only summary of local LLM configuration."""
    missing_profiles = sorted(
        {
            task.profile
            for task in task_config.tasks.values()
            if task.profile not in llm_config.profiles
        }
    )

    task_config_path = getattr(task_config, "path", None)

    lines = [
        "MarcBot LLM status",
        f"Provider config: valid ({llm_config.path})",
        (
            f"Task config: valid ({task_config_path})"
            if task_config_path is not None
            else "Task config: valid"
        ),
        f"Profiles: {len(llm_config.profiles)} configured",
        f"Tasks: {len(task_config.tasks)} configured",
    ]

    if missing_profiles:
        lines.append(
            "Task routes: invalid; missing profiles: "
            + ", ".join(missing_profiles)
        )
    else:
        lines.append("Task routes: valid")

    if verbose:
        lines.append("")
        lines.append("Profiles:")
        for name, profile in sorted(llm_config.profiles.items()):
            lines.append(
                f"- {name}: provider={profile.provider}, "
                f"model={profile.model}, "
                f"intended_use={profile.intended_use}"
            )

        lines.append("")
        lines.append("Tasks:")
        for name, task in sorted(task_config.tasks.items()):
            lines.append(f"- {name} -> {task.profile} — {task.description}")

    return "\n".join(lines)


def _run_summary_completion_with_retry(
    *,
    provider,
    profile_name: str,
    model: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
):
    """Run a summary completion with one retry for empty provider responses."""

    last_error: MarcBotError | None = None

    for attempt in range(1, SUMMARY_COMPLETION_ATTEMPTS + 1):
        try:
            return run_openai_compatible_completion(
                provider=provider,
                profile_name=profile_name,
                model=model,
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except MarcBotError as exc:
            if exc.code != "MBOT-LLM-035":
                raise

            last_error = exc
            LOGGER.warning(
                "LLM summary completion returned empty content: profile=%s model=%s attempt=%s/%s",
                profile_name,
                model,
                attempt,
                SUMMARY_COMPLETION_ATTEMPTS,
            )

    if last_error is None:
        raise MarcBotError(
            "MBOT-LLM-065",
            "LLM summary completion failed without a captured error",
        )

    raise last_error


def build_parser() -> argparse.ArgumentParser:
    """Build the MarcBot CLI parser."""
    parser = argparse.ArgumentParser(
        prog="marcbot",
        description="MarcBot personal automation CLI",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="show MarcBot version and exit",
    )

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("doctor", help="check MarcBot runtime environment")
    subparsers.add_parser("config-check", help="validate MarcBot local configuration")
    subparsers.add_parser("telegram", help="run Telegram bot in foreground polling mode")

    llm_parser = subparsers.add_parser("llm", help="inspect configured LLM providers and profiles")
    llm_subparsers = llm_parser.add_subparsers(dest="llm_command")
    llm_status_parser = llm_subparsers.add_parser(
        "status",
        help="show read-only LLM configuration status",
    )
    llm_status_parser.add_argument(
        "--verbose",
        action="store_true",
        help="include configured profile and task-route details without contacting providers",
    )
    llm_subparsers.add_parser("profiles", help="list configured LLM profiles")
    llm_profile_parser = llm_subparsers.add_parser(
        "profile",
        help="show one configured LLM profile",
    )
    llm_profile_parser.add_argument("profile", help="configured profile name")
    llm_models_parser = llm_subparsers.add_parser(
        "models",
        help="list models from a configured LLM provider",
    )
    llm_models_parser.add_argument("provider", help="configured provider name")
    llm_health_parser = llm_subparsers.add_parser(
        "health",
        help="run a tiny health check for a configured LLM profile",
    )
    llm_health_parser.add_argument("profile", help="configured profile name")
    llm_ask_parser = llm_subparsers.add_parser(
        "ask",
        help="run a one-shot prompt through a configured LLM profile",
    )
    llm_ask_parser.add_argument("profile", help="configured profile name")
    llm_ask_parser.add_argument("prompt", help="prompt text to send")
    llm_subparsers.add_parser(
        "tasks",
        help="list configured LLM task-to-profile mappings",
    )
    llm_task_parser = llm_subparsers.add_parser(
        "task",
        help="show one configured LLM task-to-profile mapping",
    )
    llm_task_parser.add_argument("task", help="configured task name")
    llm_ask_task_parser = llm_subparsers.add_parser(
        "ask-task",
        help="run a one-shot prompt through a configured LLM task route",
    )
    llm_ask_task_parser.add_argument("task", help="configured task name")
    llm_ask_task_parser.add_argument("prompt", help="prompt text to send")
    llm_summarize_file_parser = llm_subparsers.add_parser(
        "summarize-file",
        help="summarize a workspace-relative text file through a configured LLM task route",
    )
    llm_summarize_file_parser.add_argument("task", help="configured task name")
    llm_summarize_file_parser.add_argument(
        "path",
        help="workspace-relative text file path",
    )
    llm_summarize_file_parser.add_argument("--memory-query", default=None)
    llm_summarize_file_parser.add_argument("--memory-project", default=None)
    llm_summarize_file_parser.add_argument("--memory-facts-limit", type=int, default=5)
    llm_summarize_file_parser.add_argument("--memory-summaries-limit", type=int, default=3)
    llm_summarize_file_parser.add_argument("--memory-events-limit", type=int, default=5)
    llm_summarize_file_parser.add_argument("--preview-prompt", action="store_true")
    llm_summarize_file_parser.add_argument("--preview-prompt-save", default=None)
    llm_summarize_file_save_parser = llm_subparsers.add_parser(
        "summarize-file-save",
        help="summarize a workspace file and save the result under the workspace",
    )
    llm_summarize_file_save_parser.add_argument("task", help="configured task name")
    llm_summarize_file_save_parser.add_argument(
        "input_path",
        help="workspace-relative UTF-8 input file path",
    )
    llm_summarize_file_save_parser.add_argument(
        "output_path",
        help="workspace-relative output file path",
    )
    llm_summarize_file_save_parser.add_argument("--memory-query", default=None)
    llm_summarize_file_save_parser.add_argument("--memory-project", default=None)
    llm_summarize_file_save_parser.add_argument("--memory-facts-limit", type=int, default=5)
    llm_summarize_file_save_parser.add_argument("--memory-summaries-limit", type=int, default=3)
    llm_summarize_file_save_parser.add_argument("--memory-events-limit", type=int, default=5)
    llm_summarize_file_save_parser.add_argument("--preview-prompt", action="store_true")
    llm_summarize_file_save_parser.add_argument("--preview-prompt-save", default=None)

    memory_parser = subparsers.add_parser(
        "memory",
        help="inspect local MarcBot memory",
    )
    memory_subparsers = memory_parser.add_subparsers(dest="memory_command")
    memory_subparsers.add_parser("init", help="initialize local memory store")
    memory_subparsers.add_parser("status", help="show local memory store status")

    memory_context_parser = memory_subparsers.add_parser(
        "context",
        help="assemble bounded local memory context from SQLite",
    )
    memory_context_parser.add_argument("--profile", default=None)
    memory_context_parser.add_argument("--query", default=None)
    memory_context_parser.add_argument("--project", default=None)
    memory_context_parser.add_argument("--facts-limit", type=int, default=5)
    memory_context_parser.add_argument("--summaries-limit", type=int, default=3)
    memory_context_parser.add_argument("--events-limit", type=int, default=5)
    memory_context_parser.add_argument("--format", choices=["text", "json"], default="text")
    memory_sqlite_parser = memory_subparsers.add_parser(
        "sqlite",
        help="manage imported SQLite memory view",
    )
    memory_sqlite_subparsers = memory_sqlite_parser.add_subparsers(
        dest="memory_sqlite_command",
    )
    memory_sqlite_subparsers.add_parser(
        "status",
        help="show SQLite memory database status",
    )
    memory_sqlite_subparsers.add_parser(
        "init",
        help="initialize SQLite memory database schema",
    )
    memory_sqlite_subparsers.add_parser(
        "import",
        help="import file memory into SQLite",
    )
    memory_sqlite_subparsers.add_parser(
        "counts",
        help="show imported SQLite memory counts",
    )
    memory_sqlite_subparsers.add_parser(
        "validate",
        help="validate SQLite import against file memory",
    )

    memory_sqlite_facts_parser = memory_sqlite_subparsers.add_parser(
        "facts",
        help="list/query facts from the SQLite memory view",
    )
    memory_sqlite_facts_parser.add_argument("--status", default="active")
    memory_sqlite_facts_parser.add_argument("--category", default=None)
    memory_sqlite_facts_parser.add_argument("--project", default=None)
    memory_sqlite_facts_parser.add_argument("--query", default=None)
    memory_sqlite_facts_parser.add_argument("--limit", type=int, default=20)

    memory_sqlite_summaries_parser = memory_sqlite_subparsers.add_parser(
        "summaries",
        help="list/query summaries from the SQLite memory view",
    )
    memory_sqlite_summaries_parser.add_argument("--project", default=None)
    memory_sqlite_summaries_parser.add_argument("--query", default=None)
    memory_sqlite_summaries_parser.add_argument("--limit", type=int, default=20)

    memory_sqlite_events_parser = memory_sqlite_subparsers.add_parser(
        "events",
        help="list/query events from the SQLite memory view",
    )
    memory_sqlite_events_parser.add_argument("--type", default=None)
    memory_sqlite_events_parser.add_argument("--project", default=None)
    memory_sqlite_events_parser.add_argument("--source", default=None)
    memory_sqlite_events_parser.add_argument("--query", default=None)
    memory_sqlite_events_parser.add_argument("--limit", type=int, default=20)

    memory_search_parser = memory_subparsers.add_parser(
        "search",
        help="search local memory files",
    )
    memory_search_parser.add_argument("query")
    memory_search_parser.add_argument("--limit", type=int, default=20)
    memory_event_parser = memory_subparsers.add_parser(
        "event",
        help="add or list explicit memory events",
    )
    memory_event_subparsers = memory_event_parser.add_subparsers(
        dest="memory_event_command"
    )
    memory_event_add_parser = memory_event_subparsers.add_parser(
        "add",
        help="add an explicit memory event",
    )
    memory_event_add_parser.add_argument("--type", required=True)
    memory_event_add_parser.add_argument("--summary", required=True)
    memory_event_add_parser.add_argument("--source", required=True)
    memory_event_add_parser.add_argument("--confidence", required=True)
    memory_event_add_parser.add_argument("--project", default=None)
    memory_event_add_parser.add_argument("--details", default=None)
    memory_event_add_parser.add_argument("--cause", default=None)
    memory_event_add_parser.add_argument("--resolution", default=None)
    memory_event_add_parser.add_argument("--verification", default=None)
    memory_event_add_parser.add_argument("--follow-up", default=None)
    memory_event_add_parser.add_argument("--related-file", action="append", default=[])
    memory_event_add_parser.add_argument("--related-command", action="append", default=[])
    memory_event_add_parser.add_argument("--related-artifact", action="append", default=[])
    memory_event_add_parser.add_argument("--related-commit", action="append", default=[])
    memory_event_list_parser = memory_event_subparsers.add_parser(
        "list",
        help="list recent memory events",
    )
    memory_event_list_parser.add_argument("--limit", type=int, default=10)
    memory_event_show_parser = memory_event_subparsers.add_parser(
        "show",
        help="show one recent memory event by index",
    )
    memory_event_show_parser.add_argument("--index", type=int, default=1)
    memory_event_show_parser.add_argument("--limit", type=int, default=10)
    memory_summary_parser = memory_subparsers.add_parser(
        "summary",
        help="add or list explicit memory summaries",
    )
    memory_summary_subparsers = memory_summary_parser.add_subparsers(
        dest="memory_summary_command"
    )
    memory_summary_add_parser = memory_summary_subparsers.add_parser(
        "add",
        help="add an explicit memory summary",
    )
    memory_summary_add_parser.add_argument("--title", required=True)
    memory_summary_add_parser.add_argument("--body", required=True)
    memory_summary_add_parser.add_argument("--source", required=True)
    memory_summary_add_parser.add_argument("--project", default=None)
    memory_summary_add_parser.add_argument("--related-file", action="append", default=[])
    memory_summary_add_parser.add_argument("--related-command", action="append", default=[])
    memory_summary_add_parser.add_argument("--related-artifact", action="append", default=[])
    memory_summary_add_parser.add_argument("--related-commit", action="append", default=[])
    memory_summary_list_parser = memory_summary_subparsers.add_parser(
        "list",
        help="list recent memory summaries",
    )
    memory_summary_list_parser.add_argument("--limit", type=int, default=10)
    memory_summary_show_parser = memory_summary_subparsers.add_parser(
        "show",
        help="show one memory summary by file name",
    )
    memory_summary_show_parser.add_argument("--name", required=True)
    memory_fact_parser = memory_subparsers.add_parser(
        "fact",
        help="add or list explicit memory facts",
    )
    memory_fact_subparsers = memory_fact_parser.add_subparsers(
        dest="memory_fact_command"
    )
    memory_fact_add_parser = memory_fact_subparsers.add_parser(
        "add",
        help="add an explicit memory fact",
    )
    memory_fact_add_parser.add_argument("--id", required=True)
    memory_fact_add_parser.add_argument("--statement", required=True)
    memory_fact_add_parser.add_argument("--category", required=True)
    memory_fact_add_parser.add_argument("--source", required=True)
    memory_fact_add_parser.add_argument("--confidence", required=True)
    memory_fact_add_parser.add_argument("--project", default=None)
    memory_fact_add_parser.add_argument("--details", default=None)
    memory_fact_list_parser = memory_fact_subparsers.add_parser(
        "list",
        help="list memory facts",
    )
    memory_fact_list_parser.add_argument("--status", default="active")
    memory_fact_list_parser.add_argument("--limit", type=int, default=50)
    memory_fact_show_parser = memory_fact_subparsers.add_parser(
        "show",
        help="show one memory fact by id",
    )
    memory_fact_show_parser.add_argument("--id", required=True)
    memory_fact_supersede_parser = memory_fact_subparsers.add_parser(
        "supersede",
        help="supersede an active memory fact with a corrected fact",
    )
    memory_fact_supersede_parser.add_argument("--id", required=True)
    memory_fact_supersede_parser.add_argument("--new-id", required=True)
    memory_fact_supersede_parser.add_argument("--statement", required=True)
    memory_fact_supersede_parser.add_argument("--reason", required=True)
    memory_fact_supersede_parser.add_argument("--source", required=True)
    memory_fact_supersede_parser.add_argument("--confidence", required=True)
    memory_fact_supersede_parser.add_argument("--category", default=None)
    memory_fact_supersede_parser.add_argument("--project", default=None)
    memory_fact_supersede_parser.add_argument("--details", default=None)
    memory_fact_reject_parser = memory_fact_subparsers.add_parser(
        "reject",
        help="mark a memory fact as rejected",
    )
    memory_fact_reject_parser.add_argument("--id", required=True)
    memory_fact_reject_parser.add_argument("--reason", required=True)
    memory_fact_reject_parser.add_argument("--source", required=True)
    memory_fact_reject_parser.add_argument("--confidence", required=True)
    memory_proposal_parser = memory_subparsers.add_parser(
        "proposal",
        help="add, list, or reject memory proposals",
    )
    memory_proposal_subparsers = memory_proposal_parser.add_subparsers(
        dest="memory_proposal_command"
    )
    memory_proposal_add_parser = memory_proposal_subparsers.add_parser(
        "add",
        help="add a pending memory proposal",
    )
    memory_proposal_add_parser.add_argument("--id", required=True)
    memory_proposal_add_parser.add_argument("--proposed-type", required=True)
    memory_proposal_add_parser.add_argument("--proposed-statement", required=True)
    memory_proposal_add_parser.add_argument("--source", required=True)
    memory_proposal_add_parser.add_argument("--rationale", required=True)
    memory_proposal_add_parser.add_argument("--risk-level", required=True)
    memory_proposal_add_parser.add_argument("--project", default=None)
    memory_proposal_add_parser.add_argument("--details", default=None)
    memory_proposal_list_parser = memory_proposal_subparsers.add_parser(
        "list",
        help="list memory proposals",
    )
    memory_proposal_list_parser.add_argument("--status", default="pending")
    memory_proposal_list_parser.add_argument("--limit", type=int, default=50)
    memory_proposal_show_parser = memory_proposal_subparsers.add_parser(
        "show",
        help="show one memory proposal by id",
    )
    memory_proposal_show_parser.add_argument("--id", required=True)
    memory_proposal_reject_parser = memory_proposal_subparsers.add_parser(
        "reject",
        help="reject a pending memory proposal",
    )
    memory_proposal_reject_parser.add_argument("--id", required=True)
    memory_proposal_reject_parser.add_argument("--reason", required=True)
    memory_proposal_reject_parser.add_argument("--source", required=True)
    memory_proposal_approve_parser = memory_proposal_subparsers.add_parser(
        "approve",
        help="approve a pending fact memory proposal",
    )
    memory_proposal_approve_parser.add_argument("--id", required=True)
    memory_proposal_approve_parser.add_argument("--source", required=True)
    memory_proposal_approve_parser.add_argument("--review-reason", default=None)
    memory_proposal_approve_parser.add_argument("--fact-id", default=None)
    memory_proposal_approve_parser.add_argument("--category", default="general")
    memory_proposal_approve_parser.add_argument("--confidence", default="high")

    report_parser = subparsers.add_parser("report", help="generate local MarcBot reports")
    report_subparsers = report_parser.add_subparsers(dest="report_name")
    report_subparsers.add_parser("daily-status", help="write daily status Markdown report")
    report_subparsers.add_parser("send-latest", help="send newest daily status report")

    source_monitor_parser = subparsers.add_parser(
        "source-monitor",
        help="run allowlisted source monitor tasks",
    )
    source_monitor_subparsers = source_monitor_parser.add_subparsers(
        dest="source_monitor_command",
    )
    source_monitor_run_parser = source_monitor_subparsers.add_parser(
        "run",
        help="write source monitor Markdown report",
    )
    source_monitor_run_parser.add_argument(
        "project",
        nargs="?",
        default="ai",
        help="source project name (default: ai)",
    )
    source_monitor_run_summary_parser = source_monitor_subparsers.add_parser(
        "run-summary",
        help="write source monitor report and save an LLM summary",
    )
    source_monitor_run_summary_parser.add_argument(
        "project",
        nargs="?",
        default="ai",
        help="source project name (default: ai)",
    )
    source_monitor_run_summary_parser.add_argument(
        "--task",
        default="source_monitor_analysis",
        help="configured LLM task name (default: source_monitor_analysis)",
    )
    source_monitor_run_summary_parser.add_argument("--memory-query", default=None)
    source_monitor_run_summary_parser.add_argument("--memory-project", default=None)
    source_monitor_run_summary_parser.add_argument(
        "--memory-facts-limit", type=int, default=5
    )
    source_monitor_run_summary_parser.add_argument(
        "--memory-summaries-limit", type=int, default=3
    )
    source_monitor_run_summary_parser.add_argument(
        "--memory-events-limit", type=int, default=5
    )
    source_monitor_summarize_latest_parser = source_monitor_subparsers.add_parser(
        "summarize-latest",
        help="summarize the latest existing source monitor report",
    )
    source_monitor_summarize_latest_parser.add_argument(
        "project",
        nargs="?",
        default="ai",
        help="source project name (default: ai)",
    )
    source_monitor_summarize_latest_parser.add_argument(
        "--task",
        default="source_monitor_analysis",
        help="configured LLM task name (default: source_monitor_analysis)",
    )
    source_monitor_summarize_latest_parser.add_argument("--memory-query", default=None)
    source_monitor_summarize_latest_parser.add_argument("--memory-project", default=None)
    source_monitor_summarize_latest_parser.add_argument(
        "--memory-facts-limit", type=int, default=5
    )
    source_monitor_summarize_latest_parser.add_argument(
        "--memory-summaries-limit", type=int, default=3
    )
    source_monitor_summarize_latest_parser.add_argument(
        "--memory-events-limit", type=int, default=5
    )
    source_monitor_status_parser = source_monitor_subparsers.add_parser(
        "status", help="show latest saved source monitor artifacts",
    )
    source_monitor_status_parser.add_argument(
        "project",
        nargs="?",
        default="ai",
        help="source project name (default: ai)",
    )
    source_monitor_artifact_path_parser = source_monitor_subparsers.add_parser(
        "artifact-path",
        help="resolve a source monitor artifact ID to an approved local path",
    )
    source_monitor_artifact_path_parser.add_argument(
        "project",
        help="source project name",
    )
    source_monitor_artifact_path_parser.add_argument(
        "artifact_id",
        help="artifact ID such as report:2026-05-08-113613",
    )
    source_monitor_config_parser = source_monitor_subparsers.add_parser(
        "config-check",
        help="validate source monitor configuration",
    )
    source_monitor_config_parser.add_argument(
        "project",
        nargs="?",
        default="ai",
        help="source project name (default: ai)",
    )

    weather_parser = subparsers.add_parser(
        "weather-report",
        help="generate local weather reports",
    )
    weather_subparsers = weather_parser.add_subparsers(dest="weather_command")
    weather_subparsers.add_parser(
        "run",
        help="fetch configured weather forecast and write a Markdown report",
    )
    weather_subparsers.add_parser(
        "latest",
        help="show newest generated weather report path",
    )
    weather_subparsers.add_parser(
        "send-latest",
        help="send newest weather report to Telegram as a document",
    )
    weather_subparsers.add_parser(
        "send-latest-text",
        help="send newest weather report to Telegram as text",
    )
    weather_subparsers.add_parser(
        "run-send-text",
        help="fetch weather, write report, and send it to Telegram as text",
    )

    support_parser = subparsers.add_parser(
        "support",
        help="support and session restart helpers",
    )
    support_subparsers = support_parser.add_subparsers(
        dest="support_command",
        required=True,
    )
    support_subparsers.add_parser(
        "snapshot",
        help="print a redacted MarcBot session restart snapshot",
    )

    return parser


def _run_git_command(args: list[str]) -> str:
    """Run a read-only git command and return stripped output."""

    try:
        result = subprocess.run(
            ["git", *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except OSError, subprocess.CalledProcessError:
        return "unknown"

    return result.stdout.strip()


def _format_support_snapshot() -> str:
    """Format a redacted support snapshot for restarting AI sessions."""

    docs_to_check = [
        "docs/SESSION_START.md",
        "docs/ROADMAP.md",
        "docs/CHANGELOG.md",
        "docs/ARCHITECTURE.md",
        "docs/SECURITY.md",
        "docs/COMMANDS.md",
        "docs/LLM.md",
    ]

    branch = _run_git_command(["branch", "--show-current"]) or "unknown"
    commit = _run_git_command(["log", "-1", "--oneline"]) or "unknown"
    status = _run_git_command(["status", "--short"])
    status_summary = "dirty" if status else "clean"

    lines = [
        "# MarcBot Support Snapshot",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        f"MarcBot version: {__version__}",
        "",
        "## Git",
        "",
        f"Branch: {branch}",
        f"Latest commit: {commit}",
        f"Working tree: {status_summary}",
    ]

    if status:
        lines.extend(["", "Changed files:", status])

    lines.extend(
        [
            "",
            "## Runtime paths",
            "",
            f"Repo/app: {Path.cwd()}",
            f"Workspace: {WORKSPACE_DIR}",
            f"Logs: {LOG_DIR}",
            "",
            "## Runtime directory check",
            "",
        ]
    )

    missing_dirs = missing_runtime_dirs()
    if missing_dirs:
        lines.extend(f"- missing: {path}" for path in missing_dirs)
    else:
        lines.append("- required runtime directories found")

    lines.extend(["", "## Important docs", ""])

    for doc in docs_to_check:
        state = "present" if Path(doc).is_file() else "missing"
        lines.append(f"- {doc}: {state}")

    lines.extend(
        [
            "",
            "## Validation command",
            "",
            "Run from the repo as the marc user:",
            "",
            "    ./scripts/check.sh",
            "",
            "## Security note",
            "",
            "This snapshot intentionally does not include secrets, local config file "
            "contents, environment variables, tokens, or unrestricted logs.",
            "",
            "For a new AI session, attach or paste this snapshot with "
            "docs/SESSION_START.md and the exact error or feature goal.",
        ]
    )

    return "\n".join(lines)


def run_doctor() -> int:
    """Check the MarcBot runtime environment."""
    print("MarcBot doctor")

    missing = missing_runtime_dirs()
    if missing:
        missing_list = ", ".join(str(path) for path in missing)
        raise MarcBotError("MBOT-FILES-001", f"Missing required directories: {missing_list}")

    print("OK: required runtime directories found")

    if not LOG_DIR.is_dir():
        raise MarcBotError("MBOT-FILES-002", f"Log directory is missing: {LOG_DIR}")

    test_file = LOG_DIR / ".doctor-write-test"
    try:
        test_file.write_text("ok\n", encoding="utf-8")
        test_file.unlink()
    except OSError as exc:
        raise MarcBotError("MBOT-FILES-003", f"Log directory is not writable: {LOG_DIR}") from exc

    print("OK: logs directory writable")
    print("OK: Python package import works")
    print("OK: MarcBot foundation checks passed")
    LOGGER.info("Doctor check passed")
    return 0


def run_config_check() -> int:
    """Validate the local MarcBot configuration file."""
    print("MarcBot config check")

    config = load_config(DEFAULT_CONFIG_PATH)

    print(f"OK: config loaded from {DEFAULT_CONFIG_PATH}")
    print(f"OK: app.name = {config.app.name}")
    print(f"OK: app.environment = {config.app.environment}")
    print(f"OK: telegram.enabled = {str(config.telegram.enabled).lower()}")
    LOGGER.info("Config check passed: %s", DEFAULT_CONFIG_PATH)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the MarcBot CLI."""
    configure_logging()

    parser = build_parser()
    args = parser.parse_args(argv)

    command_name = "version" if args.version else args.command or "help"
    LOGGER.info("MarcBot CLI command started: %s", command_name)

    try:
        if args.version:
            print(f"🤖 MarcBot {__version__}")
            return 0

        if args.command == "doctor":
            return run_doctor()

        if args.command == "config-check":
            return run_config_check()

        if args.command == "telegram":
            config = load_config(DEFAULT_CONFIG_PATH)
            LOGGER.info("Starting Telegram foreground bot")
            run_foreground_bot(config)
            return 0

        if args.command == "llm":
            if args.llm_command == "status":
                llm_config = load_llm_config()
                task_config = load_llm_task_config()
                print(
                    _format_llm_status(
                        llm_config,
                        task_config,
                        verbose=args.verbose,
                    )
                )
                LOGGER.info("LLM status shown: verbose=%s", args.verbose)
                return 0
            if args.llm_command == "profiles":
                llm_config = load_llm_config()
                print(format_llm_profiles(llm_config))
                LOGGER.info("LLM profiles listed: %s", llm_config.path)
                return 0

            if args.llm_command == "profile":
                llm_config = load_llm_config()
                profile = llm_config.profiles.get(args.profile)
                if profile is None:
                    raise MarcBotError(
                        "MBOT-LLM-037",
                        f"Unknown LLM profile: {args.profile}",
                    )
                provider = llm_config.providers[profile.provider]
                print(format_llm_profile_detail(profile, provider))
                LOGGER.info("LLM profile shown: profile=%s", profile.name)
                return 0

            if args.llm_command == "models":
                _load_llm_env_for_provider_contact()
                llm_config = load_llm_config()
                provider = llm_config.providers.get(args.provider)
                if provider is None:
                    raise MarcBotError(
                        "MBOT-LLM-031",
                        f"Unknown LLM provider: {args.provider}",
                    )
                models = list_openai_compatible_models(provider)
                print(format_llm_models(args.provider, models))
                LOGGER.info("LLM models listed: provider=%s", args.provider)
                return 0

            if args.llm_command == "health":
                _load_llm_env_for_provider_contact()
                llm_config = load_llm_config()
                profile = llm_config.profiles.get(args.profile)
                if profile is None:
                    raise MarcBotError(
                        "MBOT-LLM-037",
                        f"Unknown LLM profile: {args.profile}",
                    )
                provider = llm_config.providers[profile.provider]
                result = run_openai_compatible_health_check(
                    provider=provider,
                    profile_name=profile.name,
                    model=profile.model,
                )
                print(format_llm_health_result(result))
                LOGGER.info("LLM health checked: profile=%s", profile.name)
                return 0

            if args.llm_command == "ask":
                _load_llm_env_for_provider_contact()
                llm_config = load_llm_config()
                profile = llm_config.profiles.get(args.profile)
                if profile is None:
                    raise MarcBotError(
                        "MBOT-LLM-037",
                        f"Unknown LLM profile: {args.profile}",
                    )
                provider = llm_config.providers[profile.provider]
                result = run_openai_compatible_completion(
                    provider=provider,
                    profile_name=profile.name,
                    model=profile.model,
                    prompt=args.prompt,
                    temperature=profile.temperature,
                    max_tokens=profile.max_tokens,
                )
                print(format_llm_completion_result(result))
                LOGGER.info("LLM completion ran: profile=%s", profile.name)
                return 0

            if args.llm_command == "tasks":
                task_config = load_llm_task_config()
                print(format_llm_tasks(task_config))
                LOGGER.info("LLM tasks listed")
                return 0

            if args.llm_command == "task":
                task_config = load_llm_task_config()
                task = task_config.tasks.get(args.task)
                if task is None:
                    raise MarcBotError(
                        "MBOT-LLM-046",
                        f"Unknown LLM task: {args.task}",
                    )
                print(format_llm_task_detail(task))
                LOGGER.info("LLM task shown: task=%s", task.name)
                return 0

            if args.llm_command == "ask-task":
                _load_llm_env_for_provider_contact()
                task_config = load_llm_task_config()
                task = task_config.tasks.get(args.task)
                if task is None:
                    raise MarcBotError(
                        "MBOT-LLM-046",
                        f"Unknown LLM task: {args.task}",
                    )

                llm_config = load_llm_config()
                profile = llm_config.profiles.get(task.profile)
                if profile is None:
                    raise MarcBotError(
                        "MBOT-LLM-047",
                        f"LLM task {task.name} references unknown profile: {task.profile}",
                    )

                provider = llm_config.providers[profile.provider]
                result = run_openai_compatible_completion(
                    provider=provider,
                    profile_name=profile.name,
                    model=profile.model,
                    prompt=args.prompt,
                    temperature=profile.temperature,
                    max_tokens=profile.max_tokens,
                )
                print(format_llm_completion_result(result))
                LOGGER.info(
                    "LLM task completion ran: task=%s profile=%s",
                    task.name,
                    profile.name,
                )
                return 0

            if args.llm_command == "summarize-file":
                summary_input = load_workspace_summary_input(args.path)
                prompt = build_summary_prompt(summary_input)
                prompt = _append_optional_memory_context_to_prompt(prompt, args)
                if args.preview_prompt_save:
                    saved_path = _save_prompt_preview(prompt, args.preview_prompt_save)
                    print(f"Saved LLM prompt preview: {saved_path}")
                if args.preview_prompt:
                    print(prompt)
                if args.preview_prompt or args.preview_prompt_save:
                    return 0

                _load_llm_env_for_provider_contact()
                task_config = load_llm_task_config()
                task = task_config.tasks.get(args.task)
                if task is None:
                    raise MarcBotError(
                        "MBOT-LLM-046",
                        f"Unknown LLM task: {args.task}",
                    )

                llm_config = load_llm_config()
                profile = llm_config.profiles.get(task.profile)
                if profile is None:
                    raise MarcBotError(
                        "MBOT-LLM-047",
                        f"LLM task {task.name} references unknown profile: {task.profile}",
                    )

                provider = llm_config.providers[profile.provider]
                result = _run_summary_completion_with_retry(
                    provider=provider,
                    profile_name=profile.name,
                    model=profile.model,
                    prompt=prompt,
                    temperature=profile.temperature,
                    max_tokens=profile.max_tokens,
                )
                print(format_llm_completion_result(result))
                LOGGER.info(
                    "LLM file summary ran: task=%s profile=%s path=%s",
                    task.name,
                    profile.name,
                    summary_input.requested_path,
                )
                return 0

            if args.llm_command == "summarize-file-save":
                summary_input = load_workspace_summary_input(args.input_path)
                prompt = build_summary_prompt(summary_input)
                prompt = _append_optional_memory_context_to_prompt(prompt, args)
                if not args.preview_prompt and not args.preview_prompt_save:
                    resolve_workspace_summary_output_path(args.output_path)
                if args.preview_prompt_save:
                    saved_path = _save_prompt_preview(prompt, args.preview_prompt_save)
                    print(f"Saved LLM prompt preview: {saved_path}")
                if args.preview_prompt:
                    print(prompt)
                if args.preview_prompt or args.preview_prompt_save:
                    return 0

                _load_llm_env_for_provider_contact()
                task_config = load_llm_task_config()
                task = task_config.tasks.get(args.task)
                if task is None:
                    raise MarcBotError(
                        "MBOT-LLM-046",
                        f"Unknown LLM task: {args.task}",
                    )

                llm_config = load_llm_config()
                profile = llm_config.profiles.get(task.profile)
                if profile is None:
                    raise MarcBotError(
                        "MBOT-LLM-047",
                        f"LLM task {task.name} references unknown profile: {task.profile}",
                    )

                provider = llm_config.providers[profile.provider]
                result = _run_summary_completion_with_retry(
                    provider=provider,
                    profile_name=profile.name,
                    model=profile.model,
                    prompt=prompt,
                    temperature=profile.temperature,
                    max_tokens=profile.max_tokens,
                )
                output_path = write_workspace_summary_output(
                    args.output_path,
                    result.response_text,
                )
                print(f"Saved LLM summary: {output_path}")
                LOGGER.info(
                    "LLM file summary saved: task=%s profile=%s input=%s output=%s",
                    task.name,
                    profile.name,
                    summary_input.requested_path,
                    args.output_path,
                )
                return 0

            parser.print_help()
            return 1

        if args.command == "support":
            if args.support_command == "snapshot":
                print(_format_support_snapshot())
                LOGGER.info("Support snapshot generated")
                return 0

        if args.command == "memory":
            if args.memory_command == "init":
                result = init_memory_store()
                print(result.message)
                return 0
            if args.memory_command == "status":
                print(format_memory_status_message(include_sqlite=True))
                return 0

            if args.memory_command == "context":
                formatter = (
                    format_memory_context_json
                    if args.format == "json"
                    else format_memory_context
                )
                query = args.query
                project = args.project
                facts_limit = args.facts_limit
                summaries_limit = args.summaries_limit
                events_limit = args.events_limit
                if args.profile:
                    profile = get_memory_context_profile(args.profile)
                    query = query if query is not None else profile.query
                    project = project if project is not None else profile.project
                    facts_limit = profile.facts_limit
                    summaries_limit = profile.summaries_limit
                    events_limit = profile.events_limit
                print(
                    formatter(
                        query=query,
                        project=project,
                        facts_limit=facts_limit,
                        summaries_limit=summaries_limit,
                        events_limit=events_limit,
                    )
                )
                return 0
            if args.memory_command == "sqlite":
                if args.memory_sqlite_command == "status":
                    print(format_memory_sqlite_status())
                    return 0
                if args.memory_sqlite_command == "init":
                    result = initialize_memory_sqlite()
                    print(result.message)
                    return 0
                if args.memory_sqlite_command == "import":
                    result = import_file_memory_to_sqlite()
                    print(result.message)
                    return 0
                if args.memory_sqlite_command == "counts":
                    print(format_memory_sqlite_counts())
                    return 0
                if args.memory_sqlite_command == "validate":
                    print(format_memory_sqlite_validation())
                    return 0

                if args.memory_sqlite_command == "facts":
                    print(
                        format_sqlite_memory_fact_list(
                            status=args.status,
                            category=args.category,
                            project=args.project,
                            query=args.query,
                            limit=args.limit,
                        )
                    )
                    return 0

                if args.memory_sqlite_command == "summaries":
                    print(
                        format_sqlite_memory_summary_list(
                            project=args.project,
                            query=args.query,
                            limit=args.limit,
                        )
                    )
                    return 0

                if args.memory_sqlite_command == "events":
                    print(
                        format_sqlite_memory_event_list(
                            event_type=args.type,
                            project=args.project,
                            source=args.source,
                            query=args.query,
                            limit=args.limit,
                        )
                    )
                    return 0
                parser.error("memory sqlite requires a subcommand")
            if args.memory_command == "search":
                print(format_memory_search_results(args.query, limit=args.limit))
                return 0
            if args.memory_command == "event":
                if args.memory_event_command == "add":
                    result = add_memory_event(
                        event_type=args.type,
                        summary=args.summary,
                        source=args.source,
                        confidence=args.confidence,
                        project=args.project,
                        details=args.details,
                        cause=args.cause,
                        resolution=args.resolution,
                        verification=args.verification,
                        follow_up=args.follow_up,
                        related_files=tuple(args.related_file),
                        related_commands=tuple(args.related_command),
                        related_artifacts=tuple(args.related_artifact),
                        related_commits=tuple(args.related_commit),
                    )
                    print(result.message)
                    return 0
                if args.memory_event_command == "list":
                    print(format_memory_event_list(limit=args.limit))
                    return 0
                if args.memory_event_command == "show":
                    print(format_memory_event_detail(index=args.index, limit=args.limit))
                    return 0
                parser.error("memory event requires a subcommand")
            if args.memory_command == "summary":
                if args.memory_summary_command == "add":
                    result = add_memory_summary(
                        title=args.title,
                        body=args.body,
                        source=args.source,
                        project=args.project,
                        related_files=tuple(args.related_file),
                        related_commands=tuple(args.related_command),
                        related_artifacts=tuple(args.related_artifact),
                        related_commits=tuple(args.related_commit),
                    )
                    print(result.message)
                    return 0
                if args.memory_summary_command == "list":
                    print(format_memory_summary_list(limit=args.limit))
                    return 0
                if args.memory_summary_command == "show":
                    print(format_memory_summary_detail(name=args.name))
                    return 0
                parser.error("memory summary requires a subcommand")
            if args.memory_command == "proposal":
                if args.memory_proposal_command == "add":
                    result = add_memory_proposal(
                        proposal_id=args.id,
                        proposed_type=args.proposed_type,
                        proposed_statement=args.proposed_statement,
                        source=args.source,
                        rationale=args.rationale,
                        risk_level=args.risk_level,
                        project=args.project,
                        details=args.details,
                    )
                    print(result.message)
                    return 0
                if args.memory_proposal_command == "list":
                    print(
                        format_memory_proposal_list(
                            status=args.status,
                            limit=args.limit,
                        )
                    )
                    return 0
                if args.memory_proposal_command == "show":
                    print(format_memory_proposal_detail(proposal_id=args.id))
                    return 0
                if args.memory_proposal_command == "reject":
                    result = reject_memory_proposal(
                        proposal_id=args.id,
                        reason=args.reason,
                        source=args.source,
                    )
                    print(result.message)
                    return 0
                if args.memory_proposal_command == "approve":
                    result = approve_memory_proposal(
                        proposal_id=args.id,
                        source=args.source,
                        review_reason=args.review_reason,
                        fact_id=args.fact_id,
                        category=args.category,
                        confidence=args.confidence,
                    )
                    print(result.message)
                    return 0
                parser.error("memory proposal requires a subcommand")
            if args.memory_command == "fact":
                if args.memory_fact_command == "add":
                    result = add_memory_fact(
                        fact_id=args.id,
                        statement=args.statement,
                        category=args.category,
                        source=args.source,
                        confidence=args.confidence,
                        project=args.project,
                        details=args.details,
                    )
                    print(result.message)
                    return 0
                if args.memory_fact_command == "list":
                    print(format_memory_fact_list(status=args.status, limit=args.limit))
                    return 0
                if args.memory_fact_command == "show":
                    print(format_memory_fact_detail(fact_id=args.id))
                    return 0
                if args.memory_fact_command == "supersede":
                    result = supersede_memory_fact(
                        fact_id=args.id,
                        new_fact_id=args.new_id,
                        statement=args.statement,
                        reason=args.reason,
                        source=args.source,
                        confidence=args.confidence,
                        category=args.category,
                        project=args.project,
                        details=args.details,
                    )
                    print(result.message)
                    return 0
                if args.memory_fact_command == "reject":
                    result = reject_memory_fact(
                        fact_id=args.id,
                        reason=args.reason,
                        source=args.source,
                        confidence=args.confidence,
                    )
                    print(result.message)
                    return 0
                parser.error("memory fact requires a subcommand")
            parser.error("memory requires a subcommand")

        if args.command == "weather-report":
            if args.weather_command == "run":
                result = write_weather_report()
                print(result.message)
                return 0
            if args.weather_command == "latest":
                latest = find_latest_weather_report()
                if latest is None:
                    print("No weather reports found.")
                    return 1
                print(latest)
                return 0
            if args.weather_command == "send-latest":
                config = load_config()
                result = send_latest_weather_report(config)
                print(result.message)
                return 0
            if args.weather_command == "send-latest-text":
                config = load_config()
                result = send_latest_weather_report_text(config)
                print(result.message)
                return 0
            if args.weather_command == "run-send-text":
                report_result = write_weather_report()
                print(report_result.message)
                config = load_config()
                send_result = send_latest_weather_report_text(config)
                print(send_result.message)
                memory_result = record_approved_workflow_event(
                    event_type="workflow_completed",
                    project="weather-report",
                    summary="Weather report generated and sent to Telegram as cleaned text.",
                    source="weather_report_run_send_text",
                    details=(
                        "The weather-report run-send-text workflow fetched the configured "
                        "forecast, wrote a Markdown artifact, and sent the latest weather "
                        "report to Telegram as cleaned text."
                    ),
                    verification="Command completed successfully with no exception.",
                    follow_up=(
                        "Use /weather_status for latest artifact status, /timer_status for "
                        "scheduled timer health, and /send_weather_report to resend the "
                        "latest report manually."
                    ),
                    related_files=(report_result.path,),
                    related_commands=(
                        "python -m marcbot weather-report run-send-text",
                    ),
                )
                print(memory_result.message)
                return 0
            parser.error("weather-report requires a subcommand")

        if args.command == "source-monitor":
            if args.source_monitor_command == "status":
                print(format_source_monitor_cli_status(project_name=args.project))
                LOGGER.info("Source monitor status shown: project=%s", args.project)
                return 0
            if args.source_monitor_command == "artifact-path":
                artifact_path = resolve_source_monitor_artifact(
                    args.artifact_id,
                    project_name=args.project,
                )
                if artifact_path is None:
                    print(
                        "MarcBot source monitor artifact\n"
                        f"Project: {args.project}\n"
                        f"Artifact ID: {args.artifact_id}\n"
                        "Status: not found"
                    )
                    LOGGER.info(
                        "Source monitor artifact not found: project=%s artifact_id=%s",
                        args.project,
                        args.artifact_id,
                    )
                    return 1

                print(
                    "MarcBot source monitor artifact\n"
                    f"Project: {args.project}\n"
                    f"Artifact ID: {args.artifact_id}\n"
                    f"Path: {artifact_path}"
                )
                LOGGER.info(
                    "Source monitor artifact resolved: project=%s artifact_id=%s path=%s",
                    args.project,
                    args.artifact_id,
                    artifact_path,
                )
                return 0

            if args.source_monitor_command == "config-check":
                config = load_source_config(project_name=args.project)
                print(format_source_config_summary(config))
                LOGGER.info(
                    "Source monitor config checked: project=%s path=%s",
                    config.project_name,
                    config.path,
                )
                return 0

            if args.source_monitor_command == "run":
                result = write_source_monitor_report(project_name=args.project)
                print(result.message)
                LOGGER.info("Source monitor report generated: %s", result.path)
                return 0

            if args.source_monitor_command == "summarize-latest":
                latest_report = find_latest_source_monitor_report(
                    project_name=args.project,
                )
                if latest_report is None:
                    raise MarcBotError(
                        "MBOT-SOURCE-030",
                        f"No source monitor report found for project: {args.project}",
                    )

                print(f"Using latest source monitor report: {latest_report}")
                written_summary_path = _write_source_monitor_summary_for_report(
                    project_name=args.project,
                    report_path=latest_report,
                    task_name=args.task,
                    memory_args=args,
                )
                print(f"Source monitor summary written: {written_summary_path}")
                return 0

            if args.source_monitor_command == "run-summary":
                result = write_source_monitor_report(project_name=args.project)
                print(result.message)

                written_summary_path = _write_source_monitor_summary_for_report(
                    project_name=args.project,
                    report_path=result.path,
                    task_name=args.task,
                    memory_args=args,
                )
                print(f"Source monitor summary written: {written_summary_path}")
                return 0

            parser.print_help()
            return 1

        if args.command == "report":
            if args.report_name == "daily-status":
                result = write_daily_status_report()
                print(result.message)
                LOGGER.info("Report generated: %s", result.path)
                memory_result = record_approved_workflow_event(
                    event_type="report_generated",
                    project="daily-status-report",
                    summary="Daily status report generated.",
                    source="daily_status_report_cli",
                    details=(
                        "The daily status report CLI wrote a Markdown report artifact "
                        "for later inspection or Telegram delivery."
                    ),
                    verification="Command completed successfully with no exception.",
                    follow_up=(
                        "Use python -m marcbot report send-latest to send the newest "
                        "daily status report to Telegram."
                    ),
                    related_files=(result.path,),
                    related_commands=("python -m marcbot report daily-status",),
                )
                print(memory_result.message)
                return 0

            if args.report_name == "send-latest":
                config = load_config(DEFAULT_CONFIG_PATH)
                result = send_latest_report(config)
                print(result.message)
                LOGGER.info(
                    "Report sent: path=%s chat_ids=%s",
                    result.path,
                    result.chat_ids,
                )
                memory_result = record_approved_workflow_event(
                    event_type="report_sent",
                    project="daily-status-report",
                    summary="Latest daily status report sent to Telegram.",
                    source="daily_status_report_send_latest_cli",
                    details=(
                        "The daily status report send-latest CLI sent the newest "
                        "validated daily status report artifact to configured Telegram "
                        "chat IDs."
                    ),
                    verification="Command completed successfully with no exception.",
                    follow_up=(
                        "Use /send_latest_report to manually resend the newest daily "
                        "status report from Telegram."
                    ),
                    related_files=(result.path,),
                    related_commands=("python -m marcbot report send-latest",),
                )
                print(memory_result.message)
                return 0

            parser.print_help()
            return 1

        parser.print_help()
        return 0

    except MarcBotError as exc:
        LOGGER.warning("MarcBot command failed: %s", exc)
        print(str(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        LOGGER.info("MarcBot command interrupted by operator")
        print("Interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
