"""Volatile in-memory chat session state for MarcBot."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class ChatMessage:
    """One bounded chat history message."""

    role: str
    content: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ChatSession:
    """Volatile chat state for one Telegram chat."""

    chat_id: int
    profile_name: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    history: list[ChatMessage] = field(default_factory=list)

    @property
    def is_active(self) -> bool:
        """Return whether the session is active."""

        return bool(self.profile_name)


class ChatSessionStore:
    """In-memory chat session store keyed by Telegram chat ID."""

    def __init__(self, *, max_messages: int = 12) -> None:
        if max_messages < 1:
            raise ValueError("max_messages must be at least 1")
        self._max_messages = max_messages
        self._sessions: dict[int, ChatSession] = {}

    @property
    def max_messages(self) -> int:
        """Return maximum stored chat messages per session."""

        return self._max_messages

    def start(self, *, chat_id: int, profile_name: str) -> ChatSession:
        """Start or replace a chat session."""

        cleaned_profile = profile_name.strip()
        if not cleaned_profile:
            raise ValueError("profile_name must not be empty")

        now = datetime.now(UTC)
        session = ChatSession(
            chat_id=chat_id,
            profile_name=cleaned_profile,
            created_at=now,
            updated_at=now,
        )
        self._sessions[chat_id] = session
        return session

    def get(self, *, chat_id: int) -> ChatSession | None:
        """Return the active session for a chat, if any."""

        return self._sessions.get(chat_id)

    def stop(self, *, chat_id: int) -> bool:
        """Stop a chat session.

        Returns true when a session existed.
        """

        return self._sessions.pop(chat_id, None) is not None

    def clear(self, *, chat_id: int) -> bool:
        """Clear chat history while keeping the selected profile active.

        Returns true when a session existed.
        """

        session = self._sessions.get(chat_id)
        if session is None:
            return False

        session.history.clear()
        session.updated_at = datetime.now(UTC)
        return True

    def append_message(
        self,
        *,
        chat_id: int,
        role: str,
        content: str,
    ) -> ChatMessage:
        """Append a bounded message to an active chat session."""

        session = self._sessions.get(chat_id)
        if session is None:
            raise KeyError(f"No active chat session for chat_id={chat_id}")

        cleaned_role = role.strip()
        cleaned_content = content.strip()
        if not cleaned_role:
            raise ValueError("role must not be empty")
        if not cleaned_content:
            raise ValueError("content must not be empty")

        message = ChatMessage(role=cleaned_role, content=cleaned_content)
        session.history.append(message)
        if len(session.history) > self._max_messages:
            del session.history[: len(session.history) - self._max_messages]
        session.updated_at = datetime.now(UTC)
        return message

    def status_text(self, *, chat_id: int) -> str:
        """Return provider-contact-free chat session status text."""

        session = self._sessions.get(chat_id)
        if session is None:
            return (
                "MarcBot chat status\n"
                "Status: inactive\n"
                "Provider contact: no"
            )

        return (
            "MarcBot chat status\n"
            "Status: active\n"
            f"Profile: {session.profile_name}\n"
            f"Stored messages: {len(session.history)}/{self._max_messages}\n"
            "Provider contact: no"
        )
