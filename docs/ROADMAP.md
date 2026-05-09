# MarcBot Roadmap

This roadmap tracks the intended development path for MarcBot.

MarcBot is not intended to be only a cron/report wrapper. The long-term target is a personal-only Telegram-facing agent shell with approved commands, approved workflows, model-selectable execution, controlled artifact handling, and future auditable memory.

See also:

- `docs/PROJECT_DIRECTION.md`
- `docs/WORKFLOW_MODEL.md`
- `docs/LLM.md`
- `docs/MEMORY.md`
- `docs/COMMANDS.md`

## Current baseline

Current baseline: MarcBot 0.3.2.

MarcBot currently has:

- a personal-only Telegram bot service
- allowlisted Telegram chat IDs
- bounded Telegram commands
- health/status/version/help commands
- git/status/report/doc/file helper commands
- backup and timer status commands
- source-monitor CLI and scheduled report support
- LLM profile/config plumbing
- CLI-only LLM provider contact commands
- read-only `/llm_status`
- docs covering security, deployment, architecture, commands, LLMs, memory, and workflow model

## Current direction

The immediate direction is documentation and architecture clarification before further feature coding.

Near-term priority:

1. clarify the project direction
2. clarify interaction modes
3. clarify project development workflow
4. clarify command/workflow/model boundaries
5. clarify frontier-model research assumptions
6. remove stale or contradictory documentation
7. then resume small, tested feature increments

## Interaction modes

MarcBot should develop toward four distinct interaction modes.

### Command mode

Command mode is the current mature surface.

It means Marc invokes a specific Telegram slash command or CLI command with bounded behavior.

Command mode should stay narrow and explicit. Each command should be documentable as:

- read-only or state-changing
- Telegram-facing or CLI-only
- model-contacting or non-model-contacting
- provider-secret-loading or provider-secret-free
- artifact-producing or status-only

### Workflow mode

Workflow mode is the next major operating model.

A workflow is a named, approved multi-step process built from tested components.

A workflow may:

- read approved configuration
- read approved source data
- generate reports
- call an approved LLM task route
- save artifacts
- report status
- deliver selected artifacts through Telegram

A workflow is not arbitrary shell access or arbitrary tool use.

### Chat mode

Chat mode is a long-term goal.

Chat mode means a controlled Telegram conversation with a selected approved model profile. Chat should be able to discuss project state, explain artifacts, help plan workflows, and eventually assist with controlled operations.

Initial chat design should assume:

- no automatic shell execution
- no unrestricted file access
- no unrestricted internet access
- no automatic persistent memory writes
- no direct secret exposure
- no implicit workflow execution
- explicit start/stop/status behavior
- explicit model/profile selection

Chat mode must be designed before implementation.

### Development mode

Development mode is the current human-supervised process where Marc and an AI assistant modify MarcBot over SSH/Git.

Development mode should remain:

- Git-backed
- reviewable
- test-gated
- commit/push based
- service-validated for Telegram-facing changes

Future MarcBot features may assist development, but runtime Telegram autonomy should not be confused with the current development process.

## Near-term roadmap

### 1. Documentation cleanup

Status: current priority.

Tasks:

- make `docs/PROJECT_DIRECTION.md` the project north-star document
- align `docs/ROADMAP.md` with the direction document
- update `docs/ARCHITECTURE.md` to avoid stale duplicated command lists
- update `docs/COMMANDS.md` with the current command surface
- update `docs/LLM.md` with frontier-model research boundaries
- update `docs/CHANGELOG.md` with the docs-direction milestone
- keep `docs/WORKFLOW_MODEL.md` and `docs/MEMORY.md` aligned with the direction document

### 2. Interaction-model design

Status: next design discussion after docs cleanup.

Questions to answer:

- What should Telegram chat be allowed to do?
- How should chat start, stop, and select a model?
- How should chat refer to saved artifacts?
- Can chat propose workflows?
- How does Marc approve a workflow proposed by chat?
- What state is retained between chat sessions?
- What state is explicitly not retained?
- What should be logged?
- What must never be logged?

Expected output:

- update `docs/PROJECT_DIRECTION.md`
- possibly add `docs/INTERACTION_MODEL.md`
- update `docs/ARCHITECTURE.md`
- update `docs/COMMANDS.md`

### 3. Model routing and task routes

Status: partially implemented for CLI LLM use; needs design refinement.

Current principle:

- `/llm_status` is read-only
- `/llm_status` does not contact providers
- `/llm_status` does not load provider secrets
- explicit provider contact remains CLI-only through commands such as:
  - `python -m marcbot llm models <provider>`
  - `python -m marcbot llm health <profile>`

Future design should clarify:

- profile categories
- task-route names
- which task uses which profile
- which commands contact models
- which workflows contact models
- whether a task route is local-only, frontier-capable, or experimental
- how failed model access is reported

### 4. Frontier-model access research

Status: research track only.

Marc does not plan to use per-call OpenAI API billing for MarcBot.

MarcBot should investigate whether a safe, stable, supportable subscription/OAuth-style frontier model path is available, similar in purpose to OpenClaw's current `openai-codex/gpt-5.5` usage.

Research boundaries:

- do not store secrets in Git
- do not paste secrets into chat
- do not expose secrets through Telegram
- do not expose secrets through logs, reports, or memory
- prefer CLI-only explicit experiments first
- do not make MarcBot depend on OpenClaw as a backend worker
- document findings before implementation

### 5. Source-monitor artifact improvements

Status: later, after docs cleanup.

Useful next increments may include:

- list latest source-monitor reports
- list latest source-monitor summaries
- improve `/report_status source ai`
- deliver specific recent source-monitor artifacts through Telegram
- compare local and frontier summary profiles once frontier access is resolved
- keep scheduled jobs separate from interactive workflow design

### 6. Controlled Telegram workflow execution

Status: future.

Possible future commands:

- `/workflow_list`
- `/workflow_status <name>`
- `/workflow_run <name>`
- `/workflow_result <name>`
- `/workflow_send <artifact-id>`

These should only expose approved workflows with bounded arguments.

### 7. Controlled Telegram chat

Status: future, design first.

Possible future commands:

- `/chat_start <profile>`
- `/chat_stop`
- `/chat_status`
- `/chat_profile`
- `/chat_clear`
- `/chat_context`

Chat should be useful, but should not become hidden arbitrary command execution.

### 8. Durable memory

Status: future.

Memory should reduce Marc's burden, but only with strong guardrails.

The memory design should include:

- auditability
- correction
- deletion
- reviewable updates
- clear difference between transient chat context and durable memory
- no secrets
- no unreviewed sensitive data capture
- no hidden permanent writes

See `docs/MEMORY.md`.

## Development discipline

For every milestone:

1. make a small change
2. update docs if behavior or direction changes
3. run `./scripts/check.sh`
4. review diffs
5. restart and validate service behavior when Telegram-facing
6. inspect logs when Telegram-facing
7. commit
8. push
9. keep the repo clean

MarcBot should grow slowly, with reliability and inspectability ahead of feature count.
