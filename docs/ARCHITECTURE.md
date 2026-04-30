# MarcBot Architecture

This document describes the current MarcBot architecture and the intended direction for future extensions.

MarcBot is a personal-only Telegram automation bot. The design favors simple Python modules, explicit configuration, narrow Telegram commands, systemd service management, and easy restore/debug workflows.

## High-level design

Current MarcBot has four main layers:

1. Service layer
   - systemd runs MarcBot as a long-lived Telegram polling service.

2. CLI/application layer
   - `python -m marcbot` provides command entry points.

3. Telegram command layer
   - Telegram commands are handled by `python-telegram-bot`.

4. Support modules
   - Config loading
   - Health checks
   - Log setup
   - Safe log reading
   - Filesystem path definitions
   - Structured MarcBot errors

The current system is intentionally small. There is no web server, database, message queue, remote shell, or model backend in the baseline.

## Runtime layout

MarcBot runtime root:

    /srv/marcbot

Application repository:

    /srv/marcbot/app

Important runtime directories:

    /srv/marcbot/config
    /srv/marcbot/logs
    /srv/marcbot/state
    /srv/marcbot/workspace
    /srv/marcbot/backups
    /srv/marcbot/tmp

Current local config:

    /srv/marcbot/config/marcbot.toml

Current application log:

    /srv/marcbot/logs/marcbot.log

## Repository layout

Current repository root:

    /srv/marcbot/app

Important repository paths:

    marcbot/
    scripts/
    systemd/
    tests/
    docs/
    requirements.txt
    requirements-dev.txt
    pyproject.toml
    README.md

## Current Python modules

### `marcbot/__init__.py`

Defines package metadata, including:

    __version__

This is used by CLI output and Telegram `/version` and `/status`.

### `marcbot/__main__.py`

Allows MarcBot to run as:

    python -m marcbot

It delegates to:

    marcbot.cli.main

### `marcbot/cli.py`

Main command-line entry point.

Current CLI responsibilities:

- Configure logging
- Parse CLI arguments
- Run `--version`
- Run `doctor`
- Run `config-check`
- Run `telegram`
- Catch expected `MarcBotError` exceptions
- Return clean exit codes

Current CLI commands:

    python -m marcbot --version
    python -m marcbot doctor
    python -m marcbot config-check
    python -m marcbot telegram

### `marcbot/config.py`

Loads and validates local TOML configuration.

Current config file:

    /srv/marcbot/config/marcbot.toml

Current config sections:

    [app]
    [telegram]

Current dataclasses:

- `AppConfig`
- `TelegramConfig`
- `MarcBotConfig`

Expected behavior:

- Missing config produces a clean MarcBot error.
- Invalid TOML produces a clean MarcBot error.
- Telegram enabled with no token fails validation.
- `allowed_chat_ids` must be a list of integers.

### `marcbot/errors.py`

Defines expected MarcBot error behavior.

Current main type:

    MarcBotError

Error string format:

    ERROR [MBOT-CATEGORY-001]: Human-readable message

Expected errors should be shown cleanly without normal Python tracebacks in operator-facing output.

### `marcbot/paths.py`

Defines important filesystem paths.

Current path constants include:

- `PROJECT_ROOT`
- `APP_DIR`
- `STATE_DIR`
- `WORKSPACE_DIR`
- `LOG_DIR`
- `CONFIG_DIR`
- `BACKUP_DIR`
- `TMP_DIR`

Also provides:

    missing_runtime_dirs()

This supports `doctor` and `/health`.

### `marcbot/logging_setup.py`

Configures rotating file logging.

Current log file:

    /srv/marcbot/logs/marcbot.log

Current rotation policy:

- 1 MB per active log
- 5 backup logs

Logging is configured by the CLI at process startup.

### `marcbot/log_reader.py`

Provides safe reading of recent MarcBot logs for Telegram `/logs`.

Current safety properties:

- Reads only the fixed MarcBot application log
- Uses a fixed line count by default
- Redacts obvious Telegram-token-shaped strings
- Redacts the configured Telegram bot token if present
- Truncates long output before Telegram send

This module should remain narrow. It should not become a general file reader.

### `marcbot/health.py`

Provides local health checks.

Current checks:

- Required runtime directories exist
- Log directory is writable
- Config file loads

Current Telegram command:

    /health

Current output shape:

    🤖 MarcBot health
    OK: required runtime directories found
    OK: logs directory writable
    OK: config loads
    Overall: healthy

### `marcbot/telegram_bot.py`

Builds and runs the Telegram bot.

Current responsibilities:

- Validate Telegram config before startup
- Build `python-telegram-bot` Application
- Store allowed chat IDs in application bot data
- Store app environment in application bot data
- Register command handlers
- Enforce chat authorization on each command
- Log command handling
- Return short Telegram responses

Current Telegram commands:

    /ping
    /version
    /status
    /health
    /logs
    /help

All current Telegram commands are fixed, narrow, and read-only.

## Service architecture

MarcBot runs as a systemd service:

    marcbot-telegram.service

Primary unit file:

    /etc/systemd/system/marcbot-telegram.service

Repository copy:

    /srv/marcbot/app/systemd/marcbot-telegram.service

Expected service behavior:

- Run as user `marc`
- Working directory `/srv/marcbot/app`
- Start command uses the virtual environment Python
- Execute `python -m marcbot telegram`
- Restart on failure
- Apply basic systemd hardening

Conceptual service flow:

    systemd
      -> /srv/marcbot/app/.venv/bin/python -m marcbot telegram
      -> marcbot.__main__
      -> marcbot.cli.main
      -> configure_logging()
      -> load_config()
      -> run_foreground_bot()
      -> Telegram polling loop

## Telegram command flow

Typical command flow:

    Telegram user sends command
      -> Telegram API
      -> python-telegram-bot polling receives Update
      -> registered command handler runs
      -> handler extracts chat ID
      -> handler checks allowed_chat_ids
      -> unauthorized users receive "Unauthorized chat."
      -> authorized command executes fixed logic
      -> response sent to Telegram
      -> action logged to marcbot.log

Example `/health` flow:

    /health
      -> health_command()
      -> is_authorized_chat()
      -> run_health_checks()
      -> format_health_report()
      -> reply_text()

Example `/logs` flow:

    /logs
      -> logs_command()
      -> is_authorized_chat()
      -> read_last_log_lines()
      -> redact_sensitive_text()
      -> format_logs_message()
      -> reply_text()

## Config flow

Config lives outside Git:

    /srv/marcbot/config/marcbot.toml

Startup config flow:

    CLI starts
      -> load_config()
      -> parse TOML
      -> validate [app]
      -> validate [telegram]
      -> build MarcBotConfig dataclass
      -> pass config to Telegram app builder

The config file should be readable only by `marc`.

Expected permission:

    marc:marc 600 /srv/marcbot/config/marcbot.toml

## Logging flow

Logging is initialized in:

    marcbot.cli.main

Log setup function:

    configure_logging()

Current logging destination:

    /srv/marcbot/logs/marcbot.log

Current handler:

    RotatingFileHandler

Current format:

    timestamp level logger_name: message

Examples of logged events:

- CLI command startup
- Telegram polling startup
- Handled command
- Unauthorized command attempt
- Expected MarcBot command failure

## Test architecture

Tests live in:

    /srv/marcbot/app/tests

Current validation script:

    /srv/marcbot/app/scripts/check.sh

Current validation flow:

    python -m marcbot --version
    python -m marcbot doctor
    pytest -q
    ruff check .

The test suite should stay fast and runnable on every small change.

## Dependency architecture

Runtime dependencies:

    python-telegram-bot

Development dependencies:

    pytest
    ruff

Dependencies are intentionally limited.

Future dependencies should be added only when they clearly reduce complexity or risk.

