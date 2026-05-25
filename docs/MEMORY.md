# MarcBot Memory Design Notes

MarcBot does not yet have a full memory subsystem.

This document records the intended direction for a future memory system so the
project can revisit the design deliberately when the core workflows justify it.

## Long-term retrieval and automation target

The long-term purpose of MarcBot memory is not to create another manual
filing system that Marc has to operate command by command. The target is
for MarcBot to automatically and safely capture, organize, retrieve, update,
and explain important durable knowledge during normal approved chat and
workflow activity.

Memory is broader than MarcBot project development. Project work is the
safest early test bed because it has a public repository, repeatable tests,
clear validation output, and explicit commits, but the memory system is
intended to support any MarcBot-supported domain where durable context helps
future work. Examples include operational troubleshooting, cron and systemd
timer failures, backup and restore issues, local model configuration, source
monitoring, recurring workflow preferences, design decisions, lessons
learned, and important chat-derived context.

A mature memory workflow should let MarcBot notice when a conversation or
workflow produced useful durable knowledge, such as a problem description,
symptoms, debug path, root cause, fix, validation result, and follow-up
warning. Marc should not need to manually tell MarcBot to save ordinary
low-risk troubleshooting knowledge, and Marc should not need to manually
request routine retrieval when a similar future problem appears.

The desired end state is:

1. MarcBot identifies when prior context, user preferences, operational
   facts, workflow history, troubleshooting history, decisions, or
   corrections are relevant.
2. MarcBot retrieves the most useful memory records without requiring Marc
   to explicitly ask for a memory search.
3. MarcBot assembles a bounded context package from durable facts,
   troubleshooting records, summaries, recent events, decisions, preferences,
   and corrections before model-assisted work where memory is appropriate.
4. MarcBot avoids stale or superseded memory by respecting fact status,
   correction records, approval state, timestamps, and source metadata.
5. MarcBot remains auditable: Marc should be able to inspect what memory
   exists, what was proposed, what was approved or rejected, and why a
   memory item influenced a workflow.

The current file-backed memory store is intentionally conservative and
human-readable while the project proves the memory model. SQLite is being
added as the structured, indexed, queryable repository that should become
the primary durable memory backend for records that need filtering, search,
review state, supersession, correction, or context assembly. Markdown files
remain important for design notes, workflow documentation, runbooks, and
human-readable handoff material, but they are not the intended long-term
backend for all memory records.

Manual CLI commands are implementation and diagnostic tools. They are not
the final user experience. The final MarcBot behavior should reduce Marc's
burden by using memory automatically where safe, while preserving explicit
guardrails for high-risk facts, corrections, security-sensitive decisions,
and actions.

## Goal

MarcBot should eventually have a reliable hybrid memory system that helps
future chats and actions consider important prior context without becoming
mysterious, unsafe, or difficult to correct.

The goal is not just to store facts, and it is not limited to project
development. The goal is to reduce Marc's operational burden by allowing
MarcBot to remember, retrieve, update, correct, and explain important
context over time, including debug history, validated fixes, operational
lessons learned, recurring preferences, and durable chat-derived knowledge.

## Design principles

MarcBot memory should be:

- durable
- auditable
- source-linked
- timestamped
- correctable
- reviewable
- reversible where practical
- explicit about confidence and authority
- careful about secrets and sensitive local config
- designed around MarcBot's personal-only operating model

Memory should improve continuity without giving the bot broad or hidden
autonomy.

## Memory versus authority

MarcBot must distinguish authoritative truth from helpful memory.

For MarcBot project-development work, authoritative sources include:

- current repository files
- current local config schemas
- actual command output
- Git commits
- validation results
- support snapshots
- explicit Marc approvals or corrections

For non-repository operational and chat workflows, authoritative sources are
the live system, current command output, current configuration, explicit Marc
corrections, and any external source Marc intentionally provides for the task.
Memory can suggest likely causes, prior debug paths, known fixes, and
standing preferences, but it must not override current evidence.

Helpful but non-authoritative sources include:

- generated summaries
- retrieved memories
- LLM interpretations
- older session notes
- inferred preferences
- proposed reflections

Memory can help decide what to check first. It cannot, by itself, prove what
is true now.

## Hybrid memory direction

The long-term memory direction is hybrid, but SQLite should become the main
structured repository for memory records. Human-readable files remain useful
for design documents, project policy, runbooks, bootstrap context, exported
snapshots, and reviewable handoff material.

Memory should be organized primarily as typed records in a structured store,
not as unrelated storage layers. Record types may include:

- event
- troubleshooting
- fact
- summary
- decision
- preference
- workflow_rule
- correction
- proposal

Each record type should carry enough metadata to make retrieval and review
safe: source, timestamp, project or domain, risk tier, status, confidence
where appropriate, related commands, related files or artifacts, and
supersession/correction links where needed.

The current implementation still uses inspectable file-backed records for
several memory classes and validates SQLite against those records. That is a
transitional implementation detail, not the final architecture. Future
migration work should deliberately move toward SQLite as the primary
structured memory repository once the migration path is explicit, tested, and
easy to inspect.

### 1. Curated human-readable memory files

Markdown or TOML files should store stable context that is better maintained as
human-facing documentation than as individual memory records, such as:

- project principles
- architecture notes
- security rules
- runbooks
- workflow documentation
- design charters
- bootstrap/session-start guidance

These files are easy to inspect, edit, back up, and review. Some human-readable
memory or runbook files may belong outside Git if they contain personal or
local operational details.

### 2. Structured SQLite-backed memory

SQLite is the intended primary structured repository for durable memory records
that need query, status, correction, review, filtering, or context assembly.

SQLite-backed memory should store typed records such as facts, events,
troubleshooting cases, summaries, decisions, preferences, workflow rules,
corrections, source metadata, and pending proposals.

A stronger database backend such as PostgreSQL, MariaDB, or MySQL should be
considered only if justified by concurrency, scale, indexing, remote access, or
operational needs.

### 3. Event ledger

MarcBot should maintain an append-only or mostly append-only event history for
important project activity.

Examples:

- feature completed
- validation passed
- backup completed
- service restarted
- report generated
- source monitor run completed
- repository visibility changed
- design decision made

