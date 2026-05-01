# MarcBot Architecture

MarcBot is a personal-only Telegram automation bot running on Ubuntu Server.

The architecture is intentionally simple. MarcBot should be easy to reason about, easy to back up, easy to restore, and difficult to misuse accidentally.

## High-level layout

Project root:

    /srv/marcbot

Application repository:

    /srv/marcbot/app

Local configuration:

    /srv/marcbot/config/marcbot.toml

Logs:

    /srv/marcbot/logs/marcbot.log

Workspace:

    /srv/marcbot/workspace

Service:

    marcbot-telegram.service

## Runtime model

MarcBot runs as a Python process under systemd.

The Telegram bot uses foreground polling mode.

The systemd service runs as the non-root user:

    marc

The service is intentionally narrow:

- no root execution
- no general shell access
- fixed application directory
- systemd hardening
- local config outside Git

## Main modules

### `marcbot.cli`

Command-line entry point.

Responsibilities:

- parse CLI arguments
- configure logging
- run doctor checks
- run config checks
- start Telegram foreground bot

### `marcbot.config`

Configuration loading and validation.

Responsibilities:

- read `/srv/marcbot/config/marcbot.toml`
- validate app settings
- validate Telegram settings
- require token when Telegram is enabled
- require explicit approved Telegram chat IDs

### `marcbot.errors`

Operator-facing MarcBot error type.

Expected MarcBot errors use codes like:

    ERROR [MBOT-CONFIG-001]: Missing config file: ...

The intent is to avoid raw tracebacks for expected operator errors.

### `marcbot.paths`

Central path definitions.

Important paths:

- `/srv/marcbot`
- `/srv/marcbot/app`
- `/srv/marcbot/state`
- `/srv/marcbot/workspace`
- `/srv/marcbot/logs`
- `/srv/marcbot/config`
- `/srv/marcbot/backups`
- `/srv/marcbot/tmp`

### `marcbot.logging_setup`

Rotating log configuration.

Current log file:

    /srv/marcbot/logs/marcbot.log

Current policy:

- rotate at 1 MB
- keep 5 backups

### `marcbot.backup_status`

Read-only app-level backup status helper.

Reads:

    /srv/marcbot/backups/latest-backup.txt

Validates:

- marker file exists
- required fields are present
- archive exists
- archive is non-empty
- checksum file exists
- backup age is within threshold

Safety properties:

- read-only
- fixed marker file
- no arbitrary paths from Telegram
- no backup creation from Telegram
- no deletion or rotation from Telegram

### `marcbot.health`

Local health checks.

Current checks:

- required runtime directories exist
- log directory is writable
- config file loads

### `marcbot.log_reader`

Safe reader for recent MarcBot application logs.

Safety properties:

- fixed log file
- bounded output
- Telegram token redaction

### `marcbot.uptime`

Host and process uptime helpers.

Data sources:

- host uptime from `/proc/uptime`
- process uptime from bot startup timestamp

### `marcbot.disk`

Disk usage helpers.

Data sources:

- Python standard-library disk usage calls

No shell execution is used.

### `marcbot.service_status`

Read-only systemd status helper.

Current fixed commands:

    systemctl is-active marcbot-telegram.service
    systemctl is-enabled marcbot-telegram.service

No start, stop, restart, enable, or disable action is exposed.

### `marcbot.git_status`

Read-only Git status helper.

Fixed repository:

    /srv/marcbot/app

Current fixed checks:

- branch
- short commit hash
- clean or dirty working tree

No arbitrary repository paths or arbitrary Git arguments are accepted from Telegram.

### `marcbot.docs_index`

Approved documentation allowlist and documentation reader.

Current approved docs:

- `deploy`
- `roadmap`
- `security`
- `architecture`
- `changelog`
- `commands`

Safety properties:

- approved names only
- no arbitrary paths
- bounded Telegram output
- friendly unknown-name response

### `marcbot.workspace_list`

Read-only workspace listing helper.

Current scope:

- lists only `/srv/marcbot/workspace`
- omits hidden dotfiles
- sorts directories before files
- reports file sizes
- bounds Telegram output

Safety properties:

- read-only
- no shell execution
- fixed workspace root
- no arbitrary paths in first implementation

### `marcbot.workspace_sender`

Safe workspace file-send validator.

Workspace root:

    /srv/marcbot/workspace

Safety properties:

- workspace-relative paths only
- rejects absolute paths
- rejects parent-directory traversal
- resolves the real path before sending
- verifies resolved path stays inside workspace
- rejects non-regular files
- enforces a file size limit

