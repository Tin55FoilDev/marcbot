## 2026-05-01 — Source monitor systemd templates tracked

Added Git-tracked systemd templates and recovery documentation for the AI source monitor timer.

- Added `systemd/marcbot-source-monitor-ai.service`.
- Added `systemd/marcbot-source-monitor-ai.timer`.
- Documented install, comparison, and restore steps.
- Clarified that local source config remains outside Git.

## 0.3.0 — Source monitor baseline

MarcBot 0.3.0 is the source monitor baseline.

Highlights:

- Added project-scoped source monitor configuration.
- Added bounded allowlisted HTTPS source fetch metadata.
- Added HTML page-title extraction.
- Added metadata-only state tracking with new/changed/unchanged classification.
- Added compact source-monitor summary counts.
- Added generic Telegram report access through `/report_status source ai`.
- Added scheduled local AI source-monitor report generation through `marcbot-source-monitor-ai.timer`.
- Refreshed source-monitor documentation and deployment notes.

## 2026-05-01 — Source monitor documentation refreshed

Updated project documentation after source-monitor report access and timer work.

- Clarified that `/report_status source ai` is the supported Telegram read-only path.
- Removed stale guidance implying Telegram source-monitor access was still future work.
- Added architecture notes for source project config, reports, and metadata state.
- Added deploy notes for `marcbot-source-monitor-ai.service` and `marcbot-source-monitor-ai.timer`.
- Strengthened source-monitor safety notes.

## 2026-05-01 — AI source monitor timer visibility added

Prepared MarcBot for scheduled local AI source monitor report generation.

- Added `marcbot-source-monitor-ai.timer` to approved `/timer_status` visibility.
- Documented the source monitor systemd service/timer pattern.
- The scheduled run writes local reports only.
- Telegram remains read-only through `/report_status source ai`.

## 2026-05-01 — Source monitor report status added

Extended the generic `/report_status` command for source monitor visibility.

- `/report_status` keeps its existing daily status report behavior.
- `/report_status source ai` reads the newest local AI source monitor report.
- The source-monitor status response returns only the compact summary section and report path.
- It does not perform network fetches or call an LLM.

# Changelog

## 0.2.1 — Scheduled reporting baseline

MarcBot 0.2.1 is the scheduled reporting baseline.

This release includes:

- `/backup_list`
- `/send_latest_report`
- `python -m marcbot report send-latest`
- scheduled Telegram delivery of the latest daily status report
- expanded `/timer_status` coverage for the report-delivery timer
- documentation updates for the reporting and delivery flow

The reporting chain is now:

    23:30 America/New_York — app-level backup
    23:45 America/New_York — daily status report generation
    23:50 America/New_York — latest report Telegram delivery

## 2026-05-01 — Scheduled report delivery timer added

Added dedicated systemd units for scheduled Telegram delivery of the latest daily status report.

New units:

- `marcbot-daily-status-report-send.service`
- `marcbot-daily-status-report-send.timer`

Schedule:

- `23:50 America/New_York`
- `Persistent=true`
- `RandomizedDelaySec=2m`

Behavior:

- sends the newest generated daily status report through Telegram
- does not generate a report
- does not call AI models
- keeps delivery separate from backup and report generation

## 2026-05-01 — CLI latest-report Telegram sender added

Added a manual CLI command to send the newest daily status report through Telegram.

New command:

    python -m marcbot report send-latest

Behavior:

- loads the local MarcBot config
- finds the newest generated daily status report
- sends it to configured Telegram allowed chat IDs
- prints a compact success or error message
- does not generate reports
- does not call AI models
- does not install timers

## 2026-05-01 — `/send_latest_report` command added

Added a user-triggered Telegram command to send the newest daily status report.

New command:

- `/send_latest_report`

Behavior:

- finds the newest `daily-status-*.md` file under `/srv/marcbot/workspace/reports`
- sends that report as a Telegram document
- reports a clean error if no report exists
- does not generate reports
- does not call AI models
- does not install timers
- does not automatically send reports

## 2026-05-01 — `/backup_list` command added

Added a read-only Telegram command for recent MarcBot app-level backups.

New command:

- `/backup_list`

Behavior:

- lists recent `marcbot-backup-*.tar.gz` archives
- shows size, modified time, age, and checksum-file presence
- reports healthy or warning state
- does not create, delete, rotate, restore, or verify backups

## 2026-05-01 — `/timer_status` command added

Added a read-only Telegram command for approved MarcBot systemd timers.

New command:

- `/timer_status`

Approved timers:

- `marcbot-backup.timer`
- `marcbot-daily-status-report.timer`

Behavior:

- shows timer enablement and active state
- shows next scheduled run and last timer trigger
- shows paired service result and exit status
- reports healthy or warning state
- does not enable, disable, start, stop, or modify timers

## 2026-05-01 — `/report_status` command added

Added a read-only Telegram status command for local daily reports.

New command:

- `/report_status`

Behavior:

- shows latest local daily status report filename, path, size, modified time, and age
- checks `marcbot-daily-status-report.timer` enablement
- reports healthy or warning state
- does not generate reports
- does not send Telegram files
- does not call AI models
- does not modify systemd

## 2026-05-01 — Daily status report timer added

Added systemd scheduling for the local daily status report.

New systemd units:

- `marcbot-daily-status-report.service`
- `marcbot-daily-status-report.timer`

Schedule:

- `11:45 PM America/New_York`

Behavior:

- runs `python -m marcbot report daily-status`
- writes a Markdown report to `/srv/marcbot/workspace/reports`
- does not call AI models
- does not send Telegram messages

## 2026-05-01 — Restore drill documentation added

Added restore readiness documentation.

New document:

- `docs/RESTORE.md`

Telegram access:

- `/doc restore`
- `/senddoc restore`

Coverage:

- recovery decision guide
- Proxmox VM restore
- MarcBot app-level tarball restore
- GitHub source restore
- systemd unit restore notes
- post-restore validation checklist
- backup verification after restore
- success criteria
- restore safety warnings

## 0.2.0 — First stable operational baseline

MarcBot now has a stable personal-operations baseline.

Highlights:

- Telegram command handling with allowlisted chat authorization
- `/ping`, `/version`, `/help`, `/status`, and `/health`
- read-only diagnostics:
  - `/uptime`
  - `/disk`
  - `/service`
  - `/git`
  - `/logs`
  - `/tail <app|service>`
- documentation access:
  - `/docs`
  - `/doc <name>`
  - `/senddoc <name>`
- safe workspace discovery and retrieval:
  - `/ls [workspace-relative-directory]`
  - `/send <workspace-relative-path>`
- app-level backup support:
  - manual backup script
  - daily systemd backup timer at 23:30 America/New_York
  - `/backup_status`
- GitHub-backed source workflow
- deployment, security, architecture, command, roadmap, and changelog documentation

Safety properties:

- no arbitrary shell execution from Telegram
- read-only operational commands by default
- workspace paths are constrained under `/srv/marcbot/workspace`
- documentation access is allowlisted
- backup status is read-only
- Telegram service runs as the non-sudo `marc` user
- systemd hardening enabled for runtime services

This release is the recommended restore/checkpoint baseline after the Proxmox backup.

## 2026-05-01 — `/ls` expanded to support workspace-relative directories

Expanded the safe workspace listing command.

Updated command:

- `/ls [workspace-relative-directory]`

Examples:

- `/ls`
- `/ls reports`
- `/ls reports/health`

Safety properties:

- read-only
- workspace-relative directories only
- absolute paths rejected
- parent traversal rejected
- resolved paths must stay under `/srv/marcbot/workspace`
- hidden dotfiles omitted
- bounded Telegram output
- no shell execution

