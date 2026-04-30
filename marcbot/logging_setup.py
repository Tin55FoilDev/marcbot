"""Logging setup for MarcBot."""

from __future__ import annotations

import logging
from pathlib import Path

from marcbot.paths import LOG_DIR

DEFAULT_LOG_FILE = LOG_DIR / "marcbot.log"


def configure_logging(log_file: Path | None = None) -> Path:
    """Configure application logging and return the active log file path.

    MarcBot keeps this intentionally simple for now:
    - one application log file
    - INFO level by default
    - timestamps, levels, logger names, and messages
    - force=True so tests and CLI invocations can reconfigure predictably
    """

    target = log_file or DEFAULT_LOG_FILE
    target.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        filename=target,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,
    )

    logging.getLogger(__name__).info("MarcBot logging configured: %s", target)
    return target