This gives MarcBot a reliable timeline for later summaries and troubleshooting.

### 4. Session and milestone summaries

MarcBot should be able to write concise handoff summaries for future sessions.

These summaries should include:

- what changed
- what was validated
- latest commits
- known issues
- next suggested steps
- links or paths to relevant docs/artifacts

Summaries are useful, but they should not become unquestioned truth. They should
remain source-linked and correctable.

### 5. Search and retrieval

MarcBot should eventually search memory and project history.

The preferred order is:

1. simple metadata and structured lookup
2. full-text search
3. optional vector/embedding search later

Vector search should not silently inject untrusted context into high-risk
actions. Retrieved memory should be dated, source-labeled, and visible enough to
audit.

### 6. Reflection and learning

MarcBot should eventually identify repeated patterns and propose durable memory
updates.

Examples:

- Marc prefers small milestones with validation after each patch.
- MarcBot should keep Telegram commands bounded and read-only unless explicitly
  designed otherwise.
- Source monitor workflows should be CLI-first before Telegram exposure.

Reflections should be handled carefully because they can overgeneralize or
become confidently wrong.

## Automatic memory updates

Marc does not want to have to explicitly tell MarcBot every time something
should be remembered.

A useful memory system should reduce burden by identifying important memory
candidates during normal sessions.

However, automatic memory updates need guardrails.

A future system should use a tiered autonomy model.

### Low-risk memory

MarcBot may auto-record low-risk events.

Examples:

- command completed
- report generated
- summary written
- validation passed
- commit hash recorded
- backup completed
- source monitor run completed

These records should still be timestamped and source-linked.

### Medium-risk memory

MarcBot may propose or apply medium-risk updates with a visible audit trail.

Examples:

- recurring workflow preference
- project design direction
- non-sensitive operational pattern
- repeated user preference
- corrected project fact

Some of these may be auto-applied if confidence is high and the risk is low, but
they should remain reviewable and reversible.

### High-risk memory

Marc approval should be required for high-risk durable memory changes.

Examples:

- security policy changes
- permission model changes
- new trusted hosts or services
- destructive-action rules
- credentials or secret-handling assumptions
- changes that would broaden Telegram authority
- changes that would allow autonomous code modification or execution

High-risk memory should never be silently changed.

## Correction workflow

MarcBot memory must support correction, not just accumulation.

When Marc corrects a fact, MarcBot should be able to:

1. preserve the old fact
2. mark the old fact as superseded
3. record the corrected fact
4. link the correction to its source
5. prefer the corrected fact in future retrieval
6. show the correction history when relevant

Example:

    Old fact:
    MarcBot source monitor config path is X.

    Correction:
    Marc says the actual config path is Y.

    Action:
    Mark X superseded, add Y as current, record the correction source/date.

## Review workflow

MarcBot should provide memory review commands before memory becomes too
autonomous.

Possible future CLI commands:

    python -m marcbot memory status
    python -m marcbot memory search "source monitor"
    python -m marcbot memory show facts
    python -m marcbot memory show events
    python -m marcbot memory review pending
    python -m marcbot memory approve <id>
    python -m marcbot memory reject <id>
    python -m marcbot memory correction add ...
    python -m marcbot memory export

Possible future Telegram command:

    /memory_status

Telegram memory commands should initially be read-only or review-oriented. They
should not allow arbitrary memory writes without explicit design and tests.

## Secrets and privacy

MarcBot memory must not store secrets.

Memory should avoid storing:

- Telegram bot tokens
- API keys
- provider tokens
- passwords
- SSH private keys
- local config file contents
- raw unrestricted logs
- unnecessary personal data

If memory references a sensitive system, it should store only safe metadata or a
redacted description.

## Failure modes to avoid

MarcBot should avoid:

- one giant memory file that grows forever
- silent vector retrieval into every prompt
- treating generated summaries as authoritative
- silently rewriting durable memory
- storing raw full chats indefinitely without retention rules
- recording secrets in memory
- overgeneralizing from one-off comments
- letting Telegram prompts directly mutate important memory
- allowing memory to broaden runtime authority without review

## Likely implementation phases

### Phase 1 — Explicit memory documentation

Capture this design direction in docs before implementation.

### Phase 2 — Curated memory files

Add a small, inspectable memory area for stable project/operator context.

### Phase 3 — Session handoff artifacts

Generate structured session or milestone handoff summaries.

### Phase 4 — Structured facts and events

Add SQLite-backed facts, events, summaries, corrections, and review state.

### Phase 5 — Full-text search

Add searchable memory over facts, events, summaries, and selected docs.

### Phase 6 — Optional embeddings

Evaluate vector search only after structured and full-text retrieval are useful.

### Phase 7 — Automatic capture with guardrails

Allow MarcBot to auto-record low-risk events and propose higher-level memory
updates.

### Phase 8 — Human-approved reflection

Let MarcBot propose durable reflections, with Marc approval required for
important behavior-shaping rules.

## Current status

MarcBot now has an early memory substrate, but not the full long-term memory
system described above.

The project already has several sources that help reconstruct development and
operational context:

- docs/SESSION_START.md
- python -m marcbot support snapshot
- docs/CHANGELOG.md
- docs/ROADMAP.md
- project documentation
- Git history
- file-backed memory records
- SQLite validation and indexing

For MarcBot project-development questions, current repository files, current
command output, validation results, Git commits, and explicit Marc corrections
remain authoritative. For broader operational and chat-derived memory, the live
system, current evidence, and explicit Marc corrections remain authoritative.

Memory records, summaries, and indexed SQLite views are helpful context and
retrieval aids. They should guide what MarcBot checks first, but they must not
override current evidence.

## Implementation charter

MarcBot memory should be implemented gradually, using the same lifecycle pattern
validated by the weather-report project.

The first goal is not autonomous learning. The first goal is a safe, inspectable
memory substrate that can later support automatic capture and review.

## Initial local memory root

The initial runtime memory root should be:

    /srv/marcbot/memory

This directory is local runtime state and should not be committed to Git.

Repo documentation and examples may describe memory schemas, but the real memory
store lives outside Git unless a future design explicitly says otherwise.

