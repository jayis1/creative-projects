# Rete Network — Forward-Chaining Rule Inference Engine

A from-scratch implementation of the classic **Rete algorithm** (Rete I) for
efficient pattern matching in forward-chaining production-rule systems.

## Overview

Rete (Latin for *net*) is the algorithm at the heart of production-rule
systems like CLIPS, Jess, and Drools.  Instead of re-scanning all facts every
cycle, it compiles rules into a **network** of nodes that incrementally
maintains the set of matching rule instantiations as facts are asserted and
retracted.

### Network structure

```
Fact ─▶ Alpha net (one-input) ─▶ Join / Beta net (two-input) ─▶ Production nodes
         type + field tests       variable-binding joins          (rules → agenda)
```

* **Alpha nodes** — filter single facts by type and intra-fact tests
  (constant equality, variable binding, arbitrary predicates).
* **Join nodes** — combine partial instantiations from two parents using
  inter-fact variable-consistency checks.
* **Production nodes** — leaf nodes that collect complete instantiations for
  a rule and feed the agenda.
* **Negated conditions** — supported via negated conjunctive conditions
  (NCC): a rule fires only when *no* fact matches the negated pattern.

## Features

- Pure Python, zero dependencies
- `Fact` working-memory elements with structural equality
- `Rule` definitions with ordered conditions + actions
- `Var` / `Const` pattern terms for variable binding and constant tests
- Arbitrary intra-fact predicates
- **Negated conditions** (`negated=True`) with full NCC semantics
- **Alpha-node sharing** across rules with overlapping patterns
- **Incremental assertion / retraction** — no full re-scan needed
- **5 conflict-resolution strategies**: FIFO, LIFO, Priority, Recent, Refraction
- **Infinite-loop detection** via `max_steps`
- **Truth maintenance (TMS)** — logically derived facts auto-retract when
  their supporting instantiation disappears
- **Query API** — `query()`, `query_one()`, `fact_count()` for direct
  working-memory access
- **Rule statistics** — per-rule fire counts and activation counts
- **Firing trace** — record every firing for debugging
- **JSON serialization** — load rules and facts from JSON files; save facts
- **CLI** — `run`, `agenda`, `validate`, `repl` subcommands
- **Logging** with configurable log levels
- **Interactive REPL** for debugging rule sets

## Usage

### Python API

```python
from rete import Engine, Fact, Rule, Condition, Var, Const

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

### Multi-condition join

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

### Negated condition

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

### Predicate tests

```python
Condition("person", age=Var("a"),
          predicate=lambda fact, b: b["a"] >= 18)
```

### Truth maintenance

```python
# Logically assert a fact supported by a rule firing
sig = ("my-rule", (some_fact,))
eng.assert_logical(Fact("derived", value=42), support=sig)
# If the supporting fact is retracted, the derived fact auto-retracts too
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

### Tracing & statistics

```python
eng.enable_tracing()
eng.run()
for entry in eng.get_trace():
    print(f"Step {entry['step']}: {entry['rule']} {entry['bindings']}")

stats = eng.get_stats()
# {"greet": {"fires": 2, "activations": 0}, ...}
```

### JSON rule files

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

Field values starting with `?` are variables; everything else is a constant.
Supported action types in JSON: `print`, `assert`, `retract`, `log`.

### CLI

```bash
# Run a JSON rule file
python -m rete.cli run examples/social.json --trace

# Show agenda without firing
python -m rete.cli agenda examples/social.json

# Validate a rule file
python -m rete.cli validate examples/social.json

# Interactive REPL
python -m rete.cli repl examples/social.json

# Run with a specific strategy
python -m rete.cli run examples/social.json --strategy priority

# Save final facts
python -m rete.cli run examples/social.json --save-facts output.json
```

### Loading from Python

```python
from rete import load_engine

eng = load_engine("examples/social.json", strategy="refc")
eng.run()
```

## Examples

- `examples/social.json` — social network with friends detection and banned-person negation
- `examples/ancestry.json` — transitive ancestor computation via recursive rules

## Known Issues (Resolved)

The following bugs were found during the bug hunt phase and have been fixed:

1. **`clear()` didn't reset refraction memory** — After calling `clear()`, rules
   could not re-fire when the same facts were re-asserted, because the `_fired`
   set retained old instantiation signatures. **Fix**: `clear()` now calls
   `reset_agenda()` to clear the refraction set.

2. **`_action_print` crashed on missing format keys** — The `str.format()` call
   raised `KeyError` when a template referenced a binding key that wasn't
   present (e.g., a partial match). **Fix**: Switched to
   `string.Template.safe_substitute()`, which leaves missing keys as-is
   instead of crashing.

3. **`_action_assert` leaked template strings into fact values** — When a
   variable binding was missing, `bindings.get(v[1:], v)` returned the default
   value `v` (the literal string `"?x"`), so facts ended up with `"?x"` as a
   field value. **Fix**: Changed to `bindings.get(v[1:])` which returns `None`
   for missing bindings.

4. **`remove_rule` left orphaned join nodes** — Removing a rule deleted the
   production node and join-chain references, but the join nodes remained in
   alpha-node and beta-memory successor lists, causing potential errors and
   memory leaks. **Fix**: `remove_rule` now iterates the join chain and removes
   each join node from all successor lists.

5. **`_action_log` had the same `str.format()` crash** as `_action_print`.
   **Fix**: Same `string.Template.safe_substitute()` approach.

## Installation

```bash
cd rete-network
pip install -e .
```

## Architecture

The engine builds a Rete network from rule definitions:

1. **Alpha net**: Each condition becomes an alpha node (shared if identical
   patterns exist). Alpha nodes test fact type and field constraints.
2. **Beta net**: Join nodes chain conditions left-to-right, checking
   variable-binding consistency across conditions.
3. **Production nodes**: Leaf nodes collect complete instantiations per rule.
4. **Agenda**: The conflict set is resolved per the chosen strategy, and
   actions fire one at a time, potentially asserting/retracting facts that
   cause incremental network updates.

Negated conditions (NCC) are handled by negated join nodes that check *absence*
of matching facts rather than presence. When a fact matching a negated pattern
is asserted, previously-eligible instantiations are blocked; when it's
retracted, they may become eligible again.

## License

MIT