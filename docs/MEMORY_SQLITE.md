# MarcBot SQLite Memory Design

MarcBot memory currently uses inspectable files under:

    /srv/marcbot/memory

This file layout remains the source of truth during the initial SQLite work.

SQLite will be introduced carefully as an indexed, queryable representation of
the existing memory store. The first implementation must be import-only and
read-only from the application perspective.

## Goals

SQLite should make memory easier to query, validate, export, and eventually use
for bounded context retrieval.

Primary goals:

- preserve the existing audit-friendly file memory layout
- import existing memory into a structured database
- validate database counts against file memory
- support read-only inspection commands
- keep provider contact disabled
- avoid broad autonomous memory behavior
- avoid forcing Marc into routine low-risk memory transactions
- keep explicit approval/correction behavior for high-risk changes

## Non-goals for the first SQLite phase

The first SQLite phase must not:

- replace file memory as the source of truth
- change existing memory write commands
- change Telegram memory behavior
- add LLM-assisted memory generation
- add embeddings
- add background indexing jobs
- add automatic fact/proposal/correction writes
- remove or rewrite existing memory files

## Proposed database location

Default SQLite database path:

    /srv/marcbot/memory/marcbot-memory.sqlite3

The database lives inside `/srv/marcbot/memory` so it is included in app-level
backups.

## Schema overview

Initial tables:

    memory_events
    memory_facts
    memory_summaries
    memory_proposals
    memory_corrections
    import_runs

## Table: memory_events

Stores JSONL event records.

Suggested fields:

    id INTEGER PRIMARY KEY
    timestamp TEXT NOT NULL
    type TEXT NOT NULL
    project TEXT
    summary TEXT NOT NULL
    source TEXT NOT NULL
    confidence TEXT NOT NULL
    details TEXT
    cause TEXT
    resolution TEXT
    verification TEXT
    follow_up TEXT
    related_files_json TEXT NOT NULL DEFAULT '[]'
    related_commands_json TEXT NOT NULL DEFAULT '[]'
    related_artifacts_json TEXT NOT NULL DEFAULT '[]'
    related_commits_json TEXT NOT NULL DEFAULT '[]'
    source_file TEXT NOT NULL
    source_line INTEGER NOT NULL
    imported_at TEXT NOT NULL

Indexes:

    timestamp
    type
    project
    source

## Table: memory_facts

Stores TOML fact records.

Suggested fields:

    id TEXT PRIMARY KEY
    statement TEXT NOT NULL
    category TEXT NOT NULL
    project TEXT
    source TEXT NOT NULL
    created_at TEXT NOT NULL
    updated_at TEXT NOT NULL
    confidence TEXT NOT NULL
    status TEXT NOT NULL
    details TEXT
    supersedes TEXT
    superseded_by TEXT
    superseded_reason TEXT
    rejected_at TEXT
    rejected_reason TEXT
    rejected_source TEXT
    source_file TEXT NOT NULL
    imported_at TEXT NOT NULL

Indexes:

    status
    category
    project
    updated_at

## Table: memory_summaries

Stores Markdown summary metadata and body.

Suggested fields:

    name TEXT PRIMARY KEY
    title TEXT NOT NULL
    project TEXT
    source TEXT NOT NULL
    created_at TEXT NOT NULL
    body TEXT NOT NULL
    source_file TEXT NOT NULL
    imported_at TEXT NOT NULL

Indexes:

    created_at
    project

## Table: memory_proposals

Stores JSON proposal records.

Suggested fields:

    id TEXT PRIMARY KEY
    created_at TEXT NOT NULL
    proposed_type TEXT NOT NULL
    proposed_statement TEXT NOT NULL
    source TEXT NOT NULL
    rationale TEXT NOT NULL
    risk_level TEXT NOT NULL
    status TEXT NOT NULL
    project TEXT
    details TEXT
    reviewed_at TEXT
    review_reason TEXT
    source_file TEXT NOT NULL
    imported_at TEXT NOT NULL

Indexes:

    status
    proposed_type
    risk_level
    project
    created_at

## Table: memory_corrections

Stores JSONL correction records.

Suggested fields:

    id INTEGER PRIMARY KEY
    timestamp TEXT NOT NULL
    type TEXT NOT NULL
    fact_id TEXT
    old_fact_id TEXT
    new_fact_id TEXT
    proposal_id TEXT
    created_type TEXT
    created_id TEXT
    previous_status TEXT
    reason TEXT
    source TEXT
    confidence TEXT
    raw_json TEXT NOT NULL
    source_file TEXT NOT NULL
    source_line INTEGER NOT NULL
    imported_at TEXT NOT NULL

Indexes:

    timestamp
    type
    fact_id
    proposal_id

## Table: import_runs

Stores import validation metadata.

Suggested fields:

    id INTEGER PRIMARY KEY
    started_at TEXT NOT NULL
    completed_at TEXT
    source_root TEXT NOT NULL
    database_path TEXT NOT NULL
    event_count INTEGER NOT NULL DEFAULT 0
    fact_count INTEGER NOT NULL DEFAULT 0
    summary_count INTEGER NOT NULL DEFAULT 0
    proposal_count INTEGER NOT NULL DEFAULT 0
    correction_count INTEGER NOT NULL DEFAULT 0
    status TEXT NOT NULL
    message TEXT

## Import strategy

Initial import should be destructive/rebuild-style:

1. Create SQLite database if missing.
2. Create tables if missing.
3. Clear imported memory tables.
4. Re-read file memory.
5. Insert all records.
6. Record import run.
7. Validate counts.

This avoids complex incremental sync during early development.

## Source of truth rule

Until explicitly changed in a later milestone:

    file memory is source of truth
    SQLite is an imported/indexed view

Existing commands continue using file memory.

## Failure behavior

Import failures should not corrupt file memory.

If import fails:

- exit non-zero
- leave file memory untouched
- record or print a clear error where possible
- do not partially switch runtime behavior

## Provider boundary

SQLite import and validation must not contact model providers.

The status output must continue to show:

    Provider contact: no

## Future possibilities

Possible future phases:

- read-only SQLite-backed search
- richer structured queries
- export/import validation reports
- optional SQLite-first read path
- optional SQLite-first write path with file export
- embeddings or LLM-assisted proposal generation

Those are intentionally deferred.
