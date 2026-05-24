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

## Implemented S2 schema initialization

MarcBot now includes a SQLite schema initialization module:

    marcbot/memory_sqlite.py

Initial support includes:

- database path definition
- schema version metadata
- table creation
- index creation
- read-only SQLite status formatting
- tests for schema creation and idempotency

This does not import file memory yet and does not change runtime memory behavior.

## Implemented S3 file-memory import

SQLite import support can rebuild the imported SQLite view from the file memory
source of truth.

Current behavior:

- initializes schema if needed
- clears imported memory tables
- imports events from JSONL
- imports facts from TOML
- imports summaries from Markdown metadata/body
- imports proposals from JSON
- imports corrections from JSONL
- records each import in `import_runs`
- preserves file memory as source of truth

Runtime memory reads and writes still use file memory.

## Implemented S4 SQLite import validation

SQLite validation can now compare file-memory record counts with imported
SQLite row counts.

Validation compares:

- events
- facts
- summaries
- proposals
- corrections

The validation result reports file counts, SQLite counts, per-table OK/MISMATCH,
overall validity, and provider-contact-free status.

File memory remains the source of truth.

## Implemented S5 SQLite CLI commands

MarcBot now exposes controlled SQLite memory commands:

    python -m marcbot memory sqlite status
    python -m marcbot memory sqlite init
    python -m marcbot memory sqlite import
    python -m marcbot memory sqlite counts
    python -m marcbot memory sqlite validate

These commands keep file memory as the source of truth. SQLite remains an
imported/indexed view. Commands are CLI-only and provider-contact-free.

## SQLite visibility in memory status

`python -m marcbot memory status` now includes a passive SQLite section.

The status command does not import, rebuild, or switch memory behavior. It only
reports whether the SQLite database is present, which schema version is present,
and whether the current imported view validates against file memory.

File memory remains the source of truth.


## Planned production SQLite sync model

SQLite should eventually stay current as memory is written, but not by running a
full rebuild import after every memory write.

The preferred production model is file-first incremental sync:

1. Write the file-memory record first.
2. If the file write succeeds, update SQLite for that specific record.
3. If the SQLite update fails, do not remove or rewrite the file-memory record.
4. Surface the SQLite failure clearly.
5. Keep full `memory sqlite import` as a rebuild/recovery command.
6. Keep `memory sqlite validate` as the drift detection command.

## Source of truth

Until a future milestone explicitly changes this:

    file memory remains the source of truth
    SQLite remains an indexed/queryable view

This means a file write is the authoritative memory transaction.

## Why not full import after every write?

Running a full import after each memory write is simple but not ideal:

- it is inefficient as memory grows
- it rewrites unrelated tables
- it creates more lock/contention opportunities
- it makes small writes slower
- it hides which specific record caused a sync issue

Full import remains useful for rebuilds, recovery, migrations, and validation,
but not as the normal per-write sync mechanism.

## Incremental sync order

For each memory write, the intended order is:

    write file memory
    sync affected SQLite row or rows
    optionally validate narrow expectations

The first incremental sync target should be events because events are append-only
and are already produced by low-risk automatic workflows.

## Phase order

Suggested implementation order:

1. Add SQLite helper to insert one event row from an event object/source metadata.
2. Add tests for event-row insertion and duplicate-safe behavior.
3. Wire `add_memory_event` to attempt SQLite sync after the JSONL append.
4. Keep the full import command available.
5. Validate that automatic workflow events appear in SQLite without a full import.
6. Extend the same pattern later to summaries.
7. Extend later to facts/proposals/corrections only after correction semantics are
   carefully designed.

## Failure behavior

The first version should be strict:

- if the file-memory write succeeds but SQLite sync fails, the command should
  return an error
- the file record remains present
- `memory sqlite import` can repair the SQLite view
- the error should be visible rather than silent

This matches MarcBot's preference for stable, testable, explicit behavior.

A future version may allow best-effort SQLite sync for selected low-risk
scheduled workflows, but only if that behavior is documented and tested.

