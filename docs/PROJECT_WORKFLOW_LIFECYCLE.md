# MarcBot Project Workflow Lifecycle

This document defines the preferred lifecycle for adding new MarcBot projects and workflows.

A MarcBot project is a bounded area of functionality with its own goal, configuration, state, artifacts, commands, tests, and documentation.

Examples may include:

- source monitoring
- system integrity reporting
- stock research
- model comparison
- personal knowledge tools
- future memory maintenance
- future report generation projects

The goal is to make each project useful without turning MarcBot into an unrestricted agent, shell, file browser, or hidden automation layer.

See also:

- `docs/PROJECT_DIRECTION.md`
- `docs/INTERACTION_MODEL.md`
- `docs/WORKFLOW_MODEL.md`
- `docs/ARCHITECTURE.md`
- `docs/COMMANDS.md`
- `docs/LLM.md`
- `docs/MEMORY.md`
- `docs/SECURITY.md`

## Core lifecycle

New MarcBot projects should move through small, reviewable stages.

Preferred lifecycle:

1. project idea
2. project charter
3. safety boundaries
4. configuration layout
5. state layout
6. artifact layout
7. deterministic CLI behavior
8. validation and status behavior
9. tests
10. documentation
11. manual run
12. artifact listing and retrieval
13. optional LLM task route
14. optional scheduling
15. optional Telegram status
16. optional Telegram workflow execution
17. optional memory integration
18. commit, push, and backup checkpoint as appropriate

Not every project needs every stage. However, projects should not skip directly from idea to Telegram automation.

## Stage 1: Project idea

A project starts with a plain-English goal.

The idea should answer:

- What is Marc trying to accomplish?
- What problem does this solve?
- How often will Marc use it?
- Is it interactive, scheduled, or both?
- What output should it produce?
- What should Marc be able to inspect later?

Example:

    Build a source-monitor project that checks approved AI sources, saves a report, optionally summarizes it with a selected model, and lets Marc retrieve the report through Telegram.

## Stage 2: Project charter

A project charter turns the idea into a bounded scope.

The charter should define:

- project name
- purpose
- non-goals
- expected users
- expected commands
- expected workflows
- expected artifacts
- whether it is CLI-only, Telegram-facing, scheduled, or mixed
- whether it needs model access
- whether it may eventually use memory

The charter should be written before implementation when the project is substantial.

For small changes, the charter may be a short section in an existing doc.

## Stage 3: Safety boundaries

Every project needs explicit boundaries.

Define:

- allowed input sources
- allowed configuration files
- allowed state directories
- allowed artifact directories
- allowed Telegram commands, if any
- allowed model profiles, if any
- allowed network access, if any
- allowed file reads
- allowed file writes
- forbidden paths
- forbidden actions
- secret-handling rules

Default assumptions:

- no arbitrary shell access from Telegram
- no arbitrary host file access from Telegram
- no unrestricted model access
- no secrets in Git
- no secrets in Telegram
- no secrets in logs
- no secrets in reports
- no secrets in memory

## Stage 4: Configuration layout

Each project should have an explicit configuration layout.

Configuration should define what the project is allowed to do.

Possible locations:

- `/srv/marcbot/config/<project>.toml`
- `/srv/marcbot/source-projects/<name>/config/<project>.toml`
- repository defaults for non-secret examples
- local runtime config for machine-specific values

Configuration should separate:

- non-secret config
- secret config
- environment-specific config
- project-specific config
- shared MarcBot config

Secrets should remain outside Git.

## Stage 5: State layout

Each project should define where runtime state lives.

State may include:

- last run timestamps
- cache files
- source fetch metadata
- run records
- retry records
- local indexes
- temporary working files

State should be separate from:

- source configuration
- generated artifacts
- logs
- secrets
- Git-tracked code

State should be safe to inspect and safe to delete when practical, or documented when not safe to delete.

## Stage 6: Artifact layout

Each project should define its artifact outputs.

Artifacts may include:

