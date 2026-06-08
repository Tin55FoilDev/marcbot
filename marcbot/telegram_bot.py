"""Foreground Telegram bot for MarcBot."""

from __future__ import annotations

import logging
import platform
import sys
from datetime import UTC, datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from marcbot import __version__
from marcbot.about import format_about_message
from marcbot.backup_list import format_backup_list_message
from marcbot.backup_status import format_backup_status_message
from marcbot.chat_context import load_chat_context
from marcbot.chat_session import ChatSessionStore
from marcbot.config import MarcBotConfig
from marcbot.disk import format_disk_report
from marcbot.docs_index import format_doc_message, format_docs_index, validate_send_doc
from marcbot.errors import MarcBotError
from marcbot.git_status import format_git_report
from marcbot.health import format_health_report, run_health_checks
from marcbot.latest_report import validate_latest_daily_status_report
from marcbot.llm_client import run_openai_compatible_completion
from marcbot.llm_config import load_llm_config
from marcbot.llm_status import format_llm_status_message
from marcbot.log_reader import format_logs_message, read_last_log_lines
from marcbot.memory_candidate import (
    format_memory_candidate_preview,
    format_memory_proposal_preview,
    preview_memory_candidate,
    preview_memory_candidate_proposal,
)
from marcbot.memory_context import (
    format_memory_context,
    format_memory_context_profiles,
    resolve_memory_context_request,
)
from marcbot.memory_store import (
    add_memory_proposal,
    format_memory_event_list,
    format_memory_fact_list,
    format_memory_proposal_detail,
    format_memory_proposal_list,
    format_memory_status_message,
    reject_memory_proposal,
)
from marcbot.report_sender import format_weather_report_for_telegram
from marcbot.report_status import format_report_status_message
from marcbot.service_status import format_service_report
from marcbot.source_status import (
    format_source_status_message,
    resolve_source_monitor_artifact,
)
from marcbot.tail_reader import format_tail_message
from marcbot.timer_status import format_timer_status_message
from marcbot.uptime import format_uptime_report
from marcbot.weather_report import find_latest_weather_report
from marcbot.weather_status import format_weather_status_message
from marcbot.workflow_confirmation import (
    DEFAULT_CONFIRMATION_TTL_SECONDS,
    WorkflowConfirmation,
    WorkflowConfirmationStore,
)
from marcbot.workflow_registry import format_workflow_list
from marcbot.workflow_runner import (
    format_workflow_artifacts,
    format_workflow_run,
    format_workflow_status,
    resolve_workflow_artifact,
)
from marcbot.workspace_list import format_workspace_ls_message
from marcbot.workspace_sender import validate_workspace_send

LOGGER = logging.getLogger(__name__)
CHAT_SESSIONS = ChatSessionStore()
MAX_CHAT_INPUT_CHARS = 2000
MAX_CHAT_PROMPT_CHARS = 12000
MAX_CHAT_REPLY_CHARS = 3500


def _chat_id_from_update(update: Update) -> int | None:
    """Return the Telegram chat ID from an update, if present."""
    if update.effective_chat is None:
        return None
    return update.effective_chat.id


def is_authorized_chat(chat_id: int | None, allowed_chat_ids: tuple[int, ...]) -> bool:
    """Return whether a chat ID is allowed to use MarcBot.

    If allowed_chat_ids is empty, no chats are authorized. This avoids
    accidentally allowing all Telegram chats when a token is configured.
    """
    if chat_id is None:
        return False
    return chat_id in allowed_chat_ids


async def _reject_unauthorized(update: Update) -> None:
    """Send a generic unauthorized response."""
    if update.message is not None:
        await update.message.reply_text("Unauthorized chat.")


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /ping."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /ping from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /ping for chat_id=%s", chat_id)

    if update.message is not None:
        await update.message.reply_text("🤖 MarcBot pong")


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /about."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /about from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /about for chat_id=%s", chat_id)

    if update.message is not None:
        await update.message.reply_text(format_about_message())


async def version_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /version."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /version from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /version for chat_id=%s", chat_id)

    version_text = (
        "🤖 MarcBot version\n"
        f"MarcBot: {__version__}\n"
        f"Python: {platform.python_version()}\n"
        f"Executable: {sys.executable}"
    )

    if update.message is not None:
        await update.message.reply_text(version_text)


async def uptime_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /uptime."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    process_started_at = context.application.bot_data["process_started_at"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /uptime from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /uptime for chat_id=%s", chat_id)
    uptime_text = format_uptime_report(process_started_at=process_started_at)

    if update.message is not None:
        await update.message.reply_text(uptime_text)


async def disk_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /disk."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /disk from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /disk for chat_id=%s", chat_id)
    disk_text = format_disk_report()

    if update.message is not None:
        await update.message.reply_text(disk_text)


async def service_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /service."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /service from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /service for chat_id=%s", chat_id)
    service_text = format_service_report()

    if update.message is not None:
        await update.message.reply_text(service_text)


async def git_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /git."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /git from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /git for chat_id=%s", chat_id)
    git_text = format_git_report()

    if update.message is not None:
        await update.message.reply_text(git_text)


async def docs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /docs."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /docs from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /docs for chat_id=%s", chat_id)
    docs_text = format_docs_index()

    if update.message is not None:
        await update.message.reply_text(docs_text)


async def doc_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /doc <name>."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /doc from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    doc_name = " ".join(context.args).strip()
    LOGGER.info("Handled /doc for chat_id=%s doc_name=%s", chat_id, doc_name or "<empty>")
    doc_text = format_doc_message(doc_name)

    if update.message is not None:
        await update.message.reply_text(doc_text)


async def senddoc_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /senddoc <name>."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /senddoc from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    doc_name = " ".join(context.args).strip()
    result = validate_send_doc(doc_name)
    LOGGER.info(
        "Handled /senddoc for chat_id=%s doc_name=%s ok=%s",
        chat_id,
        doc_name or "<empty>",
        result.ok,
    )

    if update.message is None:
        return

    if not result.ok or result.entry is None:
        await update.message.reply_text(result.message)
        return

    await update.message.reply_document(
        document=result.entry.path,
        filename=result.entry.path.name,
        caption=f"🤖 MarcBot doc: {result.entry.name} - {result.entry.title}",
    )


async def ls_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /ls."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /ls from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    requested_path = " ".join(context.args).strip()
    LOGGER.info("Handled /ls for chat_id=%s path=%r", chat_id, requested_path)
    listing_text = format_workspace_ls_message(requested_path=requested_path)

    if update.message is not None:
        await update.message.reply_text(listing_text)


