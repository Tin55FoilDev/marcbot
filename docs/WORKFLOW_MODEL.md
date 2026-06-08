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

Implemented read-only Telegram workflow visibility examples:

- `/workflow_list`
- `/workflow_status source-monitor-ai-report`
- `/workflow_status source-monitor-ai-summary`
- `/workflow_artifacts source-monitor-ai-report`
- `/workflow_artifacts source-monitor-ai-summary`

Implemented bounded Telegram workflow artifact send examples:

- `/workflow_send_artifact source-monitor-ai-report report:...`
- `/workflow_send_artifact source-monitor-ai-summary summary:...`

Implemented controlled Telegram workflow execution example:

- `/workflow_run source-monitor-ai-report`

Possible future Telegram examples after explicit safety design:

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

## Implemented workflow artifact visibility v1

MarcBot supports CLI-only workflow artifact visibility for registered
source-monitor workflows:

```text
python -m marcbot workflow artifacts source-monitor-ai-report --project ai
python -m marcbot workflow artifacts source-monitor-ai-summary --project ai
```

Workflow artifact visibility reuses existing source-monitor artifact ID
discovery. It is read-only and provider-contact-free. It does not run
workflows, write artifacts, write memory, send files, or expose Telegram
workflow execution.

## Implemented Telegram workflow visibility v1

MarcBot exposes read-only workflow visibility through Telegram:

```text
/workflow_list
/workflow_status source-monitor-ai-report
/workflow_status source-monitor-ai-summary
/workflow_artifacts source-monitor-ai-report
/workflow_artifacts source-monitor-ai-summary
```

These Telegram commands reuse the existing workflow registry, workflow
status formatting, and workflow artifact visibility paths. They are read-only
and provider-contact-free. They do not run workflows, send files, write
artifacts, write memory, or approve durable memory changes. Telegram workflow
execution remains intentionally absent.

## Implemented Telegram workflow artifact sending v1

MarcBot supports bounded Telegram sending for existing workflow artifacts:

```text
/workflow_send_artifact source-monitor-ai-report report:2026-05-26-113618
/workflow_send_artifact source-monitor-ai-summary summary:2026-05-24-113518
```

The command resolves artifacts through workflow-specific safety gates. Report
workflows accept only `report:...` IDs, and summary workflows accept only
`summary:...` IDs. The resolver then reuses the existing source-monitor
artifact ID path resolution, so Telegram never receives arbitrary paths.

This sends only existing approved artifacts. It does not run workflows,
contact providers, write artifacts, write memory, or approve durable memory
changes. Broader Telegram workflow execution remains intentionally absent.

## Implemented controlled Telegram workflow execution v1

MarcBot supports one controlled Telegram workflow execution command:

```text
/workflow_run source-monitor-ai-report
```

This first execution surface is intentionally narrow. It accepts exactly one
workflow ID, allows only `source-monitor-ai-report`, uses the fixed `ai`
project, contacts no providers, and writes no memory. It runs the existing
deterministic source-monitor report workflow and writes the resulting report
artifact through the approved workflow implementation.

`/workflow_run source-monitor-ai-summary` returns a provider-contact
preflight from Telegram. It discloses provider contact, artifact/memory
boundaries, and the fact that Telegram execution is not enabled. It does not
contact providers or run the workflow.

`source-monitor-ai-summary` and other provider-contacting workflows remain
CLI-only until an explicit provider-contact confirmation path, timeout/error
behavior, and Telegram UX are designed.

## Planned provider-contact Telegram confirmation policy

`source-monitor-ai-summary` is the first registered workflow that is useful from Telegram but requires model/provider contact. Telegram must not run this workflow directly from `/workflow_run source-monitor-ai-summary` until the provider-contact confirmation policy is implemented and tested.

The current `/workflow_run source-monitor-ai-summary` behavior is intentionally preflight-only. It should disclose that the workflow would contact a configured provider/task route, write a bounded summary artifact, and write no memory, but it must not contact a provider or run the summary workflow.

