# MarcBot

MarcBot is Marc's personal-only Telegram bot and automation project.

It is intended to replace the reliable subset of OpenClaw workflows with a smaller, safer, more testable system that Marc can maintain over time.

Current baseline: **MarcBot 0.3.2**.

Project direction: see `docs/PROJECT_DIRECTION.md` for the long-term target: a personal Telegram-facing OpenClaw replacement for chat, commands, workflows, local models, and frontier model profiles.

## Design goals

MarcBot favors:

- narrow, explicit capabilities
- stable behavior over rapid feature growth
- CLI-first development workflows
- safe Telegram commands
- saved report and summary artifacts
- local configuration outside Git
- unit tests and Ruff validation
- clear documentation for future AI-assisted development sessions

MarcBot intentionally avoids broad agent autonomy.

## Security model

Runtime MarcBot should stay constrained.

MarcBot does **not** provide:

- arbitrary shell execution from Telegram
- arbitrary file writes from Telegram
- arbitrary patch application from Telegram
- unrestricted internet browsing from Telegram
- secrets in Git, docs, logs, or chat
- unrestricted self-modification commands

Preferred pattern:

- build and test features through CLI workflows first
- save generated reports/summaries as artifacts
- expose only bounded, reviewed artifact/status commands through Telegram
- keep local operational config under `/srv/marcbot/config`, outside Git

## Current capabilities

MarcBot currently includes:

- Telegram command gateway with allowlisted chat authorization
- basic health, version, uptime, service, Git, log, and status commands
- safe documentation access from Telegram
- safe workspace-relative file listing and file sending
- app-level backup visibility and recent backup listing
- daily local status report generation
- scheduled daily report delivery
- timer visibility for backup/report jobs
- source monitor project scaffolding
- CLI-only source monitor report generation
- CLI-only source monitor LLM summary generation
- CLI-only LLM provider/profile/task inspection
- CLI-only workspace file summarization
- CLI-only saved workspace summary generation
- read-only support snapshot generation for future session restarts

## Session restart support

MarcBot 0.3.2 hardens LLM status behavior so Telegram status remains read-only while explicit health checks stay CLI-only.

Important files/commands:

    docs/SESSION_START.md
    python -m marcbot support snapshot

Use `docs/SESSION_START.md` as the human-readable restart guide.

Use `python -m marcbot support snapshot` to print a redacted live state packet containing version, Git state, runtime paths, required docs, and validation instructions.

The snapshot intentionally excludes secrets, local config contents, environment variables, tokens, and unrestricted logs.

Suggested new-session prompt:

    I am continuing MarcBot development. Attached is docs/SESSION_START.md,
    and here is the output of python -m marcbot support snapshot.

    Please follow the documented security and development workflow. I am
    logged into the server as adminuser. For repo commands, use sudo -u marc
    with cd /srv/marcbot/app inside the sudo block.

## Standard repo command pattern

Marc is usually logged into the server as `adminuser`.

The MarcBot repo/app is owned by the non-sudo runtime user `marc`.

Run repo commands using this pattern:

    sudo -u marc env \
      HOME=/home/marc \
      GIT_PAGER=cat \
      PATH="/srv/marcbot/app/.venv/bin:/usr/local/bin:/usr/bin:/bin" \
      bash -lc '
    set -e
    cd /srv/marcbot/app

    git status --short
    ./scripts/check.sh
    '

Keep `cd /srv/marcbot/app` inside the `sudo -u marc ... bash -lc` block.

## Validation

Before committing code or documentation changes, run:

    ./scripts/check.sh

Current clean baseline:

- MarcBot version command passes
- MarcBot doctor passes
- pytest passes
- Ruff passes

For deployed Telegram-facing changes, restart/test the service and inspect logs.

## Important paths

Common paths:

- repo/app: `/srv/marcbot/app`
- runtime root: `/srv/marcbot`
- workspace: `/srv/marcbot/workspace`
- local config: `/srv/marcbot/config`
- logs: `/srv/marcbot/logs/marcbot.log`