async def send_latest_report_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /send_latest_report."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /send_latest_report from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    result = validate_latest_daily_status_report()
    LOGGER.info(
        "Handled /send_latest_report for chat_id=%s ok=%s path=%s",
        chat_id,
        result.ok,
        result.path if result.path is not None else "<none>",
    )

    if update.message is None:
        return

    if not result.ok or result.path is None:
        await update.message.reply_text(result.message)
        return

    await update.message.reply_document(
        document=result.path,
        filename=result.path.name,
        caption=f"🤖 MarcBot latest daily status report: {result.path.name}",
    )


async def send_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /send <workspace-relative-path>."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /send from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    requested_path = " ".join(context.args).strip()
    result = validate_workspace_send(requested_path)
    LOGGER.info(
        "Handled /send for chat_id=%s requested_path=%s ok=%s",
        chat_id,
        requested_path or "<empty>",
        result.ok,
    )

    if update.message is None:
        return

    if not result.ok or result.path is None:
        await update.message.reply_text(result.message)
        return

    await update.message.reply_document(
        document=result.path,
        filename=result.path.name,
        caption=f"🤖 MarcBot workspace file: {requested_path}",
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    app_environment = context.application.bot_data["app_environment"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /status from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /status for chat_id=%s", chat_id)

    status_text = (
        "🤖 MarcBot status\n"
        "Service: running\n"
        f"Version: {__version__}\n"
        f"Environment: {app_environment}"
    )

    if update.message is not None:
        await update.message.reply_text(status_text)


async def backup_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /backup_list."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /backup_list from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /backup_list for chat_id=%s", chat_id)

    if update.message is not None:
        await update.message.reply_text(format_backup_list_message())


async def backup_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /backup_status."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /backup_status from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /backup_status for chat_id=%s", chat_id)
    backup_text = format_backup_status_message()

    if update.message is not None:
        await update.message.reply_text(backup_text)


async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /health."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /health from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /health for chat_id=%s", chat_id)
    health_text = format_health_report(run_health_checks())

    if update.message is not None:
        await update.message.reply_text(health_text)


async def tail_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /tail <approved-log-name>."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /tail from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    tail_name = " ".join(context.args).strip()
    LOGGER.info("Handled /tail for chat_id=%s tail_name=%s", chat_id, tail_name or "<empty>")
    tail_text = format_tail_message(tail_name)

    if update.message is not None:
        await update.message.reply_text(tail_text)



async def send_weather_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /send_weather_report."""

    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /send_weather_report from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    latest = find_latest_weather_report()
    if latest is None:
        LOGGER.info("Handled /send_weather_report for chat_id=%s ok=false missing_report", chat_id)
        if update.message is not None:
            await update.message.reply_text("No weather reports found.")
        return

    message = format_weather_report_for_telegram(latest.read_text(encoding="utf-8"))

    LOGGER.info(
        "Handled /send_weather_report for chat_id=%s ok=true path=%s chars=%s",
        chat_id,
        latest,
        len(message),
    )

    if update.message is not None:
        await update.message.reply_text(message)



async def memory_facts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /memory_facts."""

    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /memory_facts from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /memory_facts for chat_id=%s", chat_id)

    if update.message is not None:
        await update.message.reply_text(format_memory_fact_list(status="active", limit=8))






def format_memory_candidate_help_message() -> str:
    """Return Telegram help text for the memory candidate workflow."""

    return "\n".join(
        [
            "MarcBot memory candidate workflow",
            "",
            "1. Preview classification:",
            "   /memory_candidate_preview <project> | <text>",
            "",
            "2. Preview pending proposal fields:",
            "   /memory_proposal_preview <project> | <text>",
            "",
            "3. Create pending proposal only when classified propose_fact:",
            "   /memory_candidate_propose <project> | <text>",
            "",
            "4. Review pending proposals:",
            "   /memory_proposals",
            "   /memory_proposal <id>",
            "",
            "5. Reject pending proposal if needed:",
            "   /memory_reject_proposal <id> | <reason>",
            "",
            "Boundaries:",
            "- Preview commands write no memory.",
            "- Candidate propose creates pending proposals only.",
            "- Telegram cannot approve durable facts.",
            "- Provider contact: no",
        ]
    )


def format_memory_candidate_status_message() -> str:
    """Return read-only Telegram status for candidate-memory workflow."""

    return "\n".join(
        [
            "MarcBot memory candidate status",
            "",
            "Available commands:",
            "- /memory_candidate_help - explain the workflow",
            "- /memory_candidate_preview <project> | <text> - classify text",
            "- /memory_proposal_preview <project> | <text> - preview pending proposal",
            "- /memory_candidate_propose <project> | <text> - create pending proposal",
            "- /memory_proposals - list pending proposals",
            "- /memory_proposal <id> - inspect one proposal",
            "- /memory_reject_proposal <id> | <reason> - reject pending proposal",
            "",
            "Boundaries:",
            "- This status command writes no memory.",
            "- Preview commands write no memory.",
            "- Candidate propose writes pending proposals only.",
            "- Telegram cannot approve durable facts.",
            "- Provider contact: no",
            "- Writes: no",
        ]
    )


async def memory_candidate_status_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /memory_candidate_status."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning(
            "Rejected unauthorized /memory_candidate_status from chat_id=%s",
            chat_id,
        )
        await _reject_unauthorized(update)
        return

    await update.message.reply_text(format_memory_candidate_status_message())
    LOGGER.info("Handled /memory_candidate_status for chat_id=%s", chat_id)

async def memory_candidate_help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /memory_candidate_help."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning(
            "Rejected unauthorized /memory_candidate_help from chat_id=%s",
            chat_id,
        )
        await _reject_unauthorized(update)
        return

    await update.message.reply_text(format_memory_candidate_help_message())
    LOGGER.info("Handled /memory_candidate_help for chat_id=%s", chat_id)

