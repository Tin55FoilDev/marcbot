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