Initial layout:

    /srv/marcbot/memory/
      README.md
      events/
      facts/
      summaries/
      pending/
      corrections/
      exports/

## Initial command surface

Start CLI-first.

Initial CLI commands:

    python -m marcbot memory init
    python -m marcbot memory status

Initial Telegram command:

    /memory_status

The Telegram command must be read-only and provider-contact-free.

## Memory classes

Initial memory classes:

1. events
2. facts
3. summaries
4. pending proposals
5. corrections

Events are append-only or mostly append-only records of what happened.

Facts are durable statements believed to be currently true.

Summaries are handoff or milestone documents.

Pending proposals are possible memory updates awaiting review.

Corrections record superseded or corrected facts.

## Operational usefulness rule

Memory must be useful to future Marc and future MarcBot, not just a simple list
of activities.

For operational events, memory should preserve enough structured detail to make
future retrieval actionable.

A weak memory event says:

    backup fixed

A useful memory event explains:

- what happened
- how it was detected
- what evidence was observed
- likely cause
- fix applied
- verification result
- future guidance
- related files, commands, services, timers, commits, or artifacts

Not every event needs every field, but the schema must support enough detail for
debugging, recovery, and future decision-making.

Example:

    Summary: Fixed backup timer warning caused by unreadable root-owned tuning
    backup files.

    Details: /timer_status showed marcbot-backup.service with Last service
    result exit-code and Last exit status 2. Journal logs showed tar permission
    errors for stale *.bak-* files under /srv/marcbot/config and
    /srv/marcbot/config/chat.

    Cause: Temporary backup files created during chat-context tuning were owned
    by root:root with mode 600, while marcbot-backup.service runs as marc.

    Resolution: Confirmed active config files were marc:marc and readable,
    removed stale root-owned tuning backup files, and manually restarted
    marcbot-backup.service.

    Verification: Manual service run exited status=0/SUCCESS and /timer_status
    reported all timers healthy.

    Follow-up: Avoid creating root-owned files under /srv/marcbot/config during
    future tuning; use sudo -u marc for runtime config backups where possible.

This level of detail is especially important for operational fixes, service
failures, timer problems, deployment issues, security decisions, and project
workflow lessons.

## Storage format v1

The current implementation uses inspectable file-backed records plus SQLite
validation and indexing. This early format made records easy to review, diff,
back up, and test while the memory model was still being shaped.

Current file-backed record locations include:

    /srv/marcbot/memory/events/
    /srv/marcbot/memory/facts/
    /srv/marcbot/memory/summaries/
    /srv/marcbot/memory/proposals/
    /srv/marcbot/memory/corrections/

The design direction is to migrate toward SQLite as the primary structured
memory repository for records that need status, review, correction,
supersession, filtering, search, or context assembly. Any migration away from
file-backed source records must be explicit, tested, backed up, and documented
so the system remains inspectable and recoverable.

## Event schema v1

Events should be JSON lines with stable fields.

Required fields:

    timestamp
    type
    summary
    source
    confidence

Optional fields:

    project
    details
    cause
    resolution
    verification
    follow_up
    related_files
    related_commands
    related_artifacts
    related_commits

The optional fields are important. They allow memory events to become
operationally useful instead of merely chronological.

The `details`, `cause`, `resolution`, `verification`, and `follow_up` fields
should be used when an event records a fix, failure, debugging session, service
change, deployment, or meaningful project decision.

The `related_commands` field should include only safe, non-secret command
examples. Do not include tokens, credentials, private keys, or raw sensitive
output.

Allowed initial event types should be narrow. Examples:

    validation_passed
    report_generated
    report_sent
    timer_validated
    service_restarted
    backup_completed
    issue_detected
    issue_resolved
    commit_pushed
    workflow_completed
    design_decision

## Fact schema v1

Facts should be explicit and correctable.

Suggested fields:

    id
    statement
    category
    project
    source
    created_at
    updated_at
    confidence
    status
    details

Allowed statuses:

    active
    superseded
    rejected

Facts should not be silently changed. A correction should supersede an old fact
rather than overwriting it without history.

Use `details` when a fact needs context to be useful. For example, a fact about
a timer schedule may include why that time was selected, where the unit is
defined, and how to validate it.

## Summary schema v1

Summaries should be Markdown files with a short metadata block.

Suggested fields:

    title
    created_at
    project
    source
    related_commits
    related_artifacts

Summaries are useful context but should not override current command output,
current repo files, validation results, or Marc's explicit corrections.

## Pending proposal schema v1

Pending proposals should be JSON files.

Suggested fields:

    id
    created_at
    proposed_type
    proposed_statement
    project
    source
    rationale
    risk_level
    status
    details

Allowed statuses:

    pending
    approved
    rejected

Telegram should not approve or reject proposals until that command surface is
explicitly designed and tested.

## Risk tiers

Low-risk memory may eventually be auto-recorded.

Examples:

    report generated
    report sent
    validation passed
    backup completed
    commit pushed
    workflow completed

Medium-risk memory should initially be proposed for review.

Examples:

    recurring workflow preference
    durable project direction
    non-sensitive operational pattern
    repeated user preference
    corrected project fact

High-risk memory requires explicit Marc approval before becoming durable.

Examples:

    security policy changes
    permission model changes
    trusted host or service changes
    destructive-action rules
    credential or secret-handling assumptions
    Telegram authority expansion
    autonomous code modification or execution rules

## Forbidden memory content

Memory must not store:

    API keys
    Telegram bot tokens
    OAuth tokens
    provider tokens
    passwords
    SSH private keys
    raw unrestricted logs
    full local config files containing secrets
    unnecessary personal data

If a sensitive system must be referenced, store only safe metadata or a redacted
description.

## Authority rule

Memory is helpful context, not final authority.

Authoritative sources remain:

    current repo files
    current local config schemas
    actual command output
    Git commits
    validation results
    support snapshots
    explicit Marc approvals or corrections

Memory retrieval should never silently override those sources.

## Initial implementation phases

Phase M1: implementation charter and schema docs.

Phase M2: local memory scaffold plus CLI `memory init` and `memory status`.

Phase M3: read-only Telegram `/memory_status`.

