"""MarcBot command-line interface."""

from __future__ import annotations

import argparse
import logging
import sys

from marcbot import __version__
from marcbot.config import DEFAULT_CONFIG_PATH, load_config
from marcbot.errors import MarcBotError
from marcbot.logging_setup import configure_logging
from marcbot.paths import LOG_DIR, missing_runtime_dirs
from marcbot.report_sender import send_latest_report
from marcbot.reports import write_daily_status_report
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
    source_monitor_subparsers.add_parser(
        "run",
        help="write source monitor Markdown report",
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

        if args.command == "source-monitor":
            if args.source_monitor_command == "run":
                result = write_source_monitor_report()
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
