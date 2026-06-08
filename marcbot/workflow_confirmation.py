from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe

ALLOWED_PROVIDER_CONTACT_WORKFLOWS = ("source-monitor-ai-summary",)
DEFAULT_CONFIRMATION_TTL_SECONDS = 300


@dataclass(frozen=True)
class WorkflowConfirmation:
    token: str
    workflow_id: str
    chat_id: int
    issued_at: datetime
    expires_at: datetime
    used_at: datetime | None = None


@dataclass(frozen=True)
class WorkflowConfirmationResult:
    ok: bool
    reason: str
    message: str
    record: WorkflowConfirmation | None = None


class WorkflowConfirmationStore:
    def __init__(
        self,
        *,
        now_fn: Callable[[], datetime] | None = None,
        token_factory: Callable[[], str] | None = None,
    ) -> None:
        self._now_fn = now_fn or (lambda: datetime.now(UTC))
        self._token_factory = token_factory or (lambda: token_urlsafe(18))
        self._records: dict[str, WorkflowConfirmation] = {}

    def issue(
        self,
        *,
        workflow_id: str,
        chat_id: int,
        ttl_seconds: int = DEFAULT_CONFIRMATION_TTL_SECONDS,
    ) -> WorkflowConfirmation:
        if workflow_id not in ALLOWED_PROVIDER_CONTACT_WORKFLOWS:
            raise ValueError(f"unsupported provider-contact workflow: {workflow_id}")
        if not isinstance(chat_id, int):
            raise ValueError("chat_id must be an integer")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")

        token = self._token_factory().strip()
        if not token:
            raise ValueError("token factory returned an empty token")

        issued_at = self._now()
        record = WorkflowConfirmation(
            token=token,
            workflow_id=workflow_id,
            chat_id=chat_id,
            issued_at=issued_at,
            expires_at=issued_at + timedelta(seconds=ttl_seconds),
        )
        self._records[token] = record
        return record

    def consume(
        self,
        *,
        workflow_id: str,
        chat_id: int,
        token: str,
    ) -> WorkflowConfirmationResult:
        if workflow_id not in ALLOWED_PROVIDER_CONTACT_WORKFLOWS:
            return WorkflowConfirmationResult(
                ok=False,
                reason="unsupported_workflow",
                message="Unsupported provider-contact workflow.",
            )

        token = token.strip()
        if not token:
            return WorkflowConfirmationResult(
                ok=False,
                reason="missing_token",
                message="Missing confirmation token.",
            )

        record = self._records.get(token)
        if record is None:
            return WorkflowConfirmationResult(
                ok=False,
                reason="unknown_token",
                message="Unknown confirmation token.",
            )

        if record.workflow_id != workflow_id:
            return WorkflowConfirmationResult(
                ok=False,
                reason="workflow_mismatch",
                message="Confirmation token does not match this workflow.",
                record=record,
            )

        if record.chat_id != chat_id:
            return WorkflowConfirmationResult(
                ok=False,
                reason="chat_mismatch",
                message="Confirmation token does not match this chat.",
                record=record,
            )

        if record.used_at is not None:
            return WorkflowConfirmationResult(
                ok=False,
                reason="already_used",
                message="Confirmation token was already used.",
                record=record,
            )

        now = self._now()
        if now > record.expires_at:
            return WorkflowConfirmationResult(
                ok=False,
                reason="expired",
                message="Confirmation token expired.",
                record=record,
            )

        used_record = replace(record, used_at=now)
        self._records[token] = used_record
        return WorkflowConfirmationResult(
            ok=True,
            reason="accepted",
            message="Confirmation token accepted.",
            record=used_record,
        )

    def _now(self) -> datetime:
        now = self._now_fn()
        if now.tzinfo is None:
            return now.replace(tzinfo=UTC)
        return now