Phase M4: explicit low-risk event ledger commands.

Phase M5: integrate one proven workflow, likely weather-report, to record
low-risk events.

Phase M6: milestone summaries.

Phase M7: facts and corrections.

Phase M8: pending proposal review queue.

Phase M9: LLM-assisted memory candidate generation with Marc approval.

Automatic capture should not begin until the memory root, status commands,
event schema, review expectations, and safety boundaries are implemented and
tested.

## Implemented M2 scaffold

The initial memory scaffold provides:

    python -m marcbot memory init
    python -m marcbot memory status

`memory init` creates the local memory root and expected subdirectories.

`memory status` reports initialization state and file counts.

This milestone does not write events, facts, summaries, proposals, or
corrections beyond the initial scaffold files.

## Implemented M3 Telegram memory status

The read-only Telegram command:

    /memory_status

shows the same provider-free memory status as:

    python -m marcbot memory status

It does not write memory, approve proposals, inspect arbitrary paths, or contact
model providers.

## Implemented M4 explicit event ledger

The explicit memory event ledger provides:

    python -m marcbot memory event add
    python -m marcbot memory event list

Events are written to monthly JSONL files under:

    /srv/marcbot/memory/events/

The event add command supports operational detail fields, including:

    details
    cause
    resolution
    verification
    follow_up
    related_files
    related_commands
    related_artifacts
    related_commits

This keeps memory useful for future debugging and recovery, not merely a thin
activity list.

This milestone remains explicit and CLI-only. It does not perform automatic
capture and does not expose memory writes through Telegram.

## Implemented M5 first workflow memory integration

The first controlled automatic memory write is integrated with the weather-report
workflow.

The command:

    python -m marcbot weather-report run-send-text

now records a low-risk `workflow_completed` memory event after successful report
generation and Telegram text delivery.

The event includes:

- project: `weather-report`
- summary of the completed workflow
- generated report artifact path
- command used
- verification that the command completed successfully
- follow-up guidance for `/weather_status`, `/timer_status`, and
  `/send_weather_report`

This is intentionally narrow. It does not enable broad automatic memory capture,
Telegram memory writes, proposal approval, or LLM-assisted memory generation.

## Implemented M6 explicit milestone summaries

The explicit memory summary commands are:

    python -m marcbot memory summary add
    python -m marcbot memory summary list

Summaries are Markdown files written under:

    /srv/marcbot/memory/summaries/

Summaries are intended for milestone, project, and session handoff context.
They are useful context, but they do not override current repo files, command
output, validation results, Git commits, or Marc's explicit corrections.

This milestone remains explicit and CLI-only. It does not perform automatic
summary generation and does not use LLMs.

## Implemented M7A explicit facts

The explicit memory fact commands are:

    python -m marcbot memory fact add
    python -m marcbot memory fact list

Facts are TOML files written under:

    /srv/marcbot/memory/facts/

This first fact milestone supports active facts only. Correction and supersession
are intentionally deferred to the next milestone.

Facts are more authoritative than events or summaries, so they should be added
carefully and explicitly. They remain helpful context, not final authority over
current repo files, command output, validation results, Git commits, or Marc's
explicit corrections.

## Implemented M7B fact supersession

Facts can now be corrected by supersession rather than editing in place.

Command:

    python -m marcbot memory fact supersede

Supersession behavior:

- old fact is marked `status = "superseded"`
- old fact records `superseded_by`
- new fact is written with `status = "active"`
- new fact records `supersedes`
- correction metadata is appended under `/srv/marcbot/memory/corrections/`

This preserves history while allowing retrieval to prefer active facts.

## Implemented M7C fact rejection

Facts can now be marked rejected without deleting their history.

Command:

    python -m marcbot memory fact reject

Rejection behavior:

- fact is marked `status = "rejected"`
- fact records `rejected_at`
- fact records `rejected_reason`
- fact records `rejected_source`
- correction metadata is appended under `/srv/marcbot/memory/corrections/`

This is useful for cleaning up temporary or incorrect facts while preserving an
audit trail.

## Implemented M8A pending proposals

The pending proposal commands are:

    python -m marcbot memory proposal add
    python -m marcbot memory proposal list
    python -m marcbot memory proposal reject

Proposals are JSON files written under:

    /srv/marcbot/memory/pending/

This milestone supports explicit proposal creation, listing, and rejection.

Proposal approval is intentionally deferred. Approval must safely create the
appropriate durable memory type and should be implemented as a separate
milestone.

This milestone is CLI-only, provider-contact-free, and does not perform
automatic proposal generation.

## Implemented M8B fact proposal approval

Pending fact proposals can now be approved explicitly.

Command:

    python -m marcbot memory proposal approve

Initial approval behavior supports `proposed_type = "fact"` only.

Approval behavior:

- reads a pending proposal
- verifies it is still pending
- verifies it is a fact proposal
- creates an active memory fact from the proposed statement
- marks the proposal approved
- records `reviewed_at` and `review_reason`
- writes a correction/review record

Approval remains CLI-only and provider-contact-free. Event and summary proposal
approval are deferred.




## Implemented M8F proposal list review ergonomics

MarcBot proposal list output includes source, rationale, optional details,
review timestamp, review reason, and backing file path when present. This keeps
the proposal review loop easier to audit now that fact, event, and summary
proposal approval are all supported from the CLI.

This change is read-only formatting and does not expand Telegram approval
authority.

## Implemented M8E summary proposal approval

MarcBot supports CLI-only approval of pending memory proposals where
`proposed_type = "summary"`. Approval creates a memory summary, marks the
proposal approved, records review metadata, and appends a proposal-approved
correction/audit record.

The proposal statement becomes the summary title. Proposal details become the
summary body when present; otherwise the proposal rationale is used.

This is intentionally not exposed as Telegram approval authority. Telegram
memory proposal commands remain read-only/review-oriented unless explicitly
expanded by a later design step.

## Implemented M8D event proposal approval

MarcBot supports CLI-only approval of pending memory proposals where
`proposed_type = "event"`. Approval creates an event using the existing
event ledger, marks the proposal approved, records review metadata, and
appends a proposal-approved correction/audit record.

