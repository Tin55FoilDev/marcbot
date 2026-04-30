# MarcBot Roadmap

This roadmap captures the planned direction for MarcBot.

MarcBot is intended to be a personal-only, stable, understandable replacement for the parts of OpenClaw that are most useful to Marc.

The near-term priority is not feature volume. The priority is a reliable foundation that is easy to test, restore, update, and reason about.

## Guiding principles

- Personal-only; no multi-user design unless explicitly needed later.
- Prefer simple, inspectable Python over complex frameworks.
- Make small, reversible changes.
- Add tests where practical.
- Keep runtime secrets outside Git.
- Avoid arbitrary shell execution from Telegram commands.
- Avoid arbitrary file reads from Telegram commands.
- Prefer fixed, narrow commands over open-ended powerful commands.
- Use standard Linux/systemd behavior where possible.
- Keep logs useful but avoid exposing secrets.
- Keep documentation current as the system evolves.

## Current completed baseline

MarcBot currently has:

- Python package structure under `/srv/marcbot/app`
- GitHub remote
- Virtual environment
- Runtime directory structure under `/srv/marcbot`
- Local TOML config outside Git
- Config validation
- CLI entry point
- `doctor` command
- Telegram bot integration
- systemd service
- Telegram authorization by allowed chat ID
- Telegram commands:
  - `/ping`
  - `/version`
  - `/status`
  - `/health`
  - `/logs`
  - `/help`
- Rotating file logging
- Safe `/logs` redaction
- pytest test suite
- Ruff linting
- Deployment runbook

## Phase 1: Foundation hardening

Goal: make the current baseline boring, dependable, and easy to recover.

Planned work:

1. Keep `DEPLOY.md` current.
2. Add this roadmap.
3. Add `ARCHITECTURE.md` describing the major modules and data flow.
4. Add `SECURITY.md` describing token handling, Telegram authorization, and command safety rules.
5. Add `CHANGELOG.md` for human-readable project milestones.
6. Add a simple pre-deploy checklist script or command.
7. Add a backup/restore note once the VM backup pattern is finalized.

Definition of done:

- A future restore can be validated using only the repo docs and local config.
- The current command surface is documented.
- The safety model is documented.
- No secrets are committed.

## Phase 2: Operator convenience commands

Goal: add useful read-only Telegram commands that help Marc operate the bot.

Candidate commands:

- `/uptime`
  - Show host uptime and MarcBot process uptime if available.
- `/disk`
  - Show disk usage for `/srv/marcbot` and root filesystem.
- `/memory`
  - Show basic memory usage.
- `/service`
  - Show whether `marcbot-telegram.service` is active and enabled.
- `/git`
  - Show current branch, short commit hash, and whether the repo is dirty.
- `/docs`
  - Show a list of available local documentation files.

Safety rules:

- Read-only only.
- No arbitrary shell input.
- No arbitrary path input.
- Fixed commands with fixed data sources.
- Output should be short enough for Telegram.

Definition of done:

- Each command has tests where practical.
- Each command is included in `/help`.
- Each command logs success/failure without leaking secrets.

## Phase 3: Local document access

Goal: allow MarcBot to safely expose selected project documentation through Telegram.

Candidate features:

- `/docs`
  - List approved docs in `/srv/marcbot/app/docs`.
- `/doc deploy`
  - Return a summarized or chunked version of `DEPLOY.md`.
- `/doc roadmap`
  - Return a summarized or chunked version of `ROADMAP.md`.
- `/doc security`
  - Return a summarized or chunked version of `SECURITY.md`.

Safety rules:

- Only read from an explicit allowlist.
- Do not allow arbitrary filenames.
- Do not allow path traversal.
- Keep Telegram responses bounded.
- Prefer summaries or first sections instead of entire long files.

Definition of done:

- Safe doc allowlist exists.
- Tests cover allowed and disallowed doc requests.
- Telegram output remains readable.

## Phase 4: Scheduled reports

Goal: rebuild selected OpenClaw-style scheduled reports in a simpler, explicit MarcBot way.

Candidate reports:

- Daily health summary
- AI news digest
- Yankees/baseball report
- Local model update watcher
- System backup status report
- Stock research project inputs

Design direction:

- Use systemd timers or cron for scheduling.
- Keep report scripts explicit and testable.
- Write reports to `/srv/marcbot/workspace` or a dedicated reports directory.
- Send Telegram notifications only after report generation succeeds.
- Keep failed report errors concise and logged.
- Avoid hiding report failures.