## Drift handling

If validation reports SQLite drift:

    python -m marcbot memory sqlite import
    python -m marcbot memory sqlite validate

should repair and confirm the imported view.

Drift is not a data-loss condition as long as file memory is intact.

## Implemented S8 incremental event row helper

MarcBot now has a SQLite helper for inserting one memory event row into the
imported SQLite view.

The helper:

- initializes the SQLite schema if needed
- inserts one event row
- stores source file and source line metadata
- is duplicate-safe using source file plus source line
- does not change file memory
- does not switch runtime reads or writes to SQLite

This is preparation for wiring file-first event writes to SQLite sync.

## Implemented S9 event-write SQLite sync

Memory event writes now use file-first SQLite sync.

When `add_memory_event` appends an event to the JSONL file, it then checks
whether the SQLite database exists. If the database exists, MarcBot inserts the
single appended event row into SQLite using the event source file and source
line. If the database does not exist, SQLite sync is skipped.

The file write remains the authoritative memory transaction. If SQLite sync
fails after the file write, the command raises a clear error and the full
`memory sqlite import` command can rebuild the SQLite view from file memory.

## Event sync root guard

Incremental SQLite event sync only runs for event files under the real memory
root:

    /srv/marcbot/memory

This prevents tests, temporary memory roots, and ad-hoc imports from polluting
the production SQLite database. Temporary roots remain file-only unless a test
explicitly calls SQLite helpers with a temporary database path.

## Implemented incremental summary row helper

MarcBot now has a SQLite helper for inserting or replacing one memory summary
row in the imported SQLite view.

The helper:

- initializes the SQLite schema if needed
- reads one Markdown summary file
- parses summary metadata and body
- upserts one SQLite row by summary filename
- does not change file memory
- does not switch runtime reads or writes to SQLite

This prepares summary writes for file-first SQLite sync.

## Implemented summary-write SQLite sync

Memory summary writes now use file-first SQLite sync.

When `add_memory_summary` writes a Markdown summary file, it then checks whether
the summary path is under the real memory root and whether the SQLite database
exists. If both are true, MarcBot upserts that summary row into SQLite.

The file write remains the authoritative memory transaction. If SQLite sync
fails after the file write, the command raises a clear error and the full
`memory sqlite import` command can rebuild the SQLite view from file memory.

## Planned SQLite sync for facts, proposals, and corrections

Events and summaries now have file-first incremental SQLite sync. Facts,
proposals, and corrections need a more careful design because they involve
durable state transitions.

File memory remains the source of truth.

## Fact sync model

Facts are stored as TOML files under:

    /srv/marcbot/memory/facts

SQLite table:

    memory_facts

Fact writes should use file-first upsert semantics:

1. Write or update the TOML fact file.
2. If the file path is under the real memory root and SQLite exists, upsert that
   one fact row into SQLite.
3. If SQLite sync fails, raise a clear error after the file write.
4. Repair drift with:

       python -m marcbot memory sqlite import
       python -m marcbot memory sqlite validate

### Fact add

`add_memory_fact` writes a new TOML fact file.

SQLite sync should upsert the new fact row keyed by fact ID.

Expected result:

    file facts count increases by 1
    SQLite facts count increases by 1
    validation remains valid

### Fact supersession

`supersede_memory_fact` changes the old fact and creates a new fact.

SQLite sync should:

1. upsert the old fact row after its status/metadata changes
2. upsert the new fact row after creation
3. insert the related correction ledger row

Expected result:

    file fact count increases by 1
    SQLite fact count increases by 1
    old fact row status becomes superseded
    new fact row status becomes active
    correction count increases by 1
    validation remains valid

### Fact rejection

`reject_memory_fact` changes an existing fact status.

SQLite sync should:

1. upsert the rejected fact row after its status/metadata changes
2. insert the related correction ledger row

Expected result:

    file fact count unchanged
    SQLite fact count unchanged
    fact row status becomes rejected
    correction count increases by 1
    validation remains valid

