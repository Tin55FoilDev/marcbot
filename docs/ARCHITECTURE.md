# MarcBot Architecture

MarcBot is a personal-only Telegram-facing agent shell and workflow system.

The architecture target is intentionally smaller and more inspectable than OpenClaw. MarcBot should grow through narrow, tested, documented capabilities rather than broad autonomous behavior.

See also:

- `docs/PROJECT_DIRECTION.md`
- `docs/ROADMAP.md`
- `docs/WORKFLOW_MODEL.md`
- `docs/COMMANDS.md`
- `docs/INTERACTION_MODEL.md`
- `docs/LLM.md`
- `docs/MEMORY.md`
- `docs/SECURITY.md`
- `docs/DEPLOY.md`

## Current operating model

MarcBot currently runs as a Python application on the Ubuntu server.

Current baseline assumptions:

- repository path: `/srv/marcbot/app`
- runtime user: `marc`
- administrative user: `adminuser`
- Telegram service: `marcbot-telegram.service`
- project configuration under `/srv/marcbot/config`
- project logs under `/srv/marcbot/logs`
- project workspace and generated artifacts under the MarcBot-controlled `/srv/marcbot` structure

App and repo operations should run as `marc`, not directly as `adminuser`.

The normal command pattern from an `adminuser` shell is:

    sudo -u marc env HOME=/home/marc GIT_PAGER=cat PATH="/srv/marcbot/app/.venv/bin:/usr/local/bin:/usr/bin:/bin" bash -lc 'cd /srv/marcbot/app && <command>'

Do not assume `adminuser` can directly access or operate inside `/srv/marcbot/app`.

## Architecture goals

MarcBot should be:

- personal-only
- Telegram-facing
- allowlist-protected
- inspectable
- testable
- Git-backed
- secure by default
- explicit about model use
- explicit about file access
- explicit about workflow boundaries
- conservative about secrets
- conservative about autonomous behavior

MarcBot should not become an unrestricted remote shell, unrestricted file browser, unrestricted web agent, or hidden automation layer.

## Runtime planes

MarcBot should be understood as four separate runtime planes.

### 1. Telegram command plane

The Telegram command plane exposes approved slash commands.

Characteristics:

- allowlisted Telegram chat IDs
- bounded command arguments
- read-only status commands by default
- explicit allowlists for file/doc/log access
- no arbitrary shell access
- no arbitrary filesystem access
- no unrestricted provider contact
- no secret output

Command details belong in `docs/COMMANDS.md`.

Architecture rule: if a command's behavior changes, update `docs/COMMANDS.md` and any affected architecture, security, or LLM docs in the same milestone.

### 2. Workflow plane

The workflow plane runs named, approved multi-step processes.

A workflow may combine:

- deterministic Python code
- local configuration
- local source data
- scheduled execution
- report generation
- bounded LLM analysis
- artifact storage
- Telegram status or delivery commands

A workflow should not be arbitrary tool use.

Workflow design should specify:

- workflow name
- allowed inputs
- configuration location
- state location
- output/artifact location
- logs
- model task route, if any
- whether it is CLI-only or Telegram-facing
- whether it is read-only or state-changing
- failure behavior
- tests
- documentation

### 3. Model/provider plane

The model/provider plane handles local and future frontier model access.

Current model principles:

- model access should use named providers and named profiles
- routine status commands should not unexpectedly contact providers
- provider-contacting commands should remain CLI-only until deliberately exposed
- provider secrets must not enter Git, Telegram, logs, reports, or memory
- local model access should be testable independently of Telegram
- frontier model access is a research track until a safe path is documented

`/llm_status` is part of the Telegram command plane, but it must remain provider-contact-free.

Explicit provider contact belongs in CLI-only commands such as:

    python -m marcbot llm models <provider>
    python -m marcbot llm health <profile>

LLM details belong in `docs/LLM.md`.

### 4. Memory and artifact plane

The memory and artifact plane covers generated outputs, saved reports, summaries, future transcripts, and future durable memory.

Artifacts should be:

- stored under approved MarcBot-controlled paths
- retrievable through bounded commands
- identifiable by safe names or artifact IDs
- separated from secrets
- bounded by size and path controls
- documented when exposed through Telegram

Durable memory is a future feature.

Future memory must support:

- auditability
- correction
- deletion
- review
- clear distinction between transient context and durable memory
- no secrets
- no hidden sensitive data capture

Memory details belong in `docs/MEMORY.md`.

## Interaction modes

The architecture supports four interaction modes.

### Command mode

Command mode is narrow slash-command or CLI-command execution.

This is the current mature surface.

### Workflow mode

