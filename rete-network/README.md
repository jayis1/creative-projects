# Rete Network — Forward-Chaining Rule Inference Engine

[![CI](https://img.shields.io/badge/CI-passing-brightgreen)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Version 3.0.0](https://img.shields.io/badge/version-3.0.0-orange)](#)
[![Tests: 174](https://img.shields.io/badge/tests-174-brightgreen)](#)
[![Dependencies: Zero](https://img.shields.io/badge/dependencies-0-lightgrey)](#)

A from-scratch implementation of the classic **Rete algorithm** (Rete I) for
efficient pattern matching in forward-chaining production-rule systems.
Pure Python, zero required dependencies (YAML support is optional).

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Python API](#python-api)
  - [Multi-Condition Joins](#multi-condition-joins)
  - [Negated Conditions](#negated-conditions)
  - [Predicate Tests](#predicate-tests)
  - [Truth Maintenance](#truth-maintenance)
  - [Query API](#query-api)
  - [Tracing & Statistics](#tracing--statistics)
  - [Event Listeners](#event-listeners)
  - [Batch Operations](#batch-operations)
  - [Network Visualization](#network-visualization)
  - [JSON / YAML Rule Files](#json--yaml-rule-files)
  - [CLI](#cli)
- [Examples](#examples)
- [Architecture](#architecture)
- [Conflict Resolution Strategies](#conflict-resolution-strategies)
- [Changelog](#changelog)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## Overview

Rete (Latin for *net*) is the algorithm at the heart of production-rule
systems like CLIPS, Jess, and Drools. Instead of re-scanning all facts every
cycle, it compiles rules into a **network** of nodes that incrementally
maintains the set of matching rule instantiations as facts are asserted and
retracted.

```
Fact ─▶ Alpha net (one-input) ─▶ Join / Beta net (two-input) ─▶ Production nodes
         type + field tests       variable-binding joins          (rules → agenda)
```

- **Alpha nodes** — filter single facts by type and intra-fact tests
  (constant equality, variable binding, arbitrary predicates).
- **Join nodes** — combine partial instantiations from two parents using
  inter-fact variable-consistency checks.
- **Production nodes** — leaf nodes that collect complete instantiations for
  a rule and feed the agenda.
- **Negated conditions** — supported via negated conjunctive conditions
  (NCC): a rule fires only when *no* fact matches the negated pattern.

## Features

- **Pure Python, zero required dependencies** (PyYAML optional for YAML support)
- `Fact` working-memory elements with structural equality and unique IDs
- `Rule` definitions with ordered conditions + actions
- `Var` / `Const` pattern terms for variable binding and constant tests
- Arbitrary intra-fact predicates
- **Negated conditions** (`negated=True`) with full NCC semantics
- **Alpha-node sharing** across rules with overlapping patterns
- **Incremental assertion / retraction** — no full re-scan needed
- **6 conflict-resolution strategies**: FIFO, LIFO, Priority, Recent,
  Refraction (REFC), and Priority+Refraction (PRIORITY_REFC)
- **Infinite-loop detection** via `max_steps`
- **Truth maintenance (TMS)** — logically derived facts auto-retract when
  their supporting instantiation disappears; multiple supports tracked
- **Query API** — `query()`, `query_one()`, `fact_count()` for direct
  working-memory access
- **Rule statistics** — per-rule fire counts and activation counts
- **Firing trace** — record every firing for debugging
- **Event listeners** — observer pattern for assert/retract/fire events
- **Batch operations** — `assert_batch()`, `retract_batch()` for bulk loads
- **Network visualization** — Graphviz DOT export and JSON network summary
- **JSON serialization** — load rules and facts from JSON files; save facts
- **YAML serialization** — load rules from YAML; save facts to YAML
- **CLI** — `run`, `agenda`, `validate`, `network`, `stats`, `repl`, `version` subcommands
- **Interactive REPL** for debugging rule sets
- **Logging** via stdlib `logging` module with configurable levels
- **Comprehensive test suite** — 174 tests covering all features
- **GitHub Actions CI** — tested on Python 3.10, 3.11, 3.12

## Installation

```bash
cd rete-network

# Basic install (zero dependencies)
pip install -e .

# With YAML support
pip install -e ".[yaml]"

# With development tools (pytest + pyyaml)
pip install -e ".[dev]"
```

## Quick Start

```python
from rete import Engine, Fact, Rule, Condition, Var

eng = Engine()

# A simple greeting rule
eng.add_rule(Rule(
    name="greet",
    conditions=[Condition("person", name=Var("n"))],
    actions=[lambda b, e: print(f"Hello, {b['n']}!")],
))

eng.assert_fact(Fact("person", name="Alice"))
eng.assert_fact(Fact("person", name="Bob"))
eng.run()
# Hello, Alice!
# Hello, Bob!
```

## Usage

### Python API

```python
from rete import Engine, Fact, Rule, Condition, Var, Const

eng = Engine()
```

### Multi-Condition Joins

```python
# "If person ?x likes person ?y and ?y likes ?x, they are friends."
eng.add_rule(Rule(
    name="friends",
    conditions=[
        Condition("likes", a=Var("x"), b=Var("y")),
        Condition("likes", a=Var("y"), b=Var("x")),
    ],
    actions=[lambda b, e: e.assert_fact(Fact("friends", a=b["x"], b=b["y"]))],
))
```

### Negated Conditions

```python
# "If someone is a person and NOT banned, they can enter."
eng.add_rule(Rule(
    name="allow-entry",
    conditions=[
        Condition("person", name=Var("n")),
        Condition("banned", name=Var("n"), negated=True),
    ],
    actions=[lambda b, e: e.assert_fact(Fact("allowed", name=b["n"]))],
))
```

### Predicate Tests

```python
# Match only adults (age >= 18)
Condition("person", age=Var("a"),
          predicate=lambda fact, b: b["a"] >= 18)
```

### Truth Maintenance

```python
# Logically assert a fact supported by a rule firing
sig = ("my-rule", (some_fact,))
eng.assert_logical(Fact("derived", value=42), support=sig)

# Multiple supports: fact survives until ALL supports are retracted
eng.assert_logical(Fact("derived", value=42), support=sig2)

# If a support instantiation is retracted, the derived fact auto-retracts
# when no remaining supports exist
eng._retract_support(sig)  # fact still present (sig2 remains)
eng._retract_support(sig2) # fact auto-retracted
```

### Query API

```python
# Find all persons aged 30
matches = eng.query("person", age=30)

# Find first match
first = eng.query_one("person", name="Alice")

# Count facts
total = eng.fact_count()
persons = eng.fact_count("person")
```

### Tracing & Statistics

```python
eng.enable_tracing()
eng.run()
for entry in eng.get_trace():
    print(f"Step {entry['step']}: {entry['rule']} {entry['bindings']}")

stats = eng.get_stats()
# {"greet": {"fires": 2, "activations": 0}, ...}
```

### Event Listeners

```python
class MyListener:
    def on_assert(self, fact):
        print(f"Asserted: {fact}")
    def on_retract(self, fact):
        print(f"Retracted: {fact}")
    def on_fire(self, rule_name, bindings):
        print(f"Fired: {rule_name} with {bindings}")

eng.add_listener(MyListener())
```

### Batch Operations

```python
# Assert multiple facts at once
facts = [Fact("person", name=n) for n in ["Alice", "Bob", "Carol"]]
count = eng.assert_batch(facts)
assert count == 3

# Retract multiple facts
count = eng.retract_batch(some_facts)
```

### Network Visualization

```python
# Export as Graphviz DOT
dot_string = eng.to_dot()
# Render with: dot -Tpng network.dot -o network.png

# Get a structured summary
summary = eng.network_summary()
# {"rules": 3, "alpha_nodes": 5, "facts": 10, "strategy": "REFC", ...}
```

### JSON / YAML Rule Files

**JSON format:**

```json
{
  "rules": [
    {
      "name": "greet",
      "priority": 0,
      "conditions": [
        {"type": "person", "fields": {"name": "?n"}}
      ],
      "actions": [
        ["print", "Hello, {n}!"]
      ]
    }
  ],
  "facts": [
    {"type": "person", "fields": {"name": "Alice"}}
  ]
}
```

**YAML format** (requires `pip install pyyaml`):

```yaml
rules:
  - name: greet
    priority: 0
    conditions:
      - type: person
        fields:
          name: "?n"
    actions:
      - ["print", "Hello, {n}!"]
facts:
  - type: person
    fields:
      name: Alice
```

Field values starting with `?` are variables; everything else is a constant.
Supported action types: `print`, `assert`, `assert_logical`, `retract`, `log`.

**Loading from Python:**

```python
from rete import load_engine

# Auto-detects format from extension
eng = load_engine("examples/social.json", strategy="priority-refc")
eng.run()

# Or load YAML
eng = load_engine("examples/pricing.yaml", strategy="fifo")
eng.run()
```

### CLI

```bash
# Run a JSON/YAML rule file
python -m rete.cli run examples/social.json --trace
python -m rete.cli run examples/pricing.yaml --strategy priority-refc

# Show the agenda without firing
python -m rete.cli agenda examples/social.json

# Validate a rule file
python -m rete.cli validate examples/social.json

# Show network structure (human-readable)
python -m rete.cli network examples/social.json

# Export network as Graphviz DOT
python -m rete.cli network examples/social.json --dot > network.dot

# Get JSON network summary
python -m rete.cli network examples/social.json --summary

# Show engine statistics
python -m rete.cli stats examples/social.json

# Run with a specific strategy
python -m rete.cli run examples/social.json --strategy priority-refc

# Save final facts
python -m rete.cli run examples/social.json --save-facts output.json

# Interactive REPL
python -m rete.cli repl examples/social.json

# Print version
python -m rete.cli version
```

**CLI help:**

```bash
python -m rete.cli --help
python -m rete.cli run --help
python -m rete.cli network --help
```

## Examples

| File | Description |
|------|-------------|
| `examples/social.json` | Social network with friends detection and banned-person negation |
| `examples/ancestry.json` | Transitive ancestor computation via recursive rules |
| `examples/pricing.yaml` | Business pricing engine: VIP discounts, bulk discounts, tax by state |

**Running examples:**

```bash
# Social network example
python -m rete.cli run examples/social.json --trace
# Hello, Alice!
# Hello, Bob!
# Hello, Carol!
# Bob and Alice are friends!
# Alice and Bob are friends!
# Alice is allowed to enter.
# Bob is allowed to enter.
# Fired 7 rule(s).

# Pricing engine (YAML)
python -m rete.cli run examples/pricing.yaml --strategy priority-refc
# VIP discount applied for Alice: 20% off 500
# Bulk discount: 150 units for Bob
# California tax (8.75%) applied for Alice
# New York tax (8.875%) applied for Bob
# Fired 5 rule(s).
```

## Architecture

The engine builds a Rete network from rule definitions:

### Network Structure

```
                    ┌──────────────────────────────────────────────────────────┐
                    │                    Rete Network                            │
                    │                                                          │
  Fact ──────────── ▶  ┌─────────────┐     ┌──────────────┐     ┌────────────┐  │
  (assert/retract)    │  Alpha net  │────▶│  Join / beta │──▶ │ Production │  │
                      │  (one-input │     │  net (two-   │     │ nodes      │  │
                      │   nodes)    │     │   input)     │     │ (rules)    │  │
                      └─────────────┘     └──────────────┘     └─────┬──────┘  │
                      Type + field          Variable-binding         │         │
                      tests                 consistency checks       ▼         │
                                                                     Agenda     │
                                                                     (conflict  │
                                                                      resolution│
                                                                      → fire)   │
                    └──────────────────────────────────────────────┬───────────┘
                                                                     │
                                                                     ▼
                                                            Actions execute,
                                                            assert/retract facts
                                                            → incremental
                                                              network updates
```

1. **Alpha net**: Each condition becomes an alpha node (shared if identical
   patterns exist). Alpha nodes test fact type and field constraints.
2. **Beta net**: Join nodes chain conditions left-to-right, checking
   variable-binding consistency across conditions.
3. **Production nodes**: Leaf nodes collect complete instantiations per rule.
4. **Agenda**: The conflict set is resolved per the chosen strategy, and
   actions fire one at a time, potentially asserting/retracting facts that
   cause incremental network updates.

### Module Layout

```
rete-network/
├── rete/
│   ├── __init__.py        # Public API exports
│   ├── engine.py          # Core engine, network nodes, conflict resolution, TMS
│   ├── serialization.py   # JSON/YAML loading and saving
│   ├── cli.py             # Command-line interface (run, agenda, validate, ...)
│   └── exceptions.py      # Custom exception hierarchy
├── tests/
│   ├── test_core.py       # Basic engine, facts, conditions, rules
│   ├── test_join.py       # Multi-condition joins, variable binding
│   ├── test_negation.py   # Negated conditions (NCC)
│   ├── test_conflict.py   # Conflict resolution strategies
│   ├── test_tms.py        # Truth maintenance system
│   ├── test_query.py      # Query API
│   ├── test_serialization.py # JSON/YAML serialization
│   ├── test_cli.py        # CLI smoke tests
│   ├── test_listeners.py  # Event listener / observer
│   ├── test_visualization.py # Network visualization
│   ├── test_batch.py      # Batch operations
│   ├── test_edge_cases.py # Edge cases and error handling
│   └── test_bug_hunt.py   # Regression tests from bug hunt phase
├── examples/
│   ├── social.json        # Social network example
│   ├── ancestry.json      # Transitive ancestor computation
│   └── pricing.yaml       # Business pricing engine
├── .github/workflows/
│   └── ci.yml             # GitHub Actions CI config
├── pyproject.toml         # Build config, dependencies, pytest config
├── smoke_test.py          # Core smoke tests
├── enhanced_test.py       # Enhanced feature tests
├── CONTRIBUTING.md        # Contribution guidelines
├── LICENSE                # MIT License
└── README.md              # This file
```

### Negated Conditions (NCC)

Negated conditions are handled by negated join nodes that check *absence*
of matching facts rather than presence. When a fact matching a negated
pattern is asserted, previously-eligible instantiations are blocked; when
it's retracted, they may become eligible again. Duplicate instantiation
creation on retraction is prevented by checking for existing entries.

## Conflict Resolution Strategies

| Strategy | Description | Prevents Loops? |
|----------|-------------|:-:|
| `FIFO` | Oldest activation fires first | No |
| `LIFO` | Newest activation fires first (depth-first) | No |
| `PRIORITY` | Highest priority rule fires first, ties → FIFO | No |
| `RECENT` | Most-recently-added fact fires first | No |
| `REFC` | Refraction: never fire same instantiation twice | Yes |
| `PRIORITY_REFC` | Priority ordering + refraction (recommended) | Yes |

**Recommendation**: Use `REFC` (default) or `PRIORITY_REFC` for production
use to prevent infinite loops. Use `FIFO`/`LIFO`/`RECENT` only when you
ensure rules retract their triggering facts after firing.

## Changelog

### v3.0.0 (2026-07-15) — Comprehensive Improvement

**New Features:**
- **YAML support**: Load rules from YAML files (`load_yaml`, `load_file`); save facts to YAML (`save_facts_yaml`)
- **PRIORITY_REFC strategy**: Combined priority ordering + refraction for production use
- **Event listeners**: Observer pattern with `on_assert`, `on_retract`, `on_fire` callbacks
- **Batch operations**: `assert_batch()`, `retract_batch()` for bulk fact management
- **Network visualization**: Graphviz DOT export (`to_dot()`) and JSON summary (`network_summary()`)
- **New CLI commands**: `network` (with `--dot` and `--summary` flags), `stats`
- **`assert_logical` action type** for JSON/YAML rules
- **`Fact.to_dict()`** method for easy serialization
- **`SerializationError`** exception class

**Improvements:**
- **Logging**: Switched to stdlib `logging` module with named logger and configurable handlers
- **`Condition.key`**: Fixed to serialize terms into comparable representation (no more `TypeError` on mixed Var/Const)
- **Alpha node field matching**: Fixed `None` field check to use `in` operator instead of `is None` check
- **NCC retraction**: Added duplicate-instantiation guard in `right_retract` for negated conditions
- **`load_engine`**: Accepts string strategy names (e.g., `"fifo"`) in addition to enum values
- **`load_file`**: Auto-detects JSON vs YAML from file extension
- **CLI**: Added `query`, `network`, `rules` commands to REPL; type conversion for numeric fields
- **Type hints**: Added throughout; `EngineListener` Protocol class
- **Error handling**: Better error messages with `SerializationError` for invalid input data
- **pyproject.toml**: Added keywords, classifiers, optional dependencies, entry point

**Test Suite:**
- Expanded from 26 to **174 tests** organized into 12 test modules
- Tests cover: core engine, joins, negation, conflict resolution, TMS, query,
  serialization (JSON+YAML), CLI, listeners, visualization, batch ops, edge cases

**Infrastructure:**
- GitHub Actions CI (Python 3.10, 3.11, 3.12)
- CONTRIBUTING.md with development workflow
- LICENSE file
- Proper `pyproject.toml` with optional dependencies and pytest config

### v2.0.0 — Enhanced Features

- Truth maintenance (TMS)
- Query API (`query`, `query_one`, `fact_count`)
- Rule statistics and firing trace
- JSON serialization (`load_json`, `save_facts`, `save_state`)
- CLI with `run`, `agenda`, `validate`, `repl` subcommands
- 5 conflict-resolution strategies
- Alpha-node sharing
- Logging with configurable levels

### v1.0.0 — Initial Implementation

- Core Rete algorithm (alpha net, beta net, production nodes)
- Facts, rules, conditions, Var/Const pattern terms
- Predicate tests
- Negated conditions (NCC)
- Incremental assertion/retraction
- Refraction conflict resolution

## Known Issues (Resolved)

The following bugs were found during the bug hunt phase and have been fixed:

1. **`clear()` didn't reset refraction memory** — After calling `clear()`, rules
   could not re-fire when the same facts were re-asserted, because the `_fired`
   set retained old instantiation signatures. **Fix**: `clear()` now calls
   `reset_agenda()` to clear the refraction set.

2. **`_action_print` crashed on missing format keys** — The `str.format()` call
   raised `KeyError` when a template referenced a binding key that wasn't
   present. **Fix**: Switched to `string.Template.safe_substitute()`.

3. **`_action_assert` leaked template strings into fact values** — When a
   variable binding was missing, `bindings.get(v[1:], v)` returned the default
   value `v` (the literal string `"?x"`). **Fix**: Changed to
   `bindings.get(v[1:])` which returns `None` for missing bindings.

4. **`remove_rule` left orphaned join nodes** — Removing a rule deleted the
   production node and join-chain references, but the join nodes remained in
   alpha-node and beta-memory successor lists. **Fix**: `remove_rule` now
   iterates the join chain and removes each join node from all successor lists.

5. **`_action_log` had the same `str.format()` crash** as `_action_print`.
   **Fix**: Same `string.Template.safe_substitute()` approach.

6. **`Condition.key` could raise `TypeError`** — Sorting mixed `Var`/`Const`
   instances could fail because they aren't directly comparable. **Fix**: Key
   now serializes terms into a tuple representation `(is_var, name_or_repr)`
   that is always comparable.

7. **NCC retraction could create duplicate instantiations** — Retracting a
   negated fact could add the same instantiation multiple times. **Fix**: Added
   a duplicate check before appending to `successor.items`.

8. **Alpha node `None` field check was incorrect** — The check
   `if val is None and fname not in fact.fields` would fail for facts that
   legitimately have a field set to `None`. **Fix**: Changed to check
   `if fname not in fact.fields` first, then get the value.

## Roadmap

- **Rete II / TREAT**: More efficient join handling for large fact bases
- **Indexed alpha nodes**: Hash-indexed field lookups for faster matching
- **Rule compilation from DSL**: A human-readable rule language (not just JSON/YAML)
- **Watch patterns**: Specify which fact types a rule is interested in for
  more efficient propagation
- **Multi-engine coordination**: Run multiple engines with fact sharing
- **Web dashboard**: Real-time visualization of network state and firing
- **Persistent working memory**: Save/load full engine state including TMS
- **Distributed mode**: Shard working memory across multiple processes
- **Rule versioning and hot-swap**: Update rules without losing facts

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style,
testing guidelines, and how to submit contributions.

```bash
# Quick dev setup
cd rete-network
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# Run a specific test
python -m pytest tests/test_negation.py -v
```

## License

MIT — see [LICENSE](LICENSE) for full text.