async def memory_candidate_propose_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /memory_candidate_propose."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning(
            "Rejected unauthorized /memory_candidate_propose from chat_id=%s",
            chat_id,
        )
        await _reject_unauthorized(update)
        return

    raw_text = " ".join(context.args).strip()
    if " | " not in raw_text:
        await update.message.reply_text(
            "Usage: /memory_candidate_propose <project> | <text>"
        )
        LOGGER.info(
            "Handled /memory_candidate_propose for chat_id=%s "
            "ok=false invalid_format",
            chat_id,
        )
        return

    project, candidate_text = [part.strip() for part in raw_text.split(" | ", 1)]
    if not project or not candidate_text:
        await update.message.reply_text(
            "Usage: /memory_candidate_propose <project> | <text>"
        )
        LOGGER.info(
            "Handled /memory_candidate_propose for chat_id=%s "
            "ok=false missing_value",
            chat_id,
        )
        return

    preview = preview_memory_candidate_proposal(text=candidate_text, project=project)
    if not preview.would_create_proposal:
        await update.message.reply_text(
            "MarcBot memory candidate proposal\n"
            "Created: no\n"
            f"Reason: {preview.reason}\n"
            "Provider contact: no\n"
            "Writes: no"
        )
        LOGGER.info(
            "Handled /memory_candidate_propose for chat_id=%s "
            "ok=true created=false reason=%s",
            chat_id,
            preview.reason,
        )
        return

    proposal_id = (
        "telegram-candidate-fact-"
        f"{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
    )
    try:
        result = add_memory_proposal(
            proposal_id=proposal_id,
            proposed_type="fact",
            proposed_statement=preview.proposed_statement or "",
            source="telegram_memory_candidate_propose",
            rationale=preview.rationale,
            risk_level=preview.risk_level,
            project=preview.project,
            details=(
                "Created by /memory_candidate_propose. "
                "Candidate preview action was propose_fact. This is a "
                "pending proposal, not an approved durable fact."
            ),
        )
    except ValueError as exc:
        await update.message.reply_text(f"Memory candidate propose failed: {exc}")
        LOGGER.info(
            "Handled /memory_candidate_propose for chat_id=%s ok=false error=%s",
            chat_id,
            exc,
        )
        return

    await update.message.reply_text(
        "Memory proposal added:\n"
        f"ID: {result.proposal.id}\n"
        "Status: pending\n"
        "Provider contact: no\n"
        "Writes: yes"
    )
    LOGGER.info(
        "Handled /memory_candidate_propose for chat_id=%s ok=true proposal=%s",
        chat_id,
        result.proposal.id,
    )

async def memory_candidate_proposal_preview_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /memory_proposal_preview."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning(
            "Rejected unauthorized /memory_proposal_preview from chat_id=%s",
            chat_id,
        )
        await _reject_unauthorized(update)
        return

    raw_text = " ".join(context.args).strip()
    if " | " not in raw_text:
        await update.message.reply_text(
            "Usage: /memory_proposal_preview <project> | <text>"
        )
        LOGGER.info(
            "Handled /memory_proposal_preview for chat_id=%s "
            "ok=false invalid_format",
            chat_id,
        )
        return

    project, candidate_text = [part.strip() for part in raw_text.split(" | ", 1)]
    if not project or not candidate_text:
        await update.message.reply_text(
            "Usage: /memory_proposal_preview <project> | <text>"
        )
        LOGGER.info(
            "Handled /memory_proposal_preview for chat_id=%s "
            "ok=false missing_value",
            chat_id,
        )
        return

    preview = preview_memory_candidate_proposal(text=candidate_text, project=project)
    message = format_memory_proposal_preview(preview)
    await update.message.reply_text(message)
    LOGGER.info(
        "Handled /memory_proposal_preview for chat_id=%s "
        "ok=true would_create=%s risk=%s",
        chat_id,
        preview.would_create_proposal,
        preview.risk_level,
    )


async def memory_candidate_preview_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /memory_candidate_preview."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning(
            "Rejected unauthorized /memory_candidate_preview from chat_id=%s",
            chat_id,
        )
        await _reject_unauthorized(update)
        return

    raw_text = " ".join(context.args).strip()
    if " | " not in raw_text:
        await update.message.reply_text(
            "Usage: /memory_candidate_preview <project> | <text>"
        )
        LOGGER.info(
            "Handled /memory_candidate_preview for chat_id=%s ok=false invalid_format",
            chat_id,
        )
        return

    project, candidate_text = [part.strip() for part in raw_text.split(" | ", 1)]
    if not project or not candidate_text:
        await update.message.reply_text(
            "Usage: /memory_candidate_preview <project> | <text>"
        )
        LOGGER.info(
            "Handled /memory_candidate_preview for chat_id=%s ok=false missing_value",
            chat_id,
        )
        return

    preview = preview_memory_candidate(text=candidate_text, project=project)
    message = format_memory_candidate_preview(preview)
    await update.message.reply_text(message)
    LOGGER.info(
        "Handled /memory_candidate_preview for chat_id=%s ok=true action=%s risk=%s",
        chat_id,
        preview.action,
        preview.risk_level,
    )


async def memory_context_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /memory_context."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /memory_context from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    profile_name = context.args[0] if context.args else ""
    if not profile_name:
        await update.message.reply_text("Usage: /memory_context <profile>")
        LOGGER.info("Handled /memory_context for chat_id=%s ok=false missing_profile", chat_id)
        return

    try:
        request = resolve_memory_context_request(profile_name=profile_name)
    except ValueError as exc:
        await update.message.reply_text(str(exc))
        LOGGER.info(
            "Handled /memory_context for chat_id=%s ok=false invalid_profile=%s",
            chat_id,
            profile_name,
        )
        return

    message = format_memory_context(
        query=request.query,
        project=request.project,
        facts_limit=request.facts_limit,
        summaries_limit=request.summaries_limit,
        events_limit=request.events_limit,
    )
    await update.message.reply_text(message)
    LOGGER.info(
        "Handled /memory_context for chat_id=%s ok=true profile=%s",
        chat_id,
        profile_name,
    )






async def memory_reject_proposal_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /memory_reject_proposal."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning(
            "Rejected unauthorized /memory_reject_proposal from chat_id=%s",
            chat_id,
        )
        await _reject_unauthorized(update)
        return

    raw_text = " ".join(context.args).strip()
    if " | " not in raw_text:
        await update.message.reply_text(
            "Usage: /memory_reject_proposal <id> | <reason>"
        )
        LOGGER.info(
            "Handled /memory_reject_proposal for chat_id=%s ok=false invalid_format",
            chat_id,
        )
        return

    proposal_id, reason = [part.strip() for part in raw_text.split(" | ", 1)]
    if not proposal_id or not reason:
        await update.message.reply_text(
            "Usage: /memory_reject_proposal <id> | <reason>"
        )
        LOGGER.info(
            "Handled /memory_reject_proposal for chat_id=%s ok=false missing_value",
            chat_id,
        )
        return

    try:
        result = reject_memory_proposal(
            proposal_id=proposal_id,
            reason=reason,
            source="telegram_memory_reject_proposal",
        )
    except ValueError as exc:
        await update.message.reply_text(f"Memory proposal reject failed: {exc}")
        LOGGER.info(
            "Handled /memory_reject_proposal for chat_id=%s ok=false proposal=%s",
            chat_id,
            proposal_id,
        )
        return

    await update.message.reply_text(
        "Memory proposal rejected:\n"
        f"ID: {result.proposal.id}\n"
        "Status: rejected\n"
        "Provider contact: no"
    )
    LOGGER.info(
        "Handled /memory_reject_proposal for chat_id=%s ok=true proposal=%s",
        chat_id,
        result.proposal.id,
    )


