# MarcBot Memory Design Notes

MarcBot does not yet have a full memory subsystem.

This document records the intended direction for a future memory system so the
project can revisit the design deliberately when the core workflows justify it.

## Goal

MarcBot should eventually have a reliable hybrid memory system that helps future
chats and actions consider project history without becoming mysterious, unsafe,
or difficult to correct.

The goal is not just to store facts. The goal is to reduce Marc's operational
burden by allowing MarcBot to remember, retrieve, update, correct, and explain
important context over time.

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

Authoritative sources include:

- current repository files
- current local config schemas
- actual command output
- Git commits
- validation results
- support snapshots
- explicit Marc approvals or corrections

Helpful but non-authoritative sources include:

- generated summaries
- retrieved memories
- LLM interpretations
- older session notes
- inferred preferences
- proposed reflections

Memory should assist decisions, not silently override current evidence.

## Hybrid memory direction

The likely long-term design is a hybrid system using multiple memory layers.

### 1. Curated human-readable memory files

Markdown or TOML files can store stable context such as:

- operator preferences
- project principles
- security rules
- runbooks
- recurring workflow rules
- durable design decisions

These files are easy to inspect, edit, back up, and review.

Some memory files may belong outside Git if they contain personal or local
operational details.

### 2. Structured database-backed memory

A database should eventually store durable facts, events, summaries,
corrections, source metadata, and review state.

SQLite should probably be evaluated first because MarcBot is personal-only and
SQLite is simple to back up, test, and operate.

A stronger database backend such as PostgreSQL, MariaDB, or MySQL should be
considered only if justified by concurrency, scale, indexing, remote access, or
operational needs.

Possible future tables:

- memory_events
- memory_facts
- memory_summaries
- memory_corrections
- memory_sources
- memory_reviews

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

Memory is a future subsystem.

The current project already has early memory-like support through:

- docs/SESSION_START.md
- python -m marcbot support snapshot
- docs/CHANGELOG.md
- docs/ROADMAP.md
- project documentation
- Git history

These should remain the source of truth until a real memory subsystem is
designed, tested, and documented.

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

The first implementation should use inspectable files.

Suggested v1 storage:

    events/YYYY-MM.jsonl
    facts/*.toml
    summaries/YYYY-MM-DD-<slug>.md
    pending/*.json
    corrections/*.jsonl

SQLite may be added later after the file schemas are proven.

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
