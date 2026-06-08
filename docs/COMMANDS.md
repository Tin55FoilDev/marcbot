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
| `/workflow_list` | List approved workflow definitions. | Read-only and provider-contact-free. Does not run workflows. |
| `/workflow_run source-monitor-ai-report` | Run the approved deterministic source-monitor report workflow for the fixed `ai` project. | Telegram-facing controlled execution. Provider-contact-free. Writes a report artifact; writes no memory. |
| `/workflow_artifacts <workflow-id>` | Show read-only workflow artifact IDs for the `ai` project. | Read-only and provider-contact-free. Does not run workflows, send files, write artifacts, or write memory. |
| `/workflow_send_artifact <workflow-id> <artifact-id>` | Send an existing approved workflow artifact by safe workflow/artifact ID pair. | Telegram-facing bounded file send. Does not run workflows, contact providers, write artifacts, or write memory. |
| `/workflow_status <workflow-id>` | Show read-only workflow status and artifact visibility for the `ai` project. | Read-only and provider-contact-free. Does not run workflows, write artifacts, or write memory. |

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

These commands are CLI-only and provider-contact-free. File-backed memory
records remain the current transitional implementation while SQLite is the
intended primary structured memory repository.

### LLM provider-contact environment behavior

Provider-contact LLM CLI commands load `/srv/marcbot/config/llm.env`
before contacting the configured provider. This applies to explicit
`llm models`, `llm health`, `llm ask`, `llm ask-task`,
`llm summarize-file`, and `llm summarize-file-save` commands.

`llm status` remains provider-contact-free and does not require provider
contact to report configured providers, profiles, tasks, and route validity.

### CLI memory context v1 baseline

`python -m marcbot memory profiles` lists deterministic context profiles.

`python -m marcbot memory context --profile PROFILE` assembles bounded local
memory context using a named profile.

`python -m marcbot memory context --query QUERY --project PROJECT` assembles
bounded local memory context using explicit filters.

`python -m marcbot memory context --format json --query QUERY` returns the
same context as structured JSON.

The v1 context interface is read-only, SQLite-backed, and provider-contact-free.
It does not write memory, approve proposals, or contact an LLM provider.

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


`python -m marcbot memory candidate proposal-preview [--project PROJECT] TEXT`
previews whether candidate text would become a pending fact proposal.
It is read-only, provider-contact-free, and writes no memory. Use
`--format json` for structured output.


`python -m marcbot memory candidate propose --project PROJECT TEXT`
creates a pending fact proposal only when candidate preview classifies the
text as `propose_fact`. It is CLI-only, provider-contact-free, and does not
approve durable memory.

`--format json` returns a structured result with `created`, `proposal_id`,
`proposal_path`, `provider_contact`, and `writes` fields.

### Memory candidate preview

`python -m marcbot memory candidate preview [--project PROJECT] TEXT`
previews how MarcBot would classify text for memory handling. It is
read-only, provider-contact-free, and writes no memory.

`--format json` returns the same preview as structured JSON for future
workflow automation.

`--format json` returns the same preview as structured JSON for future
workflow automation.

### Telegram memory candidate preview

`/memory_candidate_preview <project> | <text>` previews how MarcBot would
classify text for memory handling. It is read-only, provider-contact-free,
and writes no memory.

Example:

```text
/memory_candidate_preview source-monitor | Source-monitor summaries should use explicit memory profiles.
```

### Telegram memory candidate proposal preview

`/memory_proposal_preview <project> | <text>` previews whether
candidate text would become a pending fact proposal. It is read-only,
provider-contact-free, and writes no memory.

Example:

```text
/memory_proposal_preview source-monitor | Source-monitor summaries should use explicit memory profiles.
```

### Telegram memory candidate propose


This command has been validated with a non-write case and a
write-pending-proposal case. The write case creates only a pending
proposal; durable approval remains CLI-only.
`/memory_candidate_propose <project> | <text>` creates a pending fact
proposal only when deterministic candidate preview classifies the text as
`propose_fact`. It is provider-contact-free and does not approve durable
memory.

Example:

```text
/memory_candidate_propose source-monitor | Source-monitor summaries should use explicit memory profiles.
```

For non-proposal candidates, the command reports `Created: no` and writes
nothing.

### CLI memory candidate record-event validation

The record-event bridge has been live-tested. Non-event candidate text writes
nothing. Event-like candidate text records a local memory event in the monthly
JSONL event log and keeps SQLite validation valid.

This command is intended for low-risk operational event capture only. It does
not create or approve durable facts.

### CLI memory candidate record-event

