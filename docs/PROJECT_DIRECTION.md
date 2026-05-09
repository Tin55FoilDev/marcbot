# MarcBot Project Direction

This document clarifies the intended direction for MarcBot so future development sessions do not mistake the project for a simple cron wrapper, narrow report bot, or unrestricted shell agent.

MarcBot is intended to become Marc's personal, stable, inspectable replacement for the parts of OpenClaw he actually uses. The goal is not to clone every OpenClaw feature. The goal is to build a smaller personal agent system with the capabilities Marc needs, using tighter boundaries, clearer tests, slower development, and better long-term reliability.

## Core purpose

MarcBot should eventually support:

- Telegram-based interaction
- model-selectable chat
- model-selectable command and workflow execution
- local model usage through LM Studio or similar local providers
- frontier model usage through subscription/OAuth-style access if a stable implementation path is available
- project-oriented workflows
- scheduled jobs where useful
- controlled file and report generation
- controlled retrieval and delivery of saved artifacts
- durable memory later, with auditability and correction workflows

MarcBot should not be limited to pre-programmed cron jobs.

Cron and systemd timers are useful execution mechanisms, but they are not the entire product. The product target is a personal Telegram-facing agent shell for chat, projects, commands, workflows, saved artifacts, and eventually auditable memory.

## Why MarcBot exists

Marc likes many OpenClaw capabilities, especially:

- Telegram access
- chat with strong models
- model routing
- project assistance
- command execution
- scheduled jobs
- local and frontier model options

The problem is operational stability.

OpenClaw continues to add features Marc does not need and sometimes breaks features Marc does use. MarcBot exists to preserve the useful operating model while reducing churn, dependency surface, and surprise regressions.

## Non-goal: full OpenClaw clone

MarcBot should not try to replicate all OpenClaw features.

MarcBot should avoid:

- broad multi-user behavior
- arbitrary shell access from Telegram
- arbitrary file access from Telegram
- arbitrary internet browsing from Telegram
- hidden autonomous behavior
- large dependency chains without clear need
- rapid feature growth without tests
- features Marc does not actually use

Every capability should be narrow, reviewed, documented, testable, and useful to Marc.

## Interaction model

Detailed interaction-mode rules live in `docs/INTERACTION_MODEL.md`.


MarcBot should develop toward four distinct interaction modes.

### 1. Command mode

Command mode means Marc uses a specific Telegram slash command or CLI command with bounded arguments.

Examples:

- `/status`
- `/health`
- `/git`
- `/llm_status`
- `/report_status`
- `/report_status source ai`
- `/send_latest_report`

Command mode should be narrow, predictable, and easy to document. Commands should clearly state whether they are read-only, whether they contact a model provider, and whether they can be used from Telegram.

### 2. Workflow mode

Workflow mode means MarcBot runs a named, approved multi-step workflow.

A workflow may combine deterministic code, local files, scheduled execution, report generation, and bounded LLM analysis. Workflows should be built from tested CLI or internal functions before Telegram exposure.

Examples:

- generate a source-monitor report for a named project
- summarize the generated report through a configured LLM task route
- save the summary as a workspace artifact
- report status through Telegram
- deliver a previously generated report or summary

Workflow mode is not arbitrary tool use. The workflow name, inputs, output paths, model task routes, and safety boundaries should be known before Telegram exposure.

### 3. Chat mode

Chat mode means Marc has a controlled Telegram conversation with a selected approved model profile.

Chat is a real long-term goal. However, normal chat should not automatically execute shell commands, browse arbitrary URLs, read arbitrary files, write files, or modify system state.

A future chat model may discuss commands, explain reports, draft plans, or suggest workflows. Executing server actions should remain routed through approved commands or workflows.

Possible future shape:

- `/chat_start <approved_profile>`
- `/chat_stop`
- `/chat_status`
- `/chat_profile`
- bounded context behavior
- explicit transcript handling
- explicit memory rules
- no automatic shell access
- no automatic unrestricted file access
- no automatic unrestricted internet access

Chat mode should be designed separately before implementation.

### 4. Development mode

Development mode is the process Marc uses with an AI assistant over SSH/Git to modify the MarcBot repository.

