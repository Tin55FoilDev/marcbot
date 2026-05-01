# MarcBot

MarcBot is a small personal automation bot intended to replace the reliable subset of OpenClaw used by Marc.

Initial goals:

- Telegram command gateway
- systemd-managed service
- cron-triggered notifications
- safe named actions
- local workspace management
- optional LLM routing later
- project scaffolding for reports and small web games

## Current baseline

MarcBot 0.2.0 is the first stable personal-operations baseline.

Core capabilities:

- Telegram command interface with allowlisted chat authorization
- read-only health and service diagnostics
- allowlisted project documentation access
- safe workspace listing and file retrieval
- app-level backup script and daily systemd backup timer
- read-only backup status reporting
- GitHub-backed source workflow

MarcBot intentionally avoids arbitrary shell execution from Telegram.