`python -m marcbot memory candidate record-event --project PROJECT TEXT`
records a memory event only when deterministic candidate preview classifies
the text as `record_event`. It is CLI-only and provider-contact-free.

`--format json` returns `created`, `event_index`, `event_path`,
`provider_contact`, and `writes` fields. `event_index` is currently
`null`; use `event_path` as the stable created-event log file identifier.
Events are stored in monthly JSONL files.

This command records low-risk operational events only. It does not create
or approve durable facts.

### CLI memory candidate propose JSON output

`python -m marcbot memory candidate propose --format json --project PROJECT TEXT`
returns a structured result for future automation.

Important fields:

- `created`: whether a pending proposal was created
- `proposal_id`: the pending proposal id, or `null`
- `proposal_path`: the pending proposal file path, or `null`
- `provider_contact`: always `false` for this deterministic command
- `writes`: whether the command wrote a pending proposal

The command writes only when candidate classification returns `propose_fact`.
It creates a pending proposal only; it does not approve durable memory.

### Telegram memory candidate help

`/memory_candidate_help` explains the memory candidate workflow from
Telegram. It is read-only, provider-contact-free, and writes no memory.

The help text summarizes:

- `/memory_candidate_preview`
- `/memory_proposal_preview`
- `/memory_candidate_propose`
- `/memory_proposals`
- `/memory_proposal <id>`
- `/memory_reject_proposal`

### Telegram memory candidate status

`/memory_candidate_status` summarizes the memory candidate workflow and
its safety boundaries from Telegram. It is read-only, provider-contact-free,
and writes no memory.

It lists the candidate preview, proposal preview, candidate propose,
proposal list/detail, and proposal rejection commands, and states that
Telegram cannot approve durable facts.

### CLI memory proposal approve event

`python -m marcbot memory proposal approve --id PROPOSAL_ID --source SOURCE --confidence high`

When the pending proposal has `proposed_type = "event"`, approval creates
a memory event through the existing event ledger, marks the proposal approved,
and records review/audit metadata. This remains CLI-only and
provider-contact-free.

The default approved event type is `workflow_completed`. Direct event writes
with a more specific event type can still use the CLI memory event add command
or the controlled candidate record-event workflow.

Telegram cannot approve durable memory proposals.

### CLI memory proposal approve summary

`python -m marcbot memory proposal approve --id PROPOSAL_ID --source SOURCE --confidence high`

When the pending proposal has `proposed_type = "summary"`, approval creates
a memory summary, marks the proposal approved, and records review/audit
metadata. The proposal statement becomes the summary title. Proposal details
become the summary body when present; otherwise the proposal rationale is used.

This remains CLI-only and provider-contact-free. Telegram cannot approve
durable memory proposals.

### CLI memory proposal list review details

`python -m marcbot memory proposal list --status pending`

Proposal list output includes the proposal source, rationale, optional details,
review timestamp, review reason, and backing file path when present. This makes
CLI review safer now that fact, event, and summary proposals can all be
approved from the CLI.

This remains read-only and provider-contact-free.

### CLI memory proposal detail review fields

`python -m marcbot memory proposal get --id PROPOSAL_ID`

Proposal detail output includes source, rationale, optional details, review
timestamp, review reason, backing file path, and provider-contact status. This
keeps single-proposal review consistent with proposal list output.

This remains read-only and provider-contact-free.
### CLI memory context detail text output

`python -m marcbot memory context --query QUERY` includes fact and event
details in text output when those records have details. This keeps
troubleshooting/debug/fix context useful in the human-readable CLI output,
not only in JSON.

This remains read-only, SQLite-backed, and provider-contact-free.
## Workflow registry CLI commands

`python -m marcbot workflow list` lists approved workflow definitions.

`python -m marcbot workflow show WORKFLOW_ID` shows one approved workflow
definition, including provider-contact, artifact, memory, and Telegram
execution boundaries.

Workflow registry v1 is read-only and provider-contact-free. It does not run
workflows. Execution is deferred to workflow run v1.
### Workflow run CLI command

`python -m marcbot workflow run source-monitor-ai-report --project ai` runs
the approved source-monitor report workflow.

Workflow run v1 supports `source-monitor-ai-report`. Workflow run v2 adds
`source-monitor-ai-summary`, which uses the existing source-monitor
summarize-latest path and explicitly discloses provider contact. Workflow
runs remain CLI-only and do not write memory.

Example summary workflow:

```text
python -m marcbot workflow run source-monitor-ai-summary --project ai --memory-profile source-monitor
```
### Workflow status CLI command

`python -m marcbot workflow status WORKFLOW_ID --project ai` shows
read-only workflow status and artifact visibility for registered
source-monitor workflows.

