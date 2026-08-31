# suffix-automaton

[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Tests](https://img.shields.io/badge/tests-pytest-informational.svg)](./tests)

A substring analytics toolkit built on a suffix automaton. It supports fast membership and counting queries, lexicographic substring enumeration, repeated-substring mining, complexity reports by length, minimal unique substring discovery, longest-common-substring analysis, Graphviz export, and config-driven batch workloads.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Reference](#cli-reference)
- [Config-Driven Workflows](#config-driven-workflows)
- [Architecture](#architecture)
- [Examples](#examples)
- [Recent Improvements](#recent-improvements)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## Features

- Online `O(n)` suffix automaton construction
- `O(m)` substring membership and occurrence queries
- Distinct substring counting and k-th lexicographic substring lookup
- Longest repeated substring and ranked repeated-substring reports
- Distinct substring complexity by length
- Minimal unique substring (MUS) extraction for positions that can be uniquely identified in-text
- Generalized longest common substring across multiple strings
- Pairwise LCS reporting
- JSON serialization and restoration
- Graphviz DOT export
- JSON/TOML config-driven batch execution
- Structured logging and output-file support

## Installation

### Local development

```bash
cd suffix-automaton
python3 -m venv .venv
. .venv/bin/activate
pip install -e . pytest
```

### Install as a CLI tool

```bash
pip install .
suffix-automaton --help
```

## Quick Start

### Rich analysis report

```bash
python3 -m suffix_automaton analyze --text banana --json
```

Excerpt:

```json
{
  "text_length": 6,
  "state_count": 10,
  "distinct_substrings": 15,
  "longest_repeated_substring": "ana",
  "longest_repeated_count": 2,
  "alphabet": ["a", "b", "n"],
  "substring_complexity_by_length": {
    "1": 3,
    "2": 3,
    "3": 3,
    "4": 3,
    "5": 2,
    "6": 1
  }
}
```

### Minimal unique substrings

```bash
python3 -m suffix_automaton mus --text banana --json
```

Excerpt:

```json
[
  {"start": 0, "end": 1, "substring": "b"},
  {"start": 1, "end": 5, "substring": "anan"},
  {"start": 2, "end": 5, "substring": "nan"}
]
```

### Complexity by length

```bash
python3 -m suffix_automaton complexity --text mississippi --json
```

### Repeated substrings

```bash
python3 -m suffix_automaton repeats --text mississippi --limit 5 --min-length 2 --json
```

### Longest common substring

```bash
python3 -m suffix_automaton lcs abracadabra cadabrac dabracad --pairwise
```

## CLI Reference

```text
analyze     Rich aggregate report including complexity and MUS output
contains    Membership query for one substring
count       Exact occurrence count
locate      Overlapping match locations
export      Serialize the automaton to JSON
dot         Export Graphviz DOT
kth         k-th lexicographic distinct substring
absent      Shortest absent substring over a chosen alphabet
repeats     Ranked repeated substrings
complexity  Distinct substring counts by length
mus         Minimal unique substrings by start position
lcs         Longest common substring across multiple strings
run-config  Run a JSON/TOML batch workload
```

Logging is available on every command:

```bash
python3 -m suffix_automaton --log-level INFO analyze --text banana --json
python3 -m suffix_automaton --log-level DEBUG --log-file suffix.log run-config examples/report-config.json
```

## Config-Driven Workflows

Two sample configs live in [`examples/`](./examples):

- [`report-config.json`](./examples/report-config.json)
- [`report-config.toml`](./examples/report-config.toml)

Run either one:

```bash
python3 -m suffix_automaton run-config examples/report-config.json
python3 -m suffix_automaton run-config examples/report-config.toml
```

A job can define:

- `command`
- `text` or `file`
- `substring`
- `k`
- `alphabet`
- `limit`
- `min_length`
- `pairwise`
- `json`
- `output`

## Architecture

```text
suffix_automaton/
├── __init__.py
├── __main__.py
├── cli.py        # argparse interface, logging, output routing
├── commands.py   # command execution and payload rendering
├── config.py     # JSON/TOML config loading and validation
└── core.py       # suffix automaton algorithms and analytics
```

Core design points:

1. `core.py` owns the online automaton, serialization, LCS helpers, and analytics primitives.
2. `commands.py` keeps CLI concerns separate from algorithm code by producing structured payloads.
3. `config.py` validates batch workload documents before execution.
4. Rich reports are assembled from reusable primitives, which keeps tests focused and extensions cheap.

## Examples

ASCII view of the kind of insights the tool surfaces:

```text
banana
├── longest repeated: ana (2)
├── shortest absent over {a,b,n}: aa
├── MUS at 0: b
└── complexity by length: 1→3, 2→3, 3→3, 4→3, 5→2, 6→1
```

More usage notes live in [`examples/README.md`](./examples/README.md).

## Recent Improvements

- Added minimal unique substring extraction for positions that can be uniquely identified in-text.
- Added substring complexity histograms by length.
- Added JSON/TOML config-driven batch execution.
- Split command orchestration and config parsing into separate modules.
- Added structured logging, output-file support in batch jobs, and stronger CLI error handling.
- Optimized repeated-substring reporting to walk the automaton DAG directly instead of repeatedly resolving ranked substrings.
- Expanded packaging metadata, examples, contributor guidance, and tests.

## Known Issues (Resolved)

- Fixed incremental-build correctness: `extend()` now updates the tracked source text and recomputes occurrence counts from terminal states, so online appends stay query-safe.
- Fixed Graphviz export for control characters: transition labels now escape newlines and other non-printable characters instead of emitting raw DOT-breaking bytes.
- Fixed deserialization validation: `from_dict()` now requires `is_clone` to be an actual boolean and reconstructs terminal-state metadata for safe post-load extensions.

## Roadmap

- Add approximate matching metrics for edit-distance-adjacent exploration.
- Add binary/text corpus adapters for multi-document indexing.
- Add optional visualization assets generated from real automata.
- Add performance benchmarks for larger corpora.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

MIT. See [LICENSE](./LICENSE).
