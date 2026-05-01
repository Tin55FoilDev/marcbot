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