This is intentionally not exposed as Telegram approval authority. Telegram
memory proposal commands remain read-only/review-oriented unless explicitly
expanded by a later design step.

## Implemented M8C richer memory status visibility

The read-only memory status output now reports proposal counts by review status.

`python -m marcbot memory status` and `/memory_status` show:

    proposal files
    pending proposals
    approved proposals
    rejected proposals

This avoids confusing approved or rejected proposal records with still-pending
review work.

The command remains provider-contact-free and read-only.

## Implemented M9A read-only memory detail retrieval

Memory now supports read-only detail retrieval for facts and proposals.

Commands:

    python -m marcbot memory fact show --id <fact-id>
    python -m marcbot memory proposal show --id <proposal-id>

These commands format known memory records by ID. They do not write memory,
inspect arbitrary paths, or contact model providers.

## Implemented M9B read-only event and summary detail retrieval

Memory now supports read-only detail retrieval for events and summaries.

Commands:

    python -m marcbot memory event show --index <n> --limit <limit>
    python -m marcbot memory summary show --name <summary-file-name>

Event detail retrieval reads from the recent sorted event list using a 1-based
index.

Summary detail retrieval accepts only a file name under the memory summaries
directory. It does not accept arbitrary paths.

These commands are read-only and provider-contact-free.

## Implemented M10 read-only memory search

Memory now supports simple read-only text search.

Command:

    python -m marcbot memory search <query>

Search behavior:

- searches only `/srv/marcbot/memory`
- searches known memory file types: `.jsonl`, `.json`, `.toml`, `.md`
- performs case-insensitive substring matching
- returns relative path, line number, and matching line excerpt
- does not accept arbitrary root paths
- does not write memory
- does not contact model providers

This is intentionally simple. LLM-assisted search or embeddings are deferred.

## M11 automatic memory integration policy

MarcBot may eventually record low-risk memory automatically from approved
workflows. This must remain narrow, explicit, auditable, and easy to disable.

The weather-report workflow is the first approved example:

    python -m marcbot weather-report run-send-text

It records a low-risk `workflow_completed` event only after the workflow
successfully generates a report artifact and sends the Telegram text report.

## Auto-record eligibility

A workflow may auto-record a memory event only when all of the following are
true:

1. The workflow is deterministic or mostly deterministic.
2. The workflow already has tests.
3. The workflow has a clear success boundary.
4. The event is low-risk operational history.
5. The event does not include secrets.
6. The event does not include raw unrestricted logs.
7. The event does not claim a user preference unless Marc explicitly stated it.
8. The event does not change facts, proposals, summaries, or corrections.
9. The event records what happened, not what should happen.
10. The memory write occurs only after the workflow succeeds.

## Approved automatic event types

Initially approved automatic event types:

    workflow_completed
    report_generated
    report_sent
    backup_completed
    validation_passed
    service_restarted

These should be used conservatively.

## Disallowed automatic writes

MarcBot must not automatically write:

    facts
    proposal approvals
    proposal rejections
    fact supersessions
    fact rejections
    high-risk security or permission changes
    credential-handling assumptions
    trusted host or service assumptions
    user preference changes
    autonomous behavior expansion

Those require explicit CLI actions or future review workflows.

## Required fields for automatic workflow events

Automatic workflow events should include:

    type
    project
    summary
    source
    confidence
    details
    verification
    related_commands

When applicable, also include:

    related_files
    related_artifacts
    follow_up

## Failure behavior

If the workflow succeeds but the memory event write fails, the first version of
automatic memory integration should fail closed for scheduled workflow commands.

This means the command should return an error so MarcBot does not silently lose
expected operational memory.

A future design may allow non-critical best-effort memory writes, but only after
that behavior is explicit and tested.

## Review cadence

Automatic memory events should be reviewed periodically with:

    python -m marcbot memory event list
    python -m marcbot memory search <term>
    python -m marcbot memory status

If automatic events become noisy, the integration should be tightened rather
than allowing memory to become cluttered.

## Telegram boundary

Telegram may show memory status and memory retrieval in future read-only
commands, but Telegram must not approve, reject, supersede, or create durable
memory until that command surface is explicitly designed and tested.

## Implemented M11B approved automatic workflow helper

MarcBot now has a narrow helper for approved automatic workflow event writes.

The helper requires:

- an approved low-risk event type
- project
- summary
- source
- details
- verification

It supports optional follow-up guidance, related files, related commands, and
related artifacts.

The weather-report `run-send-text` workflow now uses this helper instead of
hand-rolling its automatic memory event.

This keeps Marc out of routine low-risk memory transactions while preserving
guardrails and auditability.

## Daily status report automatic memory integration

The daily status report commands now use the approved automatic workflow helper.

The generation command:

    python -m marcbot report daily-status

records a low-risk `report_generated` event after successfully writing the daily
status report artifact.

The send command:

    python -m marcbot report send-latest

records a low-risk `report_sent` event after successfully sending the newest
daily status report to Telegram.

These events are operational history only. They do not create or modify facts,
proposals, summaries, or corrections.

## Backup workflow automatic memory integration

The MarcBot app-level backup script now records a low-risk `backup_completed`
memory event after successfully creating:

- the backup archive
- the checksum file
- the latest-backup marker

The app-level backup archive also includes `/srv/marcbot/memory`.

The backup completion event is recorded after archive creation, so that specific
event is included in a later backup rather than the archive it describes. This
avoids recording a successful backup before the backup has actually completed.

## Telegram read-only memory events

MarcBot now exposes recent memory events through Telegram with:

    /memory_events

This command is read-only, limited to authorized Telegram chats, and shows a
compact recent event list. It does not search memory, write memory, approve
proposals, correct facts, or contact providers.

## Telegram read-only memory facts

MarcBot now exposes active memory facts through Telegram with:

    /memory_facts

This command is read-only, limited to authorized Telegram chats, and shows only
active facts. It does not search memory, show corrections, expose rejected or
superseded facts, write memory, approve proposals, correct facts, or contact
providers.

## SQLite memory design

SQLite migration planning is documented in `docs/MEMORY_SQLITE.md`.

## SQLite status visibility

The CLI memory status command now includes passive SQLite visibility:

    python -m marcbot memory status