- Markdown reports
- text reports
- JSON summaries
- PDF outputs
- model summaries
- comparison reports
- status snapshots
- exported project files

Artifact rules:

- artifacts live under approved MarcBot-controlled directories
- artifact names should be predictable and safe
- artifacts should not contain secrets
- artifacts should be retrievable through bounded commands
- artifacts should be documented
- large artifacts should have size limits or delivery rules

Future artifact handling may use an artifact registry with IDs.

## Stage 7: Deterministic CLI behavior

Build deterministic CLI behavior before Telegram exposure.

A CLI command should exist for the core operation before adding scheduling or Telegram access.

Good CLI behavior:

- explicit arguments
- clear output
- clear error messages
- non-zero exit on failure
- no raw tracebacks for expected errors
- logs enough detail for debugging
- does not require Telegram
- can be run manually by Marc

Example pattern:

    python -m marcbot <project> validate
    python -m marcbot <project> status
    python -m marcbot <project> run
    python -m marcbot <project> list-artifacts

Actual command names may differ by project.

## Stage 8: Validation and status behavior

Validation and status commands should be added early.

Validation should answer:

- Is the config readable?
- Are required paths present?
- Are required sources configured?
- Are required profiles configured?
- Are output directories writable?
- Are secrets missing, if a command explicitly requires them?

Status should answer:

- When did the project last run?
- Did it succeed?
- Where are the latest artifacts?
- Are there recent failures?
- Is the scheduled timer active, if applicable?
- Does the project need attention?

Status commands should avoid provider contact unless explicitly documented.

## Stage 9: Tests

Each project should include tests before becoming Telegram-facing or scheduled.

Tests should cover:

- config parsing
- invalid config
- path validation
- artifact path creation
- status output
- expected failure messages
- command argument parsing
- no secret leakage
- no unsafe path traversal
- no accidental provider contact in read-only status paths

Provider-contacting tests should be opt-in or CLI-driven. Normal `./scripts/check.sh` should not depend on LM Studio, internet access, or frontier provider availability.

## Stage 10: Documentation

Documentation should be updated with the project.

Project docs should explain:

- purpose
- configuration
- commands
- workflows
- artifacts
- scheduling
- Telegram exposure
- model usage
- failure modes
- safety boundaries
- restore considerations

Relevant docs may include:

- `docs/COMMANDS.md`
- `docs/ARCHITECTURE.md`
- `docs/WORKFLOW_MODEL.md`
- `docs/LLM.md`
- `docs/SECURITY.md`
- project-specific docs such as `docs/SOURCE_MONITOR.md`
- `docs/CHANGELOG.md`

## Stage 11: Manual run

A project should be manually runnable before scheduling or Telegram execution.

Manual run should verify:

- config loads
- paths work
- outputs are created
- logs are useful
- failure behavior is understandable
- artifacts are inspectable
- cleanup behavior is understood

Manual run is the first real operational proof.

## Stage 12: Artifact listing and retrieval

After artifacts exist, add safe listing and retrieval behavior.

Artifact listing should be bounded by:

- project name
- approved artifact directory
- safe path normalization
- file type expectations
- size limits
- predictable names or IDs

Telegram retrieval should not expose arbitrary file paths.

Future preferred pattern:

    list artifacts by safe ID
    send artifact by safe ID

Rather than:

    send any host path typed into Telegram

## Stage 13: Optional LLM task route

LLM use should be added only where it provides clear value.

Good LLM uses:

- summarization
- classification
- comparison
- explanation
- synthesis
- drafting
- project planning
- source interpretation

LLM use should define:

- task route name
- approved profile
- provider-contact behavior
- input files or text
- output artifact
- timeout behavior
- failure behavior
- whether it is CLI-only or Telegram-facing
- whether it loads provider secrets

LLM-backed workflows should save outputs as artifacts when practical.

## Stage 14: Optional scheduling

Scheduling should come after manual CLI runs are stable.

A scheduled project should have:

- a systemd timer or cron entry
- clear run logs
- clear output path
- status visibility
- failure visibility
- documented timing
- manual run instructions
- restore notes if needed

Scheduled jobs should call approved CLI commands or workflow entry points. Scheduling should not hide unique behavior that cannot be run manually.

## Stage 15: Optional Telegram status

Telegram status should usually come before Telegram execution.

A status command may show:

- last run
- latest artifact
- latest summary
- timer state
- recent failure
- next expected run
- whether model contact occurred during the last run

Status should be read-only and should avoid provider contact unless explicitly documented.

## Stage 16: Optional Telegram workflow execution

Telegram workflow execution should be added only after CLI behavior, tests, docs, and status are stable.

Telegram workflow commands should:

- expose only named approved workflows
- accept bounded arguments
- use approved config
- use approved paths
- report clear success/failure
- save artifacts
- avoid secrets
- avoid arbitrary shell access
- avoid arbitrary file access

A future pattern may be:

    /workflow_list
    /workflow_status <name>
    /workflow_run <name>
    /workflow_result <name>
    /workflow_send <artifact-id>

Exact command names should be designed later.

## Stage 17: Optional memory integration

Memory is a later subsystem.

A project should not write durable memory until memory design exists.

When memory exists, a project should define:

- what it may remember
- what it must not remember
- what requires Marc approval
- what may be updated automatically
- how Marc reviews memory writes
- how Marc corrects memory
- how Marc deletes memory
- how secrets are excluded

Until then, projects may write normal artifacts and state, but not hidden durable memory.

## Stage 18: Commit, push, and backup checkpoint

Each completed milestone should end cleanly.

Standard milestone closeout:

1. run `./scripts/check.sh`
2. review diffs
3. restart services if Telegram-facing behavior changed
4. validate Telegram behavior if needed
5. inspect logs if needed
6. update docs
7. commit
8. push
9. confirm clean Git status
10. take a VM backup checkpoint when the milestone is significant

Backups are especially useful after:

- new Telegram-facing behavior
- new scheduled jobs
- new provider integration
- new artifact layout
- new restore-relevant behavior
- major docs/architecture baselines

## Project readiness levels

MarcBot projects can be described by readiness level.

### Level 0: Idea

The goal is known, but no implementation exists.

### Level 1: Charter

The project scope and boundaries are documented.

### Level 2: CLI prototype

A manual CLI command exists.

### Level 3: Tested CLI

Core CLI behavior has tests and passes `./scripts/check.sh`.

### Level 4: Artifact-producing workflow

The project produces approved artifacts in known locations.

### Level 5: Status-visible workflow

The project has validation/status commands and clear run visibility.

### Level 6: Scheduled workflow

The project can run from a timer or cron job.

### Level 7: Telegram-visible workflow

Telegram can show status and retrieve approved artifacts.

### Level 8: Telegram-executable workflow

Telegram can run approved workflows with bounded arguments.

### Level 9: Model-routed workflow

The project uses explicit task routes and profiles for LLM-backed steps.

### Level 10: Memory-aware workflow

The project safely integrates with the future durable memory subsystem.

Projects do not need to reach Level 10. The level should match the project's actual need.

## Project template

A new project design can start with this template:

    Project name:
    Purpose:
    Non-goals:
    Readiness target:
    CLI commands:
    Telegram commands:
    Scheduled jobs:
    Config paths:
    State paths:
    Artifact paths:
    Log paths:
    Model task routes:
    Provider-secret requirements:
    Approved file reads:
    Approved file writes:
    Forbidden actions:
    Status behavior:
    Failure behavior:
    Tests:
    Docs to update:
    Backup/restore notes:

## Design rule

A project should earn each capability step by step.

Do not add Telegram execution before CLI behavior is stable.
Do not add scheduling before manual runs are reliable.
Do not add LLM analysis before deterministic inputs and outputs are clear.
Do not add memory before durable memory is designed.
Do not expose broad access when a narrow workflow will solve the problem.