async def memory_proposal_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /memory_proposal."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /memory_proposal from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    proposal_id = context.args[0] if context.args else ""
    if not proposal_id:
        await update.message.reply_text("Usage: /memory_proposal <id>")
        LOGGER.info(
            "Handled /memory_proposal for chat_id=%s ok=false missing_id",
            chat_id,
        )
        return

    try:
        message = format_memory_proposal_detail(proposal_id=proposal_id)
    except ValueError as exc:
        await update.message.reply_text(f"Memory proposal not found: {exc}")
        LOGGER.info(
            "Handled /memory_proposal for chat_id=%s ok=false proposal=%s",
            chat_id,
            proposal_id,
        )
        return

    await update.message.reply_text(message)
    LOGGER.info(
        "Handled /memory_proposal for chat_id=%s ok=true proposal=%s",
        chat_id,
        proposal_id,
    )


async def memory_proposals_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /memory_proposals."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /memory_proposals from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    message = format_memory_proposal_list(status="pending", limit=8)
    await update.message.reply_text(message)
    LOGGER.info("Handled /memory_proposals for chat_id=%s", chat_id)


async def memory_propose_fact_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /memory_propose_fact."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /memory_propose_fact from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    raw_text = " ".join(context.args).strip()
    if " | " not in raw_text:
        await update.message.reply_text(
            "Usage: /memory_propose_fact <project> | <statement>"
        )
        LOGGER.info(
            "Handled /memory_propose_fact for chat_id=%s ok=false invalid_format",
            chat_id,
        )
        return

    project, statement = [part.strip() for part in raw_text.split(" | ", 1)]
    if not project or not statement:
        await update.message.reply_text(
            "Usage: /memory_propose_fact <project> | <statement>"
        )
        LOGGER.info(
            "Handled /memory_propose_fact for chat_id=%s ok=false missing_value",
            chat_id,
        )
        return

    proposal_id = (
        f"telegram-fact-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
    )

    try:
        result = add_memory_proposal(
            proposal_id=proposal_id,
            proposed_type="fact",
            proposed_statement=statement,
            source="telegram_memory_propose_fact",
            rationale="Proposed explicitly from an authorized Telegram command.",
            risk_level="medium",
            project=project,
            details=(
                "Created by /memory_propose_fact. This is a pending proposal, "
                "not an approved durable fact."
            ),
        )
    except ValueError as exc:
        await update.message.reply_text(f"Memory proposal failed: {exc}")
        LOGGER.info(
            "Handled /memory_propose_fact for chat_id=%s ok=false error=%s",
            chat_id,
            exc,
        )
        return

    await update.message.reply_text(
        "Memory proposal added:\n"
        f"ID: {result.proposal.id}\n"
        "Status: pending\n"
        "Provider contact: no"
    )
    LOGGER.info(
        "Handled /memory_propose_fact for chat_id=%s ok=true proposal=%s",
        chat_id,
        result.proposal.id,
    )


async def memory_profiles_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /memory_profiles."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /memory_profiles from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    message = format_memory_context_profiles()
    await update.message.reply_text(message)
    LOGGER.info("Handled /memory_profiles for chat_id=%s", chat_id)


async def memory_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /memory_status."""

    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /memory_status from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /memory_status for chat_id=%s", chat_id)

    if update.message is not None:
        await update.message.reply_text(format_memory_status_message())


async def memory_events_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /memory_events."""

    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /memory_events from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /memory_events for chat_id=%s", chat_id)

    if update.message is not None:
        await update.message.reply_text(format_memory_event_list(limit=8))


async def weather_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /weather_status."""

    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /weather_status from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /weather_status for chat_id=%s", chat_id)

    if update.message is not None:
        await update.message.reply_text(format_weather_status_message())

async def timer_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /timer_status."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /timer_status from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /timer_status for chat_id=%s", chat_id)

    if update.message is not None:
        await update.message.reply_text(format_timer_status_message())


async def report_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /report_status."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /report_status from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    args = tuple(context.args or ())
    LOGGER.info("Handled /report_status for chat_id=%s args=%s", chat_id, args)

    if not args:
        message = format_report_status_message()
    elif len(args) == 2 and args[0].lower() == "source":
        message = format_source_status_message(project_name=args[1])
    else:
        message = (
            "Usage:\n"
            "/report_status\n"
            "/report_status source <project>"
        )

    if update.message is not None:
        await update.message.reply_text(message)


async def send_source_artifact_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /send_source_artifact <project> <artifact-id>."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /send_source_artifact from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    args = tuple(context.args or ())
    LOGGER.info("Handled /send_source_artifact for chat_id=%s args=%s", chat_id, args)

    if update.message is None:
        return

    if len(args) != 2:
        await update.message.reply_text(
            "Usage:\n"
            "/send_source_artifact <project> <artifact-id>\n"
            "Example:\n"
            "/send_source_artifact ai report:2026-05-08-113613"
        )
        return

    project_name, artifact_id = args
    artifact_path = resolve_source_monitor_artifact(
        artifact_id,
        project_name=project_name,
    )

    if artifact_path is None:
        await update.message.reply_text(
            "🤖 MarcBot source monitor artifact\n"
            f"Project: {project_name}\n"
            f"Artifact ID: {artifact_id}\n"
            "Status: not found"
        )
        return

    await update.message.reply_document(
        document=artifact_path,
        filename=artifact_path.name,
        caption=(
            "🤖 MarcBot source monitor artifact\n"
            f"Project: {project_name}\n"
            f"Artifact ID: {artifact_id}"
        ),
    )


async def chat_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /chat_start <profile>."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /chat_start from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    args = list(context.args)
    LOGGER.info("Handled /chat_start for chat_id=%s args=%s", chat_id, args)

    if len(args) != 1:
        if update.message is not None:
            await update.message.reply_text("Usage: /chat_start <profile>")
        return

    profile_name = args[0].strip()
    if not profile_name:
        if update.message is not None:
            await update.message.reply_text("Usage: /chat_start <profile>")
        return

    try:
        llm_config = load_llm_config()
    except Exception:
        LOGGER.exception("Failed to load LLM config for /chat_start")
        if update.message is not None:
            await update.message.reply_text("Chat start failed: LLM config unavailable.")
        return

    profile = llm_config.profiles.get(profile_name)
    if profile is None:
        if update.message is not None:
            await update.message.reply_text(f"Unknown chat profile: {profile_name}")
        return

    if not profile.chat_enabled:
        if update.message is not None:
            await update.message.reply_text(
                f"Profile is not approved for chat: {profile_name}"
            )
        return

    CHAT_SESSIONS.start(chat_id=chat_id, profile_name=profile.name)
    if update.message is not None:
        await update.message.reply_text(
            "MarcBot chat started.\n"
            f"Profile: {profile.name}\n"
            "Provider contact: not yet; future chat text will contact "
            "the configured model provider."
        )


async def chat_stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /chat_stop."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /chat_stop from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /chat_stop for chat_id=%s", chat_id)
    stopped = CHAT_SESSIONS.stop(chat_id=chat_id)
    if update.message is not None:
        if stopped:
            await update.message.reply_text("MarcBot chat stopped.")
        else:
            await update.message.reply_text("MarcBot chat is already inactive.")


async def chat_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /chat_status."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /chat_status from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /chat_status for chat_id=%s", chat_id)
    if update.message is not None:
        await update.message.reply_text(CHAT_SESSIONS.status_text(chat_id=chat_id))




async def chat_profiles_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /chat_profiles."""

    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /chat_profiles from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /chat_profiles for chat_id=%s", chat_id)

    try:
        llm_config = load_llm_config()
    except Exception:
        LOGGER.exception("Failed to load LLM config for /chat_profiles")
        if update.message is not None:
            await update.message.reply_text("Chat profiles unavailable: LLM config unavailable.")
        return

    lines = [
        "MarcBot chat profiles",
        "Provider contact: no",
    ]

    for name in sorted(llm_config.profiles):
        profile = llm_config.profiles[name]
        intended_use = profile.intended_use or "(not set)"
        lines.append(
            f"- {profile.name}: chat_enabled={profile.chat_enabled}, "
            f"model={profile.model}, intended_use={intended_use}"
        )

    if update.message is not None:
        await update.message.reply_text("\n".join(lines))


