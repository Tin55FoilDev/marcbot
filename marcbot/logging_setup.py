"""Logging setup for MarcBot."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from marcbot.paths import LOG_DIR

DEFAULT_LOG_FILE = LOG_DIR / "marcbot.log"
DEFAULT_MAX_BYTES = 1_000_000
DEFAULT_BACKUP_COUNT = 5


def configure_logging(
    log_file: Path | None = None,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
) -> Path:
    """Configure rotating application logging and return the active log path.

    MarcBot logging policy:
    - write application logs to /srv/marcbot/logs/marcbot.log by default
    - rotate at 1 MB
    - keep 5 old log files
    - use force=True so tests and CLI invocations reconfigure predictably
    """

    target = log_file or DEFAULT_LOG_FILE
    target.parent.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        target,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"),
    )

    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler],
        force=True,
    )

    logging.getLogger(__name__).info(
        "MarcBot rotating logging configured: %s max_bytes=%s backup_count=%s",
        target,
        max_bytes,
        backup_count,
    )
    return target