Development mode is not the same as runtime Telegram autonomy. In development mode, Marc reviews proposed changes, runs commands as `adminuser` or `marc` as appropriate, runs `./scripts/check.sh`, reviews diffs, commits, pushes, restarts services when needed, and validates Telegram behavior.

Development mode may eventually be assisted by MarcBot, but it should remain controlled, inspectable, and Git-backed.

## Project development model

Detailed project lifecycle rules live in `docs/PROJECT_WORKFLOW_LIFECYCLE.md`.


New MarcBot projects should be developed in small, testable layers.

Preferred sequence:

1. Define the project goal and safety boundaries.
2. Define where local configuration, state, reports, summaries, and logs will live.
3. Build deterministic CLI commands first.
4. Add validation and status commands early.
5. Add LLM-backed steps only where a model adds clear value.
6. Route model use through named tasks and named profiles.
7. Save outputs as workspace artifacts.
8. Add tests and documentation.
9. Expose read-only Telegram status first.
10. Expose controlled Telegram actions only after CLI behavior is stable.
11. Add scheduling only after manual execution is reliable.
12. Keep Git clean after each milestone.

This model applies to source monitoring, future stock research, future memory work, and any other project-oriented workflow.

## Model-provider direction

MarcBot should support both local and frontier models.

Local models are useful for:

- heartbeat checks
- low-risk utility tasks
- small structured classification
- simple summaries
- testing new model candidates
- backup or status-adjacent tasks where quality requirements are modest

Frontier models are preferred for:

- open-ended chat
- research
- planning
- ambiguous analysis
- source-monitor synthesis
- project development assistance
- adversarial or noisy source interpretation
- long-context tasks

Capabilities should depend on named profiles, not raw provider or model IDs.

Example profile categories:

- `local_fast`
- `local_careful`
- `local_experimental`
- `frontier_chat`
- `frontier_analysis`
- `frontier_development`

## Frontier-model access requirement

Marc does not plan to use per-call OpenAI API billing for MarcBot.

MarcBot should therefore investigate a stable way to use frontier models through subscription/OAuth-style access, similar in purpose to how OpenClaw currently uses `openai-codex/gpt-5.5`.

This does not mean MarcBot should call OpenClaw as a backend worker. OpenClaw may be studied as a reference point, but MarcBot should avoid becoming dependent on OpenClaw runtime behavior.

Preferred long-term direction:

- understand the OpenClaw-style Codex/OAuth provider mechanism
- determine whether MarcBot can implement or use a stable supported client path
- keep credentials outside Git
- avoid exposing credentials through Telegram, logs, reports, memory, or generated artifacts
- test provider access through CLI-only commands first
- expose Telegram chat only after the provider boundary is reliable

Fallback direction:

- continue using local LM Studio profiles for bounded local workflows
- defer frontier-model MarcBot runtime integration until a safe implementation path is found

## Command and workflow routing

MarcBot should eventually allow commands and workflows to specify which model profile they use.

Examples:

- a heartbeat or utility workflow may use `local_fast`
- a source-monitor summary may use `frontier_analysis` or `local_careful`
- a development-assistance chat may use `frontier_development`
- a local model test workflow may use `local_experimental`

The routing layer should be explicit and inspectable.

A future task-route status command should answer:

- which task uses which profile
- which provider backs each profile
- whether the provider is local or frontier
- whether a command contacts a model
- whether a command is read-only
- whether the command can be used from Telegram

## Safety principles

MarcBot should remain:

- personal-only
- explicit
- testable
- secure by default
- narrow in each feature
- easy to back up and restore
- documented enough that a new AI-assisted session can resume quickly

MarcBot should not surprise Marc.

A feature is not complete until:

- behavior is documented
- tests pass
- `./scripts/check.sh` passes
- service behavior is validated when Telegram-facing
- logs are checked when Telegram-facing
- Git is clean
- the change is pushed

## Near-term documentation direction

Before more feature coding, the docs should clarify:

1. project direction
2. interaction model
3. model routing
4. project workflow design
5. frontier-model research boundaries
6. Telegram chat safety boundaries
7. command and workflow exposure rules

Implementation should resume after the docs give future sessions a clear, consistent path.
