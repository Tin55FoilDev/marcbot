# Changelog

## 2026-04-30 — Roadmap and architecture refresh

Updated documentation to match the current MarcBot command baseline.

Changed docs:

- `ROADMAP.md`
- `ARCHITECTURE.md`

Highlights:

- documented current Telegram command set
- documented completed phases
- documented near-term roadmap
- documented helper-module architecture
- documented command safety pattern
- documented future safe file-send model

## 2026-04-30 — Telegram operator command baseline

Added and validated the current MarcBot Telegram operator command set:

- `/ping`
- `/version`
- `/uptime`
- `/disk`
- `/service`
- `/git`
- `/docs`
- `/doc <name>`
- `/status`
- `/health`
- `/logs`
- `/help`

Documentation updates:

- Added `COMMANDS.md`
- Added `commands` to the approved `/docs` and `/doc <name>` allowlist
- Updated tests for the expanded documentation index

Safety notes:

- Commands remain personal-only through Telegram chat allowlisting
- `/doc <name>` uses an approved documentation allowlist
- `/git` is fixed to `/srv/marcbot/app`
- `/service` uses fixed read-only `systemctl` queries
- `/disk` uses Python standard-library disk usage helpers
- `/logs` uses fixed log-path reading with token redaction


## 2026-04-30 — Telegram operator command baseline

Added and validated the current MarcBot Telegram operator command set:

- `/ping`
- `/version`
- `/uptime`
- `/disk`
- `/service`
- `/git`
- `/docs`
- `/doc <name>`
- `/status`
- `/health`
- `/logs`
- `/help`

Documentation updates:

- Added `COMMANDS.md`
- Added `commands` to the approved `/docs` and `/doc <name>` allowlist
- Updated tests for the expanded documentation index

Safety notes:

- Commands remain personal-only through Telegram chat allowlisting
- `/doc <name>` uses an approved documentation allowlist
- `/git` is fixed to `/srv/marcbot/app`
- `/service` uses fixed read-only `systemctl` queries
- `/disk` uses Python standard-library disk usage helpers
- `/logs` uses fixed log-path reading with token redaction


# MarcBot Changelog

This changelog records human-readable MarcBot milestones.

It is not intended to list every Git commit. Git already does that. This file captures meaningful project checkpoints, operational changes, and feature additions.

## 2026-04-30

### Project foundation created

Completed the initial MarcBot project skeleton.

Included:

- `/srv/marcbot` runtime layout
- `/srv/marcbot/app` Git repository
- Python package structure
- Virtual environment
- Initial CLI entry point
- Basic project documentation
- GitHub remote

### Runtime paths established

Established the core runtime directories:

- `/srv/marcbot/config`
- `/srv/marcbot/logs`
- `/srv/marcbot/state`
- `/srv/marcbot/workspace`
- `/srv/marcbot/backups`
- `/srv/marcbot/tmp`

### Config system added

Added local TOML configuration loading.

Config file:

- `/srv/marcbot/config/marcbot.toml`

Important behavior:

- Config lives outside Git.
- Telegram token is not committed.
- Missing or invalid config returns clean MarcBot errors.
- Config validation is available through `python -m marcbot config-check`.

### Validation foundation added

Added standard validation flow through:

- `scripts/check.sh`

Current validation includes:

- MarcBot version command
- MarcBot doctor command
- pytest
- Ruff linting

### Telegram bot added

Added Telegram bot integration using `python-telegram-bot`.

Added foreground Telegram polling mode through:

- `python -m marcbot telegram`

Added systemd service:

- `marcbot-telegram.service`

Current service behavior:

- Runs as user `marc`
- Uses `/srv/marcbot/app/.venv/bin/python`
- Starts `python -m marcbot telegram`
- Runs as a managed systemd service

### Telegram authorization added

Added Telegram chat authorization using configured allowed chat IDs.

Important behavior:

- If `allowed_chat_ids` is empty, no chats are authorized.
- Unauthorized chats receive only `Unauthorized chat.`
- Unauthorized attempts are logged.

### Telegram baseline commands added

Added the initial Telegram command set:

- `/ping`
- `/status`
- `/health`
- `/logs`
- `/help`

Later added:

- `/version`

### Health checks added

Added local health checks through:

- `marcbot/health.py`
- Telegram `/health`

Current health checks:

- Required runtime directories exist
- Log directory is writable
- Config file loads

### File logging added

Added MarcBot application file logging.

Current log file:

- `/srv/marcbot/logs/marcbot.log`

Logging is configured at CLI startup.

### Rotating logging added

Changed logging to use rotating file logs.

Current policy:

- 1 MB per log file
- 5 backup files

### Safe Telegram `/logs` command added

Added `/logs` command to show recent MarcBot application logs from Telegram.

Safety properties:

- Reads only `/srv/marcbot/logs/marcbot.log`
- Uses fixed line count
- Redacts Telegram-token-shaped values
- Redacts the configured Telegram bot token
- Truncates long output
- Does not accept arbitrary file paths

### Token redaction improved

After testing `/logs`, redaction was strengthened to handle Telegram API URL patterns and configured token replacement.

The affected local log was cleared after the fix.

Recommendation remains:

- Rotate BotFather token later if strict security cleanup is desired.

### `/version` command added

Added Telegram `/version`.

Current output includes:

- MarcBot version
- Python version
- Python executable path

This provides a fast deploy/restore sanity check from Telegram.

### Deployment runbook added

Added:

- `docs/DEPLOY.md`

The deploy runbook documents:

- Current paths
- Service management
- Logs
- Validation
- Git workflow
- Pull/update procedure
- Restore checklist
- Current operational standard

### Roadmap added

Added:

- `docs/ROADMAP.md`

The roadmap documents:

- Guiding principles
- Completed baseline
- Planned phases
- Candidate future Telegram commands
- Scheduled report direction
- Memory direction
- Model/backend direction
- Update mechanism direction

### Security notes added

Added:

- `docs/SECURITY.md`

The security notes document:

- Current trust model
- Telegram authorization
- Token handling
- Git safety
- Runtime layout
- Systemd hardening
- Logging safety
- Command safety rules
- Confirmation policy for future risky actions
- Incident checklist
- Stop conditions

### Architecture notes added

Added:

- `docs/ARCHITECTURE.md`

The architecture notes document:

- High-level system design
- Runtime layout
- Repository layout
- Python modules
- Service flow
- Telegram command flow
- Config flow
- Logging flow
- Test architecture
- Extension points
- Future model and memory directions

## Current baseline after 2026-04-30 work

MarcBot now has:

- Working Telegram service
- Protected local config
- Authorized Telegram command handling
- Rotating file logging
- Safe Telegram log viewing
- Health checks
- Version reporting
- Tests and linting
- Deployment documentation
- Roadmap documentation
- Security documentation
- Architecture documentation
- GitHub commit/push workflow

Current Telegram commands:

- `/ping`
- `/version`
- `/status`
- `/health`
- `/logs`
- `/help`

## Next planned work

Likely next items:

1. Add `/uptime`
2. Add `/disk`
3. Add `/service`
4. Add `/git`
5. Add `/docs`
6. Add safe document reading
7. Add first scheduled report
8. Add VM backup checkpoint after current baseline