## Proposal sync model

Proposals are stored as JSON files under:

    /srv/marcbot/memory/pending

SQLite table:

    memory_proposals

Proposal writes should use file-first upsert semantics.

### Proposal add

`add_memory_proposal` writes a pending proposal JSON file.

SQLite sync should upsert that proposal row keyed by proposal ID.

Expected result:

    file proposal count increases by 1
    SQLite proposal count increases by 1
    validation remains valid

### Proposal approval

`approve_memory_proposal` changes a proposal status, creates a fact, and writes
a correction ledger record.

SQLite sync should:

1. upsert the approved proposal row
2. upsert the created fact row
3. insert the related correction ledger row

Expected result:

    proposal count unchanged
    proposal status becomes approved
    fact count increases by 1
    correction count increases by 1
    validation remains valid

### Proposal rejection

`reject_memory_proposal` changes a proposal status and writes a correction
ledger record.

SQLite sync should:

1. upsert the rejected proposal row
2. insert the related correction ledger row

Expected result:

    proposal count unchanged
    proposal status becomes rejected
    correction count increases by 1
    validation remains valid

## Correction sync model

Corrections are JSONL records under:

    /srv/marcbot/memory/corrections

SQLite table:

    memory_corrections

Corrections are append-only ledger records. They should use source file plus
source line duplicate protection, the same pattern as memory events.

Correction sync should:

1. append JSONL correction record to file memory first
2. insert the one correction row into SQLite if SQLite exists
3. skip sync for temporary roots outside `/srv/marcbot/memory`
4. raise a clear error if SQLite sync fails after the file write

Expected result:

    file correction record count increases by 1
    SQLite correction row count increases by 1
    validation remains valid

## Recommended implementation order

The safest implementation order is:

1. Add SQLite helper to upsert one fact row from a TOML fact file.
2. Add SQLite helper to upsert one proposal row from a JSON proposal file.
3. Add SQLite helper to insert one correction row from JSON data/source metadata.
4. Wire `add_memory_fact`.
5. Wire `add_memory_proposal`.
6. Wire correction append helper, if correction writing is centralized.
7. Wire fact supersession/rejection.
8. Wire proposal approval/rejection.
9. Validate each transition with production-path tests.

Do not implement all transitions in one large patch.

## Centralization requirement

Before wiring correction sync, inspect whether correction JSONL writes are
centralized. If correction writes are duplicated across multiple functions, first
refactor them into one helper so SQLite correction sync has a single safe hook.

## Testing requirements

Each transition should have tests that confirm:

- file write still happens first
- SQLite sync happens only for real `/srv/marcbot/memory` paths
- temporary roots do not pollute the real SQLite database
- SQLite drift can be repaired with full import
- validation remains valid after production-path writes

## Production boundary

Until a future milestone explicitly changes this:

    file memory remains source of truth
    SQLite remains indexed/queryable view

Runtime reads should not switch to SQLite until incremental sync for all active
write paths is complete and validated.

## Correction append centralization

Correction JSONL writes are now centralized through a memory-store helper before
SQLite correction sync is added.

Centralization keeps later SQLite correction sync safer because all correction
ledger appends can use one hook instead of duplicating sync logic across fact and
proposal transition functions.


## Implemented incremental correction row helper

MarcBot now has a SQLite helper for inserting one memory correction row into the
imported SQLite view.

The helper:

- initializes the SQLite schema if needed
- inserts one correction row
- stores source file and source line metadata
- is duplicate-safe using source file plus source line
- does not change file memory
- does not switch runtime reads or writes to SQLite

This prepares the centralized correction append helper for file-first SQLite
sync.

## Implemented correction-write SQLite sync

Correction ledger writes now use file-first SQLite sync.

When `_append_memory_correction` appends a correction JSONL record, it then checks
whether the correction path is under the real memory root and whether the SQLite
database exists. If both are true, MarcBot inserts that correction row into
SQLite using the correction source file and source line.

