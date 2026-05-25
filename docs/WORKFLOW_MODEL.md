# MarcBot Workflow Model

For the staged lifecycle used to add new MarcBot projects and workflows, see `docs/PROJECT_WORKFLOW_LIFECYCLE.md`.

MarcBot should be developed as a small, stable, personal-only automation system built from narrow, testable capabilities. The project should avoid becoming a general-purpose shell bot or an unconstrained agent.

This document describes the preferred development model for new MarcBot capabilities and projects.

## Core idea

MarcBot should orchestrate approved workflows built from well-defined commands and Python functions.

The preferred pattern is:

1. deterministic code does deterministic work;
2. LLMs perform bounded language, judgment, summarization, classification, or drafting tasks;
3. MarcBot ties approved steps together into named workflows;
4. Telegram exposes only safe workflow handles after the CLI surface is mature.

The CLI layer is not just operator convenience. It is the safe foundation for future bot-controlled workflows.

## Development pattern for new projects

For each new MarcBot project or capability, use this sequence:

1. Define the project goal and workflow.
2. Break the workflow into narrow deterministic steps.
3. Build tight CLI commands for each step.
4. Add status and validation commands early.
5. Add unit tests and documentation.
6. Add LLM-backed commands only where the model adds clear value.
7. Combine mature commands into a named workflow.
8. Expose bounded read-only Telegram commands where useful.
9. Expose controlled action workflows only after the CLI behavior is stable, tested, and documented.

A project should not begin with a broad free-form agent. It should begin with small deterministic tools and explicit boundaries.

## Role separation

MarcBot should keep these responsibilities separate.

### Deterministic Python code

Use deterministic code for:

- configuration loading and validation;
- file discovery and path checks;
- fetching allowlisted sources;
- parsing structured data;
- building reports;
- checking status;
- listing artifacts;
- enforcing security boundaries;
- logging and audit trails.

### LLM-backed analysis

Use LLMs only for bounded tasks such as:

- summarizing known inputs;
- classifying known inputs;
- comparing known report sections;
- drafting human-readable notes;
- identifying notable changes;
- helping review memory proposals in the future.

LLM calls should use named profiles and named task routes. They should not receive arbitrary file access, arbitrary shell access, or uncontrolled source access.

### MarcBot orchestration

MarcBot should orchestrate approved workflows by calling internal functions or CLI-equivalent code with validated arguments.

Examples:

- run a source-monitor workflow for a named project;
- generate and summarize a saved report;
- check LLM profile/task status;
- inspect saved artifacts;
- report a concise outcome to Marc.

### Telegram exposure

Telegram should expose only safe workflow handles, not arbitrary execution.

Good future Telegram examples:

- `/source_status ai`
- `/source_run ai`
- `/llm_status`
- `/llm_health local_fast`
- `/report_status`

Avoid Telegram behavior such as:

- arbitrary shell command execution;
- arbitrary file reads;
- arbitrary URL browsing;
- free-form tool selection by an LLM;
- exposing environment variables, secrets, or unrestricted logs.

## Status commands are first-class

Every significant workflow should have status and validation commands.

Status commands should answer questions such as:

- Is the config valid?
- Which project/profile/task is configured?
- What was the latest saved artifact?
- Is the summary current with the latest report?
- Did the last report show changes or errors?
- Which task routes point to which LLM profiles?
- Would this command contact an external or local model provider?

Status commands are useful for Marc over SSH and also become safe checkpoints for future orchestration.

Current examples:

    python -m marcbot source-monitor status ai
    python -m marcbot llm status
    python -m marcbot llm status --verbose

## Example: source monitor project

A source-monitor project can be built from deterministic commands plus one bounded LLM step.

Deterministic steps:

1. validate source config;
2. fetch allowlisted source metadata/content;
3. build a saved report;
4. inspect saved report and summary status.

LLM-backed step:

1. summarize or analyze the saved report using a configured task route.

Possible workflow:

1. `source-monitor config-check ai`
2. `source-monitor run ai`
3. `source-monitor run-summary ai`
4. `source-monitor status ai`
5. report changed sources, errors, summary freshness, and artifact paths.

## Example: future stock research project

A future stock research project should follow the same pattern.

Deterministic steps might include:

- `stock config-check`
- `stock fetch-prices`
- `stock fetch-filings`
- `stock fetch-news`
- `stock build-report`
- `stock status`
- `stock list-reports`