async def chat_context_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /chat_context."""

    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /chat_context from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /chat_context for chat_id=%s", chat_id)

    try:
        bundle = load_chat_context()
    except MarcBotError as exc:
        LOGGER.warning(
            "Chat context status failed: chat_id=%s code=%s",
            chat_id,
            exc.code,
        )
        if update.message is not None:
            await update.message.reply_text(f"Chat context error: {exc.message}")
        return

    if update.message is not None:
        await update.message.reply_text(
            bundle.format_status() + "\nProvider contact: no"
        )


async def chat_clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /chat_clear."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /chat_clear from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /chat_clear for chat_id=%s", chat_id)
    cleared = CHAT_SESSIONS.clear(chat_id=chat_id)
    if update.message is not None:
        if cleared:
            await update.message.reply_text("MarcBot chat history cleared.")
        else:
            await update.message.reply_text("MarcBot chat is inactive; nothing to clear.")


async def llm_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /llm_status."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /llm_status from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /llm_status for chat_id=%s", chat_id)
    status_text = format_llm_status_message()

    if update.message is not None:
        await update.message.reply_text(status_text)



def _format_chat_prompt(
    history: list[object],
    user_text: str,
    local_context: str = "",
) -> str:
    """Build a bounded chat prompt from volatile history and new user text."""

    lines = [
        "You are MarcBot chat mode.",
        "You may discuss, explain, plan, draft, compare, and summarize text",
        "provided directly in this Telegram chat.",
        "You must not claim that you ran commands, read files, browsed URLs,",
        "updated memory, contacted tools, inspected secrets, or changed system",
        "state.",
        "If Marc asks for an action, suggest the appropriate approved command",
        "or workflow instead of claiming to perform it.",
        "",
        "Recent conversation:",
    ]

    cleaned_context = local_context.strip()
    if cleaned_context:
        lines.extend([
            "",
            "Local configured chat context:",
            cleaned_context,
            "",
            "Recent volatile conversation:",
        ])

    for message in history:
        role = getattr(message, "role", "").strip()
        content = getattr(message, "content", "").strip()
        if not role or not content:
            continue
        lines.append(f"{role}: {content}")

    lines.extend(
        [
            "Current user message:",
            user_text.strip(),
            "",
            "Respond now with the assistant message only. Do not include role labels.",
        ]
    )
    return "\n".join(lines).strip()


def _trim_chat_reply(text: str) -> str:
    """Return a Telegram-bounded chat reply."""

    cleaned = text.strip()
    if len(cleaned) <= MAX_CHAT_REPLY_CHARS:
        return cleaned
    return cleaned[: MAX_CHAT_REPLY_CHARS - 40].rstrip() + "\n\n[truncated]"


async def chat_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle normal Telegram text when chat mode is active."""

    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized chat text from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    if chat_id is None or update.message is None:
        return

    session = CHAT_SESSIONS.get(chat_id=chat_id)
    if session is None:
        LOGGER.info("Ignored normal text for inactive chat_id=%s", chat_id)
        return

    user_text = (update.message.text or "").strip()
    if not user_text:
        return

    if len(user_text) > MAX_CHAT_INPUT_CHARS:
        await update.message.reply_text(
            f"Chat message is too long. Limit: {MAX_CHAT_INPUT_CHARS} characters."
        )
        return

    try:
        llm_config = load_llm_config()
    except Exception:
        LOGGER.exception("Failed to load LLM config for chat text")
        await update.message.reply_text("Chat failed: LLM config unavailable.")
        return

    profile = llm_config.profiles.get(session.profile_name)
    if profile is None:
        await update.message.reply_text(
            f"Chat failed: active profile no longer exists: {session.profile_name}"
        )
        return

    if not profile.chat_enabled:
        CHAT_SESSIONS.stop(chat_id=chat_id)
        await update.message.reply_text(
            f"Chat stopped: profile is no longer approved for chat: {profile.name}"
        )
        return

    provider = llm_config.providers[profile.provider]
    try:
        context_bundle = load_chat_context()
    except MarcBotError as exc:
        LOGGER.warning(
            "Chat context load failed: chat_id=%s profile=%s code=%s",
            chat_id,
            profile.name,
            exc.code,
        )
        await update.message.reply_text(f"Chat context error: {exc.message}")
        return

    local_context = context_bundle.assemble_text()
    LOGGER.info(
        "Chat context loaded: chat_id=%s profile=%s files=%s chars=%s",
        chat_id,
        profile.name,
        len(context_bundle.files),
        context_bundle.total_chars,
    )
    prompt = _format_chat_prompt(
        session.history,
        user_text,
        local_context=local_context,
    )
    if len(prompt) > MAX_CHAT_PROMPT_CHARS:
        await update.message.reply_text(
            "Chat history is too large for the current prompt limit. "
            "Use /chat_clear and try again."
        )
        return

    LOGGER.info(
        "Handling chat text: chat_id=%s profile=%s input_chars=%s history=%s",
        chat_id,
        profile.name,
        len(user_text),
        len(session.history),
    )

    bot = getattr(context, "bot", None)
    if bot is not None:
        try:
            await bot.send_chat_action(chat_id=chat_id, action="typing")
        except Exception:
            LOGGER.warning(
                "Failed to send Telegram typing action: chat_id=%s",
                chat_id,
                exc_info=True,
            )

    try:
        result = run_openai_compatible_completion(
            provider=provider,
            profile_name=profile.name,
            model=profile.model,
            prompt=prompt,
            temperature=profile.temperature,
            max_tokens=profile.max_tokens,
            max_prompt_chars=MAX_CHAT_PROMPT_CHARS,
        )
    except MarcBotError as exc:
        LOGGER.warning(
            "Chat provider error: chat_id=%s profile=%s code=%s",
            chat_id,
            profile.name,
            exc.code,
        )
        await update.message.reply_text(f"Chat provider error: {exc.message}")
        return
    except Exception:
        LOGGER.exception("Unexpected chat provider failure")
        await update.message.reply_text("Chat failed: unexpected provider error.")
        return

    CHAT_SESSIONS.append_message(chat_id=chat_id, role="user", content=user_text)
    CHAT_SESSIONS.append_message(
        chat_id=chat_id,
        role="assistant",
        content=result.response_text,
    )

    LOGGER.info(
        "Chat text handled: chat_id=%s profile=%s output_chars=%s finish=%s",
        chat_id,
        profile.name,
        len(result.response_text),
        result.finish_reason,
    )
    await update.message.reply_text(_trim_chat_reply(result.response_text))