Definition of done:

- At least one scheduled report runs reliably.
- Report output is saved locally.
- Telegram notification includes success/failure and location.
- Logs provide enough detail to debug failures.

## Phase 5: Safe command execution helpers

Goal: add narrow helper actions without opening the door to arbitrary shell control.

Possible helpers:

- Run the MarcBot validation script.
- Restart MarcBot service.
- Show service status.
- Trigger a known report job.
- Trigger a known backup check.

Safety rules:

- Every action must be an explicit allowlisted function.
- No raw command text from Telegram.
- Destructive or risky actions should require confirmation.
- Confirmation should expire quickly.
- All actions should be logged.
- Errors should be operator-friendly.

Definition of done:

- There is an action allowlist.
- Tests cover action routing.
- Restart/status helpers work reliably.
- No arbitrary command execution exists.

## Phase 6: Memory and continuity

Goal: build a simple, local memory system that supports continuity without becoming fragile.

Initial design:

- Plain Markdown daily notes.
- Curated `MEMORY.md`.
- Explicit update commands or scheduled maintenance.
- Later optional search index.
- Avoid complex vector dependencies until the foundation is stable.

Possible files:

- `/srv/marcbot/workspace/memory/daily/YYYY-MM-DD.md`
- `/srv/marcbot/workspace/memory/MEMORY.md`
- `/srv/marcbot/workspace/memory/INDEX.md`

Candidate commands:

- `/note <text>`
  - Append a timestamped note to today's daily memory file.
- `/memory`
  - Show curated memory summary.
- `/remember`
  - Later, support explicit durable memory updates.

Safety rules:

- Do not store secrets.
- Avoid storing sensitive personal data unless explicitly requested.
- Keep memory files inspectable and editable.
- Prefer Markdown over databases at first.

Definition of done:

- Daily notes can be appended safely.
- Memory files are easy to back up.
- Memory behavior is documented.

## Phase 7: Model/backend integrations

Goal: optionally connect MarcBot to local or remote model backends after the bot foundation is stable.

Possible integrations:

- OpenAI API or OAuth-style backend if appropriate.
- LM Studio OpenAI-compatible API on the Mac mini.
- vLLM or llama.cpp server if selected later.
- Local summarization for reports or docs.

Design direction:

- Keep model calls behind a small provider abstraction.
- Configure endpoints in local config, not Git.
- Add timeouts.
- Add clear error messages.
- Log model failures without logging prompts that may contain sensitive content.
- Keep non-model commands functional even when models are unavailable.

Definition of done:

- One simple model-backed command works.
- Model failures do not crash the Telegram service.
- Timeouts and fallback behavior are clear.

## Phase 8: Update mechanism

Goal: create a simple, controlled way to update MarcBot.

Candidate workflow:

1. Pull latest Git changes.
2. Install/update dependencies.
3. Run checks.
4. Restart service.
5. Run Telegram validation.
6. Roll back if validation fails.

Possible command:

- `/update-check`
  - Show current branch/commit and whether local repo differs from origin.
- Later:
  - `/update`
  - Pull and deploy only if explicitly confirmed.

Safety rules:

- No automatic background updates by default.
- No update without validation.
- Keep rollback steps documented.
- Avoid changing system packages from Telegram.

Definition of done:

- Manual update process is documented.
- Update check is read-only.
- Any future update action has confirmation and rollback guidance.

## Preferred implementation sequence

Near-term sequence:

1. `ROADMAP.md`
2. `ARCHITECTURE.md`
3. `SECURITY.md`
4. `CHANGELOG.md`
5. `/uptime`
6. `/disk`
7. `/service`
8. `/git`
9. `/docs`
10. Safe document reading
11. First scheduled report

## Stop conditions

Pause feature work if any of these occur:

- Telegram service becomes unreliable.
- Tests fail and the cause is unclear.
- Logs expose secrets.
- Commands become too broad or powerful.
- Restore/deploy process becomes unclear.
- The bot starts accumulating undocumented behavior.

## Current operating rule

For each new feature:

1. Add the smallest useful version.
2. Add tests where practical.
3. Run `./scripts/check.sh`.
4. Restart the service.
5. Test in Telegram.
6. Inspect logs.
7. Commit and push.
8. Update docs if behavior changed.