This reports the SQLite database presence, schema version, and whether the
imported view validates against file memory. It does not import or switch runtime
memory behavior.

## Memory context assembly v1
Initial implementation command:

```bash
python -m marcbot memory context --query "weather report"
python -m marcbot memory context --project weather-report --query delivery
python -m marcbot memory context --project weather-report --query delivery --format json
```

The v1 output is a local, human-readable package with Facts, Summaries,
and Recent events sections. It is intentionally suitable for inspection
before any future workflow uses it automatically.


The next implementation phase is a bounded memory context assembly layer.
This layer should answer a practical question for future MarcBot workflows:

```text
Given a topic, project, or task, what local memory context should MarcBot
retrieve before doing model-assisted work?
```

The first version should stay local, deterministic, and CLI-only. It should
not contact any LLM provider. The command should assemble a compact context
package from SQLite-backed memory reads while preserving compatibility with
the current transitional file-backed records.

Expected v1 behavior:

1. Accept a query/topic and optional project filter.
2. Retrieve active matching facts first.
3. Retrieve matching summaries second.
4. Retrieve recent matching events third.
5. Exclude rejected or superseded facts by default.
6. Keep independent limits per section so one category cannot crowd out the
   others.
7. Clearly report `Provider contact: no`.

The context assembler is not the final automatic memory behavior, but it is
the bridge toward it. Once the CLI helper is stable and tested, future
approved chat/workflow paths can call it automatically during their planning
or prompt-preparation stage.

## Controlled model access to memory

MarcBot should not prevent model-assisted workflows from using memory.
The goal is controlled capability, not over-locking.

The intended boundary is:

```text
The model may choose the memory intent.
MarcBot code controls the retrieval method.
```

In practice, a future model-assisted workflow may decide that it needs
context about a project, topic, user preference, correction, or workflow
history. It should request that context through bounded MarcBot memory
interfaces such as a context assembler or structured memory search helper.

The model should not directly rummage through arbitrary files or decide
how much raw memory to load. Deterministic MarcBot code should enforce:

- which memory sources are searched;
- active/rejected/superseded filtering;
- project and query filters;
- per-section limits;
- recency handling;
- stale/correction handling;
- output shape for human inspection or later prompt assembly;
- provider-contact boundaries.

This keeps memory useful and flexible while preserving auditability,
bounded context size, and safety. The model can ask for specific memory;
MarcBot decides how to retrieve it safely.

### Memory context JSON contract

`python -m marcbot memory context --format json` exposes the first
structured workflow-facing memory context contract.

Top-level fields:

- `provider_contact`: always `false` for local memory retrieval.
- `sqlite`: SQLite database existence and schema version metadata.
- `warnings`: local retrieval warnings such as missing database or empty context.
- `path`: SQLite database path used for the derived query view.
- `query`: requested topic/query, or `null`.
- `project`: requested project filter, or `null`.
- `limits`: independent limits for facts, summaries, and events.
- `counts`: number of returned facts, summaries, and events.
- `facts`: active fact records only.
- `summaries`: matching summary records with full body and preview.
- `events`: recent matching event records.

Future workflow code should consume the direct Python helper
`build_memory_context_dict(...)` where possible. The CLI JSON output is
for inspection, integration testing, and shell-facing workflows.


The first controlled workflow integration is opt-in file summarization.
`llm summarize-file` and `llm summarize-file-save` can explicitly request
bounded memory context with `--memory-query` and/or `--memory-project`.
This keeps memory retrieval automatic within that selected workflow only
when requested, while preserving provider-contact boundaries.


Source-monitor summaries can explicitly request bounded memory context.
`source-monitor summarize-latest` and `source-monitor run-summary` accept
`--memory-query` and/or `--memory-project` plus per-section memory limits.
This is the next controlled workflow integration after LLM file summaries.
The memory retrieval step remains local and provider-contact-free; provider
contact remains part of the explicit source-monitor LLM summary command.

## Workflow integration boundary

The memory context helper is now suitable as a local workflow-facing API.
Future workflows should prefer `build_memory_context_dict(...)` over parsing
CLI text or JSON output.

Memory retrieval may become automatic in selected workflows, but it must
remain:

- local;
- deterministic;
- bounded by project/query and per-section limits;
- warning-aware;
- provider-contact-free;
- separate from any later explicit LLM/provider call.

A workflow may use memory context to prepare a safer prompt, report, or
analysis input. It should not treat memory retrieval itself as a model call,
and it should not give the model arbitrary file or memory-store access.

### Live validation of opt-in file summarization memory context

The first live validation used a small manual workspace note and explicit
memory flags on `llm summarize-file` and `llm summarize-file-save`.

Validated behavior:

- `memory context` retrieved bounded weather-report context locally.
- local memory retrieval reported `Provider contact: no`.
- `llm summarize-file` included the supplied weather-report memory context.
- `llm summarize-file-save` wrote a summary artifact under the workspace.
- provider contact occurred only during the explicit LLM commands.

The live run also confirmed that provider-contact LLM commands need the
LM Studio environment secret loaded in the shell before execution.

## Prompt-use rules for memory context

When MarcBot includes retrieved memory context in a model prompt, the prompt
should make the memory boundary explicit. The model should understand that
the memory block is local MarcBot context assembled by deterministic code,
not unrestricted file-system access and not provider-generated truth.

Prompt-use rules:

1. Use supplied memory context only when it is relevant to the requested task.
2. Prefer active facts over summaries and recent events when they conflict.
3. Treat warnings from the memory context package as important.
4. Do not invent memory not present in the supplied context block.
5. Do not assume recent events are durable facts unless they are also
   represented as active facts or explicit summaries.
6. Use corrections, rejected state, and supersession state when present.
7. Keep memory retrieval separate from provider contact; retrieval should
   already be complete before the model receives the prompt.

These rules are intended to improve prompt quality before memory context is
used by more workflows. They keep the model useful while preserving the
controlled retrieval boundary.



Source-monitor summary commands can also consume memory profiles with
`--memory-profile <name>`. This keeps source-monitor summary behavior
consistent with LLM file-summary commands while preserving explicit opt-in
memory retrieval.
LLM file-summary commands can consume memory profiles with
`--memory-profile <name>`. This lets a workflow use a deterministic
memory profile without repeating query/project/limit flags manually.
The first supported profile is `weather-report`.

