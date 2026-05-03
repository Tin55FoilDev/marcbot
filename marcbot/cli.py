"""MarcBot command-line interface."""

from __future__ import annotations

import argparse
import logging
import sys

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
from marcbot.llm_file_summary import build_summary_prompt, load_workspace_summary_input
from marcbot.llm_tasks import format_llm_task_detail, format_llm_tasks, load_llm_task_config
from marcbot.logging_setup import configure_logging
from marcbot.paths import LOG_DIR, missing_runtime_dirs
from marcbot.report_sender import send_latest_report
from marcbot.reports import write_daily_status_report
from marcbot.source_config import format_source_config_summary, load_source_config
from marcbot.source_monitor import write_source_monitor_report
from marcbot.telegram_bot import run_foreground_bot

LOGGER = logging.getLogger(__name__)


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

    return parser


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

            parser.print_help()
            return 1

        if args.command == "source-monitor":
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

            parser.print_help()
            return 1

        if args.command == "report":
            if args.report_name == "daily-status":
                result = write_daily_status_report()
                print(result.message)
                LOGGER.info("Report generated: %s", result.path)
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
