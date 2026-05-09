# MarcBot Interaction Model

This document defines how MarcBot should behave when Marc interacts with it through Telegram, CLI commands, approved workflows, future chat, and development sessions.

MarcBot is intended to be useful, not symbolic. It should be able to inspect real project state, approved files, reports, artifacts, and server status where those capabilities are explicitly designed and bounded.

The goal is controlled usefulness, not unrestricted autonomy.

See also:

- `docs/PROJECT_DIRECTION.md`
- `docs/ROADMAP.md`
- `docs/ARCHITECTURE.md`
- `docs/COMMANDS.md`
- `docs/WORKFLOW_MODEL.md`
- `docs/LLM.md`
- `docs/MEMORY.md`
- `docs/SECURITY.md`

## Core principles

MarcBot interaction should follow these principles:

1. Commands are explicit.
2. Workflows are named and approved.
3. Chat is conversational by default, not action-taking by default.
4. Models do not get raw shell access.
5. Models may access approved project files and artifact directories, but not unrestricted host files.
6. Telegram may expose approved server status and workflow controls, but not arbitrary server control.
7. State-changing actions require an approved command or workflow.
8. Project development remains Git-backed and human-reviewed.
9. Durable memory is a later subsystem and must be designed with auditability, correction, and deletion before automatic memory updates are enabled.
10. Secrets are never available to chat, reports, logs, memory, Telegram output, or generated artifacts.
11. Approved access should be useful: MarcBot should be able to inspect real project state, files, reports, and server status where those capabilities are explicitly designed and bounded.

## Interaction modes

MarcBot should develop around four interaction modes:

1. command mode
2. workflow mode
3. chat mode
4. development mode

These modes may work together, but they should not be blurred.

For example, chat may eventually propose a workflow, but workflow execution should still happen through an approved workflow path. Development mode may use MarcBot docs and generated artifacts, but code changes should remain Git-backed and human-reviewed.

## Command mode

Command mode means Marc invokes a specific Telegram slash command or CLI command with bounded arguments.

Examples:

- `/status`
- `/health`
- `/service`
- `/timer_status`
- `/report_status`
- `/llm_status`
- `/docs`
- `/doc <name>`
- `/send <approved-path>`
- `python -m marcbot llm health <profile>`

Command mode should be:

- explicit
- predictable
- documented
- testable
- bounded by allowlists where appropriate
- clear about whether it is read-only or state-changing
- clear about whether it contacts a model provider
- clear about whether it loads provider secrets

A command should not unexpectedly become a workflow, a shell, a file browser, or a hidden model call.

## Workflow mode

Workflow mode means MarcBot runs a named, approved multi-step process.

A workflow may combine:

- deterministic code
- approved configuration
- approved project files
- approved source data
- report generation
- artifact storage
- bounded LLM analysis
- scheduled execution
- Telegram status reporting
- Telegram artifact delivery

Workflow mode is not arbitrary tool use.

A workflow should define:

- name
- purpose
- allowed inputs
- allowed file paths
- output paths
- whether it can contact a model
- which task route or profile it uses
- whether it loads provider secrets
- whether it is CLI-only or Telegram-facing
- whether it is read-only or state-changing
- expected artifacts
- failure behavior
- tests
- documentation

Examples of future workflows:

- run a source-monitor project
- summarize a source-monitor report
- list recent artifacts for a project
- produce a system integrity report
- run a model comparison task
- generate a stock research packet
- prepare a project status summary

## Chat mode

Chat mode means Marc has a controlled Telegram conversation with a selected approved model profile.

Chat is a real long-term goal, but it must be designed before implementation.

Initial chat should be conversational by default. It may explain, summarize, plan, compare, draft, or propose. It should not automatically execute commands, modify files, browse arbitrary paths, browse arbitrary websites, or update durable memory.

A future chat session may be allowed to:

- answer questions
- discuss project direction
- explain reports
- summarize approved artifacts
- compare model outputs
- help plan a workflow
- propose an approved command
- propose an approved workflow
- draft documentation text
- help interpret server status returned by approved commands

A future chat session should not automatically:

- run shell commands
- edit files
- send files
- restart services
- install packages
- inspect arbitrary paths
- load secrets
- contact unapproved providers
- write durable memory
- run workflows without approval

Possible future chat commands:

- `/chat_start <profile>`
- `/chat_stop`
- `/chat_status`
- `/chat_profile`
- `/chat_clear`
- `/chat_context`

The exact commands should be designed later.

## Development mode

Development mode is the current process where Marc and an AI assistant modify MarcBot over SSH/Git.

Development mode is not runtime Telegram autonomy.

Development mode should remain:

- human-supervised
- Git-backed
- diff-reviewed
- test-gated
- committed in small milestones
- pushed after successful validation
- service-validated for Telegram-facing changes
- documented when behavior changes

Normal development flow:

1. discuss the goal
2. update or add docs first when direction changes
3. make a small code or docs change
4. run `./scripts/check.sh`
5. review diffs
6. restart services if Telegram-facing behavior changed
7. validate Telegram behavior if needed
8. inspect logs if needed
9. commit
10. push
11. keep the repo clean

MarcBot may eventually assist development, but the safe baseline is that development changes remain reviewable and explicit.

## File access model

MarcBot should be able to work with approved files. It should not have unrestricted host filesystem access from Telegram or chat.

Approved file access may include:

- MarcBot docs
- approved project workspaces under `/srv/marcbot`
- approved report directories
- approved source-monitor outputs
- approved generated summaries
- future artifact registry entries
- files explicitly passed into a CLI workflow
- files explicitly included in a project configuration

Default-deny file access should apply to:

- secret files
- token caches
- SSH keys
- arbitrary home directories
- arbitrary `/etc` files
- arbitrary host paths
- provider credential files
- environment files containing secrets
- files outside approved project/workspace/report structures

The long-term pattern should be:

- commands and workflows receive approved paths
- chat receives approved context or artifact references
- models see the content they need for the task
- models do not browse the host filesystem freely

## Server status model

MarcBot may expose approved server status through Telegram.

This is useful and expected.

Allowed server-status examples:

- MarcBot service status
- health summary
- timer status for approved timers
- report status
- bounded logs
- bounded tail output
- backup status
- disk or uptime summary if implemented safely

Not allowed by default:

- arbitrary shell command execution
- arbitrary systemd unit control
- arbitrary package installation
- arbitrary config editing
- arbitrary process management
- unrestricted log browsing
- unrestricted host diagnostics

Telegram should be useful for status and approved controls without becoming an unrestricted remote admin panel.

## Model access model

Model access should be routed through explicit provider, profile, and task-route configuration.

Preferred hierarchy:

- provider
- profile
- task route
- command or workflow

Example:

- provider: `lmstudio`
- profile: `local_fast`
- task route: `source_summary`
- workflow: `source-monitor run-summary ai`

Routine status commands should not unexpectedly contact providers.

Provider-contacting behavior should be explicit. In the current baseline, provider contact remains CLI-only unless a future feature deliberately changes that boundary.

Examples of explicit provider-contacting CLI commands:

- `python -m marcbot llm models <provider>`
- `python -m marcbot llm health <profile>`

A future Telegram model command should clearly say whether it contacts a model, loads provider secrets, wakes local models, or sends prompts.

## Approval model

MarcBot should distinguish suggestion from execution.

Suggested rule:

- chat can suggest
- commands can inspect
- workflows can act if approved and named
- development changes require Git review
- dangerous or broad operations remain CLI-only

Examples:

- Chat may say: "I recommend running the source-monitor summary workflow."
- Marc approves by invoking an approved command or workflow.
- The workflow runs known steps with known inputs.
- Results are saved as artifacts.
- Telegram may report status or send the approved artifact.

This keeps chat useful without making it implicitly action-taking.

## Artifact model

Artifacts are generated outputs such as reports, summaries, logs, comparisons, or project files.

Artifacts should be:

- stored in approved locations
- identified by safe names or IDs
- listed through approved commands
- sent through Telegram only when approved
- bounded by file size and path rules
- separated from secrets
- documented when tied to a workflow

Future artifact commands may include:

- `/artifact_list`
- `/artifact_status <id>`
- `/artifact_send <id>`
- `/workflow_result <name>`

The exact command names should be designed later.

## Memory model

Durable memory is a future subsystem.

MarcBot should eventually use memory to reduce Marc's burden, but automatic memory updates should not be quietly added as a side effect of chat, commands, or workflows.

Before durable memory is enabled, the design must define:

- what can be remembered
- what must never be remembered
- what requires explicit approval
- what may be inferred automatically
- how Marc reviews memory
- how Marc corrects memory
- how Marc deletes memory
- how memory changes are logged
- how secrets are excluded
- how sensitive data is handled

Until that design exists, chat and workflows should not perform hidden durable memory writes.

## Project-oriented workflow model

New projects should follow a repeatable development path.

Recommended lifecycle:

1. define the project goal
2. define safety boundaries
3. define configuration paths
4. define state paths
5. define artifact paths
6. build deterministic CLI behavior first
7. add tests
8. add docs
9. add status visibility
10. add artifact listing or retrieval
11. add LLM analysis only where it adds clear value
12. add scheduling only after manual runs are stable
13. add Telegram exposure only after CLI behavior is stable
14. add memory integration only after the memory subsystem exists

This pattern should apply to:

- source monitoring
- stock research
- system integrity reporting
- model comparison
- future personal knowledge tools
- future project assistants

## Non-goals

MarcBot interaction should not become:

- arbitrary Telegram shell access
- arbitrary Telegram file access
- arbitrary Telegram web browsing
- hidden autonomous development
- hidden durable memory capture
- unrestricted provider access
- unrestricted server administration
- a full OpenClaw clone

The goal is controlled usefulness through approved commands, approved workflows, approved files, approved models, and reviewable development.
