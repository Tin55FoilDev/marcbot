# MarcBot Commands

This document describes the intended MarcBot command surface.

MarcBot commands should remain narrow, explicit, documented, and safe. Telegram commands are for approved status checks, approved artifact retrieval, and approved workflows. They are not arbitrary shell access.

See also:

- `docs/PROJECT_DIRECTION.md`
- `docs/ROADMAP.md`
- `docs/WORKFLOW_MODEL.md`
- `docs/INTERACTION_MODEL.md`
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
| `/report_status source ai` | Show source-monitor AI report status and recent artifact IDs. | Read-only and provider-contact-free. |
| `/send_source_artifact <project> <artifact-id>` | Send an approved source-monitor report or summary by safe artifact ID. | Telegram-facing, bounded artifact retrieval, provider-contact-free. |
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


### Source-monitor CLI artifact commands

| Command | Purpose | Notes |
| --- | --- | --- |
| `python -m marcbot source-monitor summarize-latest <project>` | Summarize the newest existing source-monitor report without generating a new report first. | CLI-only, provider-contacting, requires LLM secret env. |
| `python -m marcbot source-monitor artifact-path <project> <artifact-id>` | Resolve a source-monitor artifact ID to an approved local path. | CLI-only, read-only, provider-contact-free. |

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

## Provider-contacting Telegram commands

Provider-contacting Telegram commands are not part of the default command
surface.

A Telegram command is provider-contacting if it may:

- load LLM provider credentials
- call a local or remote model provider
- wake or load a local model
- send prompt text, report text, file text, chat text, or derived context to a model
- create a model-generated artifact

Provider-contacting Telegram commands may be added only when the command is:

- named explicitly
- documented in this command reference
- limited to bounded arguments
- routed through an approved provider/profile/task configuration
- clear in user-facing help that it contacts a model provider
- tested for authorization, argument validation, success, and safe failure behavior
- logged without prompt text, secret values, provider credentials, or large generated output

Provider-contacting Telegram commands must not accept arbitrary provider names,
model IDs, URLs, host file paths, shell commands, or free-form tool requests.

Existing provider-contacting workflows should remain CLI-only until the
Telegram command has a deliberate safety design. For example:

    python -m marcbot source-monitor summarize-latest <project>

is currently CLI-only because it loads LLM provider configuration and sends
bounded report content to a model provider.

### Initial chat lifecycle commands

Initial chat lifecycle commands are Telegram-facing but provider-contact-free
except for `/chat_start` loading local LLM configuration to validate that the
requested profile exists and is approved for chat.

    /chat_start <profile>
    /chat_status
    /chat_clear
    /chat_stop

These commands do not send prompts to a model provider. Normal Telegram text is
not yet handled as chat input in this milestone.

### Active chat text

When chat mode is active, normal Telegram text may be sent to the selected
chat-approved LLM profile.

This is provider-contacting behavior. It is limited to bounded conversational
text and volatile in-memory history. It must not read files, browse URLs, run
commands, trigger workflows, update durable memory, or expose secrets.

### Chat context status

`/chat_context` shows which local chat context files are loaded without showing
their contents.

It is provider-contact-free and safe for tuning local chat context.

Example output:

    MarcBot chat context
    Directory: /srv/marcbot/config/chat
    Loaded files: 3
    Total chars: 4200
    - system.md: loaded
    - agent.md: loaded
    - user.md: loaded
    - project.md: missing
    Provider contact: no

### Chat profile status

`/chat_profiles` shows configured LLM profiles and whether each one is approved
for Telegram chat.

It is provider-contact-free. It reads local LLM configuration but does not call a
model provider, load remote model lists, run health checks, or send prompts.

Example output:

    MarcBot chat profiles
    Provider contact: no
    - local_fast: chat_enabled=True, model=google/gemma-4-e4b, intended_use=low_risk_utility
    - local_careful: chat_enabled=False, model=qwen3.6-35b-a3b, intended_use=bounded_local_analysis

### Weather report status

`/weather_status` shows the latest weather report artifact and basic weather
workflow status.

It is provider-contact-free and does not fetch a new forecast.

Use `/timer_status` for systemd timer status.

### Weather timer visibility

`/timer_status` includes the approved weather report timer:

    marcbot-weather-report.timer
    marcbot-weather-report.service

This remains read-only and limited to approved MarcBot-related units.

### Send latest weather report

`/send_weather_report` resends the latest generated weather report as cleaned
Telegram text.

It is provider-contact-free and does not fetch a new forecast.

### Future memory status

`/memory_status` is the planned read-only Telegram command for MarcBot memory
visibility.

Initial behavior should show memory root status, event counts, fact counts,
summary counts, and pending proposal counts.

It must not write memory, approve proposals, fetch arbitrary files, expose
secrets, or contact model providers.

### Memory CLI scaffold

Initial memory CLI commands:

    python -m marcbot memory init
    python -m marcbot memory status

These commands are local, provider-contact-free, and do not use LLMs.

### Memory status

`/memory_status` shows local MarcBot memory status.

It is read-only and provider-contact-free. It does not write memory, approve
memory proposals, inspect arbitrary paths, or contact model providers.

### Memory event ledger

Explicit memory event commands:

    python -m marcbot memory event add
    python -m marcbot memory event list

These commands are CLI-only, provider-contact-free, and intended for explicit
low-risk memory events.

### Memory summaries

Explicit memory summary commands:

    python -m marcbot memory summary add
    python -m marcbot memory summary list

These commands are CLI-only, provider-contact-free, and intended for milestone,
project, and session handoff summaries.