The planned execution model is a two-step confirmation flow:

    /workflow_run source-monitor-ai-summary
    /workflow_confirm source-monitor-ai-summary CONFIRMATION_TOKEN

The confirmation command name is the preferred design target, not an implemented command until the corresponding implementation milestone lands.

The confirmation policy should be narrow:

1. It should allow only explicitly approved provider-contacting workflow IDs.
2. The first allowed workflow should be `source-monitor-ai-summary`.
3. It should use the fixed `ai` source-monitor project for the initial Telegram surface.
4. It should not accept arbitrary project names, paths, URLs, prompts, providers, models, task routes, or workflow arguments.
5. It should bind each confirmation token to the requesting Telegram chat and workflow ID.
6. It should make each token single-use and short-lived.
7. It should reject expired, reused, malformed, mismatched, or unauthorized tokens.
8. It should log preflight issuance, confirmation acceptance/rejection, workflow start, artifact result, and failure outcome.
9. It should keep provider details safe: Telegram may disclose provider contact in general terms, but should not expose secret values, local config paths, raw prompts, provider keys, unrestricted model inventories, or environment details.
10. It should preserve the durable-memory boundary. Running the summary workflow from Telegram must not approve durable memory writes or expand Telegram memory authority.

The confirmed workflow result should remain artifact-oriented. A successful confirmation may create a bounded summary artifact, and Marc can inspect or send that artifact through the existing workflow artifact commands. Failures should be summarized without dumping unrestricted logs, stack traces, config contents, or provider internals into Telegram.

Implementation should wait until tests cover the preflight-only path, the confirmation-token lifecycle, authorization failures, unsupported workflow IDs, provider-contact disclosure text, artifact result reporting, and the no-memory-write boundary.

## Implemented provider-contact confirmation token lifecycle v1

MarcBot includes an internal provider-contact confirmation-token helper for future Telegram workflow confirmation. This is implementation prep only.

The helper supports issuing and consuming short-lived, single-use, chat-bound confirmation tokens for explicitly allowed provider-contacting workflow IDs. The initial allowlist is limited to `source-monitor-ai-summary`.

This helper does not register `/workflow_confirm`, does not run `source-monitor-ai-summary` from Telegram, does not contact providers, does not write artifacts, and does not write memory. It exists so token lifecycle behavior can be tested before any Telegram execution path is enabled.

## Telegram workflow confirmation skeleton v1

MarcBot 0.3.30 registers `/workflow_confirm` as a non-executing Telegram skeleton for provider-contact confirmation UX.

The command accepts the planned shape:

    /workflow_confirm source-monitor-ai-summary CONFIRMATION_TOKEN

In 0.3.30 this command does not consume confirmation tokens, does not run `source-monitor-ai-summary`, does not contact providers, does not write artifacts, and does not write memory. It returns safe status text documenting that provider-contacting Telegram execution is not enabled yet.

This milestone exists to make the user-facing command surface testable before any provider-contacting workflow execution is wired to Telegram.

## Provider-contact preflight token issuance v1

MarcBot 0.3.31 updates `/workflow_run source-monitor-ai-summary` to issue a short-lived in-memory confirmation token during provider-contact preflight.

The preflight still does not run `source-monitor-ai-summary`, does not contact providers, does not write artifacts, and does not write memory. The token is issued only to exercise the planned provider-contact confirmation UX.

`/workflow_confirm` remains non-executing in this milestone. It does not consume confirmation tokens and cannot trigger provider-contacting workflow execution.

## Non-executing confirmation token validation v1

MarcBot 0.3.32 updates `/workflow_confirm` to validate and consume confirmation tokens issued by `/workflow_run source-monitor-ai-summary`.

A valid confirmation token is accepted once and then marked used. Unknown, malformed, expired, reused, wrong-chat, and unsupported-workflow confirmations are rejected.

This remains non-executing. Token validation does not run `source-monitor-ai-summary`, does not contact providers, does not write artifacts, and does not write memory.

