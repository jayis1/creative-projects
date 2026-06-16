# 🔬 Mini-Prolog Engine

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-green.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-195%20passing-brightgreen.svg)](tests/)
[![Built-in Predicates](https://img.shields.io/badge/builtins-60%2B-orange.svg)](prolog_engine/builtins.py)

A complete logic programming engine implementing a subset of Prolog in pure Python, featuring Robinson's unification with occurs-check, backtracking search, predicate indexing, and **60+ built-in predicates**.

```
         ╔══════════════════════════════════════╗
         ║   Mini-Prolog Engine v2.0            ║
         ║   A Logic Programming Engine in Py    ║
         ╚══════════════════════════════════════╝
```

## ✨ Features

- **Robinson's unification** with occurs-check to prevent infinite terms
- **Backtracking search** with depth-first SLD resolution
- **Predicate indexing** for efficient clause lookup by name/arity
- **60+ built-in predicates** covering unification, type checking, control flow, arithmetic, lists, term inspection, dynamic database, meta-logical, string manipulation, and I/O
- **Standard Prolog syntax**: clauses, queries, lists, infix operators
- **Arithmetic with operator precedence**: `X is 3 + 4 * 2.` correctly evaluates to 11
- **Dynamic database**: `assertz/1`, `asserta/1`, `retract/1`, `clause/2`
- **Meta-logical**: `findall/3`, `bagof/3`, `setof/3`, `copy_term/2`
- **String manipulation**: `atom_length/2`, `atom_concat/3`, `sub_atom/5`, `char_code/2`
- **List aggregation**: `max_list/2`, `min_list/2`, `sum_list/2`
- **Cut (!)** for pruning choice points
- **Negation as failure** (`not/1`, `\+/1`)
- **Tracing mode** for debugging
- **Max depth protection** against infinite loops
- **Interactive REPL** with readline, history, and colorized output
- **Configuration file support** (YAML, JSON, TOML)
- **Structured logging** throughout
- **Comprehensive test suite** (195 tests)
- **Installable** via pip

## 📑 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Command-Line REPL](#command-line-repl)
  - [Python API](#python-api)
  - [Configuration](#configuration)
- [Built-in Predicates](#built-in-predicates)
- [Arithmetic Functions](#arithmetic-functions)
- [Architecture](#architecture)
- [Examples](#examples)
- [Running Tests](#running-tests)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## Installation

```bash
# From source (recommended for development)
cd prolog-engine
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Install with YAML config support
pip install -e ".[yaml]"
```

## Quick Start

```python
from prolog_engine import create_engine

engine = create_engine()
engine.load_source("""
    parent(tom, bob).
    parent(tom, liz).
    parent(bob, ann).
    grandparent(X, Z) :- parent(X, Y), parent(Y, Z).
""")

results = engine.query("?- grandparent(tom, X).")
for result in results:
    print(engine.format_solution(result))
# Output: X = ann
```

## Usage

### Command-Line REPL

```bash
# Start interactive REPL
prolog-engine

# Load a file and start REPL
prolog-engine examples/family_tree.pl -i

# Load a file and run a query
prolog-engine examples/fibonacci.pl -q "?- fib(6, X)."

# Enable tracing
prolog-engine --trace

# Set custom depth/solution limits
prolog-engine --max-depth 500 --max-solutions 1000

# Use a config file
prolog-engine --config prolog-engine.json

# Disable colors
prolog-engine --no-color

# Show version
prolog-engine --version
```

**REPL Commands:**

| Command | Description |
|---------|-------------|
| `help.` | Show help message |
| `trace.` | Toggle trace mode |
| `listing.` | Show all loaded clauses |
| `statistics.` | Show engine statistics |
| `reset.` | Clear the database |
| `consult('file.pl').` | Load a Prolog source file |
| `quit.` | Exit (also: `exit.`, `halt.`, Ctrl-D) |

### Python API

```python
from prolog_engine import create_engine, EngineConfig
from prolog_engine.engine import Engine

# Create engine with default settings
engine = create_engine()

# Create engine with custom config
config = EngineConfig(max_depth=500, trace=True)
engine = create_engine(config=config)

# Load Prolog source
engine.load_source("parent(tom, bob). parent(tom, liz).")

# Load from file
engine.load_file("examples/family_tree.pl")

# Run a query
results = engine.query("?- parent(tom, X).")
for result in results:
    print(engine.format_solution(result))

# Get first solution only
result = engine.query_one("?- parent(tom, X).")

# Access engine statistics
stats = engine.statistics()
print(f"Clauses: {stats['clauses']}, Builtins: {stats['builtins']}")

# Enable/disable trace mode
engine.trace = True

# Access configuration
print(f"Max depth: {engine.max_depth}")
print(f"Max solutions: {engine.max_solutions}")
```

### Configuration

The engine supports configuration via YAML, JSON, or TOML files:

**JSON config (`prolog-engine.json`):**
```json
{
  "max_depth": 2000,
  "max_solutions": 50000,
  "trace": false
}
```

**YAML config (`.prolog-engine.yml`):**
```yaml
max_depth: 2000
max_solutions: 50000
trace: false
```

The engine searches for config files automatically (`load_config()`), or you can specify one explicitly (`--config`).

## Built-in Predicates

| Category | Predicates |
|----------|-----------|
| **Unification** | `=/2`, `\=/2`, `==/2`, `\==/2` |
| **Arithmetic** | `is/2`, `</2`, `>/2`, `=</2`, `>=/2`, `between/3`, `succ/2`, `plus/3` |
| **Type checking** | `var/1`, `nonvar/1`, `atom/1`, `number/1`, `compound/1`, `integer/1`, `float/1`, `string/1`, `atomic/1`, `ground/1` |
| **Control flow** | `true/0`, `fail/0`, `!/0`, `not/1`, `\+/1`, `once/1`, `forall/2`, `repeat/0`, `halt/0` |
| **Lists** | `length/2`, `member/2`, `append/3`, `reverse/2`, `nth0/3`, `nth1/3`, `last/2`, `sort/2`, `msort/2`, `max_list/2`, `min_list/2`, `sum_list/2` |
| **Term inspection** | `functor/3`, `arg/3`, `copy_term/2`, `=../2`, `variables/2`, `numbervars/3` |
| **Dynamic DB** | `assertz/1`, `asserta/1`, `retract/1`, `clause/2` |
| **Meta-logical** | `findall/3`, `bagof/3`, `setof/3` |
| **String/Atom** | `atom_length/2`, `atom_concat/3`, `sub_atom/5`, `char_code/2` |
| **I/O** | `write/1`, `writeln/1`, `nl/0`, `write_canonical/1` |

## Arithmetic Functions

Supported in `is/2` expressions:

| Function | Description |
|----------|-------------|
| `+`, `-`, `*`, `/` | Basic arithmetic |
| `//` | Integer division (rounds toward zero) |
| `mod` | Modulo |
| `rem` | Remainder (toward zero) |
| `**`, `^` | Exponentiation |
| `abs(X)` | Absolute value |
| `max(X, Y)`, `min(X, Y)` | Maximum/minimum |
| `sqrt(X)`, `sin(X)`, `cos(X)`, `tan(X)` | Trigonometric functions |
| `log(X)`, `exp(X)` | Logarithm and exponential |
| `floor(X)`, `ceiling(X)`, `round(X)` | Rounding |
| `pi`, `e` | Mathematical constants |

## Architecture

```
                    ┌──────────────┐
                    │  Source Code  │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │    Lexer     │  Tokenization
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │    Parser    │  Precedence-climbing
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  AST Nodes   │  Clause, Query, Compound, ...
                    └──────┬───────┘
                           │
          ┌────────────────▼────────────────┐
          │           Engine                │
          │  ┌──────────────────────────┐   │
          │  │   Unifier (Robinson's)    │   │
          │  │   + Occurs-check         │   │
          │  └──────────────────────────┘   │
          │  ┌──────────────────────────┐   │
          │  │   SLD Resolution         │   │
          │  │   + Backtracking         │   │
          │  │   + Predicate Indexing   │   │
          │  └──────────────────────────┘   │
          │  ┌──────────────────────────┐   │
          │  │   Built-in Predicates   │   │
          │  │   (~60 generators)       │   │
          │  └──────────────────────────┘   │
          │  ┌──────────────────────────┐   │
          │  │   Arithmetic Evaluator   │   │
          │  └──────────────────────────┘   │
          └─────────────────────────────────┘
                           │
                    ┌──────▼───────┐
                    │   Results    │  Substitutions
                    └──────────────┘
```

**Key Design Decisions:**

1. **Generator-based builtins** — All builtins are Python generators that yield substitutions for success and return for failure, naturally integrating with the backtracking engine.

2. **Predicate indexing** — The engine maintains a `name/arity → clause indices` mapping for O(1) clause lookup, significantly improving performance for large knowledge bases.

3. **Standardizing apart** — Each clause is renamed (variables prefixed with unique counters) before resolution to prevent variable capture between different rule applications.

4. **Occurs-check** — The unifier always performs occurs-check, preventing creation of infinite terms (cyclic structures). This is safer but slightly slower than Prolog systems that skip it.

5. **Depth limit** — Default max depth is 1000 to prevent infinite loops. Configurable via `EngineConfig` or `engine.max_depth`.

6. **Modular architecture** — Lexer, Parser, Unifier, Engine, and Builtins are cleanly separated, making it easy to extend or modify individual components.

## Examples

See the [`examples/`](examples/) directory for complete Prolog programs:

| Example | Description |
|---------|-------------|
| [`family_tree.pl`](examples/family_tree.pl) | Classic family relationships with recursive rules |
| [`fibonacci.pl`](examples/fibonacci.pl) | Fibonacci sequence with arithmetic |
| [`quicksort.pl`](examples/quicksort.pl) | Quicksort algorithm with list manipulation |
| [`dynamic_database.pl`](examples/dynamic_database.pl) | Runtime fact manipulation with assert/retract |
| [`map_coloring.pl`](examples/map_coloring.pl) | Constraint satisfaction: Australian map coloring |
| [`hanoi.pl`](examples/hanoi.pl) | Towers of Hanoi puzzle |

**Family Tree:**
```prolog
parent(tom, bob).
parent(tom, liz).
grandparent(X, Z) :- parent(X, Y), parent(Y, Z).

% ?- grandparent(tom, X).  →  X = ann
```

**Quicksort:**
```prolog
qsort([], []).
qsort([H|T], Sorted) :-
    partition(H, T, Less, Greater),
    qsort(Less, SortedLess),
    qsort(Greater, SortedGreater),
    append(SortedLess, [H|SortedGreater], Sorted).

% ?- qsort([3, 1, 4, 1, 5], R).  →  R = [1, 1, 3, 4, 5]
```

**Atom Manipulation:**
```prolog
?- atom_length(hello, N).        → N = 5
?- atom_concat(hello, world, X). → X = helloworld
?- char_code(a, C).              → C = 97
?- max_list([3, 1, 4, 1, 5], M). → M = 5
?- sum_list([1, 2, 3, 4], S).    → S = 10
```

## Running Tests

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/ --cov=prolog_engine --cov-report=term-missing

# Run a specific test file
python3 -m pytest tests/test_improvements.py -v
```

**195 tests** covering:
- Lexer tokenization
- Parser precedence and error handling
- Unification (with and without occurs-check)
- Engine SLD resolution
- All 60+ built-in predicates
- Configuration system
- Error hierarchy
- CLI functionality
- Integration scenarios (family tree, fibonacci, quicksort, etc.)

## Known Issues (Resolved)

The following bugs were found and fixed during development:

1. **Anonymous variable reuse** — Multiple `_` in the same query were treated as the same variable. **Fix**: Parser generates unique `__anon_N` names.

2. **Unary minus not supported** — `X is -3.` failed to parse. **Fix**: Added unary `-`/`+` handling in parser.

3. **Integer division rounding** — Python's `//` rounds toward -infinity, Prolog's `//` rounds toward zero. **Fix**: Changed to `int(a/b)`.

4. **Division by zero swallowed** — `is/2` caught all exceptions silently. **Fix**: Introduced `EvaluationError` subclass.

5. **Bare `except Exception` masking errors** — **Fix**: Replaced with specific exception hierarchy.

6. **Atom-as-rule-head resolution bug** — Rules with atom heads were treated as facts. **Fix**: Added proper fact/rule dispatch.

7. **`=..` (univ) operator not parseable** — **Fix**: Added special multi-character lexer rule.

8. **Dead code** — `matching_keys` computed but unused. **Fix**: Removed.

9. **`rem` operator semantics** — Python `%` differs from Prolog `rem` for negatives. **Fix**: Toward-zero remainder.

## Roadmap

- [ ] **ISO Prolog compliance** — Expand toward DCG (Definite Clause Grammars)
- [ ] **Module system** — Add `use_module/1` and `module/2` declarations
- [ ] **Operator declarations** — `op/3` for custom infix operators
- [ ] **Tabling/memoization** — SLG resolution for better termination
- [ ] **Constraint logic programming** — CLP(FD) style constraints
- [ ] **Unicode atoms** — Full Unicode support in atom names
- [ ] **Consult/1** — Load files from within Prolog queries
- [ ] **REPL history persistence** — Save/load REPL sessions
- [ ] **Web playground** — Browser-based Prolog environment
- [ ] **Performance benchmarks** — vs. SWI-Prolog, PySWIP, etc.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Setting up the development environment
- Running tests
- Adding new built-in predicates
- Submitting changes

## Changelog

### v2.0.0 (2026-06-16) — Comprehensive Improvement

**New Features:**
- 10 new built-in predicates: `atom_length/2`, `atom_concat/3`, `sub_atom/5`, `char_code/2`, `max_list/2`, `min_list/2`, `sum_list/2`, `variables/2`, `numbervars/3`, `halt/0`
- Configuration file support (YAML, JSON, TOML)
- Structured exception hierarchy (`PrologError`, `InstantiationError`, `TypeError`, `ExistenceError`, `PermissionError`)
- Enhanced CLI with readline, colorized output, and interactive commands (`help.`, `trace.`, `listing.`, `statistics.`, `reset.`, `consult/1`)
- Engine statistics API (`engine.statistics()`)
- Configurable properties (`engine.max_depth`, `engine.max_solutions`)
- `engine.load_file()` for loading Prolog source files
- `engine.get_builtins()` for introspecting registered builtins
- `create_engine()` convenience function with config support
- 6 example Prolog programs in `examples/`
- GitHub Actions CI configuration
- CONTRIBUTING.md and LICENSE files

**Improvements:**
- Full type hints on all public functions
- Comprehensive docstrings throughout
- Structured logging (Python `logging` module)
- Version bump to 2.0.0
- 57 new tests (195 total, up from 138)
- Improved `pyproject.toml` with optional dependencies and dev extras

### v1.0.0 (Initial Release)

- Core Prolog engine with 50+ built-in predicates
- Lexer, Parser, Unifier, Engine architecture
- 138 tests
- Basic CLI REPL

## License

This project is licensed under the [MIT License](LICENSE).