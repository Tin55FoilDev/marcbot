# MarcBot Project Direction

This document clarifies the intended direction for MarcBot so future development sessions do not mistake the project for a simple cron wrapper or narrow report bot.

MarcBot is intended to become Marc’s personal, stable, inspectable replacement for the parts of OpenClaw he actually uses.

The goal is not to clone every OpenClaw feature. The goal is to build a smaller personal agent system with the capabilities Marc needs, using tighter boundaries, clearer tests, slower development, and better long-term reliability.

## Core purpose

MarcBot should eventually support:

- Telegram-based interaction
- model-selectable chat
- model-selectable command execution
- local model usage through LM Studio or similar local providers
- frontier model usage through subscription/OAuth-style access if a stable implementation path is available
- project-oriented workflows
- scheduled jobs where useful
- controlled file/report generation
- controlled retrieval and delivery of saved artifacts
- durable memory later, with auditability and correction workflows

MarcBot should not be limited to pre-programmed cron jobs. Cron and systemd timers are useful execution mechanisms, but they are not the entire product.

The product target is a personal Telegram-facing agent shell for chat, projects, commands, and workflows.

## Why MarcBot exists

Marc likes many OpenClaw capabilities, especially:

- Telegram access
- chat with strong models
- model routing
- project assistance
- command execution
- scheduled jobs
- local and frontier model options

The problem is operational stability. OpenClaw continues to add features Marc does not need and sometimes breaks features Marc does use.

MarcBot exists to preserve the useful operating model while reducing churn, dependency surface, and surprise regressions.

## Non-goal: full OpenClaw clone

MarcBot should not try to replicate all OpenClaw features.

MarcBot should avoid:

- broad multi-user behavior
- arbitrary shell access from Telegram
- arbitrary file access from Telegram
- hidden autonomous behavior
- large dependency chains without clear need
- rapid feature growth without tests
- features Marc does not actually use

Every capability should be narrow, reviewed, documented, testable, and useful to Marc.

## Interface model

Telegram is the primary user interface.

Over time, Telegram should support three broad interaction types:

1. Status and inspection commands
2. Approved workflow commands
3. Controlled chat sessions with selected approved models

The current safe pattern remains:

- build CLI capability first
- test locally
- document behavior
- add Telegram exposure only when the command boundary is clear
- keep Telegram arguments bounded and validated
- avoid unrestricted prompt/file/shell access until a separate safety design exists

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

Capabilities should depend on named profiles, not raw provider/model IDs.

Examples:

- `local_fast`
- `local_careful`
- `local_experimental`
- `frontier_chat`
- `frontier_analysis`
- `frontier_development`

## Frontier-model access requirement

Marc does not plan to use per-call OpenAI API billing for MarcBot.

MarcBot should therefore investigate a stable way to use frontier models through subscription/OAuth-style access, similar in purpose to how OpenClaw currently uses `openai-codex/gpt-5.5`.

This does not mean MarcBot should call OpenClaw as a backend worker.

Preferred long-term direction:

- understand the OpenClaw-style Codex/OAuth provider mechanism
- determine whether MarcBot can implement or reuse a stable supported client path
- keep credentials outside Git
- avoid exposing credentials through Telegram, logs, reports, memory, or generated artifacts
- test through CLI-only commands first
- expose Telegram chat only after the provider boundary is reliable

Fallback direction:

- continue using local LM Studio profiles for bounded local workflows
- defer frontier-model MarcBot runtime integration until a safe implementation path is found

## Command and workflow routing

MarcBot should eventually allow commands and workflows to specify which model profile they use.

Examples:

- a heartbeat/status workflow may use `local_fast`
- a source-monitor summary may use `frontier_analysis`
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

## Chat direction

MarcBot should eventually support controlled Telegram chat with selected approved models.

This is a real project goal, not an accidental feature.

However, chat should be added deliberately.

A possible future shape:

- `/chat_start <profile>`
- `/chat_stop`
- `/chat_status`
- `/model` or equivalent profile selection only from an allowlist
- bounded context behavior
- explicit transcript/memory rules
- no automatic shell/file access from normal chat
- project-specific chat modes only after project boundaries are designed

Chat is separate from command execution.

A chat model may discuss a command or workflow, but executing server actions should remain routed through approved MarcBot commands.

## Development sequence

Near-term development should prioritize clarity before more automation.

Recommended order:

1. Clarify project direction in documentation.
2. Research OpenClaw-style Codex/OAuth model-provider implementation.
3. Decide whether MarcBot can safely support subscription/OAuth frontier profiles directly.
4. Keep local model profile support working.
5. Add task/profile routing metadata.
6. Add one bounded LLM-assisted workflow from CLI.
7. Add saved artifact review and retrieval.
8. Add Telegram exposure for saved artifacts.
9. Add controlled Telegram chat only after model-provider and safety boundaries are reviewed.

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
- logs are checked
- Git is clean
- the change is pushed
