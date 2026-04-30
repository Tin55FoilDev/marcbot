# MarcBot Design

## Purpose

MarcBot is a small, stable personal automation bot. It favors explicit commands, ordinary Linux services, readable logs, and simple recovery over large agent-framework complexity.

## Phase 1 Scope

- Run as a systemd service.
- Respond to basic Telegram commands.
- Maintain clear logs.
- Send cron-triggered test notifications.
- Avoid LLM calls until the transport layer is stable.

## Non-Goals for Phase 1

- No arbitrary shell execution from chat.
- No autonomous multi-agent behavior.
- No vector memory.
- No browser automation.
- No OpenClaw clone.
