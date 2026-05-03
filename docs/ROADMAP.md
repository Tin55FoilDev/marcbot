# MarcBot Roadmap

MarcBot is Marc's personal-only Telegram automation bot.

The project goal is to build a stable, simple, secure replacement for OpenClaw-style personal operations. Development favors careful incremental progress over speed.

## Short-term development path

This section is a practical session-restart anchor. Keep it current at the end of each work session so a new session can quickly identify the next safe step.

Current near-term order:

1. Harden LLM file summary reliability.
   - Add retry-on-empty behavior for safe summary tasks.
   - Improve diagnostics when a provider returns empty content.
   - Preserve the rule that failed provider responses must not create partial output files.

2. Integrate LLM summaries into the source monitor workflow.
   - Generate the source monitor report.
   - Summarize it through the configured `source_monitor_analysis` task.
   - Save the summary as a workspace artifact.

3. Add status/listing commands for generated report and summary artifacts.
   - Show latest reports.
   - Show latest summaries.
   - Include file paths, timestamps, and basic health/failure details.

4. Schedule the stable source-monitor summary workflow.
   - Add automation only after the manual CLI workflow is reliable.
   - Prefer one narrow daily workflow before adding more scheduled tasks.

5. Add Telegram delivery for saved artifacts only.
   - Start with commands that send already-generated summaries.
   - Do not expose arbitrary LLM prompts, arbitrary file paths, or arbitrary output paths through Telegram.

6. Add broader model/profile testing.
   - Support Marc's workflow of adding models in LM Studio.
   - Compare profiles on fixed prompts.
   - Document known-good models and task fit.

Current design principle: CLI first, deterministic boundaries, saved artifacts, then Telegram delivery.

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
- `marcbot-source-monitor-ai.timer`

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


## Scheduled daily report Telegram delivery

Status: complete.

MarcBot includes a dedicated systemd timer to send the newest generated daily status report through Telegram.

Units:

    marcbot-daily-status-report-send.service
    marcbot-daily-status-report-send.timer

Schedule:

    23:50 America/New_York

The delivery step is intentionally separate from report generation:

- backup runs first
- report generation runs second
- report delivery runs third

This keeps each operation isolated, observable, and independently testable.


## Longer-term roadmap

### Source monitor / AI awareness

Build a narrow allowlisted source monitor for Marc's AI information workflow. The first goal is controlled source checking and local Markdown reports, not autonomous browsing or LLM-driven decision-making.

Planned sequence:

1. Source monitor report scaffold.
2. Local source config validation.
3. Documentation and example config.
4. Safe fetch implementation for allowlisted HTTPS sources.
5. Bounded local Markdown reports.
6. Optional Telegram report delivery after the local path is stable.
7. Optional higher-level AI summaries after deterministic source collection is reliable.


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

## AI source monitor timer

MarcBot now includes scheduled local AI source monitor report generation.

Systemd units:

    marcbot-source-monitor-ai.service
    marcbot-source-monitor-ai.timer

The service runs:

    python -m marcbot source-monitor run ai

The timer writes local reports only. Telegram access is read-only through:

    /report_status source ai

The timer is visible in:

    /timer_status


## LLM provider/profile foundation

MarcBot should grow from deterministic command and report workflows into a controlled, multi-provider LLM system.

Planned sequence:

1. Add a reusable LLM provider/profile configuration layer.
2. Support OpenAI-compatible local providers, starting with LM Studio.
3. Support model discovery for LM Studio through `/v1/models`.
4. Support profile validation and tiny completion health checks from the CLI.
5. Add OpenAI/frontier provider structure for future GPT-5.5-style profiles.
6. Allow capabilities to assign work to named profiles instead of hardcoded models.
7. Expose read-only LLM profile/model/health status through Telegram.
8. Later, add explicit controlled chat sessions, such as `/chat_start <profile>`, rather than an unrestricted prompt interface.

Initial profile categories:

- `frontier_chat` for chat, research, planning, and discussion.
- `frontier_analysis` for higher-confidence analysis.
- `local_fast` for low-risk utility tasks.
- `local_careful` for bounded local analysis.
- `local_experimental` for testing newly added local models.

Local models are expected to be useful for heartbeat functions, backups, simple analysis, deterministic reports, and model experimentation. Frontier models are expected to be preferred for open-ended chat, research, discussion, planning, and adversarial or ambiguous reasoning.

### LLM provider/profile operational baseline

The LLM foundation now supports CLI-only provider/profile operations:

~~bash
python -m marcbot llm profiles
python -m marcbot llm models lmstudio
python -m marcbot llm health local_fast
~~

Next likely steps:

1. Add read-only Telegram LLM status/profile visibility.
2. Keep arbitrary prompt relay out of Telegram until a separate safety design exists.
3. Add task-to-profile routing only after profile health checks are stable.