## Provider-contact execution enablement gate v1

MarcBot 0.3.33 documents the final design gate before Telegram may execute the provider-contacting `source-monitor-ai-summary` workflow.

This is a design milestone only. It does not enable provider contact from Telegram. In 0.3.33, `/workflow_run source-monitor-ai-summary` may issue a confirmation token, and `/workflow_confirm source-monitor-ai-summary CONFIRMATION_TOKEN` may validate that token, but confirmation still must not run the workflow.

Before execution is enabled, the implementation must satisfy these conditions:

1. The only executable provider-contacting Telegram workflow is `source-monitor-ai-summary`.
2. The project remains fixed to `ai`.
3. The memory profile remains fixed to `source-monitor`.
4. The command accepts no arbitrary project, memory profile, prompt, URL, path, provider, model, task route, or workflow argument.
5. Token validation must happen before provider contact.
6. Expired, unknown, reused, wrong-chat, malformed, unsupported-workflow, and unauthorized confirmations must be rejected before provider contact.
7. A valid token may trigger exactly one workflow run.
8. Provider contact must be disclosed before and after execution.
9. The workflow may write only the approved bounded summary artifact.
10. The workflow must write no durable memory and approve no durable memory proposals.
11. The Telegram result must be artifact-oriented and include the summary artifact ID when successful.
12. The Telegram result must not expose arbitrary paths, raw prompts, provider keys, local config, environment values, stack traces, unrestricted logs, or full provider internals.
13. Failures must be summarized safely with provider contact, workflow ran, and writes status.
14. Logs must audit preflight token issuance, confirmation validation, workflow start, provider-contacting execution attempt, artifact result, and failure outcome.

The first execution-enabled response should use a bounded result shape similar to:

    MarcBot workflow confirmation
    Workflow: source-monitor-ai-summary
    Status: executed
    Provider contact: yes
    Workflow ran: yes
    Writes: summary artifact
    Artifact: summary:YYYY-MM-DD-HHMMSS

Failure responses should use a bounded result shape similar to:

    MarcBot workflow confirmation
    Workflow: source-monitor-ai-summary
    Status: failed
    Provider contact: yes|no
    Workflow ran: yes|no
    Writes: no|unknown|summary artifact
    Reason: SAFE_SUMMARY

Execution-enablement tests must prove that provider contact is not attempted for invalid confirmations and that valid confirmations still preserve the artifact, memory, path, provider-detail, and logging boundaries.

## Safe workflow execution result formatting v1

MarcBot 0.3.34 adds bounded Telegram result formatting helpers for future provider-contacting workflow execution.

The helper supports the planned success shape:

    MarcBot workflow confirmation
    Workflow: source-monitor-ai-summary
    Status: executed
    Provider contact: yes
    Workflow ran: yes
    Writes: summary artifact
    Artifact: summary:...

The helper also supports bounded failure responses with provider contact, workflow ran, writes, and a safe reason. Local path prefixes are redacted, long reasons are truncated, and path-like artifact IDs are not exposed.

This milestone does not wire the helper into `/workflow_confirm`, does not run `source-monitor-ai-summary`, does not contact providers, does not write artifacts, and does not write memory.

## Centralized confirmation result formatting v1

MarcBot 0.3.35 routes non-executing `/workflow_confirm` validated and rejected responses through the safe workflow execution result formatter.

This keeps the Telegram result shape aligned with the future execution-enabled path before provider contact is enabled. The command remains non-executing: it validates tokens but does not run `source-monitor-ai-summary`, does not contact providers, does not write artifacts, and does not write memory.

## Corrected non-executing confirmation UX wording v1

MarcBot 0.3.36 corrects the Telegram wording for non-executing `/workflow_confirm` responses.

A valid token now reports `Status: validated` while still reporting provider contact no, workflow ran no, and writes no. Invalid confirmations report `Status: rejected`. The command remains non-executing and does not run `source-monitor-ai-summary`, contact providers, write artifacts, or write memory.