Workflow status is provider-contact-free and does not run workflows, write
artifacts, write memory, or expose Telegram execution.

### Workflow artifacts CLI command

`python -m marcbot workflow artifacts WORKFLOW_ID --project ai` shows
recent artifact IDs for a registered workflow.

Examples:

```text
python -m marcbot workflow artifacts source-monitor-ai-report --project ai
python -m marcbot workflow artifacts source-monitor-ai-summary --project ai
```

Workflow artifact visibility is CLI-only, read-only, and
provider-contact-free. It does not run workflows, write artifacts, write
memory, send files, or expose Telegram workflow execution.

### Telegram workflow visibility commands

`/workflow_list` lists approved workflow definitions from Telegram.

`/workflow_status <workflow-id>` shows read-only workflow status and
artifact visibility for the fixed `ai` project from Telegram.

`/workflow_artifacts <workflow-id>` shows read-only workflow artifact IDs
for the fixed `ai` project from Telegram.

`/workflow_send_artifact <workflow-id> <artifact-id>` sends an existing
approved workflow artifact from Telegram by safe workflow/artifact ID pair.
The command is intentionally explicit: report workflows require `report:...`
artifact IDs, and summary workflows require `summary:...` artifact IDs.

Example:

```text
/workflow_send_artifact source-monitor-ai-report report:2026-05-26-113618
/workflow_send_artifact source-monitor-ai-summary summary:2026-05-24-113518
```

Telegram workflow visibility and bounded artifact sending are
provider-contact-free and do not write memory or approve durable memory
changes. Telegram workflow execution is limited to the explicitly approved
deterministic report workflow described below.

### Telegram workflow execution command

`/workflow_run source-monitor-ai-report` runs the approved deterministic
source-monitor report workflow for the fixed `ai` project from Telegram.

This command is intentionally narrow: it accepts exactly one workflow ID,
allows only `source-monitor-ai-report`, contacts no providers, writes one
report artifact through the existing workflow implementation, and writes no
memory. `/workflow_run source-monitor-ai-summary` now returns a
provider-contact preflight from Telegram, but the provider-contacting summary
workflow remains CLI-only until an explicit confirmation path, timeout/error
behavior, and Telegram UX are implemented.

### Provider-contact workflow commands

`source-monitor-ai-summary` is provider-contacting and remains disabled for Telegram execution.

Current Telegram behavior:

    /workflow_run source-monitor-ai-summary

This command performs provider-contact preflight only. It issues a short-lived in-memory confirmation token and shows the planned confirmation command. It does not contact providers, run the workflow, write artifacts, or write memory.

Current confirmation behavior:

    /workflow_confirm source-monitor-ai-summary CONFIRMATION_TOKEN

This command validates and consumes the token, but remains non-executing. A valid token reports:

- Status: validated
- Provider contact: no
- Workflow ran: no
- Writes: no

Invalid confirmations report `Status: rejected` with a bounded reason. Invalid cases include unknown tokens, expired tokens, reused tokens, wrong-chat tokens, malformed requests, unsupported workflow IDs, and unauthorized chats.

The command must not accept arbitrary project names, memory profile names, prompts, URLs, file paths, provider names, model names, task routes, shell commands, or workflow arguments.

Future execution enablement must remain fixed to:

- workflow: `source-monitor-ai-summary`
- project: `ai`
- memory profile: `source-monitor`

When execution is eventually enabled, a successful response should report:

- Status: executed
- Provider contact: yes
- Workflow ran: yes
- Writes: summary artifact
- Artifact: `summary:...`

Failure responses must remain bounded and must not expose arbitrary paths, raw prompts, provider keys, local config, environment values, stack traces, unrestricted logs, or full provider internals.


In MarcBot 0.3.38, a Telegram-safe summary execution adapter exists for future `/workflow_confirm` execution enablement. `/workflow_confirm` behavior is unchanged in this milestone: it validates tokens but does not run `source-monitor-ai-summary`, contact providers, write artifacts, or write memory.

In MarcBot 0.3.39, `/workflow_confirm source-monitor-ai-summary CONFIRMATION_TOKEN` executes the provider-contacting summary workflow after a valid token is consumed. Execution uses the fixed Telegram-safe adapter only. Invalid confirmations are rejected before provider contact. Telegram still accepts no arbitrary project, prompt, URL, path, provider, model, task route, memory query, or workflow arguments.

In MarcBot 0.3.40, Telegram summary execution uses zero memory-context limits to preserve the LLM prompt-size safety cap. The command remains fixed to the approved summary workflow path and still accepts no arbitrary execution arguments.
