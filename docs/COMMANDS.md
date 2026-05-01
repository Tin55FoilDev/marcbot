# MarcBot Telegram Commands

This document lists the currently supported MarcBot Telegram commands.

MarcBot is personal-only. All commands are intended for Marc's approved Telegram chat only.

## Current command set

### `/ping`

Checks whether MarcBot is responding.

Expected output:

    🤖 MarcBot pong

### `/version`

Shows the MarcBot version, Python version, and Python executable path.

Useful for confirming which runtime is serving Telegram.

### `/uptime`

Shows host uptime and MarcBot process uptime.

Useful after server reboots, service restarts, or maintenance.

Data sources:

- Host uptime: `/proc/uptime`
- Process uptime: MarcBot process start timestamp

### `/disk`

Shows disk usage for:

- Root filesystem
- `/srv/marcbot`

This command uses Python standard-library disk usage helpers. It does not execute shell commands.

### `/service`

Shows read-only systemd state for:

- `marcbot-telegram.service`

Current checks:

- `systemctl is-active marcbot-telegram.service`
- `systemctl is-enabled marcbot-telegram.service`

This command is intentionally read-only. It does not start, stop, restart, enable, or disable services.

### `/git`

Shows the Git state of the MarcBot application repository.

Current checks:

- Repository path
- Current branch
- Current short commit hash
- Clean or dirty working tree state

The command is fixed to `/srv/marcbot/app`. It does not accept arbitrary repository paths or arbitrary Git arguments.

### `/docs`

Lists approved MarcBot documentation names.

The list is generated from MarcBot's documentation allowlist.

### `/doc <name>`

Shows one approved MarcBot Markdown document through Telegram.

Current approved names:

- `deploy`
- `roadmap`
- `security`
- `architecture`
- `changelog`
- `commands`

Safety properties:

- Approved document names only
- No arbitrary paths
- No shell execution
- Bounded Telegram output
- Friendly error for unknown names

### `/senddoc <name>`

Sends one approved MarcBot Markdown document as a Telegram file attachment.

Current approved names:

- `deploy`
- `roadmap`
- `security`
- `architecture`
- `changelog`
- `commands`

This is the full-file counterpart to `/doc <name>`.

Safety properties:

- Approved document names only
- No arbitrary paths
- No shell execution
- File must remain under the approved docs directory
- File must be a regular file
- File size limit enforced
- Request is logged

### `/send <workspace-relative-path>`

Sends a file from the MarcBot workspace as a Telegram file attachment.

Workspace root:

    /srv/marcbot/workspace

Example:

    /send reports/send-test.txt

This resolves internally to:

    /srv/marcbot/workspace/reports/send-test.txt

Safety properties:

- Workspace-relative paths only
- Absolute paths rejected
- Parent-directory traversal rejected
- Resolved path must remain under `/srv/marcbot/workspace`
- Non-regular files rejected
- File size limit enforced
- Request is logged

Rejected examples:

    /send /etc/passwd
    /send ../config/marcbot.toml
    /send ../../home/marc/.ssh/id_ed25519
    /send /srv/marcbot/config/marcbot.toml

### `/status`


Shows basic MarcBot service status from the bot's perspective.

This is a lightweight status command and is separate from `/service`.

### `/backup_status`

Shows read-only status for the latest MarcBot app-level backup.

Reads:

    /srv/marcbot/backups/latest-backup.txt

Reports:

- latest backup name
- created time
- backup size
- retention setting
- archive path
- checksum path
- archive presence
- checksum presence
- backup age
- overall health

This command does not create, delete, or modify backups.

Safety properties:

- Read-only
- Fixed marker file
- No arbitrary paths from Telegram
- No backup creation from Telegram
- No backup deletion from Telegram

### `/health`

Runs local MarcBot health checks.

Current checks include:

- Required runtime directories exist
- Logs directory is writable
- Config file loads

### `/tail <app|service>`

Shows a bounded diagnostic tail from an approved log source.

Approved names:

- `app`
- `service`

Examples:

    /tail app
    /tail service

Current behavior:

- `/tail app` reads the last 40 lines from `/srv/marcbot/logs/marcbot.log`
- `/tail service` reads the last 40 journal lines for `marcbot-telegram.service`

Safety properties:

- Approved tail names only
- No arbitrary file paths
- No arbitrary service names
- Bounded Telegram output
- Telegram token redaction
- Fixed `journalctl` command for service logs

### `/logs`

Shows recent MarcBot application logs from:

    /srv/marcbot/logs/marcbot.log

Safety properties:

- Fixed log file only
- Bounded output
- Telegram token redaction

### `/help`

Shows the Telegram command help text.

## Unknown commands

Unknown slash commands return a short help response instead of failing silently.

Example:

    /sendoc

Expected response:

    🤖 MarcBot
    Unknown command: /sendoc
    Use /help to see available commands.

## Safety model

MarcBot command design favors:

- Read-only commands first
- Fixed paths over user-supplied paths
- Allowlists over arbitrary access
- Bounded output
- Explicit error handling
- Tests for helper logic

## Future command candidates

Possible future commands:

- `/senddoc <name>` — send an approved doc as a Telegram file attachment
- `/send <workspace-relative-path>` — send a file from `/srv/marcbot/workspace`
- `/tail <approved-log-name>` — read from an allowlisted log file
- `/backup_status` — show last backup status
- `/update-check` — check for safe/manual update candidates

General `/send` should not accept arbitrary absolute paths.