async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /logs."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /logs from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /logs for chat_id=%s", chat_id)
    logs_text = format_logs_message(read_last_log_lines())

    if update.message is not None:
        await update.message.reply_text(logs_text)


def _workflow_confirmation_store(context: ContextTypes.DEFAULT_TYPE) -> WorkflowConfirmationStore:
    """Return the Telegram application workflow-confirmation store."""
    store = context.application.bot_data.get("workflow_confirmation_store")
    if store is None:
        store = WorkflowConfirmationStore()
        context.application.bot_data["workflow_confirmation_store"] = store
    if not isinstance(store, WorkflowConfirmationStore):
        raise TypeError("workflow_confirmation_store must be a WorkflowConfirmationStore")
    return store


def format_provider_contact_preflight_message(
    *,
    record: WorkflowConfirmation,
    ttl_seconds: int = DEFAULT_CONFIRMATION_TTL_SECONDS,
) -> str:
    """Return the provider-contact preflight message with a confirmation token."""
    return "\n".join(
        [
            "MarcBot workflow provider-contact preflight",
            f"Workflow: {record.workflow_id}",
            "Project: ai",
            "Provider contact when run: yes",
            "Writes artifacts when run: yes",
            "Writes memory when run: no",
            "Telegram execution: not enabled",
            "Provider contact: no",
            "Workflow ran: no",
            "Writes: no",
            "",
            "Confirmation token issued for future confirmation UX.",
            f"Token expires in: {ttl_seconds} seconds",
            "",
            "Planned confirmation command:",
            f"/workflow_confirm {record.workflow_id} {record.token}",
            "",
            "/workflow_confirm remains non-executing in this version. "
            "No provider was contacted and no workflow was run.",
        ]
    )


async def workflow_list_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /workflow_list."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /workflow_list from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /workflow_list for chat_id=%s", chat_id)
    if update.message is not None:
        await update.message.reply_text(format_workflow_list())


async def workflow_run_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /workflow_run <workflow-id>."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /workflow_run from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    args = context.args
    if len(args) != 1:
        if update.message is not None:
            await update.message.reply_text("Usage: /workflow_run source-monitor-ai-report")
        LOGGER.info(
            "Handled /workflow_run for chat_id=%s ok=false invalid_args",
            chat_id,
        )
        return

    workflow_id = args[0]

    if workflow_id == "source-monitor-ai-summary":
        if not isinstance(chat_id, int):
            if update.message is not None:
                await update.message.reply_text("Unable to issue confirmation token.")
            LOGGER.info(
                "Handled /workflow_run for chat_id=%s workflow_id=%s ok=false "
                "missing_chat_id",
                chat_id,
                workflow_id,
            )
            return

        store = _workflow_confirmation_store(context)
        record = store.issue(
            workflow_id=workflow_id,
            chat_id=chat_id,
            ttl_seconds=DEFAULT_CONFIRMATION_TTL_SECONDS,
        )
        if update.message is not None:
            await update.message.reply_text(
                format_provider_contact_preflight_message(record=record)
            )
        LOGGER.info(
            "Handled /workflow_run for chat_id=%s workflow_id=%s ok=false "
            "preflight_token_issued",
            chat_id,
            workflow_id,
        )
        return

    if workflow_id != "source-monitor-ai-report":
        if update.message is not None:
            await update.message.reply_text(
                "Telegram workflow execution is currently approved only for "
                "source-monitor-ai-report. Provider-contacting workflows such "
                "as source-monitor-ai-summary remain gated by preflight and CLI-only "
                "execution."
            )
        LOGGER.info(
            "Handled /workflow_run for chat_id=%s workflow_id=%s ok=false unsupported",
            chat_id,
            workflow_id,
        )
        return

    message = format_workflow_run(workflow_id, project="ai")
    LOGGER.info(
        "Handled /workflow_run for chat_id=%s workflow_id=%s project=ai",
        chat_id,
        workflow_id,
    )
    if update.message is not None:
        await update.message.reply_text(message)


def format_workflow_confirm_result_message(
    *,
    workflow_id: str,
    status: str,
    reason: str,
) -> str:
    """Return the non-executing Telegram workflow-confirmation result message."""
    from marcbot.workflow_execution_result import (
        WorkflowExecutionTelegramResult,
        format_workflow_execution_result,
    )

    return format_workflow_execution_result(
        WorkflowExecutionTelegramResult(
            workflow_id=workflow_id,
            status=status,
            provider_contact="no",
            workflow_ran="no",
            writes="no",
            reason=reason,
        )
    )


