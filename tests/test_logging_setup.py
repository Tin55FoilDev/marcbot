"""Tests for MarcBot logging setup."""

import logging

from marcbot.logging_setup import configure_logging


def test_configure_logging_writes_to_file(tmp_path) -> None:
    log_file = tmp_path / "marcbot-test.log"

    configured_path = configure_logging(log_file)
    logger = logging.getLogger("marcbot.test")
    logger.info("test log message")

    logging.shutdown()

    assert configured_path == log_file
    assert log_file.is_file()
    assert "test log message" in log_file.read_text(encoding="utf-8")
