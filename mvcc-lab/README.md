# MVCC Lab

A dependency-free, deterministic simulator for multiversion-concurrency-control transactions. Explore snapshot reads, first-committer-wins write conflicts, version visibility, and optimistic transaction outcomes without a database server.

## How it works

The engine stores an immutable history of committed row versions, each tagged with a commit timestamp and tombstone state. A transaction reads the newest version at or before its start timestamp, stages private writes/deletes, and commits atomically if no row it writes has changed since its snapshot. Read-only transactions can commit regardless of newer versions. The simulator is single-threaded: concurrency is represented by interleaving transaction operations, making schedules reproducible.

## Usage

Requires Python 3.10+; no third-party packages.

```sh
python3 mvcc.py demo
python3 mvcc.py run example.json
python3 -m unittest -v
```

The JSON input shape is `{"initial": {"account": 10}, "transactions": [{"name": "T1", "ops": [{"get": "account"}, {"put": ["account", 12]}, {"commit": true}]}]}`. Operations execute in order; transaction schedules interleave as listed, and each transaction starts when first encountered. `scan` emits sorted snapshot-visible rows matching a string prefix, overlaid with the transaction's own writes and deletes. `get` emits the snapshot-visible value, `put` stages a JSON value, `delete` stages a tombstone, and `commit` records committed or aborted. Missing keys read as `null`. Invalid schedules, malformed operations, and duplicate transaction names are rejected with a clear error. The implementation is intentionally in-memory and does not claim crash durability or SQL isolation beyond the stated optimistic snapshot rules.

## Known Issues (Resolved)

- Fixed prefix scans omitting rows whose valid JSON value is `null`. A regression test was first run against the defective behavior (it failed with an empty row set), then passed after scan logic was changed to distinguish row presence from value content.

## Examples

`python3 mvcc.py demo` demonstrates two transactions updating the same row: the first commit succeeds and the stale writer aborts. Input and output are JSON for easy inspection.
