# MarcBot Session Start Guide

This guide is the restart packet for a new AI-assisted MarcBot development session.

Use it when starting a new browser ChatGPT session, debugging a MarcBot issue, or planning a new MarcBot feature.

## What MarcBot is

MarcBot is Marc's personal-only Telegram bot and automation project.

Primary goals:

- stable, narrow, testable replacement for selected OpenClaw workflows
- personal operational commands through Telegram
- CLI-first development and automation workflows
- saved report and summary artifacts
- explicit safety boundaries
- clear docs so a new session can restart quickly

MarcBot should favor reliability, small changes, and understandable behavior over broad agent autonomy.

## Current operating model

MarcBot has two separate modes:

1. Runtime MarcBot

   The deployed Telegram bot and scheduled CLI workflows.

2. Development workflow

   The controlled process used to change MarcBot itself.

Runtime MarcBot should stay constrained. Development support can be powerful, but it should remain explicit, testable, and reviewable.

## Important users and paths

Marc is usually logged into the server as `adminuser`.

The MarcBot runtime and repository user is `marc`.

Important paths:

- repo/app: `/srv/marcbot/app`
- runtime root: `/srv/marcbot`
- workspace: `/srv/marcbot/workspace`
- local config outside Git: `/srv/marcbot/config`
- logs: `/srv/marcbot/logs/marcbot.log`

Do not assume `adminuser` can directly access `/srv/marcbot/app`.

## Standard repo command pattern

Run repository commands as `marc` from the `adminuser` shell.

Use this pattern:

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

## Validation standard

Before committing code or docs changes, run:

    ./scripts/check.sh

A clean validation currently means:

- MarcBot version command works
- MarcBot doctor passes
- pytest passes
- Ruff passes

For deployed Telegram-facing changes, also restart/test the service and inspect logs.

## Git workflow

Use small, focused commits.

Expected flow:

1. inspect current status
2. make one bounded change
3. run validation
4. inspect diff
5. commit with a clear message
6. push
7. confirm clean status

Do not commit secrets or local operational config.

## Security boundaries

Do not add:

- arbitrary Telegram shell access
- arbitrary Telegram file writes
- arbitrary Telegram patch application
- unrestricted internet browsing from Telegram
- secrets in chat, logs, docs, or Git
- broad self-modification commands

Prefer:

- CLI-first workflows
- bounded source/project configuration
- saved artifacts under the workspace
- explicit allowlists
- redacted diagnostics
- deterministic helper functions with tests

## LLM workflow guidance

MarcBot may use local or online LLM profiles through explicit task/profile configuration.

Current design preference:

- local models for bounded summaries, heartbeat-style checks, and low-risk deterministic jobs
- frontier models for richer chat/research later, behind controlled workflows
- no arbitrary Telegram prompt-to-tool execution
- save outputs as artifacts before exposing them through Telegram

LLM configuration lives outside Git under `/srv/marcbot/config`.

## Source monitor workflow

The AI source monitor is project-based.

Important command:

    python -m marcbot source-monitor run-summary ai

This writes a source monitor report, builds a bounded summary input if needed, summarizes through the configured `source_monitor_analysis` task, and saves a summary artifact under:

    /srv/marcbot/workspace/source-projects/ai/summaries/

## New feature development pattern

For a new report/project workflow, prefer this sequence:

1. define the project shape and non-goals
2. add CLI-only artifact generation
3. add deterministic tests
4. add optional LLM summary of the generated artifact
5. add status/listing commands for saved artifacts
6. add Telegram delivery of saved artifacts only
7. add scheduling after manual smoke tests pass

Example future projects:

- Yankees/baseball report
- stock research support
- AI source monitoring improvements
- weather/status reporting

## Bug report restart packet

When starting a new AI session for a bug, provide:

- this file
- `docs/ROADMAP.md`
- `docs/CHANGELOG.md`
- the exact command that failed
- the exact error output
- `git status --short`
- relevant log excerpts with secrets redacted
- relevant source/test files if needed

## Feature restart packet

When starting a new AI session for a feature, provide:

- this file
- `docs/ROADMAP.md`
- `docs/ARCHITECTURE.md`
- `docs/SECURITY.md`
- `docs/COMMANDS.md`
- `docs/CHANGELOG.md`
- the desired feature goal
- any non-goals or safety constraints

## Suggested new-session prompt

Use a prompt like this:

    I am continuing MarcBot development. Attached are SESSION_START.md,
    ROADMAP.md, CHANGELOG.md, and any relevant source/test files.

    Please follow the documented security and development workflow.

    I am logged into the server as adminuser. For repo commands, use
    sudo -u marc with cd /srv/marcbot/app inside the sudo block.

    Start by checking the current state, then proceed in small validated steps.

## Current priorities

Use `docs/ROADMAP.md` as the current project direction.

When in doubt:

- preserve security boundaries
- make one small change
- add or update tests
- update docs
- run `./scripts/check.sh`
- inspect diff before commit
- Review `docs/WORKFLOW_MODEL.md` before designing new project workflows or Telegram exposure.