The file append remains the authoritative memory transaction. If SQLite sync
fails after the file write, the command raises a clear error and the full
`memory sqlite import` command can rebuild the SQLite view from file memory.

## Implemented incremental proposal row helper

MarcBot now has a SQLite helper for inserting or replacing one memory proposal
row in the imported SQLite view.

The helper:

- initializes the SQLite schema if needed
- reads one proposal JSON file
- upserts one SQLite row by proposal ID
- handles status changes such as pending to rejected
- does not change file memory
- does not switch runtime reads or writes to SQLite

This prepares proposal add/reject paths for file-first SQLite sync.

## Implemented proposal add/reject SQLite sync

Memory proposal add and reject now use file-first SQLite sync.

When `add_memory_proposal` writes a proposal JSON file, it then checks whether
the proposal path is under the real memory root and whether the SQLite database
exists. If both are true, MarcBot upserts that proposal row into SQLite.

When `reject_memory_proposal` updates a proposal JSON file, it upserts the
updated rejected proposal row into SQLite.

Proposal approval remains separate because approval also creates a fact and may
interact with correction records.


## Implemented incremental fact row helper

MarcBot now has a SQLite helper for inserting or replacing one memory fact row
in the imported SQLite view.

The helper:

- initializes the SQLite schema if needed
- reads one fact TOML file
- upserts one SQLite row by fact ID
- handles status changes such as active to rejected or superseded
- does not change file memory
- does not switch runtime reads or writes to SQLite

This prepares fact add/reject/supersession paths for file-first SQLite sync.

## Implemented fact add SQLite sync

Memory fact add now uses file-first SQLite sync.

When `add_memory_fact` writes a fact TOML file, it then checks whether the fact
path is under the real memory root and whether the SQLite database exists. If
both are true, MarcBot upserts that fact row into SQLite.

Fact rejection, supersession, and proposal approval remain separate because they
involve existing-record state changes and, in some cases, correction records.

## Implemented fact rejection SQLite sync

Memory fact rejection now uses file-first SQLite sync.

When `reject_memory_fact` updates a fact TOML file to rejected status, MarcBot
upserts the changed fact row into SQLite before appending the correction record.
The centralized correction append helper then syncs the correction row into
SQLite.

The file update and correction append remain the authoritative memory
transactions. If SQLite sync fails after a file write, the command raises a
clear error and the full `memory sqlite import` command can rebuild the SQLite
view from file memory.

## Implemented fact supersession SQLite sync

Memory fact supersession now uses file-first SQLite sync.

When `supersede_memory_fact` updates the old fact TOML file, MarcBot upserts the
old fact row into SQLite with superseded metadata. When it creates the new fact
TOML file, MarcBot upserts the new active fact row into SQLite. The centralized
correction append helper then syncs the fact-superseded correction row into
SQLite.

The file updates and correction append remain the authoritative memory
transactions. If SQLite sync fails after a file write, the command raises a
clear error and the full `memory sqlite import` command can rebuild the SQLite
view from file memory.

## Implemented proposal approval SQLite sync

Memory proposal approval now uses file-first SQLite sync.

When `approve_memory_proposal` approves a proposal, MarcBot creates the approved
fact through `add_memory_fact`, which syncs the new fact row into SQLite. MarcBot
then writes the approved proposal JSON file and upserts the approved proposal row
into SQLite. The centralized correction append helper then syncs the
proposal-approved correction row into SQLite.

The file writes and correction append remain the authoritative memory
transactions. If SQLite sync fails after a file write, the command raises a
clear error and the full `memory sqlite import` command can rebuild the SQLite
view from file memory.

### SQLite-backed fact reads

MarcBot begins the read/query phase with a bounded SQLite-backed fact
listing command:

```bash
python -m marcbot memory sqlite facts
python -m marcbot memory sqlite facts --query MarcBot --limit 5
python -m marcbot memory sqlite facts --category architecture --project MarcBot
```

This command reads from the imported SQLite view only. File memory remains
the source of truth, SQLite remains a query/index view, and provider contact
for memory operations remains `no`.
