# earley-parser

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests: 183](https://img.shields.io/badge/tests-183-brightgreen.svg)](tests/)
[![Version: 2.0.0](https://img.shields.io/badge/version-2.0.0-blue.svg)](pyproject.toml)

A comprehensive **Earley chart parser** for general context-free grammars (CFGs)
— works on *any* CFG, including ambiguous grammars, in O(n³) worst-case time
and O(n²) for unambiguous grammars. Includes a CYK parser, LL(1) analysis,
parse forest export, and 10-subcommand CLI.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Basic Recognition](#basic-recognition)
  - [Parse Tree Extraction](#parse-tree-extraction)
  - [Parse Forest Export](#parse-forest-export)
  - [Tokenizer](#tokenizer)
  - [BNF Grammar Files](#bnf-grammar-files)
  - [Grammar Analysis](#grammar-analysis)
  - [LL(1) Table Construction](#ll1-table-construction)
  - [CYK Parser](#cyk-parser)
  - [Configuration Files](#configuration-files)
  - [CLI](#cli)
- [Architecture](#architecture)
- [Examples](#examples)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [Known Issues (Resolved)](#known-issues-resolved)
- [License](#license)

## Features

### Core Parsing
- **Earley algorithm**: recognition + parse tree extraction for *any* CFG
- **SPPF-style tree extraction**: shared packed parse forest with ambiguity support
- **Ambiguity detection**: multiple trees returned for ambiguous inputs
- **Nullable/epsilon handling**: fixed-point computation
- **Structured error reporting**: position, unexpected token, expected token set

### Grammar Analysis
- **FIRST sets**: for all symbols, with sequence FIRST computation
- **FOLLOW sets**: with `$` endmarker convention
- **LL(1) table**: predictive parsing table construction with conflict detection
- **Productivity & reachability**: unproductive/unreachable non-terminal detection
- **Grammar validation**: comprehensive problem detection
- **Grammar statistics**: production counts, RHS lengths, nullable sets
- **Ambiguity detection**: empirical testing via string enumeration
- **Grammar comparison**: approximate language equivalence via sampling

### Alternative Algorithms
- **CYK parser**: Cocke-Younger-Kasami for CNF grammars, with tree extraction

### Developer Experience
- **Regex tokenizer**: configurable specs with skip support and zero-length guard
- **BNF grammar loader**: parse `.bnf` files with comments and alternatives
- **10-subcommand CLI**: recognize, tree, forest, check, analyze, ll1, chart, cyk, demo, config
- **JSON/YAML/TOML config**: config files for grammar + tokenizer + parser options
- **Parse forest export**: JSON, Graphviz DOT, Lisp S-expressions, pretty text
- **183 tests**: comprehensive pytest test suite
- **pip-installable**: `pip install -e ".[dev]"`
- **GitHub Actions CI**: multi-version Python testing
- **Type hints**: throughout the codebase
- **Logging**: structured logging support

## Installation

### From source (development)

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/earley-parser

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"
```

### As a package

```bash
pip install -e .
```

### Requirements

- Python 3.8+
- No runtime dependencies (pure Python)
- Optional: PyYAML for YAML config, tomli for TOML on Python <3.11

## Quick Start

```python
from earley_parser import Grammar, EarleyParser

# Build a grammar
g = Grammar.from_rules("E", [
    ("E", ("E", "+", "E")),
    ("E", ("E", "*", "E")),
    ("E", ("(", "E", ")")),
    ("E", ("id",)),
])

# Parse
p = EarleyParser(g)
print(p.parse(["id", "+", "id", "*", "id"]))  # True

# Get parse trees (ambiguous grammar → multiple trees)
forest = p.forest(["id", "+", "id", "*", "id"])
print(f"{forest.ambiguity_count} parse tree(s)")
print(forest.trees[0].pretty())
```

Output:
```
2 parse tree(s)
E  [0:5]
  E  [0:3]
    E  [0:1]
      id  [0:1]
    +  [1:2]
    E  [2:3]
      id  [2:3]
  *  [3:4]
  E  [4:5]
    id  [4:5]
```

## Usage

### Basic Recognition

```python
from earley_parser import Grammar, EarleyParser, ParseError

g = Grammar.from_rules("E", [
    ("E", ("E", "+", "E")),
    ("E", ("E", "*", "E")),
    ("E", ("(", "E", ")")),
    ("E", ("id",)),
])

p = EarleyParser(g)

# Simple recognition
print(p.parse(["id", "+", "id", "*", "id"]))   # True
print(p.parse(["id", "+"]))                     # False

# With structured error
result = p.parse_or_error(["id", "+"])
if isinstance(result, ParseError):
    print(result)
    # Parse error at position 2: unexpected EOF; expected one of: (, id
    print(result.to_dict())
    # {'position': 2, 'expected': ['(', 'id'], 'token': None, 'message': '...'}
```

### Parse Tree Extraction

```python
# Extract parse trees
trees = p.trees(["id", "+", "id", "*", "id"], max_trees=10)
print(f"{len(trees)} parse tree(s)")

for t in trees:
    print(t.pretty())
    print()

# Tree operations
tree = trees[0]
print(tree.yield_terminals())  # ['id', '+', 'id', '*', 'id']
print(tree.depth())             # 4
print(tree.count_nodes())       # 9
print(tree.to_json())           # JSON serialization

# Walk all nodes
for node in tree.walk():
    print(f"  {node.symbol} [{node.start}:{node.end}]")
```

### Parse Forest Export

```python
forest = p.forest(["id", "+", "id", "*", "id"], max_trees=10)

# JSON (for programmatic use)
print(forest.to_json())

# Graphviz DOT (for visualization)
print(forest.to_dot())
# Save to file and render: dot -Tpng tree.dot -o tree.png

# Lisp S-expression
print(forest.to_lisp())
# (E (E (E id) + (E id)) * (E id))

# Pretty text
print(forest.pretty())

# Stats
print(forest.stats())
# {'tree_count': 2, 'is_ambiguous': True, 'max_depth': 4, 'total_nodes': 20}
```

### Tokenizer

```python
from earley_parser import Tokenizer, TokenSpec

tok = Tokenizer([
    TokenSpec("NUM", r"[0-9]+"),
    TokenSpec("PLUS", r"\+"),
    TokenSpec("STAR", r"\*"),
    TokenSpec("LPAREN", r"\("),
    TokenSpec("RPAREN", r"\)"),
    TokenSpec("WS", r"\s+", skip=True),
])

# Just token names
tokens = tok.tokenize("3 + 4 * (2 + 1)")
# ['NUM', 'PLUS', 'NUM', 'STAR', 'LPAREN', 'NUM', 'PLUS', 'NUM', 'RPAREN']

# With matched text
pairs = tok.tokenize_with_text("3 + 4")
# [('NUM', '3'), ('PLUS', '+'), ('NUM', '4')]

# Full token objects with positions
full = tok.tokenize_full("3 + 4")
# [Token('NUM', '3', 0), Token('PLUS', '+', 2), Token('NUM', '4', 4)]
```

### BNF Grammar Files

```bnf
# expr.bnf
start ::= <E>

<E> ::= <E> "+" <E>
      | <E> "*" <E>
      | "(" <E> ")"
      | "id"
```

```python
from earley_parser import GrammarLoader

# Load from string
g = GrammarLoader.load(open("examples/expr.bnf").read())

# Load from file
g = GrammarLoader.load_file("examples/expr.bnf")

# Validate
problems = g.validate()
if problems:
    for p in problems:
        print(f"  - {p}")
else:
    print("Grammar is valid!")
```

### Grammar Analysis

```python
from earley_parser import grammar_summary, detect_ambiguity

g = GrammarLoader.load_file("examples/expr.bnf")

# Full grammar summary
print(grammar_summary(g))
# Grammar: expr
#   Start symbol: E
#   Non-terminals: 1
#   Terminals: 5
#   Productions: 4
#   Nullable: 0 non-terminal(s)
#   LL(1): no
#   FOLLOW sets:
#     E: { $, ), *, + }

# FIRST and FOLLOW sets
print(g.first())   # {'E': {'(', 'id'}, 'id': {'id'}, ...}
print(g.follow())  # {'E': {'$', ')', '*', '+'}}

# Ambiguity detection
ambiguous = detect_ambiguity(g, max_length=5)
print(f"{len(ambiguous)} ambiguous input(s) found")
```

### LL(1) Table Construction

```python
from earley_parser import LL1Table, is_ll1

# Build LL(1) table
table = LL1Table(g).build()
print(f"LL(1): {table.is_ll1}")
print(f"Conflicts: {len(table.conflicts)}")

# Pretty-print the table
print(table.pretty())

# Look up entries
prod = table.get("E", "id")
print(prod)  # ('E', '+', 'E')
```

### CYK Parser

```python
from earley_parser import CNFGrammar, CYKParser

# Build a CNF grammar (A → BC or A → a only)
cnf = CNFGrammar(start="S")
cnf.add_binary("S", "S", "S")
cnf.add_terminal("S", "a")

p = CYKParser(cnf)
print(p.parse(["a", "a", "a"]))  # True

trees = p.trees(["a", "a", "a"])
print(f"{len(trees)} tree(s)")
```

### Configuration Files

JSON config (`config.json`):
```json
{
    "grammar_file": "examples/expr.bnf",
    "parser": {"max_trees": 50, "algorithm": "earley"},
    "logging": {"level": "INFO"}
}
```

```python
from earley_parser import load_config

cfg = load_config("examples/config.json")
cfg.setup_logging()
g = cfg.get_grammar()
parser = EarleyParser(g)
```

### CLI

```bash
# Recognize
earley recognize --grammar examples/expr.bnf id + id '*' id

# Show parse trees
earley tree --grammar examples/expr.bnf --max 3 id + id '*' id

# Export forest as JSON / DOT / Lisp
earley forest --grammar examples/expr.bnf --format json id
earley forest --grammar examples/expr.bnf --format dot id
earley forest --grammar examples/expr.bnf --format lisp id

# Validate a grammar
earley check examples/expr.bnf

# Analyze a grammar (LL(1), FOLLOW sets, stats)
earley analyze --ambiguity examples/expr.bnf

# Build LL(1) table
earley ll1 examples/expr.bnf

# Dump chart contents
earley chart --grammar examples/expr.bnf id + id

# Parse with CYK (CNF grammars only)
earley cyk examples/cnf.bnf a b

# Config-based parsing
earley config examples/config.json id + id

# Run the built-in demo
earley demo
```

## Architecture

The package is organized into focused modules:

```
earley_parser/
├── __init__.py      # Public API exports
├── errors.py        # Exception hierarchy (EarleyError, ParseError, ...)
├── grammar.py       # Grammar, GrammarLoader, GrammarStats
├── tokenizer.py     # Tokenizer, TokenSpec, Token
├── parser.py        # EarleyParser, Chart, Item, ParseNode, ParseForest
├── cyk.py           # CNFGrammar, CYKParser (alternative algorithm)
├── analysis.py      # LL1Table, ambiguity detection, grammar comparison
├── config.py        # ParserConfig, load_config, save_config
└── cli.py           # CLI with 10 subcommands
```

### How the Earley Algorithm Works

The Earley algorithm uses three classic operations per chart position:

| Operation | Purpose |
|-----------|---------|
| **Predict** | If the next symbol is a non-terminal *N*, add items for every production of *N* to the current chart. |
| **Scan** | If the next symbol is a terminal matching the current input token, advance the dot and add the item to the next chart. |
| **Complete** | If an item is complete (dot at the end), advance any earlier item in the origin chart that was waiting for this non-terminal. |

Each Earley *item* is a dotted rule `(LHS → α • β, origin)`, where `origin`
records the input position at which recognition of this non-terminal began.
The parser maintains one *chart* per input position (0 … n).

**Tree extraction**: After recognition, parse trees are extracted by
enumerating all ways to split each item's span `[origin, end]` into
sub-segments matching the RHS symbols. A *path* set detects cycles, and a
*memo* cache avoids redundant recomputation.

See [docs/architecture.md](docs/architecture.md) for full details.

## Examples

The `examples/` directory contains:

| File | Description |
|------|-------------|
| `basic_usage.py` | Basic recognition and tree extraction |
| `tokenizer_usage.py` | Tokenizer + parser integration |
| `analysis_demo.py` | LL(1) analysis, ambiguity detection, grammar comparison |
| `cyk_demo.py` | CYK parser with tree extraction and Earley comparison |
| `forest_export.py` | JSON, DOT, and Lisp S-expression export |
| `expr.bnf` | Ambiguous expression grammar |
| `expr_unambiguous.bnf` | Unambiguous expression grammar with precedence |
| `balance.bnf` | Balanced parentheses with epsilon |
| `json.bnf` | Simple JSON-like grammar |
| `statement.bnf` | Python-like statement grammar |
| `config.json` | Example configuration file |

Run any example:
```bash
python3 examples/basic_usage.py
python3 examples/cyk_demo.py
python3 examples/analysis_demo.py
```

## Roadmap

- [ ] EBNF support (optional, `?`, `+`, `*` operators in grammar files)
- [ ] Automatic CNF conversion from general CFGs
- [ ] GLR parser implementation
- [ ] Packrat / PEG parser
- [ ] Syntax tree visitor pattern
- [ ] Grammar transformation (left-factoring, left-recursion removal)
- [ ] SLR(1) / LALR(1) table construction
- [ ] Web-based parse tree visualization
- [ ] Performance: NumPy-accelerated chart operations
- [ ] Incremental parsing (re-parse on edit)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style,
and pull request guidelines.

## Changelog

### v2.0.0 — Comprehensive Improvement (2026-06-22)

**Major changes:**
- **Modular architecture**: Split monolithic `earley.py` (911 lines) into
  a proper `earley_parser/` package with 8 focused modules
- **CYK parser**: Added `CNFGrammar` and `CYKParser` as an alternative
  parsing algorithm for CNF grammars
- **LL(1) analysis**: `LL1Table` with table construction, conflict
  detection, and pretty-printing
- **FOLLOW sets**: Computed via iterative closure with `$` endmarker
- **Ambiguity detection**: Empirical detection via string enumeration
- **Grammar comparison**: Approximate language equivalence via sampling
- **ParseForest class**: Container with JSON, DOT, and Lisp export
- **ParseNode enhancements**: `yield_terminals()`, `depth()`,
  `count_nodes()`, `walk()`, `to_json()`, `is_ambiguous()`
- **Token class**: Full token objects with positions (`tokenize_full()`)
- **GrammarStats**: Production counts, RHS lengths, unreachable/unproductive sets
- **Config system**: JSON/YAML/TOML configuration files
- **CLI expansion**: 10 subcommands (was 4) — added `forest`, `analyze`,
  `ll1`, `chart`, `cyk`, `config`
- **Forest export**: JSON, Graphviz DOT, Lisp S-expressions
- **pip-installable**: `pyproject.toml` with `earley` entry point
- **Type hints**: Throughout the codebase
- **Logging**: Structured logging support
- **Exception hierarchy**: `EarleyError` base with `ParseError`,
  `GrammarError`, `TokenizerError`
- **Grammar serialization**: `to_dict()` / `from_dict()`
- **Productivity & reachability**: Analysis methods
- **183 tests** (was 25): Full pytest suite with 8 test modules
- **GitHub Actions CI**: Multi-version Python testing
- **CONTRIBUTING.md**: Development guidelines
- **LICENSE**: MIT license
- **docs/**: Architecture and language reference docs
- **5 example grammars**: Added JSON, statement, and unambiguous expression

**Backward compatibility:**
- `trees_v2()` method preserved as alias for `trees()`
- Original test cases ported and verified in `tests/test_bugs.py`

### v1.0.0 — Initial Release (2026-06-22)

- Core Earley recognizer with predict/scan/complete
- Nullable fixed-point computation
- Parse tree extraction (SPPF-style with ambiguity support)
- Structured error reporting with expected-token sets
- Regex tokenizer with skip support
- BNF grammar file loader
- Grammar validation (FIRST sets, productivity)
- CLI with 4 subcommands (recognize, tree, check, demo)
- 19 tests → 25 tests (after bug hunt)
- 6 bugs found and fixed

## Known Issues (Resolved)

| # | Bug | Fix |
|---|-----|-----|
| 1 | **Memo caches truncated tree lists** — when `max_trees` was hit during tree extraction, the memo cached the incomplete result. Subsequent calls with a larger `max_trees` would receive the stale truncated list. | Only cache results in the memo when `len(nodes_list) < max_trees`. |
| 2 | **Tokenizer infinite loop on zero-length regex matches** — a regex like `[0-9]*` could match the empty string, causing the tokenizer to hang. | Detect zero-length matches (`m.end() == i`) and skip. |
| 3 | **Empty grammar file causes IndexError** — `GrammarLoader.load("")` raised unhelpful `IndexError`. | Explicit `GrammarError` with clear message. |
| 4 | **Parse tree node sharing across trees** — the memo cache returned the same `ParseNode` objects, so modifying one tree corrupted others. | Deep-copy all children when assembling completed trees. |
| 5 | **Dead code in `validate()`** — no-op loop and unused `nullable` variable. | Removed dead code. |
| 6 | **Dead code in `GrammarLoader.load()`** — redundant terminal-collecting loop. | Removed redundant loop. |

All fixes are verified by tests in `tests/test_bugs.py`.

## License

MIT License — see [LICENSE](LICENSE).