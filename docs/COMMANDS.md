# MarcBot Commands

This document describes the intended MarcBot command surface.

MarcBot commands should remain narrow, explicit, documented, and safe. Telegram commands are for approved status checks, approved artifact retrieval, and approved workflows. They are not arbitrary shell access.

See also:

- `docs/PROJECT_DIRECTION.md`
- `docs/ROADMAP.md`
- `docs/WORKFLOW_MODEL.md`
- `docs/LLM.md`
- `docs/SECURITY.md`

## Command categories

MarcBot commands should be understood in categories.

### Telegram-facing commands

Telegram-facing commands are available through the MarcBot Telegram bot.

They must be:

- allowlist-protected
- bounded in behavior
- documented
- careful with file paths
- careful with secrets
- careful with logs
- tested before release

### CLI-only commands

CLI-only commands are available on the server through `python -m marcbot ...` or project scripts.

They may be used for operations that should not be exposed through Telegram, including explicit model-provider contact, diagnostics, maintenance, or development workflows.

### Read-only commands

Read-only commands inspect local state and return status. They should not contact external providers unless explicitly documented.

### Provider-contacting commands

Provider-contacting commands call an LLM provider, local model server, or other external service.

Provider-contacting commands should normally be CLI-only until the behavior is stable, safe, and intentionally exposed.

## Current Telegram commands

The exact command list may evolve, but the current MarcBot surface is intended to include commands like the following.

### Basic service commands

| Command | Purpose | Notes |
| --- | --- | --- |
| `/ping` | Check whether MarcBot is responding. | Read-only. |
| `/version` | Show MarcBot version. | Read-only. |
| `/about` | Show MarcBot baseline information. | Read-only. |
| `/uptime` | Show service or host uptime information. | Read-only. |
| `/help` | Show available bot commands. | Read-only. |

### Status and health commands

| Command | Purpose | Notes |
| --- | --- | --- |
| `/status` | Show general MarcBot status. | Read-only. |
| `/health` | Show health summary. | Read-only. |
| `/backup_status` | Show backup-related status. | Read-only. |
| `/backup_list` | List known backup-related artifacts or status records. | Read-only. |
| `/timer_status` | Show approved systemd timer status. | Read-only. |
| `/report_status` | Show report status. | Read-only. |
| `/report_status source ai` | Show source-monitor AI report status. | Read-only. |
| `/llm_status` | Show configured LLM profile/task-route status without contacting providers. | Read-only and provider-contact-free. |

### Git and service inspection commands

| Command | Purpose | Notes |
| --- | --- | --- |
| `/git` | Show repository status summary. | Read-only. |
| `/service` | Show MarcBot service status summary. | Read-only. |
| `/logs` | Show a bounded log summary. | Read-only. |
| `/tail <app|service>` | Show bounded recent log lines for approved log targets. | Read-only, bounded target list. |

### Documentation commands

| Command | Purpose | Notes |
| --- | --- | --- |
| `/docs` | List approved project documents. | Read-only. |
| `/doc <name>` | Show an approved project document. | Read-only, allowlisted names only. |
| `/senddoc <name>` | Send an approved project document. | Read-only, allowlisted names only. |

### Workspace and artifact commands

| Command | Purpose | Notes |
| --- | --- | --- |
| `/ls [path]` | List an approved workspace-relative path. | Read-only, bounded path handling. |
| `/send <path>` | Send an approved workspace-relative file. | Read-only, bounded path handling. |
| `/send_latest_report` | Send the latest approved report artifact. | Read-only, bounded report selection. |

## `/llm_status` boundary

`/llm_status` is intentionally read-only.

It should:

- read local MarcBot configuration only
- show configured LLM profiles and task routes
- not contact LM Studio
- not contact OpenAI
- not contact other model providers
- not run model health checks
- not list live provider models
- not load provider secrets from `llm.env`

Explicit provider contact remains CLI-only.

Examples:

    python -m marcbot llm models <provider>
    python -m marcbot llm health <profile>

This boundary prevents a harmless Telegram status command from unexpectedly loading credentials, waking local models, contacting external services, or causing slow provider calls.

## `/timer_status` boundary

`/timer_status` should inspect only approved MarcBot-related timers.

Approved timers may include:

- `marcbot-backup.timer`
- `marcbot-daily-status-report.timer`
- `marcbot-source-monitor-ai.timer`

The command should not expose arbitrary systemd unit inspection from Telegram.

If new MarcBot timers are added, this document and the implementation allowlist should be updated together.

## File and document boundaries

Telegram file access must remain bounded.

MarcBot should not expose arbitrary host file access through Telegram.

Allowed file behavior should be based on:

- known workspace directories
- known report directories
- known documentation allowlists
- explicit artifact allowlists or registries
- safe path normalization
- size limits
- clear error messages

Secrets must not be sent through Telegram.

Sensitive paths must not be exposed through logs, reports, command output, or memory.

## Future command surfaces

The following command groups are design targets, not necessarily implemented.

### Future workflow commands

Possible future workflow commands:

- `/workflow_list`
- `/workflow_status <name>`
- `/workflow_run <name>`
- `/workflow_result <name>`
- `/workflow_send <artifact-id>`

Workflow commands should expose only approved workflows with bounded arguments.

### Future chat commands

Possible future chat commands:

- `/chat_start <profile>`
- `/chat_stop`
- `/chat_status`
- `/chat_profile`
- `/chat_clear`
- `/chat_context`

Chat commands should be designed before implementation.

Initial chat mode should not have automatic shell execution, unrestricted file access, unrestricted internet access, or hidden persistent memory writes.

## Command documentation requirements

When adding or changing a command, update this document with:

- command name
- purpose
- Telegram-facing or CLI-only status
- read-only or state-changing status
- whether it contacts a model provider
- whether it loads provider secrets
- file access boundaries
- relevant safety notes

If behavior changes, also update:

- `docs/CHANGELOG.md`
- `docs/ARCHITECTURE.md` if architecture changes
- `docs/LLM.md` if model behavior changes
- `docs/SECURITY.md` if security boundaries change
