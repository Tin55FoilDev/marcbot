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
