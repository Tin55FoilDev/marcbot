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

Restore drill access:

    /doc restore
    /senddoc restore

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

### `/ls [workspace-relative-directory]`

Lists visible entries under the MarcBot workspace.

Examples:

    /ls
    /ls reports
    /ls reports/health

Workspace root:

    /srv/marcbot/workspace

Reports:

- directories
- files
- basic file sizes

Safety properties:

- Read-only
- Workspace-relative directories only
- Absolute paths are rejected
- Parent traversal is rejected
- Resolved paths must stay under the workspace
- Hidden dotfiles are omitted
- Output is bounded for Telegram
- No shell execution

Use `/send <workspace-relative-path>` to send one of the listed files.

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

### `/backup_list`

Lists recent MarcBot app-level backup archives.

Reports:

- newest retained backup archives
- archive size
- modified time
- backup age
- whether the matching `.sha256` file is present
- overall health or warning state

This command is read-only. It does not create, delete, rotate, restore, or verify backups.

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

Backup creation is handled separately by `marcbot-backup.timer`.

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

### `/timer_status`

Shows read-only status for MarcBot's approved scheduled timers.

Current approved timers:

- `marcbot-backup.timer`
- `marcbot-daily-status-report.timer`

Reports:

- timer enablement state
- timer active/substate
- next scheduled run
- last timer trigger
- paired service result
- paired service exit status
- overall health or warning state

This command is read-only. It does not enable, disable, start, stop, or modify any timer.

### `/report_status source <project>`

Shows the newest local source monitor report summary for a validated source-monitor project.

For RSS sources, the output includes a compact `RSS latest items` section when RSS metadata is available in the newest local report.

This command is read-only:

- it reads only local report files;
- it does not fetch network sources;
- it does not fetch linked articles;
- it does not call an LLM;
- it remains bounded by the source-status character cap.

### `/report_status`

Shows the status of the latest local daily status report.

Reports:

- latest daily status report filename
- report path
- file size
- modified time
- report age
- `marcbot-daily-status-report.timer` enablement state
- overall health or warning state

This command is read-only. It does not generate a report, send a report, call an AI model, or modify systemd.

The report status command also supports source-monitor project summaries:

    /report_status source <project>

For the current AI source-monitor project:

    /report_status source ai

This reads the newest local source-monitor report and returns the compact summary section plus deterministic observations. It does not fetch sources, run web requests, parse articles, or call an LLM.

The generic report-status pattern should be preferred over one-off report commands.

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

## CLI-only source monitor commands

These commands are currently CLI-only and are not Telegram commands:

    python -m marcbot source-monitor config-check ai
    python -m marcbot source-monitor run ai

`config-check` validates `/srv/marcbot/config/source-projects/<project>/sources.toml` and reports the configured sources.

`run` writes a local source monitor Markdown report under `/srv/marcbot/workspace/source-projects/<project>/reports`.

The real source config is local operational config and should not be committed to Git. A safe example may live under `docs/examples/`.

Do not add one-off Telegram commands for each source monitor project. Use the generic report command pattern instead, for example `/report_status source ai`.

## Future command candidates

Possible future commands:

- `/senddoc <name>` — send an approved doc as a Telegram file attachment
- `/send <workspace-relative-path>` — send a file from `/srv/marcbot/workspace`
- `/tail <approved-log-name>` — read from an allowlisted log file
- `/backup_status` — show last backup status
- `/update-check` — check for safe/manual update candidates

General `/send` should not accept arbitrary absolute paths.

## Scheduled daily status report

The report is local-only at this stage. It does not call an AI model or send Telegram messages.

The daily status report is scheduled by systemd:

    marcbot-daily-status-report.timer

Schedule:

    11:45 PM America/New_York

Manual run:

    sudo systemctl start marcbot-daily-status-report.service

Timer check:

    sudo systemctl status marcbot-daily-status-report.timer --no-pager
    sudo systemctl list-timers --all | grep -E 'marcbot-daily-status-report|NEXT'

## Source monitor scheduled report generation

The AI source monitor is designed to run from a systemd timer:

    marcbot-source-monitor-ai.timer
    marcbot-source-monitor-ai.service

The timer runs local report generation only:

    python -m marcbot source-monitor run ai

Telegram access remains read-only through:

    /report_status source ai

The timer is visible through:

    /timer_status

## CLI-only LLM commands

Current LLM commands are CLI-only and are documented in `docs/LLM.md`.

~~bash
python -m marcbot llm profiles
python -m marcbot llm profile local_fast
python -m marcbot llm models lmstudio
python -m marcbot llm health local_fast
python -m marcbot llm ask local_fast "Say OK in one sentence."
python -m marcbot llm tasks
python -m marcbot llm task report_summary
~~

There are no Telegram LLM prompt commands yet.

### `/llm_status`

Shows read-only LLM provider/profile status.

Current behavior:

- Lists configured LLM profiles.
- Runs the tiny `local_fast` health check.
- Reads the local LLM env file from `/srv/marcbot/config/llm.env`.
- Does not accept arbitrary prompts.
- Does not expose tokens.
- Does not allow arbitrary provider or model selection.
