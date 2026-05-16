"""Tests for volatile MarcBot chat session state."""

from __future__ import annotations

import pytest

from marcbot.chat_session import ChatSessionStore


def test_chat_session_store_starts_session() -> None:
    store = ChatSessionStore(max_messages=3)

    session = store.start(chat_id=123, profile_name=" local_fast ")

    assert session.chat_id == 123
    assert session.profile_name == "local_fast"
    assert session.is_active is True
    assert store.get(chat_id=123) is session


def test_chat_session_store_rejects_empty_profile() -> None:
    store = ChatSessionStore()

    with pytest.raises(ValueError, match="profile_name"):
        store.start(chat_id=123, profile_name=" ")


def test_chat_session_store_stops_session() -> None:
    store = ChatSessionStore()
    store.start(chat_id=123, profile_name="local_fast")

    assert store.stop(chat_id=123) is True
    assert store.get(chat_id=123) is None
    assert store.stop(chat_id=123) is False


def test_chat_session_store_clears_history() -> None:
    store = ChatSessionStore()
    store.start(chat_id=123, profile_name="local_fast")
    store.append_message(chat_id=123, role="user", content="hello")

    assert store.clear(chat_id=123) is True
    session = store.get(chat_id=123)
    assert session is not None
    assert session.profile_name == "local_fast"
    assert session.history == []


def test_chat_session_store_clear_missing_session_returns_false() -> None:
    store = ChatSessionStore()

    assert store.clear(chat_id=123) is False


def test_chat_session_store_appends_bounded_messages() -> None:
    store = ChatSessionStore(max_messages=2)
    store.start(chat_id=123, profile_name="local_fast")

    store.append_message(chat_id=123, role="user", content="one")
    store.append_message(chat_id=123, role="assistant", content="two")
    store.append_message(chat_id=123, role="user", content="three")

    session = store.get(chat_id=123)
    assert session is not None
    assert [message.content for message in session.history] == ["two", "three"]


def test_chat_session_store_rejects_empty_message_fields() -> None:
    store = ChatSessionStore()
    store.start(chat_id=123, profile_name="local_fast")

    with pytest.raises(ValueError, match="role"):
        store.append_message(chat_id=123, role=" ", content="hello")

    with pytest.raises(ValueError, match="content"):
        store.append_message(chat_id=123, role="user", content=" ")


def test_chat_session_store_append_requires_active_session() -> None:
    store = ChatSessionStore()

    with pytest.raises(KeyError, match="No active chat session"):
        store.append_message(chat_id=123, role="user", content="hello")


def test_chat_session_store_status_text_inactive() -> None:
    store = ChatSessionStore()

    status = store.status_text(chat_id=123)

    assert "MarcBot chat status" in status
    assert "Status: inactive" in status
    assert "Provider contact: no" in status


def test_chat_session_store_status_text_active() -> None:
    store = ChatSessionStore(max_messages=4)
    store.start(chat_id=123, profile_name="local_fast")
    store.append_message(chat_id=123, role="user", content="hello")

    status = store.status_text(chat_id=123)

    assert "MarcBot chat status" in status
    assert "Status: active" in status
    assert "Profile: local_fast" in status
    assert "Stored messages: 1/4" in status
    assert "Provider contact: no" in status


def test_chat_session_store_requires_positive_history_limit() -> None:
    with pytest.raises(ValueError, match="max_messages"):
        ChatSessionStore(max_messages=0)