#




`/memory_reject_proposal <id> | <reason>` allows Telegram-side cleanup
of pending proposals. It is intentionally lower risk than approval: it
closes a pending proposal and does not create an approved durable fact.
`/memory_proposal <id>` provides read-only Telegram detail for one
proposal. It complements `/memory_proposals` and keeps review visibility
available without adding Telegram approval authority.
`/memory_proposals` provides read-only Telegram visibility into pending
memory proposals. It complements `/memory_propose_fact` by letting Marc
inspect pending proposal state without using the CLI.

### Telegram explicit memory proposal

`/memory_propose_fact <project> | <statement>` is the first Telegram-side
memory write path. It creates a pending fact proposal only; it does not
approve durable memory. This is the first step toward Telegram memory
candidate capture while preserving review boundaries.

Example:

```text
/memory_propose_fact source-monitor | Source-monitor summaries should use explicit memory profiles.
```





The Telegram candidate-propose bridge was validated end-to-end:

- non-proposal candidate text reports `Created: no` and writes nothing
- durable-signal candidate text creates a pending proposal only
- pending proposal details show source `telegram_memory_candidate_propose`
- SQLite validation remains valid after create and cleanup rejection
- cleanup returns the pending proposal queue to empty
- Telegram still cannot approve durable facts


`/memory_candidate_status` provides read-only Telegram status for the
candidate-memory workflow. It lists available commands and repeats the
current safety boundary: previews write nothing, candidate propose writes
pending proposals only, Telegram cannot approve durable facts, provider
contact is no, and the status command writes no memory.

`/memory_candidate_help` provides Telegram-side guidance for the memory
candidate workflow. It is intentionally read-only and summarizes preview,
proposal-preview, candidate-propose, proposal review, and proposal rejection
without adding approval authority.

`/memory_candidate_propose <project> | <text>` exposes the controlled
candidate-to-pending-proposal bridge in Telegram. It writes only pending
proposals and only when deterministic candidate preview returns
`propose_fact`. It does not approve durable facts.

`/memory_candidate_preview <project> | <text>` exposes deterministic
candidate preview in Telegram without writing memory. This allows Marc to
test memory-candidate classification from chat before automatic capture
is introduced.



`/memory_proposal_preview <project> | <text>` exposes
candidate-to-proposal preview in Telegram without creating a proposal.
This lets Marc verify what a future bridge would propose before any
automatic or semi-automatic write path exists.


### Memory candidate record-event live validation

The CLI candidate record-event bridge was validated end-to-end:

- non-event candidate text returns `created: false`, `event_path: null`, and `writes: false`
- event-like candidate text returns `created: true`, a monthly JSONL `event_path`, and `writes: true`
- the event is recorded as `workflow_completed` with source `memory_candidate_cli_record_event`
- provider contact remains `false`
- SQLite validation remains valid after the event write
- Git status remains clean because memory data is outside the app repo

This is intentionally lower risk than durable facts: it records operational
history only. Durable facts remain on the pending-proposal path and still
require explicit CLI approval.

### Memory candidate record-event

`python -m marcbot memory candidate record-event` is the first controlled
low-risk candidate-to-event bridge. It records a local memory event only
when deterministic candidate preview returns `record_event`.

For non-event candidates, the command reports `Created: no` and writes
nothing. This keeps durable facts on the pending-proposal path and avoids
automatic fact approval.

Use `--format json` when future automation needs a structured result rather
than human-readable text.

The JSON result includes `event_path` as the stable created-event log file
identifier. Events are stored in monthly JSONL files. `event_index` is
currently `null` because the memory event result object does not expose a
stable index.

### Memory candidate status

`python -m marcbot memory candidate status` provides a read-only CLI
summary of the memory candidate workflow. It mirrors the Telegram
`/memory_candidate_status` boundary summary and is intended for scripts,
future sessions, and operator checks.

### Memory candidate propose JSON contract

`python -m marcbot memory candidate propose --format json` returns a
machine-readable result for both write and non-write paths. Future
automation should consume this JSON contract instead of parsing
human-readable CLI output.

Non-write result example:

```json
{
  "created": false,
  "proposal_id": null,
  "proposal_path": null,
  "provider_contact": false,
  "reason": "text looks like a low-risk operational event",
  "writes": false
}
```

Write result example:

```json
{
  "created": true,
  "proposal_id": "candidate-fact-YYYYMMDD-HHMMSS",
  "proposal_path": "/srv/marcbot/memory/pending/candidate-fact-YYYYMMDD-HHMMSS.json",
  "provider_contact": false,
  "reason": "text looks like a durable instruction, preference, or policy",
  "writes": true
}
```

Validated behavior:

- non-write JSON returns `created: false`, `proposal_id: null`, and `writes: false`
- write JSON returns `created: true`, a `candidate-fact-*` proposal id, and `writes: true`
- pending proposal detail shows source `memory_candidate_cli_propose`
- SQLite validation remains valid after create and cleanup rejection
- cleanup returns the pending proposal queue to empty

This command creates pending proposals only. It does not approve durable
facts. Durable approval remains CLI-only and explicit.

### Memory candidate propose

`python -m marcbot memory candidate propose` is the first controlled
candidate-to-pending-proposal bridge. It is CLI-only. It creates a pending
fact proposal only when deterministic candidate preview classifies the text
as `propose_fact`.

Example:

```bash
python -m marcbot memory candidate propose --project source-monitor "Source-monitor summaries should use explicit memory profiles."
```

For non-proposal candidates, the command reports `Created: no` and writes
nothing. This preserves the durable-memory approval boundary: it creates
pending proposals only and never approves durable facts.

Use `--format json` when future automation needs a structured result rather
than human-readable text.

### Memory candidate proposal preview

`python -m marcbot memory candidate proposal-preview` bridges
candidate classification to the pending-proposal workflow without writing
memory. It shows whether MarcBot would create a pending fact proposal and
what proposal fields would be used.

Example:

```bash
python -m marcbot memory candidate proposal-preview --project source-monitor "Source-monitor summaries should use explicit memory profiles."
python -m marcbot memory candidate proposal-preview --format json --project source-monitor "Source-monitor summaries should use explicit memory profiles."
```

This remains preview-only: provider contact is no and writes is no.

### Memory candidate preview

`python -m marcbot memory candidate preview` is the first deterministic
candidate-detection surface. It classifies supplied text as a possible
memory action without writing memory or contacting a provider.

Example:

```bash
python -m marcbot memory candidate preview --project source-monitor "Source-monitor summaries should use explicit memory profiles."
python -m marcbot memory candidate preview --format json --project source-monitor "Source-monitor summaries should use explicit memory profiles."
```

Current preview actions are:

- `ignore`
- `record_event`
- `propose_fact`
- `manual_review`


The JSON format is intended for future automation paths so workflow code
can consume the action, risk level, provider-contact flag, and write flag
without parsing human-readable output.

This is intentionally preview-only. It is the foundation for future
Telegram/chat candidate detection without automatic memory capture.

## Telegram and chat memory direction

Telegram should eventually become a major memory input, but not by saving
all chat text directly. The target pipeline is:

```text
Telegram interaction
  -> bounded memory candidate detection
  -> classify as event, fact, proposal, correction, summary, or ignore
  -> apply risk-tier guardrails
  -> write low-risk events automatically
  -> propose or queue higher-risk durable facts
  -> expose read-only audit and correction commands
```

Telegram memory should include both Marc-side and bot-side context:

- Marc-side: goals, corrections, durable decisions, workflow preferences,
  and explicit instructions.
- Bot-side: commands run, artifacts sent, errors observed, retries,
  workflow completions, and summaries of important sessions.

The mature goal is selective, risk-aware automatic memory capture. MarcBot
should not require Marc to manually approve every low-risk write, but it
must remain auditable and correctable, with explicit approval for high-risk
or sensitive memory.

## Memory context profiles

MarcBot supports deterministic memory context profiles for common workflows.
The first profile is `weather-report`:

```bash
python -m marcbot memory profiles
python -m marcbot memory profiles --format json

Telegram read-only visibility:

```text
/memory_profiles
/memory_context <profile>
```
python -m marcbot memory context --profile weather-report
python -m marcbot memory context --profile source-monitor
python -m marcbot memory context --profile weather-report --format json
```

The `weather-report` profile maps to a short high-signal query, `weather`,
with bounded section limits. It intentionally does not set `project` so it
can retrieve both workflow-specific facts and cross-project reference-pattern
facts. Retrieval remains local and provider-contact-free.


Source-monitor prompt preview can inspect memory-profile prompts before
provider contact:

```bash
python -m marcbot source-monitor summarize-latest ai --memory-profile source-monitor --preview-prompt
```

This keeps profile-backed workflow prompts auditable before LLM execution.
The `source-monitor` profile maps to project `source-monitor` and query `source-monitor`. It should be used only after durable source-monitor facts exist and SQLite validation confirms those facts are available.


## Generic memory target model

MarcBot memory is intended to become a generic, workflow-aware memory
substrate, not a manual plan-file replacement. The long-term goal is for
MarcBot to remember useful operational and project context across CLI
workflows, scheduled jobs, Telegram interactions, LLM-assisted summaries,
reports, and future chat modes.

The memory system should reduce Marc's burden. It should not create a new
approval inbox where every low-risk write requires manual review. Instead,
MarcBot should use a risk-tiered write model:

1. Automatic low-risk events:
   - workflow completed;
   - report generated or sent;
   - backup completed;
   - source-monitor summary generated;
   - bounded command failure or recovery observed.

2. Automatic or semi-automatic operational facts when confidence is high:
   - latest successful workflow run;
   - repeated failure pattern;
   - current known artifact location;
   - stable workflow status facts.

3. Proposed durable facts for review while the system matures:
   - project direction;
   - durable preferences;
   - recurring workflow design decisions;
   - corrections inferred from conversation.

4. Explicit approval required:
   - sensitive personal data;
   - secrets, tokens, credentials, or security-sensitive details;
   - permission or authority changes;
   - broad behavioral changes;
   - ambiguous or low-confidence inferences.

The intended mature behavior is that MarcBot automatically captures routine
low-risk operational memory, proposes or carefully applies medium-risk
memory with auditability, and requires explicit approval for high-risk
memory. This keeps the system useful without making Marc approve every
routine memory transaction.

This is intentionally stronger than a plan-file memory system. Plan files
are useful for narrative continuity, but they are manual, stale-prone, hard
to query, difficult to supersede, and not easy for workflows to consume
consistently. MarcBot memory should be structured, indexed, correctable,
auditable, profile-aware, and available to deterministic workflow code
before model calls.

## Memory workflow reference roles

MarcBot now has two useful reference workflows for memory integration,
but they prove different things.

### Weather-report

`weather-report` is the reference workflow for useful existing memory
retrieval. It already has durable facts and recent workflow events, so
`python -m marcbot memory context --profile weather-report` returns
meaningful local context without provider contact.

This proves that named memory context profiles can retrieve useful workflow
history without Marc manually spelling out query/project/limit flags.

### Source-monitor

`source-monitor` is the reference workflow for memory-aware LLM workflow
integration mechanics. It already has a bounded CLI, local artifacts, and
an explicit LLM summary path, so it is a safe place to validate:

- deterministic memory retrieval before the model call;
- prompt-boundary rules around supplied memory;
- provider-contact-free retrieval;
- provider contact only during explicit LLM summary commands;
- prompt budget handling when memory context is added;
- LLM env loading and retry behavior outside top-level `llm` commands.

Source-monitor now also proves useful source-monitor-specific memory
retrieval because durable source-monitor facts exist and the dedicated
`source-monitor` memory profile returns meaningful local context. It remains
the reference workflow for memory-aware LLM workflow integration mechanics.

The intended sequence is:

1. Keep `weather-report` as the first useful memory profile.
2. Keep `source-monitor` as the first memory-aware LLM workflow integration.
3. Keep durable source-monitor facts current as the workflow changes.
4. Use profile-backed prompt preview before expanding automatic workflow use.
