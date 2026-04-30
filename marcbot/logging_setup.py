"""Logging setup for MarcBot."""

import logging
from pathlib import Path

from marcbot.paths import LOG_DIR


def configure_logging(log_file: Path | None = None) -> None:
    """Configure basic application logging.

    The first version keeps logging simple. Future versions can add rotation,
    structured logging, and separate audit logs.
    """

    target = log_file or (LOG_DIR / "marcbot.log")
    target.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        filename=target,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