## 2026-05-01 — Read-only `/ls` workspace listing added

Added initial safe workspace discovery.

New command:

- `/ls`

Scope:

- lists top-level entries under `/srv/marcbot/workspace`
- shows directories and files
- shows basic file sizes
- omits hidden dotfiles
- bounds Telegram output

This helps discover files before using `/send <workspace-relative-path>`.

Safety properties:

- read-only
- fixed workspace root
- no shell execution
- no arbitrary paths in first implementation

## 2026-05-01 — Read-only `/ls` workspace listing added

Added initial safe workspace discovery.

New command:

- `/ls`

Scope:

- lists top-level entries under `/srv/marcbot/workspace`
- shows directories and files
- shows basic file sizes
- omits hidden dotfiles
- bounds Telegram output

This helps discover files before using `/send <workspace-relative-path>`.

Safety properties:

- read-only
- fixed workspace root
- no shell execution
- no arbitrary paths in first implementation

## 2026-04-30 — Daily app-level backup timer added

Added systemd-based daily MarcBot app-level backup automation.

New units:

- `marcbot-backup.service`
- `marcbot-backup.timer`

Schedule:

- daily at 23:30 America/New_York America/New_York
- persistent timer
- randomized delay up to 5 minutes

Backup script:

- `/srv/marcbot/app/scripts/backup_marcbot.sh`

Output:

- `/srv/marcbot/backups/marcbot-backup-YYYYMMDD-HHMMSS.tar.gz`
- `/srv/marcbot/backups/marcbot-backup-YYYYMMDD-HHMMSS.tar.gz.sha256`
- `/srv/marcbot/backups/latest-backup.txt`

Telegram remains read-only for backups through `/backup_status`.

## 2026-04-30 — Read-only `/backup_status` command added

Added backup visibility for MarcBot app-level backups.

New command:

- `/backup_status`

Reads:

- `/srv/marcbot/backups/latest-backup.txt`

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

Safety properties:

- read-only
- fixed marker file
- no arbitrary paths from Telegram
- no backup creation from Telegram
- no backup deletion from Telegram

## 2026-04-30 — Approved `/tail` diagnostic command added

Added bounded diagnostic tail output for approved log sources.

New command:

- `/tail <app|service>`

Approved names:

- `app`
- `service`

Behavior:

- `/tail app` reads the fixed MarcBot application log
- `/tail service` reads the fixed MarcBot systemd service journal

Safety properties:

- approved tail names only
- no arbitrary file paths
- no arbitrary service names
- bounded Telegram output
- token redaction
- fixed `journalctl` command for service logs

## 2026-04-30 — Safe workspace `/send` command added

Added Telegram file sending for files under the MarcBot workspace.

New command:

- `/send <workspace-relative-path>`

Workspace root:

- `/srv/marcbot/workspace`

Safety properties:

- rejects absolute paths
- rejects parent-directory traversal
- resolves the path before sending
- verifies the resolved path remains under the workspace root
- rejects non-regular files
- enforces a file size limit
- logs each request
- does not allow arbitrary server path sending

## 2026-04-30 — Unknown command response added

Added a catch-all Telegram command handler for mistyped or unsupported slash commands.

Behavior:

- unknown slash commands no longer fail silently
- approved chats receive a short response pointing to `/help`
- unauthorized chats still receive only the generic unauthorized response
- handler is registered after all known command handlers

## 2026-04-30 — `/senddoc <name>` command added

Added Telegram file attachment support for approved MarcBot documentation.

New command:

- `/senddoc <name>`

Purpose:

- send the full approved Markdown doc as a Telegram file attachment
- complement `/doc <name>`, which remains a bounded preview command

Safety properties:

- uses the existing approved documentation allowlist
- rejects unknown names
- rejects paths outside the docs directory
- rejects non-file paths
- enforces a file size limit
- does not accept arbitrary file paths
- logs send requests

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
