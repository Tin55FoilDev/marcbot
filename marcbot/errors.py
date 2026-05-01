"""MarcBot error types and operator-facing error formatting."""

from dataclasses import dataclass


@dataclass
class MarcBotError(Exception):
    """Base exception for expected MarcBot errors.

    These errors are intended to be shown cleanly to an operator without a
    raw Python traceback in normal CLI or Telegram output.
    """

    code: str
    message: str

    def __str__(self) -> str:
        return f"ERROR [{self.code}]: {self.message}"