### Memory facts

Explicit memory fact commands:

    python -m marcbot memory fact add
    python -m marcbot memory fact list

These commands are CLI-only, provider-contact-free, and intended for durable
facts that should remain correctable in later milestones.

### Memory fact supersession

Explicit fact correction command:

    python -m marcbot memory fact supersede

This command supersedes an active fact with a corrected active fact and writes a
correction record. It is CLI-only and provider-contact-free.

### Memory fact rejection

Explicit fact rejection command:

    python -m marcbot memory fact reject

This command marks a fact rejected and writes a correction record. It is
CLI-only and provider-contact-free.

### Memory proposals

Explicit memory proposal commands:

    python -m marcbot memory proposal add
    python -m marcbot memory proposal list
    python -m marcbot memory proposal reject

These commands are CLI-only and provider-contact-free. Proposal approval is
deferred to a later milestone.

### Memory proposal approval

Explicit fact proposal approval command:

    python -m marcbot memory proposal approve

Initial approval supports fact proposals only. It is CLI-only and
provider-contact-free.

### Richer memory status counts

`/memory_status` and `python -m marcbot memory status` show proposal counts by
status:

    pending proposals
    approved proposals
    rejected proposals

This helps distinguish outstanding review work from preserved approved/rejected
proposal history.

### Memory detail retrieval

Read-only memory detail commands:

    python -m marcbot memory fact show --id <fact-id>
    python -m marcbot memory proposal show --id <proposal-id>

These commands are CLI-only and provider-contact-free.

### Memory event and summary detail retrieval

Read-only memory detail commands:

    python -m marcbot memory event show --index <n> --limit <limit>
    python -m marcbot memory summary show --name <summary-file-name>

These commands are CLI-only and provider-contact-free.

### Memory search

Read-only memory search command:

    python -m marcbot memory search <query>

The command searches local memory files by case-insensitive substring. It is
CLI-only and provider-contact-free.

### Automatic memory integration policy

MarcBot may auto-record low-risk workflow events only for approved workflows
with clear success boundaries.

Automatic memory writes are limited to low-risk events. Facts, proposal review,
fact correction, and security-sensitive memory changes remain explicit CLI
operations.
| `/memory_events` | Show recent local memory events. | Read-only; provider-contact-free. |
| `/memory_facts` | Show active local memory facts. | Read-only; provider-contact-free. |

## Telegram help ordering

The Telegram `/help` command lists commands alphabetically by command name so the
growing command list remains easier to scan.

## SQLite memory CLI commands

SQLite memory commands:

    python -m marcbot memory sqlite status
    python -m marcbot memory sqlite init
    python -m marcbot memory sqlite import
    python -m marcbot memory sqlite counts
    python -m marcbot memory sqlite validate

These commands are CLI-only and provider-contact-free. File memory remains the
source of truth.

### LLM provider-contact environment behavior

Provider-contact LLM CLI commands load `/srv/marcbot/config/llm.env`
before contacting the configured provider. This applies to explicit
`llm models`, `llm health`, `llm ask`, `llm ask-task`,
`llm summarize-file`, and `llm summarize-file-save` commands.

`llm status` remains provider-contact-free and does not require provider
contact to report configured providers, profiles, tasks, and route validity.

### Memory profile commands

`python -m marcbot memory profiles` lists deterministic memory context
profiles such as `weather-report`. The command is read-only and
provider-contact-free.

`python -m marcbot memory profiles --format json` returns the same profile
catalog as structured JSON for future workflow automation.

`python -m marcbot memory context --profile weather-report` assembles
bounded local memory context using that profile.

### Telegram memory profile visibility

`/memory_profiles` lists deterministic memory context profiles from Telegram.
It is read-only and provider-contact-free.

Current profiles include:

- `weather-report`
- `source-monitor`

### Telegram memory context visibility

`/memory_context <profile>` shows bounded local memory context for a
deterministic memory context profile. It is read-only and
provider-contact-free.

Examples:

```text
/memory_context weather-report
/memory_context source-monitor
```

### Telegram memory proposal command

`/memory_propose_fact <project> | <statement>` creates a pending
memory proposal from Telegram. It does not create an approved durable fact.

Example:

```text
/memory_propose_fact source-monitor | Source-monitor summaries should use explicit memory profiles.
```

The command is authorized-chat-only, writes a pending proposal, and remains
provider-contact-free.

### Telegram memory proposal visibility

`/memory_proposals` lists pending memory proposals from Telegram.
It is read-only and provider-contact-free. It does not approve, reject,
or modify proposals.

### Telegram memory proposal detail

`/memory_proposal <id>` shows one memory proposal from Telegram.
It is read-only and provider-contact-free. It does not approve, reject,
or modify the proposal.

### Telegram memory proposal rejection

`/memory_reject_proposal <id> | <reason>` rejects a pending memory
proposal from Telegram. It is a bounded write operation, but it does not
approve facts or create durable memory.

Example:

```text
/memory_reject_proposal telegram-fact-20260524-231420 | Validation-only test proposal.
```

### Memory candidate preview

`python -m marcbot memory candidate preview [--project PROJECT] TEXT`
previews how MarcBot would classify text for memory handling. It is
read-only, provider-contact-free, and writes no memory.

### Telegram memory candidate preview

`/memory_candidate_preview <project> | <text>` previews how MarcBot would
classify text for memory handling. It is read-only, provider-contact-free,
and writes no memory.

Example:

```text
/memory_candidate_preview source-monitor | Source-monitor summaries should use explicit memory profiles.
```