LLM-backed steps might include:

- `stock summarize-filing`
- `stock analyze-company`
- `stock compare-news-impact`
- `stock draft-watchlist-notes`

A daily workflow could then string together config validation, data fetching, report generation, bounded LLM analysis, and final status reporting.

## Anti-patterns and non-goals

MarcBot should avoid these patterns:

- building broad features before defining the workflow;
- exposing arbitrary command execution over Telegram;
- allowing the LLM to decide arbitrary tools or shell commands;
- allowing arbitrary internet browsing when an allowlist is appropriate;
- writing secrets to Git, chat, logs, reports, or memory;
- creating hidden automatic memory writes without auditability;
- adding large features without tests, docs, and status visibility;
- relying on one monolithic prompt instead of explicit, tested steps.

## Relationship to memory

Memory should come after stable workflows, task routes, and LLM profile handling.

Future memory work should use this workflow model:

1. deterministic code captures candidate facts or events;
2. LLMs may help classify or summarize bounded candidates;
3. MarcBot stores memory proposals with clear provenance;
4. Marc can approve, reject, or edit proposals;
5. approved memories are written to durable storage;
6. memory changes are auditable and correctable.

Memory should reduce Marc's burden over time, but it should not bypass safety, reviewability, or correction workflows.

See also `docs/MEMORY.md`.

## Design rule

The governing rule is:

> Deterministic code does deterministic work. LLMs do bounded judgment work. MarcBot orchestrates approved workflows. Telegram exposes only safe workflow handles.

This rule should guide future project design, CLI command design, LLM integration, Telegram exposure, and memory development.

## Memory retrieval in future workflows

Future MarcBot workflows should treat memory retrieval as part of the
workflow planning/context stage, not as a separate manual chore for Marc.

For workflows that can benefit from project history or durable user/project
context, the intended flow is:

1. Determine whether memory is relevant to the requested task.
2. Retrieve bounded memory context from structured sources first, including
   active facts, relevant summaries, recent events, and corrections.
3. Exclude rejected, superseded, stale, or unrelated memory unless the task
   explicitly asks for history.
4. Use retrieved memory to prepare safer prompts, reports, command plans,
   or workflow decisions.
5. Record new low-risk operational events automatically where appropriate,
   and route durable/high-impact facts through proposal or approval
   workflows as required.

SQLite-backed memory reads are an implementation step toward that model.
They are not intended to make Marc manually query memory forever; they are
the indexed substrate future MarcBot context assembly can rely on.

## Context assembly workflow step

Future model-assisted workflows should have an explicit context assembly
stage before asking an LLM to analyze, draft, summarize, or plan.

For v1, this stage should be implemented as a local CLI helper that returns
bounded memory context from active facts, relevant summaries, and recent
events. Later, approved workflows can call that helper automatically.

The workflow boundary remains important:

- Deterministic retrieval and filtering should happen in code.
- LLMs may use the assembled context for analysis or drafting only after the
  retrieval step has produced a bounded package.
- Memory retrieval must not require Marc to manually search every time.
- Provider contact remains explicit and separate from memory retrieval.

## Model-requested memory retrieval boundary

Future workflows may allow a model-assisted planning step to request
memory context, but the model should not receive arbitrary file-system
or raw memory access.

Approved pattern:

1. The workflow or model identifies a memory need, such as a project,
   topic, correction, preference, or prior workflow history.
2. MarcBot converts that need into a bounded memory retrieval request.
3. Deterministic memory code retrieves active facts, relevant summaries,
   recent events, and correction-aware context using configured limits.
4. The model receives only the bounded context package, not unrestricted
   file access.

This preserves the flexibility for the model to ask for specific
information while keeping retrieval safe, auditable, and efficient.
Memory retrieval remains separate from provider contact; local retrieval
should complete before any optional model call receives the assembled
context.

## Controlled memory context integration for workflows

Selected workflows may eventually retrieve memory context automatically,
but memory retrieval and provider contact must remain separate concerns.

Approved pattern:

1. The workflow determines that memory context may help.
2. MarcBot retrieves bounded local memory context using deterministic code,
   such as `build_memory_context_dict(...)`.
3. The memory retrieval step remains provider-contact-free.
4. The workflow inspects the returned `warnings`, `sqlite`, `counts`, and
   section payloads before deciding whether the context is usable.