### `marcbot.tail_reader`

Approved diagnostic tail reader.

Current approved names:

- `app`
- `service`

Sources:

- `app`: `/srv/marcbot/logs/marcbot.log`
- `service`: fixed `journalctl` query for `marcbot-telegram.service`

Safety properties:

- approved names only
- no arbitrary paths
- no arbitrary service names
- bounded output
- token redaction
- fixed subprocess command for journal access

### `marcbot.telegram_bot`

Telegram command wiring.

Responsibilities:

- build Telegram application
- enforce approved chat IDs
- register command handlers
- route commands to helper modules
- reply with bounded operator-facing messages

## Telegram authorization model

MarcBot is personal-only.

Telegram access is controlled by:

    telegram.allowed_chat_ids

If the incoming chat ID is not approved, MarcBot returns:

    Unauthorized chat.

An empty allowlist authorizes no chats.

## Current Telegram commands

Current commands:

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
- `/backup_status`
- `/logs`
- `/tail <app|service>`
- `/help`

Command categories:

### Basic runtime

- `/ping`
- `/version`
- `/uptime`

### Operational state

- `/disk`
- `/service`
- `/git`
- `/status`
- `/health`

### Documentation

- `/docs`
- `/doc <name>`

### Diagnostics

- `/logs`
- `/tail <app|service>`
- `/help`

## Command safety pattern

MarcBot commands should follow this pattern:

1. Authenticate Telegram chat ID.
2. Accept no arguments unless necessary.
3. If arguments are needed, validate strictly.
4. Prefer allowlists over free-form input.
5. Prefer fixed paths over user-provided paths.
6. Bound Telegram output size.
7. Avoid shell execution.
8. If subprocess is needed, use fixed command arrays only.
9. Log the request at a useful but non-sensitive level.
10. Add tests for formatting and validation logic.

## File access model

MarcBot currently reads only:

- local config file
- fixed app log file
- approved docs
- fixed runtime paths for health checks
- Git repo state under `/srv/marcbot/app`

Future file sending should use one of two models:

### Approved-name file send

Example:

    /senddoc deploy

Maps an approved name to an exact file.

### Workspace-relative file send

Example:

    /send reports/latest.txt

Resolves internally under:

    /srv/marcbot/workspace

Safety requirements:

- reject absolute paths
- reject `..`
- resolve real path
- verify resolved path stays under `/srv/marcbot/workspace`
- reject non-regular files
- enforce max file size
- log every request

## systemd service design

Service file:

    /etc/systemd/system/marcbot-telegram.service

Expected service characteristics:

- runs as user `marc`
- working directory `/srv/marcbot/app`
- starts `python -m marcbot telegram`
- restarts on failure
- uses local venv Python
- includes systemd hardening

The service should remain simple and inspectable.

## Testing model

Primary validation command:

    ./scripts/check.sh

Current validation includes:

- MarcBot version check
- doctor check
- pytest
- Ruff

Feature development should not be considered complete until:

- checks pass
- service restarts cleanly
- Telegram command works
- logs are clean
- Git commit is pushed
- `/git` returns clean

## Documentation model

MarcBot documentation is part of the product.

Important docs:

- `DEPLOY.md`
- `ROADMAP.md`
- `SECURITY.md`
- `ARCHITECTURE.md`
- `CHANGELOG.md`
- `COMMANDS.md`

Docs are readable through Telegram using:

    /docs
    /doc <name>

This means docs should stay accurate when commands or operational procedures change.

## Future architecture notes

Likely future helper modules:

- `marcbot.file_sender`
- `marcbot.tail_reader`
- `marcbot.backup_status`
- `marcbot.update_check`

Each should follow the same pattern:

- narrow responsibility
- fixed roots or allowlists
- no arbitrary shell
- explicit errors
- tests before Telegram wiring

## App-level backup architecture

MarcBot uses a split backup design:

- backup creation is handled by a fixed shell script and systemd timer
- backup visibility is handled by the read-only `/backup_status` Telegram command

Backup creation path:

    marcbot-backup.timer
        -> marcbot-backup.service
            -> /srv/marcbot/app/scripts/backup_marcbot.sh
                -> /srv/marcbot/backups/*.tar.gz
                -> /srv/marcbot/backups/*.sha256
                -> /srv/marcbot/backups/latest-backup.txt

Safety model:

- Telegram cannot trigger backup creation
- Telegram cannot delete backups
- `/backup_status` only reads fixed marker/artifact paths
- service runs as user `marc`
- service has systemd hardening enabled
- `/srv/marcbot` is the only writable tree exposed to the service

