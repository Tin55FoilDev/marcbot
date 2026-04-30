#!/usr/bin/env python3
"""Print recent Telegram updates to help identify MarcBot allowed chat IDs."""

from __future__ import annotations

import asyncio
import sys

from telegram import Bot

from marcbot.config import load_config
from marcbot.errors import MarcBotError


async def main() -> int:
    try:
        config = load_config()
        token = config.telegram.bot_token.strip()
        if not token:
            raise MarcBotError("MBOT-TELEGRAM-004", "Telegram bot token is empty")

        bot = Bot(token=token)
        updates = await bot.get_updates(timeout=10)

        if not updates:
            print("No updates found.")
            print("Send /ping to your bot in Telegram, then run this script again.")
            return 0

        for update in updates:
            chat = update.effective_chat
            user = update.effective_user
            message = update.effective_message

            print("---")
            print(f"update_id: {update.update_id}")
            if chat is not None:
                print(f"chat_id: {chat.id}")
                print(f"chat_type: {chat.type}")
                print(f"chat_title: {chat.title}")
            if user is not None:
                print(f"user_id: {user.id}")
                print(f"username: {user.username}")
                print(f"first_name: {user.first_name}")
            if message is not None:
                print(f"text: {message.text}")

        return 0

    except MarcBotError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
