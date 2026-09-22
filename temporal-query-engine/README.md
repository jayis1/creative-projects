# Temporal Query Engine

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A dependency-free interval index for event timelines. It combines Allen's 13 interval relations with a treap-backed augmented interval tree, giving fast overlap queries while preserving deterministic output ordering.

## Contents

- [Features](#features)
- [Installation](#installation)
- [CLI usage](#cli-usage)
- [Python API](#python-api)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Testing](#testing)
- [Limitations and roadmap](#limitations-and-roadmap)
- [Contributing and license](#contributing-and-license)
- [Changelog](#changelog)

## Features

- Half-open intervals with strict validation (`start < end`, finite endpoints).
- All 13 Allen relations: before, meets, overlaps, starts, during, finishes, and inverses.
- Treap-backed interval index with subtree maximum-end pruning.
- Deterministic ordering by start, end, then event ID.
- Duplicate-ID detection, deletion, exact label filtering, and JSON/TOML input files.
- Standard-library-only runtime; Python 3.11 or newer.

## Installation

From this directory, install an editable copy:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e .
```

Or run directly from the repository without installation:

```bash
PYTHONPATH=. python3 -m temporal_query.cli --help
```

## CLI usage

Inline events use `ID:START:END[:LABEL]`:

```bash
python3 -m temporal_query.cli 2 6 \
  --event deploy:0:3:release \
  --event outage:4:8:incident
# [{"end": 3.0, "id": "deploy", "label": "release", "start": 0.0}, {"end": 8.0, "id": "outage", "label": "incident", "start": 4.0}]
```

Load a reusable event collection and filter it:

```bash
python3 -m temporal_query.cli 0 10 --events-file examples/events.json --label incident
```

Use `--verbose` for diagnostic logging. Invalid ranges, duplicate IDs, malformed files, and missing files produce a non-zero exit code and an actionable message.

## Python API

```python
from temporal_query import Event, IntervalIndex, Relation, load_events

index = IntervalIndex([
    Event("deploy", 0, 3, "release"),
    Event("outage", 4, 8, "incident"),
])
print([event.id for event in index.overlaps(2, 5)])
assert Event("a", 0, 2).relation_to(Event("b", 2, 4)) is Relation.MEETS
events = load_events("examples/events.json")
```

`IntervalIndex.related(event, relation)` returns indexed events matching a chosen Allen relation. `remove(id)` returns the deleted event and raises `KeyError` when absent.

## Configuration

JSON and TOML files contain an `events` array. Each item requires `id`, `start`, and `end`; `label` is optional.

```json
{"events": [{"id": "deploy", "start": 0, "end": 3, "label": "release"}]}
```

TOML uses repeated tables:

```toml
[[events]]
id = "deploy"
start = 0
end = 3
label = "release"
```

## Architecture

- `temporal_query/model.py` contains the immutable `Event` value object and relation classifier.
- `temporal_query/index.py` contains the randomized-priority treap. Each node stores `max_end`, so subtrees that cannot overlap a query are skipped.
- `temporal_query/config.py` isolates JSON/TOML parsing and converts validated mappings into events.
- `temporal_query/cli.py` owns argument parsing, logging, error presentation, and JSON output.

Insertion and deletion are expected O(log n). An overlap query is O(log n + k) on average, where `k` is the number of returned intervals. Results are sorted after traversal for reproducible output.

## Testing

```bash
python3 -m unittest discover -s tests -t . -v
python3 -m pytest -q                 # optional convenience runner
python3 -m temporal_query.cli --help
```

The suite covers relation classification, ordering, duplicate IDs, invalid and non-finite values, deletion, configuration loading, and actionable configuration failures.

## Limitations and roadmap

Current limitations: the index is in-memory, event IDs are strings, and the CLI returns JSON rather than streaming large result sets.

Roadmap:

1. Add a streaming JSON Lines input mode.
2. Add optional persistence for larger timelines.
3. Add benchmark fixtures comparing treap and sorted-list indexes.
4. Add richer predicates while keeping label equality backwards compatible.

## Contributing and license

See [CONTRIBUTING.md](CONTRIBUTING.md) for the focused test and documentation workflow. The project is released under the [MIT License](LICENSE), copyright jayis1.

## Changelog

### 0.2.0

- Added JSON/TOML event configuration loading.
- Added `--events-file`, `--verbose`, and installable `temporal-query` CLI entry point.
- Added packaging metadata, examples, focused configuration tests, and expanded documentation.
- Preserved the existing dependency-free API and interval semantics.

### 0.1.0

- Added indexed overlap queries, label filtering, deletion, and Allen relation classification.
