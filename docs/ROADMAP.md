# MarcBot Roadmap

MarcBot is Marc's personal-only Telegram automation bot.

The project goal is to build a stable, simple, secure replacement for OpenClaw-style personal operations. Development favors careful incremental progress over speed.

## Design priorities

MarcBot should be:

- Personal-only
- Stable across server reboots
- Easy to inspect from Telegram
- Easy to back up and restore
- Small in dependency footprint
- Explicit in error handling
- Safe by default
- Well documented
- Testable before each deployment step

## Current baseline

MarcBot currently runs as a systemd service:

    marcbot-telegram.service

Application root:

    /srv/marcbot/app

Runtime root:

    /srv/marcbot

Git repository:

    /srv/marcbot/app

Current Telegram command set:

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

## Completed phases

### Phase 1 — Foundation

Completed:

- Project directory layout under `/srv/marcbot`
- Python package structure
- Virtual environment
- CLI entry point
- Runtime path helpers
- Configuration loader
- Explicit MarcBot error type
- Basic validation script
- Initial unit tests
- GitHub repository setup

### Phase 2 — Telegram service

Completed:

- Telegram bot integration
- Approved chat ID allowlist
- Foreground polling mode
- systemd service
- systemd hardening
- Service enable/start validation

### Phase 3 — Operator visibility

Completed:

- `/ping`
- `/version`
- `/status`
- `/health`
- `/logs`
- rotating application log file
- token redaction for log output

### Phase 4 — Read-only operations commands

Completed:

- `/uptime`
- `/disk`
- `/service`
- `/git`

These commands provide quick remote visibility into runtime, disk, service, and repository state.

### Phase 5 — Documentation from Telegram

Completed:

- `/docs`
- `/doc <name>`
- `COMMANDS.md`
- approved documentation allowlist

Current approved documentation names:

- `deploy`
- `roadmap`
- `security`
- `architecture`
- `changelog`
- `commands`

## Near-term roadmap

### 1. `/senddoc <name>`

Send an approved documentation file as a Telegram attachment.

Safety model:

- approved docs only
- no arbitrary paths
- no shell execution
- bounded file size
- log every send request

### 2. `/send <workspace-relative-path>`

Status: implemented.

Send a file from `/srv/marcbot/workspace`.

Safety model:

- workspace-relative paths only
- reject absolute paths
- reject `..`
- resolve real path and verify it remains under `/srv/marcbot/workspace`
- reject non-regular files
- reject oversized files
- log every send request

### 3. `/tail <approved-log-name>`

Status: implemented.

Show recent lines from approved logs.

Possible approved names:

- `app`
- `service`

Safety model:

- approved names only
- fixed file or command mapping
- bounded output
- redaction where appropriate

### 4. Backup visibility

Possible future command:

    /backup_status

Goal:

- show latest backup marker or report
- no backup execution at first
- read-only status only

### 5. Safe update helpers

Possible future commands:

- `/update-check`
- `/version-check`

Goal:

- check for update candidates
- report but do not auto-install
- keep operator in control

### Backup visibility

Status: implemented.

Current command:

    /backup_status

Purpose:

- report latest app-level backup metadata
- verify archive and checksum presence
- warn if backup is stale
- keep Telegram read-only for backup operations

### Workspace discovery

Status: expanded implementation.

Current command:

    /ls [workspace-relative-directory]

Purpose:

- list workspace entries
- make `/send <workspace-relative-path>` easier to use
- keep workspace browsing read-only and bounded

Future expansion:

- `/tree <workspace-relative-directory>`

## 0.2.0 baseline

Status: complete.

MarcBot 0.2.0 is the first stable operational baseline.

Completed baseline capabilities:

- Telegram command interface
- allowlisted chat authorization
- health and service diagnostics
- Git status visibility
- log and journal tails
- allowlisted documentation access
- safe workspace listing and file retrieval
- manual app-level backups
- daily systemd app-level backup timer
- read-only backup status reporting
- GitHub-backed source workflow

Recommended next phase:

- small read-only operator conveniences
- restore drill documentation
- scheduled report framework
- update-check visibility


## Restore readiness

Status: complete.

MarcBot includes a restore drill document:

    docs/RESTORE.md

Telegram access:

    /doc restore
    /senddoc restore

The document covers recovery from:

- Proxmox VM backup
- MarcBot app-level backup tarball
- GitHub repository

It also includes post-restore validation commands and success criteria.


## Report status command

Status: complete.

MarcBot includes a read-only Telegram report status command:

    /report_status

The command summarizes:

- latest local daily status report
- report size and age
- daily status report timer enablement
- overall health or warning state

It does not generate reports, send Telegram files, call AI models, or modify systemd.


## Timer status command

Status: complete.

MarcBot includes a read-only Telegram timer status command:

    /timer_status

The command summarizes approved MarcBot timers:

- `marcbot-backup.timer`
- `marcbot-daily-status-report.timer`

It reports enablement, active state, next run, last trigger, paired service result, and overall health.

It does not enable, disable, start, stop, or modify timers.


## Backup list command

Status: complete.

MarcBot includes a read-only Telegram backup list command:

    /backup_list

The command summarizes recent retained app-level backup archives under:

    /srv/marcbot/backups

It reports filename, size, modified time, age, checksum-file presence, and overall health.

It does not create, delete, rotate, restore, or verify backups.


## Send latest report command

Status: complete.

MarcBot includes a user-triggered Telegram command:

    /send_latest_report

The command sends the newest generated daily status report from:

    /srv/marcbot/workspace/reports

It does not generate reports, call AI models, install timers, or automatically send reports.

This is a bridge step before optional automatic Telegram delivery.


## CLI send latest report command

Status: complete.

MarcBot includes a manual CLI delivery command:

    python -m marcbot report send-latest

The command sends the newest generated daily status report through Telegram using configured `allowed_chat_ids`.

It does not generate reports, call AI models, install timers, or change Telegram configuration.

This prepares the project for a future scheduled report-delivery service.


## Longer-term roadmap

### Workspace file workflow

MarcBot should eventually help Marc move useful files off the Ubuntu server to his MacBook without broad SSH/SCP friction.

Preferred path:

- generate or store files under `/srv/marcbot/workspace`
- retrieve via safe Telegram file send
- avoid arbitrary absolute path access

### Scheduled reports

Potential scheduled report categories:

- system health summary
- disk warning
- backup summary
- AI/news/source checks
- project status report

Cron or systemd timers should be preferred over complex internal schedulers unless there is a strong reason otherwise.

### Local memory and notes

Possible future direction:

- daily notes
- project memory files
- curated summaries
- searchable local notes

This should be added slowly and with clear file ownership and backup behavior.

### Web access

Web access should be added only when there is a clear use case.

Possible future use cases:

- update checks
- release note summaries
- source monitoring

Web-enabled commands should clearly distinguish between local state and internet-derived state.

## Development rules

For each new feature:

1. Add helper module when practical.
2. Add tests for helper logic.
3. Wire Telegram command separately.
4. Update `/help` if user-visible.
5. Update docs when behavior changes.
6. Run `./scripts/check.sh`.
7. Restart service.
8. Test in Telegram.
9. Check logs.
10. Commit and push.
11. Verify `/git` returns clean.

## Current preferred next steps

Recommended order:

1. systemd timer for app-level backups
2. update-check visibility
3. scheduled reports
4. backup visibility
5. update-check visibility

## Non-goals for now

MarcBot should not yet:

- run arbitrary shell commands from Telegram
- send arbitrary absolute server paths
- modify systemd state from Telegram
- edit files from Telegram
- auto-update itself
- expose config secrets
- expose SSH keys or private credentials
- provide multi-user behavior
    
## Daily status report timer

Status: complete.

The local daily status report is scheduled with:

    marcbot-daily-status-report.timer

Schedule:

    11:45 PM America/New_York

The timer runs after the daily app-level backup timer so the report can include recent backup status.