## Data ownership

Current ownership model:

- Application code is owned by `marc`.
- Runtime files are owned by `marc`.
- Systemd management is performed by `adminuser` with sudo.
- MarcBot service runs as `marc`.

Important practical note:

Because `/srv/marcbot` is owned by `marc`, many inspection commands should be run as:

    sudo -u marc <command>

Example:

    sudo -u marc tail -n 80 /srv/marcbot/logs/marcbot.log

## Current boundaries

MarcBot currently does not include:

- Arbitrary shell execution
- Arbitrary file reading
- Arbitrary file writing from Telegram
- Model calls
- Web browsing
- Email sending
- Scheduled jobs
- Database storage
- Memory subsystem
- Multi-user support
- Web UI

These boundaries are intentional.

## Extension points

Future features should plug into the existing architecture using small modules.

Preferred pattern for a new feature:

1. Create a focused module under `marcbot/`.
2. Add tests under `tests/`.
3. Add a narrow Telegram command handler if needed.
4. Register the handler in `telegram_bot.py`.
5. Update `/help`.
6. Run `./scripts/check.sh`.
7. Restart service and test in Telegram.
8. Update docs if behavior changes.

Examples:

- `marcbot/system_status.py` for `/uptime`, `/disk`, `/memory`
- `marcbot/git_status.py` for `/git`
- `marcbot/doc_reader.py` for `/docs` and approved doc access
- `marcbot/reports.py` for scheduled report helpers
- `marcbot/memory.py` for future Markdown memory support

## Future command routing direction

The current `telegram_bot.py` file directly defines all command handlers.

This is acceptable for the current small command set.

If command count grows, consider refactoring to:

- Keep authorization helpers in one module
- Keep command handlers grouped by domain
- Keep registration explicit
- Avoid dynamic loading or plugin magic

Possible future layout:

    marcbot/telegram/
      __init__.py
      auth.py
      commands_basic.py
      commands_health.py
      commands_logs.py
      registry.py

Do not refactor early. Wait until the file becomes difficult to maintain.

## Future scheduled job direction

Scheduled jobs should probably use systemd timers or cron rather than being hidden inside the Telegram polling process.

Preferred direction:

    systemd timer or cron
      -> explicit script or CLI command
      -> write output to workspace/reports
      -> send Telegram notification through a narrow helper

Reasons:

- Easier to inspect
- Easier to retry manually
- Easier to log
- Easier to disable
- Keeps Telegram service simple

## Future model integration direction

Model calls are intentionally absent from the current baseline.

If added later, use a small provider abstraction.

Possible future flow:

    Telegram command or scheduled report
      -> model provider wrapper
      -> configured endpoint
      -> timeout/error handling
      -> bounded response
      -> log success/failure without logging secrets

Model config should live outside Git.

Non-model commands should continue working if the model backend is down.

## Future memory direction

Memory should start as Markdown files before adding search indexes or databases.

Possible future layout:

    /srv/marcbot/workspace/memory/daily/YYYY-MM-DD.md
    /srv/marcbot/workspace/memory/MEMORY.md
    /srv/marcbot/workspace/memory/INDEX.md

Possible future commands:

    /note
    /memory

Memory should remain inspectable and editable.

## Architecture rules

When adding features:

1. Keep modules small.
2. Keep command scope narrow.
3. Prefer explicit allowlists.
4. Avoid arbitrary shell input.
5. Avoid arbitrary path input.
6. Keep logs useful but safe.
7. Keep tests fast.
8. Keep service startup simple.
9. Keep config outside Git.
10. Update documentation when behavior changes.

## Current design summary

MarcBot is currently a small, systemd-managed Python Telegram bot with:

- Local TOML configuration
- Rotating file logs
- Narrow authorized Telegram commands
- Basic health checks
- Safe recent-log display
- Strong documentation and validation workflow

The architecture is intentionally conservative so that future automation can be added without losing reliability, auditability, or recoverability.