5. Any later LLM/provider contact remains explicit and controlled by the
   selected LLM command, task route, and profile.
6. The model receives only the bounded context package, not arbitrary
   file-system access or unrestricted memory search access.

This allows MarcBot to reduce Marc's burden by retrieving useful memory
automatically inside approved workflows, while still preserving auditability,
bounded context size, and clear provider-contact boundaries.

Initial integration should stay CLI-only. Telegram or free-form chat
integration should wait until the CLI workflow path is stable, tested, and
documented.

## Model prompt use of assembled memory

Workflows that pass assembled memory context to an LLM should include clear
instructions about how the model should treat the context.

The workflow should not simply append raw memory and hope the model handles
it correctly. It should provide a bounded memory section and short rules
for relevance, priority, warnings, and conflict handling.

This keeps deterministic retrieval separate from model reasoning while
allowing the model to benefit from project history and durable facts.


## Generic workflow memory target

Workflow memory should be generic across MarcBot projects. The pattern is:

```text
workflow event or command
  -> deterministic memory write or retrieval policy
  -> structured fact/event/summary/proposal/correction storage
  -> SQLite-backed indexed read model
  -> bounded context assembly
  -> optional LLM prompt use with preview/audit support
```

Workflows should not depend on free-form plan files as the primary memory
system. Plan files can document milestones and human-readable project
context, but workflow memory should be structured, queryable, auditable,
supersedable, and usable by code.

The autonomy target is risk-tiered. Low-risk operational events can be
written automatically. Medium-risk durable facts may be proposed or later
auto-applied with clear audit trails. High-risk or sensitive facts require
explicit approval.

## Memory-aware workflow reference roles

Memory-aware workflows should distinguish two validation questions:

1. Does a workflow have useful durable memory to retrieve?
2. Can a workflow safely consume retrieved memory in a bounded model prompt?

`weather-report` currently answers the first question. It has durable facts
and recent events that make `memory context --profile weather-report` useful.

`source-monitor` answers the second question and now also has a dedicated
memory profile backed by durable source-monitor facts. It validates the
workflow mechanics for adding retrieved memory to an explicit LLM summary
without letting the model search files or memory directly.

This distinction prevents MarcBot from adding empty or misleading automatic
memory profiles before the underlying durable facts exist. The source-monitor
profile was added only after durable source-monitor facts were created and
validated in SQLite.
## Implemented workflow registry v1

MarcBot includes a read-only approved workflow registry.

CLI commands:

```text
python -m marcbot workflow list
python -m marcbot workflow show WORKFLOW_ID
```

The registry records workflow IDs, descriptions, execution status, provider
contact expectations, artifact writes, memory writes, Telegram visibility,
Telegram execution boundaries, allowed arguments, artifact roots, and memory
profile hints.

Initial registered workflows:

- `source-monitor-ai-report`
- `source-monitor-ai-summary`

Workflow registry v1 does not run workflows. Execution is deferred to
workflow run v1 after the registry shape is validated.
## Implemented workflow run v1

MarcBot supports CLI-only execution of the approved
`source-monitor-ai-report` workflow:

```text
python -m marcbot workflow run source-monitor-ai-report --project ai
```

Workflow run v1 is intentionally narrow. It runs the existing deterministic
source-monitor report writer, writes a report artifact, writes no memory,
does not contact an LLM provider, and has no Telegram execution surface.

The `source-monitor-ai-summary` workflow remains registered but not runnable
until a later workflow run milestone adds explicit model-contact handling.
## Implemented workflow run v2

MarcBot supports CLI-only execution of the approved
`source-monitor-ai-summary` workflow:

```text
python -m marcbot workflow run source-monitor-ai-summary --project ai --memory-profile source-monitor
```

Workflow run v2 reuses the existing bounded `source-monitor summarize-latest`
CLI path. It explicitly discloses provider contact, writes a summary artifact,
writes no memory, and has no Telegram execution surface.
## Implemented workflow status v1

MarcBot supports CLI-only workflow status for registered source-monitor
workflows:

```text
python -m marcbot workflow status source-monitor-ai-report --project ai
python -m marcbot workflow status source-monitor-ai-summary --project ai
```

Workflow status v1 reuses existing source-monitor artifact status visibility.
It is read-only and provider-contact-free. It does not run workflows, write
artifacts, write memory, or expose Telegram execution.