async def workflow_confirm_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /workflow_confirm <workflow-id> <confirmation-token>."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)
    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /workflow_confirm from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    args = list(context.args)
    if len(args) != 2 or not args[0].strip() or not args[1].strip():
        if update.message is not None:
            await update.message.reply_text(
                "Usage: /workflow_confirm source-monitor-ai-summary "
                "CONFIRMATION_TOKEN"
            )
        LOGGER.info(
            "Handled /workflow_confirm for chat_id=%s ok=false invalid_args",
            chat_id,
        )
        return

    workflow_id = args[0].strip()
    token = args[1].strip()

    if not isinstance(chat_id, int):
        message = format_workflow_confirm_result_message(
            workflow_id=workflow_id,
            status="rejected",
            reason="missing chat id",
        )
        LOGGER.info(
            "Handled /workflow_confirm for chat_id=%s workflow_id=%s ok=false "
            "missing_chat_id",
            chat_id,
            workflow_id,
        )
        if update.message is not None:
            await update.message.reply_text(message)
        return

    store = _workflow_confirmation_store(context)
    result = store.consume(workflow_id=workflow_id, chat_id=chat_id, token=token)
    if result.ok:
        message = format_workflow_confirm_result_message(
            workflow_id=workflow_id,
            status="validated",
            reason="confirmation token accepted; execution remains disabled",
        )
        log_reason = "token_validated_nonexecuting"
    else:
        message = format_workflow_confirm_result_message(
            workflow_id=workflow_id,
            status="rejected",
            reason=result.message,
        )
        log_reason = result.reason

    LOGGER.info(
        "Handled /workflow_confirm for chat_id=%s workflow_id=%s ok=false "
        "reason=%s",
        chat_id,
        workflow_id,
        log_reason,
    )
    if update.message is not None:
        await update.message.reply_text(message)


async def workflow_send_artifact_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /workflow_send_artifact <workflow-id> <artifact-id>."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning(
            "Rejected unauthorized /workflow_send_artifact from chat_id=%s", chat_id
        )
        await _reject_unauthorized(update)
        return

    args = context.args
    LOGGER.info("Handled /workflow_send_artifact for chat_id=%s args=%s", chat_id, args)

    if len(args) != 2:
        if update.message is not None:
            await update.message.reply_text(
                "Usage: /workflow_send_artifact <workflow-id> <artifact-id>\n"
                "Example: /workflow_send_artifact source-monitor-ai-report "
                "report:2026-05-26-113618"
            )
        return

    workflow_id, artifact_id = args
    artifact_path = resolve_workflow_artifact(
        workflow_id,
        artifact_id,
        project="ai",
    )
    if artifact_path is None:
        if update.message is not None:
            await update.message.reply_text(
                "No matching workflow artifact found for that workflow/id pair. "
                "Report workflows require report:... IDs; summary workflows "
                "require summary:... IDs."
            )
        return

    if update.message is None:
        return

    await update.message.reply_document(
        document=artifact_path,
        filename=artifact_path.name,
        caption=(
            "🤖 MarcBot workflow artifact\n"
            f"Workflow: {workflow_id}\n"
            f"Artifact: {artifact_id}"
        ),
    )


async def workflow_artifacts_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /workflow_artifacts <workflow-id>."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /workflow_artifacts from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    workflow_id = " ".join(context.args).strip()
    if not workflow_id:
        if update.message is not None:
            await update.message.reply_text("Usage: /workflow_artifacts <workflow-id>")
        LOGGER.info(
            "Handled /workflow_artifacts for chat_id=%s ok=false missing_workflow_id",
            chat_id,
        )
        return

    message = format_workflow_artifacts(workflow_id=workflow_id, project="ai")
    LOGGER.info(
        "Handled /workflow_artifacts for chat_id=%s workflow_id=%s project=ai",
        chat_id,
        workflow_id,
    )
    if update.message is not None:
        await update.message.reply_text(message)


