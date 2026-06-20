# datalog-engine

[![CI](https://github.com/jayis1/creative-projects/actions/workflows/datalog-engine-ci.yml/badge.svg)](https://github.com/jayis1/creative-projects/actions/workflows/datalog-engine-ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests: 102](https://img.shields.io/badge/tests-102%20passing-brightgreen.svg)](#tests)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-zero-blue.svg)](#installation)

A from-scratch Datalog deductive database engine implementing bottom-up
evaluation with the **semi-naive** delta strategy, **stratified negation**,
hash-indexed joins, **arithmetic/string/type-check built-ins**,
**aggregation** (count/sum/min/max/avg), fact/rule retraction, JSON state
export/import, **configuration files** (JSON/TOML/YAML), multiple
**output formats** (binding/table/JSON/CSV), and an introspection API.

Datalog is a declarative logic programming language — a subset of Prolog
without function symbols — widely used for program analysis, database
queries, and rule-based reasoning. This engine parses a Datalog program
(facts + rules), evaluates rules to a least fixpoint, and answers
queries against the derived facts.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Syntax](#syntax)
- [Built-in Predicates](#built-in-predicates)
- [Usage](#usage)
  - [As a Library](#as-a-library)
  - [Command-Line](#command-line)
  - [Configuration Files](#configuration-files)
  - [REPL](#repl)
  - [Output Formats](#output-formats)
- [Architecture](#architecture)
- [Examples](#examples)
- [Testing](#testing)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Changelog](#changelog)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **Semi-naive bottom-up evaluation** — delta relations avoid re-deriving
  known facts, achieving efficient fixpoint computation for recursive rules.
- **Stratified negation** — supports `not` in rule bodies with automatic
  stratification via iterative SCC analysis (Tarjan's algorithm). Detects
  and rejects non-stratifiable programs.
- **Hash-indexed joins** — builds hash indexes on join columns for O(1)
  lookup during body evaluation.
- **Comparison built-ins** — `<`, `>`, `<=`, `>=`, `!=`, `==` in infix
  (`X > 3`) or prefix (`>(X, 3)`) form.
- **Arithmetic built-ins** — `add`, `sub`, `mul`, `div`, `idiv`, `mod` —
  the third argument is bound to the result.
- **String built-ins** — `concat(X, Y, Z)`, `substr(X, S, Z)`,
  `strlen(X, _, Z)` — for string manipulation in rules.
- **Type-check built-ins** — `is_int`, `is_float`, `is_str`, `is_bool` —
  for type-safe reasoning over heterogeneous data.
- **Aggregation** — `count`, `sum`, `min`, `max`, `avg` — group bindings
  and compute aggregate values per group.
- **Safety checking** — enforces the Datalog safety condition (every
  variable in the head or in negated literals must appear in a positive
  body literal; binding builtins' inputs must be bound).
- **Fact & rule retraction** — remove individual facts or rules with
  automatic re-evaluation on next query.
- **JSON export/import** — serialize EDB facts + rules to JSON for
  persistence and reloading.
- **Configuration files** — load engine settings from JSON, TOML, or YAML
  files.
- **Multiple output formats** — binding (Prolog-style), table (aligned
  ASCII), JSON, and CSV.
- **Introspection API** — `explain()` shows stratum, rules, and extension
  size for any predicate; `stats()` returns engine statistics; `rules()`
  lists loaded rules; `facts()` shows base facts.
- **Interactive REPL** — load facts/rules, issue queries, run meta-commands
  (`:preds`, `:explain`, `:rules`, `:export`, `:import`, `:stats`, `:reset`).
- **Logging** — configurable log levels (DEBUG/INFO/WARNING/ERROR) via
  CLI flag or config file.
- **Max iteration limit** — safety guard against non-terminating programs.
- **Hand-written tokenizer + recursive-descent parser** — no external
  parser dependencies.
- **Zero runtime dependencies** — pure Python standard library only
  (PyYAML optional for YAML config support).

## Installation

### From source (no build step needed)

```bash
cd datalog-engine
python3 -m datalog.cli --help
```

### Install as a package

```bash
cd datalog-engine
pip install -e ".[dev]"   # editable install with dev dependencies
# or:
pip install -e .           # editable install, no extras
```

This installs a `datalog` command-line entry point:

```bash
datalog examples/graph.dl -q "path(a, Y)"
```

### Requirements

- Python 3.11+ (uses `tomllib` for TOML config support)
- No runtime dependencies (PyYAML optional for YAML config files)
- For development: `pytest` and `pytest-cov`

## Quick Start

```python
from datalog import Engine

e = Engine()
e.add_source("""
    edge(a, b). edge(b, c). edge(c, d).
    path(X, Y) :- edge(X, Y).
    path(X, Y) :- edge(X, Z), path(Z, Y).
""")

# Query for all nodes reachable from 'a'
for r in e.query("path(a, X)"):
    print(r)  # {'X': 'b'}, {'X': 'c'}, {'X': 'd'}
```

## Syntax

```
% Comments start with % (line) or /* ... */ (block)

% Facts: predicate with constant arguments, ending with .
parent(tom, bob).
parent(tom, liz).

% Rules: head :- body. (body is comma-separated literals)
ancestor(X, Y) :- parent(X, Y).
ancestor(X, Y) :- parent(X, Z), ancestor(Z, Y).

% Negation (must be stratified)
childless(X) :- person(X), not parent(X, Y).

% Comparison built-ins (infix or prefix)
adult(X) :- age(X, A), A >= 18.
adult(X) :- age(X, A), >=(A, 18).

% Arithmetic built-ins (3-arg: inputs + output variable)
doubled(X, Y) :- num(X), mul(X, 2, Y).

% String built-ins
greeting(X, Y) :- name(X), concat(X, "!", Y).

% Type-check built-ins
intval(X) :- val(X), is_int(X).

% Aggregation (2-arg: input variable + output variable)
dept_count(Dept, N) :- employee(Name, Dept, Sal), count(Name, N).

% Queries: ?- atom.  (trailing . optional in CLI/REPL)
?- ancestor(tom, X).
```

**Naming conventions:**
- Variables: start with uppercase letter or underscore (`X`, `Person`, `_`)
- Constants: lowercase identifiers (`tom`), strings (`"hello"`), numbers
  (`42`, `3.14`), booleans (`true`, `false`)
- Predicates: lowercase identifiers (`parent`, `ancestor`)
- Anonymous variables: `_` (each occurrence is independent)

## Built-in Predicates

### Comparison (check-only, infix or prefix)

| Predicate | Description |
|-----------|-------------|
| `X < Y`   | True if X < Y |
| `X > Y`   | True if X > Y |
| `X <= Y`  | True if X ≤ Y |
| `X >= Y`  | True if X ≥ Y |
| `X != Y`  | True if X ≠ Y |
| `X == Y`  | True if X = Y |

### Arithmetic (binding, 3-arg: inputs + output)

| Predicate | Description |
|-----------|-------------|
| `add(X, Y, Z)` | Z = X + Y |
| `sub(X, Y, Z)` | Z = X − Y |
| `mul(X, Y, Z)` | Z = X × Y |
| `div(X, Y, Z)` | Z = X / Y (float) |
| `idiv(X, Y, Z)`| Z = X // Y (integer) |
| `mod(X, Y, Z)` | Z = X % Y |

### String (binding, 3-arg)

| Predicate | Description |
|-----------|-------------|
| `concat(X, Y, Z)` | Z = str(X) + str(Y) |
| `substr(X, S, Z)` | Z = str(X)[S:] |
| `strlen(X, _, Z)` | Z = len(str(X)) |

### Type-check (check-only, unary)

| Predicate | Description |
|-----------|-------------|
| `is_int(X)`    | True if X is an integer |
| `is_float(X)`  | True if X is a float |
| `is_str(X)`    | True if X is a string |
| `is_bool(X)`   | True if X is a boolean |

### Aggregation (binding, 2-arg: input + output)

| Predicate | Description |
|-----------|-------------|
| `count(X, N)` | N = number of X values in group |
| `sum(X, N)`   | N = sum of X values in group |
| `min(X, N)`   | N = minimum X value in group |
| `max(X, N)`   | N = maximum X value in group |
| `avg(X, N)`   | N = average of X values in group |

## Usage

### As a Library

```python
from datalog import Engine

e = Engine()
e.add_source("""
    edge(a, b). edge(b, c). edge(c, d).
    path(X, Y) :- edge(X, Y).
    path(X, Y) :- edge(X, Z), path(Z, Y).
""")

# Query for all nodes reachable from 'a'
results = e.query("path(a, X)")
for r in results:
    print(r)  # {'X': 'b'}, {'X': 'c'}, {'X': 'd'}

# Get the full extension of a predicate
print(e.relation("path"))

# Add facts programmatically
e.add_fact("edge", "d", "e")

# Retract a fact
e.retract_fact("edge", "d", "e")

# Explain a predicate
print(e.explain("path"))

# Get engine statistics
print(e.stats())

# JSON export/import
json_state = e.to_json()
e2 = Engine()
e2.from_json(json_state)
print(e2.query("path(a, X)"))

# Load from a file
e3 = Engine()
e3.load_file("examples/family.dl")
print(e3.query("ancestor(tom, X)"))
```

### Command-Line

```bash
# Load a file and run a query
python3 -m datalog.cli examples/family.dl -q "ancestor(tom, X)"

# Run multiple queries
python3 -m datalog.cli examples/company.dl -q "well_paid(X)" -q "underpaid(X)"

# Output in table format
python3 -m datalog.cli examples/graph.dl --format table -q "path(a, Y)"

# Output as JSON
python3 -m datalog.cli examples/graph.dl --format json -q "path(a, Y)"

# Show a relation
python3 -m datalog.cli examples/graph.dl --show path

# Explain a predicate
python3 -m datalog.cli examples/family.dl --explain ancestor

# Export state to JSON
python3 -m datalog.cli examples/graph.dl --export state.json

# Import JSON state and query
python3 -m datalog.cli --import state.json -q "path(a, X)"

# Show engine statistics
python3 -m datalog.cli examples/graph.dl -q "path(a,Y)" --stats

# Enable debug logging
python3 -m datalog.cli examples/graph.dl -q "path(a,Y)" --log-level DEBUG

# Interactive REPL
python3 -m datalog.cli examples/family.dl --repl

# Read from stdin
cat facts.dl | python3 -m datalog.cli -
```

### Configuration Files

The engine supports loading configuration from JSON, TOML, or YAML files:

```bash
python3 -m datalog.cli --config examples/datalog.toml
python3 -m datalog.cli --config examples/datalog.json
```

Example TOML config (`datalog.toml`):

```toml
files = ["examples/company.dl"]
queries = ["well_paid(X)", "worker(X)"]
log_level = "INFO"
output_format = "table"
max_iterations = 10000
```

Example JSON config (`datalog.json`):

```json
{
    "files": ["examples/company.dl"],
    "queries": ["well_paid(X)"],
    "log_level": "WARNING",
    "output_format": "table",
    "max_iterations": 10000
}
```

### REPL

```
$ python3 -m datalog.cli --repl
datalog-engine REPL. Type :help for commands, :quit to exit.
dl> edge(a, b). edge(b, c).
dl> path(X, Y) :- edge(X, Y).
dl> path(X, Y) :- edge(X, Z), path(Z, Y).
dl> ?- path(a, X)
X = 'b'
X = 'c'
(2 answers)
dl> :preds
  edge/2
  path/2
dl> :explain path
Predicate: path/2
  Type: IDB (derived)
  Stratum: 1
  Rules:
    path(X, Y) :- edge(X, Y).
    path(X, Y) :- edge(X, Z), path(Z, Y).
  Extension: 3 tuple(s)
dl> :stats
  predicates: 2
  rules: 2
  total_facts: 2
  total_derived: 3
  iterations: 2
dl> :export my_state.json
Exported to my_state.json
dl> :quit
```

### Output Formats

The CLI supports four output formats via `--format`:

**binding** (default) — Prolog-style:
```
X = 'b'
X = 'c'
(2 answers)
```

**table** — aligned ASCII table:
```
+-------+
| X     |
+-------+
| 'b'   |
| 'c'   |
+-------+
(2 rows)
```

**json** — JSON array:
```json
[
  {"X": "b"},
  {"X": "c"}
]
```

**csv** — comma-separated values:
```
X
b
c
```

## Architecture

The engine is organized into focused modules, each with a single
responsibility:

```
datalog/
├── __init__.py        # Public API exports
├── __main__.py        # CLI entry point (python -m datalog)
├── ast.py             # AST nodes (Term, Variable, Constant, Atom, Literal, Rule, Fact, Query, Program)
├── parser.py          # Lexer + recursive-descent parser
├── builtins.py        # Built-in predicate registry + evaluators
├── relation.py        # Relation storage with hash indexing
├── stratification.py  # SCC computation (iterative Tarjan) + stratification
├── evaluation.py      # Body evaluation (joins, built-in dispatch, delta support)
├── aggregation.py     # Aggregate rule evaluation (count/sum/min/max/avg)
├── engine.py          # Engine class — coordinates all modules
├── config.py          # Configuration file loading (JSON/TOML/YAML)
├── output.py          # Output formatting (binding/table/json/csv)
├── errors.py          # Exception hierarchy
└── cli.py             # Command-line interface + REPL
```

### How It Works

#### 1. Parsing

The lexer (`parser.py`) tokenizes the source into identifiers, variables,
strings, numbers, operators, and punctuation. The recursive-descent parser
produces an AST of `Fact`, `Rule`, and `Query` nodes. Safety is checked at
parse time. Comparison operators are recognized both in infix (`X > 3`)
and prefix (`>(X, 3)`) form.

#### 2. Stratification

Before evaluation, the engine builds a predicate dependency graph with
positive and negative edges (`stratification.py`). It computes
strongly-connected components (SCCs) using an **iterative** Tarjan's
algorithm (avoids Python recursion limits). If a negative edge lies
within an SCC, the program is rejected as non-stratifiable. SCCs are
then topologically sorted into strata via Kahn's algorithm with
longest-path level tracking.

#### 3. Semi-naive Evaluation

Strata are evaluated bottom-up in order (`engine.py`). Within each
stratum:

1. **Naive bootstrap**: evaluate all rules once against current relations
   to produce initial facts.
2. **Semi-naive iteration**: in each round, for every rule, evaluate the
   body with at least one positive body literal restricted to the *delta*
   (newly added tuples) of that predicate. New tuples are collected into
   new deltas. Repeat until no new tuples are derived.

This avoids re-deriving existing facts: only combinations involving at
least one new tuple are considered.

#### 4. Joins

Body literals are evaluated left-to-right (`evaluation.py`). For each
literal, the engine identifies which variables are already bound (from
earlier literals), builds a hash index on those positions in the
relation, and looks up matching tuples. Unification extends the binding
with newly-bound variables.

#### 5. Negation

Negated literals are evaluated only in higher strata (after the negated
predicate is fully derived). A negated literal `not p(X)` succeeds for a
binding if no tuple in `p` matches under that binding. Safety ensures all
variables in negated literals are already bound.

#### 6. Built-in Predicates

Built-in predicates (`builtins.py`) are dispatched during body evaluation:

- **Comparison** built-ins check values but don't bind variables.
- **Arithmetic/string** built-ins bind their output argument. If the
  output is already bound, they act as a check.
- **Type-check** built-ins test the Python type of a value.
- Division by zero and invalid operations fail gracefully (no bindings).

#### 7. Aggregation

Aggregate rules (`aggregation.py`) are identified and separated from
regular rules during evaluation. After all regular rules in a stratum
reach fixpoint, aggregate rules are evaluated: the non-aggregate body
literals produce bindings, which are grouped by the head's non-aggregate
variables, and the aggregate function is applied to each group.

## Examples

| File | Description |
|------|-------------|
| `examples/family.dl` | Family relationships: transitive ancestry, siblings (using `!=`), aunt/uncle |
| `examples/graph.dl` | Graph algorithms: transitive closure, cycle detection, source/sink, connected components |
| `examples/company.dl` | Company database with arithmetic (salary doubling), negation (worker vs. manager), management hierarchy |
| `examples/aggregation.dl` | Aggregation: count/sum/min/max/avg per department |
| `examples/strings.dl` | String built-ins (concat, strlen) and type checks (is_int, is_str) |
| `examples/demo.py` | Interactive demo showcasing all features |
| `examples/datalog.json` | Example JSON configuration file |
| `examples/datalog.toml` | Example TOML configuration file |

### Demo

```bash
python3 examples/demo.py
```

This runs a comprehensive demo of all features: transitive closure,
negation, arithmetic, string builtins, type checks, aggregation, JSON
I/O, introspection, and all output formats.

## Testing

The project has a comprehensive pytest test suite with 102 tests:

```bash
# Run the full test suite
pytest tests/ -v

# With coverage
pytest tests/ --cov=datalog --cov-report=term-missing

# Run legacy test scripts
python3 test_smoke.py
python3 test_enhanced.py
python3 test_bug_hunt.py
```

Test categories:
- **Parser tests** — facts, rules, queries, negation, comparisons, strings, comments, errors
- **AST tests** — constant equality/hashing, atom groundness, rule safety
- **Engine basic tests** — transitive closure, queries, facts, retraction, clear
- **Negation tests** — stratified negation, non-stratifiable detection, negated comparisons
- **Built-in tests** — all comparisons, arithmetic, string, type-check builtins
- **Aggregation tests** — count, sum, min, max, aggregate rule detection
- **JSON I/O tests** — export/import roundtrip, invalid input handling
- **Safety tests** — unsafe rule rejection, safe arith rules
- **Introspection tests** — explain, stats, rules listing, facts
- **Config tests** — JSON/TOML loading, invalid formats, nonexistent files
- **Output tests** — binding, table, json, csv formats
- **Edge case tests** — EDB+IDB same predicate, mutual recursion, cycle detection, max iterations

## Known Issues (Resolved)

The following bugs were found during the Phase 3 bug hunt and have been
fixed:

1. **EDB + IDB same predicate lost base facts** — When a predicate had
   both base facts (EDB) and rules (IDB), querying it only returned the
   derived (IDB) tuples, silently dropping the base facts. **Fix:** The
   evaluation now seeds IDB relations with a copy of EDB facts before
   rule evaluation, so the final relation is the union of base + derived.

2. **Safety check treated built-in comparison variables as bound** — A
   rule like `foo(X) :- X > 5.` was incorrectly accepted as safe.
   **Fix:** `is_safe()` excludes check-only builtins from the binding set.

3. **Arithmetic builtin output variables incorrectly rejected as unsafe**
   — After fixing bug #2, rules like `foo(X, Y) :- num(X), add(X, 5, Y)`
   were rejected. **Fix:** `is_safe()` iteratively adds variables bound
   by binding builtins (arithmetic, string, aggregate) whose inputs are
   already bound.

4. **`from_json` gave unclear errors on malformed input** — Invalid JSON
   or missing keys raised `JSONDecodeError` or `KeyError`. **Fix:**
   `from_json()` wraps errors with descriptive `DatalogError` messages.

5. **Ground atom evaluation silently dropped non-Constant terms** —
   **Fix:** Since `is_ground()` already confirms all terms are Constants,
   the tuple is built directly from `atom.terms`.

6. **`_load_program` fact loading used filtering instead of validation**
   — **Fix:** Now validates that all terms are Constants and raises
   `DatalogError` if not.

7. **JSON export sorting used Constant objects instead of values** —
   **Fix:** Now sorts by `str(c.value)` for deterministic ordering.

## Changelog

### v2.0.0 (2026-06-20) — Comprehensive Improvement

**New Features:**
- **Aggregation support** — `count`, `sum`, `min`, `max`, `avg` builtins
  with grouped evaluation
- **String builtins** — `concat`, `substr`, `strlen`
- **Type-check builtins** — `is_int`, `is_float`, `is_str`, `is_bool`
- **Configuration files** — JSON, TOML, and YAML config file support
- **Multiple output formats** — binding, table, JSON, CSV
- **Engine statistics** — `stats()` API for introspection
- **Max iteration limit** — safety guard against non-termination
- **Logging** — configurable log levels (DEBUG/INFO/WARNING/ERROR)
- **`load_file()` method** — load Datalog source from a file path
- **REPL `:import` and `:stats` commands**

**Architecture Improvements:**
- Split monolithic `engine.py` into focused modules:
  - `builtins.py` — built-in predicate registry and evaluators
  - `relation.py` — relation storage with hash indexing
  - `stratification.py` — SCC computation and stratification
  - `evaluation.py` — body evaluation with join dispatch
  - `aggregation.py` — aggregate rule evaluation
  - `config.py` — configuration file loading
  - `output.py` — output formatting
  - `errors.py` — exception hierarchy
  - `engine_types.py` — shared type aliases
- **Iterative Tarjan's SCC** — avoids Python recursion limit on large
  dependency graphs
- **Type hints** throughout all modules
- **Docstrings** on all classes and public methods
- **Proper exception hierarchy** — `DatalogError` base with specific
  subclasses (`SafetyError`, `StratificationError`, `ConfigurationError`)

**Testing:**
- Comprehensive pytest test suite (102 tests) covering all features
- Legacy test scripts preserved and passing (54 tests)
- GitHub Actions CI workflow for Python 3.11/3.12/3.13

**Packaging:**
- `pyproject.toml` with `setuptools` build backend
- Installable via `pip install -e .`
- `datalog` CLI entry point

**Documentation:**
- Dramatically improved README with badges, TOC, architecture section,
  roadmap, and contributing guide
- `CONTRIBUTING.md` with development setup and coding guidelines
- `LICENSE` (MIT)
- Example config files (JSON, TOML)
- New example files (`aggregation.dl`, `strings.dl`, `demo.py`)

### v1.0.0 — Initial Release

- Semi-naive bottom-up evaluation
- Stratified negation with Tarjan's SCC
- Hash-indexed joins
- Comparison and arithmetic builtins
- JSON I/O
- Retraction
- Introspection API
- CLI and REPL

## Roadmap

- **Magic-set rewriting** — optimize queries by pushing constants from
  the query into rule evaluation
- **Negation as failure (NAF) with choice** — extend negation semantics
- **More aggregate functions** — median, variance, std deviation
- **Tabling/memoization** — cache intermediate results across queries
- **Constraint handling** — extend with constraint logic programming
- **Multi-file loading with imports** — `:- include("file.dl").` directive
- **Pretty-printer for derived relations** — formatted table output for
  large relations
- **Web REPL** — browser-based interactive environment
- **Datalog-to-SQL compilation** — translate rules to SQL for execution
  on external databases

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style
guidelines, and pull request process.

## License

MIT License — see [LICENSE](LICENSE).