Workflow mode is named approved multi-step execution.

This is the next major operating model.

### Chat mode

Chat mode is a future controlled Telegram conversation with a selected approved model profile.

Chat mode should not automatically execute shell commands, browse arbitrary URLs, read arbitrary files, write files, or modify system state.

Chat may eventually discuss project state, explain artifacts, draft plans, and propose workflows. Execution should remain routed through approved commands or approved workflows.

### Development mode

Development mode is Marc plus an AI assistant modifying MarcBot through SSH/Git.

Development mode is human-supervised and Git-backed. It is not the same as runtime Telegram autonomy.

Development changes should remain:

- small
- reviewed
- test-gated
- documented
- committed
- pushed
- validated after Telegram-facing changes

## Project structure

The repository should remain organized around narrow modules and clear responsibilities.

Expected high-level areas:

- Telegram handlers
- command helpers
- configuration loaders
- report generation
- source monitor logic
- LLM provider/profile logic
- workflow orchestration
- artifact helpers
- tests
- documentation

Implementation should avoid hidden cross-module behavior. A status command should not unexpectedly trigger provider access, long-running analysis, or secret loading.

## Configuration boundaries

Configuration should be explicit.

Recommended separation:

- non-secret project configuration under `/srv/marcbot/config`
- provider secrets in local secret files outside Git
- generated reports and summaries under approved workspace/report directories
- logs under `/srv/marcbot/logs`
- documentation in the repository under `docs/`

Configuration readers should fail clearly when required configuration is missing or invalid.

Provider-secret loading should be isolated to commands or workflows that explicitly need provider access.

## Telegram boundary

Telegram is a user interface, not a trust boundary.

Telegram-facing functionality must remain restricted by:

- allowed chat IDs
- bounded commands
- bounded arguments
- approved file paths
- approved document names
- approved log targets
- size limits
- clear user-facing errors
- careful logging
- no secret output

Telegram should not expose arbitrary shell commands or arbitrary host file access.

## File boundary

MarcBot may generate and retrieve files, but only through approved paths and workflows.

Telegram-facing file access should be limited to:

- approved docs
- approved reports
- approved workspace-relative files
- future artifact registry entries

File handling should use safe path normalization and reject traversal attempts.

Secrets, environment files, tokens, private keys, and raw provider credential caches must never be sent through Telegram.

## Logging boundary

Logs should support diagnosis without leaking secrets.

Logs should avoid:

- provider tokens
- environment secret values
- Telegram bot tokens
- full secret file paths when avoidable
- sensitive report contents unless explicitly intended
- unbounded user input

Telegram-facing failures should return concise user-facing errors and write enough diagnostic detail to logs for Marc to inspect safely.

## LLM boundary

LLM-backed behavior should be explicit.

A command or workflow should document:

- whether it contacts a model
- which task route it uses
- which profile category it expects
- whether it loads provider secrets
- whether it is CLI-only or Telegram-facing
- timeout/failure behavior
- output destination

Local models and frontier models should be routed through named profiles.

MarcBot should support testing model access from the CLI before any Telegram exposure.

## Frontier model boundary

Frontier model support is a research track.

Marc currently does not plan to use per-call OpenAI API billing for MarcBot. The preferred future direction is to investigate whether a stable subscription/OAuth-style path is available, similar in purpose to OpenClaw's current frontier model usage.

Until that research is complete:

- do not implement frontier runtime assumptions
- do not depend on OpenClaw as a backend worker
- do not place provider secrets in Git
- do not expose provider tokens through Telegram
- keep experiments CLI-only
- document findings before implementation

## Scheduled jobs

Scheduled jobs are useful but should not define the whole architecture.

Cron or systemd timers may run approved workflows, but those workflows should also be manually runnable and inspectable.

Scheduled jobs should have:

- clear unit/timer names
- clear logs
- clear output locations
- clear failure behavior
- status visibility
- docs

Telegram status commands may report on approved timers, but should not expose arbitrary systemd inspection.

## Testing and validation

Every architecture change should preserve the standard discipline:

1. make a small change
2. run `./scripts/check.sh`
3. review diffs
4. restart the Telegram service if Telegram-facing behavior changed
5. validate Telegram behavior if Telegram-facing behavior changed
6. inspect logs if Telegram-facing behavior changed
7. commit
8. push
9. keep the repo clean

Tests should favor narrow deterministic behavior and clear failure messages.

## Architecture decision rule

When choosing between a powerful broad feature and a smaller inspectable feature, choose the smaller inspectable feature first.

MarcBot should grow by composing narrow trusted capabilities, not by granting broad hidden authority.