async def workflow_status_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /workflow_status <workflow-id>."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /workflow_status from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    workflow_id = " ".join(context.args).strip()
    if not workflow_id:
        if update.message is not None:
            await update.message.reply_text("Usage: /workflow_status <workflow-id>")
        LOGGER.info(
            "Handled /workflow_status for chat_id=%s ok=false missing_workflow_id",
            chat_id,
        )
        return

    message = format_workflow_status(workflow_id=workflow_id, project="ai")
    LOGGER.info(
        "Handled /workflow_status for chat_id=%s workflow_id=%s project=ai",
        chat_id,
        workflow_id,
    )
    if update.message is not None:
        await update.message.reply_text(message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized /help from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    LOGGER.info("Handled /help for chat_id=%s", chat_id)

    help_text = (
        "🤖 MarcBot commands:\n"
        "/about - show MarcBot baseline information\n"
        "/backup_list - list recent MarcBot app-level backups\n"
        "/backup_status - show latest MarcBot app-level backup status\n"
        "/chat_clear - clear volatile chat history\n"
        "/chat_context - show loaded local chat context files without contents\n"
        "/chat_profiles - show chat-approved LLM profiles without contacting providers\n"
        "/chat_start <profile> - start bounded chat mode with a chat-approved profile\n"
        "/chat_status - show chat mode status without contacting providers\n"
        "/chat_stop - stop chat mode\n"
        "/disk - show disk usage for root and /srv/marcbot\n"
        "/doc <name> - show an approved MarcBot doc preview\n"
        "/docs - list approved MarcBot docs\n"
        "/git - show MarcBot repository status\n"
        "/health - run local MarcBot health checks\n"
        "/help - show this help message\n"
        "/llm_status - show read-only LLM profile status\n"
        "/logs - show recent MarcBot application logs\n"
        "/ls - list workspace root entries\n"
        "/memory_candidate_help - explain memory candidate workflow\n"
        "/memory_candidate_preview <project> | <text> - preview memory candidate handling\n"
        "/memory_candidate_propose <project> | <text> - create candidate proposal\n"
        "/memory_candidate_status - show memory candidate workflow status\n"
        "/memory_context <profile> - show bounded memory context for a profile\n"
        "/memory_events - show recent local memory events\n"
        "/memory_facts - show active local memory facts\n"
        "/memory_profiles - list deterministic memory context profiles\n"
        "/memory_proposal <id> - show one memory proposal\n"
        "/memory_proposal_preview <project> | <text> - preview proposal handling\n"
        "/memory_proposals - show pending memory proposals\n"
        "/memory_propose_fact <project> | <statement> - propose a pending memory fact\n"
        "/memory_reject_proposal <id> | <reason> - reject a pending memory proposal\n"
        "/memory_status - show local memory status\n"
        "/ping - check whether MarcBot is responding\n"
        "/report_status - show latest daily status report status\n"
        "/report_status source <project> - show latest source monitor summary\n"
        "/send <workspace-relative-path> - send a file from /srv/marcbot/workspace\n"
        "/send_latest_report - send the newest daily status report\n"
        "/send_source_artifact <project> <artifact-id> - send approved source monitor artifact\n"
        "/send_weather_report - resend the latest weather report as text\n"
        "/senddoc <name> - send an approved MarcBot doc as a file\n"
        "/service - show MarcBot systemd service state\n"
        "/status - show basic MarcBot service status\n"
        "/tail <app|service> - show approved diagnostic log tails\n"
        "/timer_status - show MarcBot scheduled timer status\n"
        "/uptime - show host and MarcBot process uptime\n"
        "/version - show MarcBot and Python version\n"
        "/weather_status - show latest weather report status\n"
        "/workflow_artifacts <workflow-id> - show read-only workflow artifacts for ai\n"
        "/workflow_confirm source-monitor-ai-summary <token> - validate confirmation token\n"
        "/workflow_list - list approved workflows\n"
        "/workflow_run source-monitor-ai-report - run approved deterministic report workflow\n"
        "/workflow_send_artifact <workflow-id> <artifact-id> - send approved workflow artifact\n"
        "/workflow_status <workflow-id> - show read-only workflow status for ai"
    )

    if update.message is not None:
        await update.message.reply_text(help_text)


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unknown slash commands."""
    allowed_chat_ids = context.application.bot_data["allowed_chat_ids"]
    chat_id = _chat_id_from_update(update)

    if not is_authorized_chat(chat_id, allowed_chat_ids):
        LOGGER.warning("Rejected unauthorized unknown command from chat_id=%s", chat_id)
        await _reject_unauthorized(update)
        return

    command_text = "<unknown>"
    if update.message is not None and update.message.text:
        command_text = update.message.text.split()[0]

    LOGGER.info("Handled unknown command for chat_id=%s command=%s", chat_id, command_text)

    if update.message is not None:
        await update.message.reply_text(
            "🤖 MarcBot\n"
            f"Unknown command: {command_text}\n"
            "Use /help to see available commands."
        )


def build_application(config: MarcBotConfig) -> Application:
    """Build a Telegram Application from validated MarcBot config."""
    if not config.telegram.enabled:
        raise MarcBotError("MBOT-TELEGRAM-001", "Telegram is disabled in config")

    if not config.telegram.bot_token.strip():
        raise MarcBotError("MBOT-TELEGRAM-002", "Telegram bot token is empty")

    if not config.telegram.allowed_chat_ids:
        raise MarcBotError(
            "MBOT-TELEGRAM-003",
            "Telegram is enabled but no allowed_chat_ids are configured",
        )

    application = Application.builder().token(config.telegram.bot_token).build()
    application.bot_data["allowed_chat_ids"] = config.telegram.allowed_chat_ids
    application.bot_data["workflow_confirmation_store"] = WorkflowConfirmationStore()
    application.bot_data["app_environment"] = config.app.environment
    application.bot_data["process_started_at"] = datetime.now(UTC)

    application.add_handler(CommandHandler("ping", ping_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("version", version_command))
    application.add_handler(CommandHandler("uptime", uptime_command))
    application.add_handler(CommandHandler("disk", disk_command))
    application.add_handler(CommandHandler("service", service_command))
    application.add_handler(CommandHandler("git", git_command))
    application.add_handler(CommandHandler("docs", docs_command))
    application.add_handler(CommandHandler("doc", doc_command))
    application.add_handler(CommandHandler("senddoc", senddoc_command))
    application.add_handler(CommandHandler("ls", ls_command))
    application.add_handler(CommandHandler("send_latest_report", send_latest_report_command))
    application.add_handler(CommandHandler("send", send_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("health", health_command))
    application.add_handler(CommandHandler("backup_list", backup_list_command))
    application.add_handler(CommandHandler("backup_status", backup_status_command))
    application.add_handler(CommandHandler("timer_status", timer_status_command))
    application.add_handler(CommandHandler("weather_status", weather_status_command))
    application.add_handler(CommandHandler("memory_events", memory_events_command))
    application.add_handler(CommandHandler("memory_facts", memory_facts_command))
    application.add_handler(
        CommandHandler("memory_candidate_status", memory_candidate_status_command)
    )
    application.add_handler(
        CommandHandler("memory_candidate_help", memory_candidate_help_command)
    )
    application.add_handler(
        CommandHandler("memory_candidate_propose", memory_candidate_propose_command)
    )
    application.add_handler(
        CommandHandler(
            "memory_proposal_preview",
            memory_candidate_proposal_preview_command,
        )
    )
    application.add_handler(
        CommandHandler("memory_candidate_preview", memory_candidate_preview_command)
    )
    application.add_handler(CommandHandler("memory_context", memory_context_command))
    application.add_handler(CommandHandler("memory_propose_fact", memory_propose_fact_command))
    application.add_handler(
        CommandHandler("memory_reject_proposal", memory_reject_proposal_command)
    )
    application.add_handler(CommandHandler("memory_proposal", memory_proposal_command))
    application.add_handler(CommandHandler("memory_proposals", memory_proposals_command))
    application.add_handler(CommandHandler("memory_profiles", memory_profiles_command))
    application.add_handler(CommandHandler("memory_status", memory_status_command))
    application.add_handler(CommandHandler("send_weather_report", send_weather_report_command))
    application.add_handler(CommandHandler("report_status", report_status_command))
    application.add_handler(CommandHandler("send_source_artifact", send_source_artifact_command))
    application.add_handler(CommandHandler("workflow_artifacts", workflow_artifacts_command))
    application.add_handler(CommandHandler("workflow_list", workflow_list_command))
    application.add_handler(CommandHandler("workflow_run", workflow_run_command))
    application.add_handler(CommandHandler("workflow_confirm", workflow_confirm_command))
    application.add_handler(
        CommandHandler("workflow_send_artifact", workflow_send_artifact_command)
    )
    application.add_handler(CommandHandler("workflow_status", workflow_status_command))
    application.add_handler(CommandHandler("llm_status", llm_status_command))
    application.add_handler(CommandHandler("chat_start", chat_start_command))
    application.add_handler(CommandHandler("chat_status", chat_status_command))
    application.add_handler(CommandHandler("chat_clear", chat_clear_command))
    application.add_handler(CommandHandler("chat_context", chat_context_command))
    application.add_handler(CommandHandler("chat_profiles", chat_profiles_command))
    application.add_handler(CommandHandler("chat_stop", chat_stop_command))
    application.add_handler(CommandHandler("logs", logs_command))
    application.add_handler(CommandHandler("tail", tail_command))
    application.add_handler(CommandHandler("help", help_command))

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, chat_text_message)
    )

    # This must remain after all known command handlers.
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    return application


def run_foreground_bot(config: MarcBotConfig) -> None:
    """Run the Telegram bot in foreground polling mode."""
    application = build_application(config)
    LOGGER.info("Starting Telegram polling bot")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
