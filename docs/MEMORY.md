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