Local config and secrets should remain outside Git.

## Source monitor

The current source monitor workflow is project-based.

Common commands:

    python -m marcbot source-monitor config-check ai
    python -m marcbot source-monitor run ai
    python -m marcbot source-monitor run-summary ai

`run-summary` writes a source monitor report, builds a bounded summary input, routes the summary through the configured `source_monitor_analysis` task, and saves the summary under the source project's workspace `summaries/` directory.

## LLM support

LLM support is currently CLI-only.

Current LLM command groups include:

    python -m marcbot llm profiles
    python -m marcbot llm profile <profile>
    python -m marcbot llm models <provider>
    python -m marcbot llm health <profile>
    python -m marcbot llm tasks
    python -m marcbot llm task <task>
    python -m marcbot llm ask <profile> <prompt>
    python -m marcbot llm ask-task <task> <prompt>
    python -m marcbot llm summarize-file <task> <workspace-relative-path>
    python -m marcbot llm summarize-file-save <task> <input-path> <output-path>

LLM configuration lives outside Git under `/srv/marcbot/config`.

The preferred model strategy is:

- local models for bounded summaries, heartbeat-style checks, and low-risk deterministic jobs
- frontier/online models later for richer chat and research workflows behind explicit controls
- no arbitrary Telegram prompt-to-tool execution

## Documentation

Primary docs:

- `docs/SESSION_START.md` — restart guide for new AI-assisted sessions
- `docs/COMMANDS.md` — command reference
- `docs/DEPLOY.md` — deployment/service guidance
- `docs/LLM.md` — LLM configuration and workflows
- `docs/WORKFLOW_MODEL.md` — preferred CLI-first workflow and orchestration model for new MarcBot projects.
- `docs/MEMORY.md` — future memory-system design notes
- `docs/ROADMAP.md` — near-term project direction
- `docs/SECURITY.md` — security model and constraints
- `docs/ARCHITECTURE.md` — architecture overview
- `docs/CHANGELOG.md` — project changes

## Development principle

When changing MarcBot:

1. make one small, bounded change
2. add or update tests where practical
3. update docs
4. run `./scripts/check.sh`
5. inspect the diff
6. commit and push after validation
7. restart/test services for deployed Telegram-facing changes

## Documentation map

MarcBot has several design and operations documents. To avoid duplicate or conflicting information, each document should own a specific subject.

- `docs/PROJECT_DIRECTION.md` owns the long-term project goal, non-goals, and overall direction.
- `docs/ROADMAP.md` owns current sequencing, near-term priorities, and future milestones.
- `docs/ARCHITECTURE.md` owns system structure, runtime planes, and major technical boundaries.
- `docs/COMMANDS.md` owns Telegram and CLI command behavior, command boundaries, and future command surfaces.
- `docs/INTERACTION_MODEL.md` owns how command mode, workflow mode, chat mode, development mode, approvals, file access, artifacts, and future memory interact.
- `docs/LLM.md` owns providers, profiles, task routes, LM Studio behavior, model health checks, and frontier-model research boundaries.
- `docs/WORKFLOW_MODEL.md` owns the design model for approved workflows and deterministic-plus-LLM orchestration.
- `docs/MEMORY.md` owns future durable memory design, auditability, correction, and memory safety rules.
- `docs/SECURITY.md` owns security boundaries, threat controls, secrets handling, and Telegram safety rules.
- `docs/CONFIG.md` owns local runtime configuration files and non-secret versus secret config separation.
- `docs/DEPLOY.md` owns deployment and service setup procedures.
- `docs/RESTORE.md` owns restore and disaster-recovery procedures.
- `docs/SOURCE_MONITOR.md` owns source-monitor workflow details.
- `docs/CHANGELOG.md` owns historical changes.

When updating docs, prefer linking to the authoritative document instead of duplicating detailed command lists, configuration inventories, or roadmap text in multiple places.
