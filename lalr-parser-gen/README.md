# lalr-parser-gen

![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Tests: 130](https://img.shields.io/badge/tests-130%20passing-brightgreen.svg)
![Version: 3.0.0](https://img.shields.io/badge/version-3.0.0-orange.svg)

A from-scratch LALR(1) parser generator written in pure Python with zero
external dependencies. Includes a configurable lexer framework, error
recovery, grammar transformations, Graphviz visualization, JSON
configuration, and a comprehensive CLI.

---

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Usage](#usage)
  - [Programmatic API](#programmatic-api)
  - [BNF Grammar Files](#bnf-grammar-files)
  - [Configurable Lexer](#configurable-lexer)
  - [Error Recovery](#error-recovery)
  - [Grammar Transformations](#grammar-transformations)
  - [Visualization](#visualization)
  - [Configuration Files](#configuration-files)
  - [JSON Table Serialization](#json-table-serialization)
  - [CLI](#cli)
- [Examples](#examples)
- [Testing](#testing)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [Known Issues (Resolved)](#known-issues-resolved)
- [License](#license)

---

## Overview

This project implements a complete LALR(1) parser generator, including:

- **Grammar representation** with nullable, FIRST, and FOLLOW set computation
- **LR(0) automaton** construction (canonical collection of item sets)
- **LALR(1) lookahead computation** via the DeRemer-Pennello propagation algorithm
- **SLR(1) table builder** for comparison (demonstrates LALR's superiority)
- **ACTION/GOTO table** construction with conflict detection
- **Precedence & associativity** declarations for conflict resolution (yacc-style)
- **Table-driven LR parser** with semantic actions
- **BNF grammar loader** with `%token`, `%start`, `%left`, `%right`, `%nonassoc` directives
- **Configurable regex-based lexer** with longest-match, priorities, and line tracking
- **Panic-mode error recovery** with synchronization tokens and multi-error collection
- **Grammar transformations**: left-recursion removal, left factoring, useless symbol elimination
- **Graphviz DOT visualization** of the LR automaton with lookaheads
- **HTML table export** of ACTION/GOTO tables
- **JSON table serialization** for saving/loading pre-computed parse tables
- **JSON configuration files** for lexer, parser, and logging settings
- **CLI** with 12 subcommands for table inspection, conflict analysis, visualization, and parsing

LALR(1) is more powerful than SLR(1) (it handles grammars where SLR would
report spurious conflicts) while producing tables as compact as LR(0).

---

## Installation

### From source (recommended)

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/lalr-parser-gen
pip install -e ".[test]"
```

### Without installation

```bash
cd creative-projects/lalr-parser-gen
PYTHONPATH=. python3 -m lalr.cli grammar.bnf --action=table
```

### Requirements

- Python 3.9+
- No external dependencies (pure Python)
- Optional: `pytest` for running tests, `graphviz` for rendering DOT files

---

## Quick Start

```python
from lalr import Grammar, LALRTable, Parser, Token

# Define a grammar
grammar = Grammar([
    ("expr",   ["expr", "+", "term"]),
    ("expr",   ["term"]),
    ("term",   ["term", "*", "factor"]),
    ("term",   ["factor"]),
    ("factor", ["(", "expr", ")"]),
    ("factor", ["NUMBER"]),
])

# Build LALR(1) table
table = LALRTable(grammar)
print(table.summary())  # 12 states, no conflicts

# Parse with semantic actions
actions = {
    1: lambda c: c[0] + c[2],   # expr -> expr + term
    2: lambda c: c[0],          # expr -> term
    3: lambda c: c[0] * c[2],   # term -> term * factor
    4: lambda c: c[0],          # term -> factor
    5: lambda c: c[1],          # factor -> ( expr )
    6: lambda c: c[0],          # factor -> NUMBER
}
parser = Parser(grammar, table=table, actions=actions)
result = parser.parse([
    Token("NUMBER", 2), Token("+"), Token("NUMBER", 3),
    Token("*"), Token("NUMBER", 4),
])
# result = 14
```

---

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  BNF Loader  │────▶│    Grammar   │────▶│ LR(0) Auto   │
│  bnf_loader  │     │   grammar    │     │   table      │
└──────────────┘     └──────┬───────┘     └──────┬───────┘
                            │                     │
                     ┌──────▼───────┐     ┌──────▼───────┐
                     │  FIRST/FOLLOW │     │  LALR(1)     │
                     │   compute     │     │  Lookaheads  │
                     └──────┬───────┘     └──────┬───────┘
                            │                     │
                     ┌──────▼───────┐     ┌──────▼───────┐
                     │  SLR Table   │     │  LALR Table  │
                     │  slr_table   │     │  + Precedence│
                     └──────────────┘     └──────┬───────┘
                                                  │
                                          ┌───────▼───────┐
                           ┌──────────────│    Parser     │
                           │              │   parser      │
                    ┌──────▼─────┐        └───────────────┘
                    │   Lexer    │               │
                    │   lexer    │──────────────▶│
                    └────────────┘        ┌──────▼───────┐
                                          │   Results    │
                                          └──────────────┘
```

### Module Overview

| Module | Responsibility |
|--------|---------------|
| `grammar.py` | Grammar representation, FIRST/FOLLOW/nullable computation |
| `table.py` | LR(0) automaton, LALR(1) lookahead propagation, ACTION/GOTO tables |
| `slr_table.py` | SLR(1) table builder for educational comparison |
| `precedence.py` | Precedence/associativity for yacc-style conflict resolution |
| `parser.py` | Table-driven LR parser with semantic actions |
| `bnf_loader.py` | BNF grammar file parser with directives |
| `lexer.py` | Configurable regex-based lexer framework |
| `error_recovery.py` | Panic-mode error recovery with sync tokens |
| `transform.py` | Grammar transformations (left-recursion removal, factoring) |
| `visualize.py` | Graphviz DOT output, HTML tables, conflict reports |
| `config.py` | JSON configuration management |
| `cli.py` | Command-line interface (12 subcommands) |

### How LALR(1) Works

#### 1. Grammar → LR(0) Automaton

The grammar is augmented with `S' → S$`. The LR(0) automaton is built by
computing the **closure** and **goto** of item sets:

- **Closure**: For each item `A → α•Bβ`, add all items `B → •γ`.
- **GOTO**: For each symbol `X`, advance all items with `•X` and take closure.

#### 2. LALR(1) Lookahead Propagation

LALR(1) lookaheads are computed using the DeRemer-Pennello algorithm:

1. **Spontaneous generation**: For item `A → α•Bβ` with lookahead `la`,
   the item `B → •γ` gets `FIRST(β la)` as spontaneous lookaheads.
2. **Propagation**: Lookaheads flow from `A → α•Bβ` to:
   - `A → αB•β` in the GOTO state (kernel item propagation)
   - `B → •γ` in the same state (when `β` is nullable)

The propagation iterates to a fixed point until no new lookaheads appear.

#### 3. Table Construction

For each state:
- **Shift**: If `A → α•aβ` with lookahead `a`, set `ACTION[s, a] = shift`.
- **Reduce**: If `A → α•` with lookahead `a`, set `ACTION[s, a] = reduce(A → α)`.
- **Accept**: If `S' → S•` with `$`, set `ACTION[s, $] = accept`.
- **Goto**: If `A → α•Bβ` and `GOTO[s, B] = s'`, set `GOTO[s, B] = s'`.

Conflicts (shift/reduce, reduce/reduce) are detected and reported. When
precedence declarations are available, shift/reduce conflicts are resolved
automatically using yacc-style rules.

---

## Usage

### Programmatic API

```python
from lalr import Grammar, LALRTable, Parser, Token

grammar = Grammar([
    ("expr", ["expr", "+", "term"]),
    ("expr", ["term"]),
    ("term", ["term", "*", "factor"]),
    ("term", ["factor"]),
    ("factor", ["(", "expr", ")"]),
    ("factor", ["NUMBER"]),
])

table = LALRTable(grammar)
print(table.summary())

actions = {
    1: lambda c: c[0] + c[2],
    2: lambda c: c[0],
    3: lambda c: c[0] * c[2],
    4: lambda c: c[0],
    5: lambda c: c[1],
    6: lambda c: c[0],
}
parser = Parser(grammar, table=table, actions=actions)
result = parser.parse([
    Token("NUMBER", 2), Token("+"), Token("NUMBER", 3),
    Token("*"), Token("NUMBER", 4),
])
# result = 14
```

### BNF Grammar Files

```bnf
// examples/expr_prec.bnf
%start expr
%left '+' '-'
%left '*' '/'
%right '^'
%right UMINUS

expr   : expr '+' expr
       | expr '-' expr
       | expr '*' expr
       | expr '/' expr
       | expr '^' expr
       | '-' expr %prec UMINUS
       | '(' expr ')'
       | NUMBER
       ;
```

```python
from lalr import load_bnf_full, LALRTable, Parser

with open("examples/expr_prec.bnf") as f:
    grammar, precedence = load_bnf_full(f.read())
table = LALRTable(grammar, precedence=precedence)
# All 25 shift/reduce conflicts resolved by precedence
```

### Configurable Lexer

```python
from lalr.lexer import Lexer, TokenSpec

lexer = Lexer()
lexer.add_spec(TokenSpec("NUMBER", r"\d+", action=int))
lexer.add_spec(TokenSpec("PLUS", r"\+"))
lexer.add_spec(TokenSpec("ID", r"[A-Za-z_][A-Za-z0-9_]*"))
lexer.add_keyword("if", "IF", priority=20)
lexer.add_keyword("while", "WHILE", priority=20)
lexer.set_skip(r"[ \t\n]+")

tokens = lexer.lex("if 42 + foo")
# [Token(IF), Token(NUMBER, 42), Token(PLUS), Token(ID, "foo")]
```

### Error Recovery

```python
from lalr.error_recovery import RecoveringParser

parser = RecoveringParser(grammar, table=table, sync_tokens={";", "}"})
errors = []
result = parser.parse(tokens, on_error=errors.append)
for e in errors:
    print(f"Error at position {e.position}: {e.message}")
    if e.skipped:
        print(f"  (recovered by skipping {e.skipped} tokens)")
```

### Grammar Transformations

```python
from lalr.transform import remove_left_recursion, left_factor

# Remove left recursion: A → Aα | β  becomes  A → βA' | A' → αA' | ε
prods = [("expr", ["expr", "+", "term"]), ("expr", ["term"])]
transformed, start = remove_left_recursion(prods, "expr")

# Left factor: A → αβ₁ | αβ₂  becomes  A → αA' | A' → β₁ | β₂
prods = [("stmt", ["IF", "expr", "THEN", "stmt"]),
         ("stmt", ["IF", "expr", "THEN", "stmt", "ELSE", "stmt"])]
factored = left_factor(prods)
```

### Visualization

```python
from lalr.visualize import automaton_to_dot, table_to_html, conflict_report

# Generate Graphviz DOT file
dot = automaton_to_dot(table, title="My Grammar", show_lookaheads=True)
with open("automaton.dot", "w") as f:
    f.write(dot)
# Render: dot -Tpng automaton.dot -o automaton.png

# Generate HTML table
html = table_to_html(table)

# Generate conflict report
report = conflict_report(table)
print(report)
```

### Configuration Files

```json
{
    "grammar_file": "expr.bnf",
    "lexer": {
        "skip": "[ \\t\\n]+",
        "tokens": [
            {"name": "NUMBER", "pattern": "\\d+", "action": "int"},
            {"name": "ID", "pattern": "[A-Za-z_]+"}
        ],
        "keywords": {"if": "IF", "else": "ELSE"}
    },
    "parser": {
        "debug": false,
        "error_recovery": true,
        "sync_tokens": [";", "}"],
        "max_errors": 50
    },
    "logging": {"level": "INFO"}
}
```

```python
from lalr.config import LALRConfig

config = LALRConfig.load("parser_config.json")
config.apply_logging()
```

### JSON Table Serialization

```python
# Save table
table = LALRTable(grammar)
json_str = table.to_json_str()
with open("table.json", "w") as f:
    f.write(json_str)

# Load table
import json
with open("table.json") as f:
    data = json.loads(f.read())
restored = LALRTable.from_json(data)
parser = Parser(restored.grammar, table=restored)
```

### CLI

```bash
# Show table summary and conflicts
python -m lalr.cli examples/expr.bnf --action=table

# Check for conflicts only
python -m lalr.cli examples/classic-lalr.bnf --action=conflicts

# Compare LALR(1) vs SLR(1)
python -m lalr.cli examples/classic-lalr.bnf --action=slr-compare

# Dump full ACTION/GOTO tables
python -m lalr.cli examples/expr.bnf --action=dump -o table.txt

# Dump all states with LALR(1) lookaheads
python -m lalr.cli examples/expr.bnf --action=states

# Show FIRST and FOLLOW sets
python -m lalr.cli examples/expr.bnf --action=first-follow

# Show precedence levels
python -m lalr.cli examples/expr_prec.bnf --action=precedence

# Generate Graphviz DOT visualization
python -m lalr.cli examples/expr.bnf --action=visualize -o automaton.dot --lookaheads --horizontal

# Save/load pre-computed tables
python -m lalr.cli examples/expr.bnf --action=save-table -o table.json
python -m lalr.cli examples/expr.bnf --action=load-table --table-file=table.json --input="NUMBER + NUMBER"

# Parse an input string
python -m lalr.cli examples/expr.bnf --action=parse --input="NUMBER + NUMBER * NUMBER"

# Run with config file
python -m lalr.cli --action=config --config-file=examples/parser_config.json --input="NUMBER + NUMBER"
```

---

## Examples

| Example | Description |
|---------|-------------|
| `examples/expr.bnf` | Arithmetic expression grammar |
| `examples/expr_prec.bnf` | Ambiguous expression grammar with precedence |
| `examples/classic-lalr.bnf` | The classic LALR(1)-but-not-SLR(1) grammar |
| `examples/json.bnf` | JSON grammar definition |
| `examples/calculator.py` | Full calculator with semantic actions |
| `examples/json_parser.py` | Complete JSON parser with dict/list construction |
| `examples/lexer_demo.py` | Configurable lexer with arithmetic expressions |
| `examples/recovery_demo.py` | Error recovery with intentional syntax errors |
| `examples/transform_demo.py` | Grammar transformations (left-recursion, factoring) |
| `examples/visualize_demo.py` | Graphviz DOT and HTML table generation |
| `examples/parser_config.json` | JSON configuration file example |

### The Classic LALR(1) Grammar

The grammar `S → L=R | R`, `L → *R | id`, `R → L` is the textbook example
of a grammar that is **LALR(1) but not SLR(1)**. SLR(1) would use FOLLOW(R)
which includes `=` (from `S → L=R`), causing a shift/reduce conflict when
seeing `=` in the state with `R → L•`. LALR(1) correctly distinguishes the
contexts and reports no conflicts.

```bash
python -m lalr.cli examples/classic-lalr.bnf --action=slr-compare
# Output: "Grammar is LALR(1) but NOT SLR(1) — LALR is more powerful."
```

---

## Project Structure

```
lalr-parser-gen/
├── lalr/
│   ├── __init__.py       # Package exports
│   ├── grammar.py        # Grammar, Production, FIRST/FOLLOW/nullable
│   ├── table.py          # LR0Automaton, LALR1Builder, LALRTable (JSON)
│   ├── slr_table.py      # SLRTable for comparison
│   ├── precedence.py     # PrecedenceTable for conflict resolution
│   ├── parser.py         # Parser driver, Token, ParseError
│   ├── bnf_loader.py     # BNF grammar loader with directives
│   ├── lexer.py          # Configurable regex lexer framework
│   ├── error_recovery.py # Panic-mode error recovery
│   ├── transform.py      # Grammar transformations
│   ├── visualize.py      # Graphviz DOT, HTML tables, conflict reports
│   ├── config.py         # JSON configuration management
│   └── cli.py            # CLI (12 subcommands)
├── tests/
│   ├── test_lalr.py          # 30 core tests
│   ├── test_enhanced.py      # 16 enhanced feature tests
│   ├── test_bug_hunt.py      # 27 bug hunt tests
│   ├── test_lexer.py         # 14 lexer tests
│   ├── test_error_recovery.py # 7 recovery tests
│   ├── test_transform.py     # 16 transformation tests
│   ├── test_visualize.py     # 10 visualization tests
│   └── test_config.py        # 10 config tests
├── examples/
│   ├── expr.bnf              # Arithmetic grammar
│   ├── expr_prec.bnf         # Ambiguous grammar with precedence
│   ├── classic-lalr.bnf     # Classic non-SLR LALR grammar
│   ├── json.bnf             # JSON grammar
│   ├── calculator.py        # Calculator demo
│   ├── json_parser.py       # JSON parser demo
│   ├── lexer_demo.py        # Lexer demo
│   ├── recovery_demo.py     # Error recovery demo
│   ├── transform_demo.py    # Grammar transformation demo
│   ├── visualize_demo.py    # Visualization demo
│   └── parser_config.json   # Config file example
├── pyproject.toml        # Package metadata & install config
├── CONTRIBUTING.md       # Contributing guidelines
├── LICENSE               # MIT License
└── README.md             # This file
```

---

## Testing

```bash
# Install test dependencies
pip install -e ".[test]"

# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=lalr --cov-report=term-missing

# Run specific test file
python -m pytest tests/test_lexer.py -v
```

**130 tests** across 8 test files, all passing.

---

## Roadmap

### Planned Features

- [ ] **GLR (Generalized LR) parsing** for ambiguous grammars without precedence
- [ ] **Error productions** (yacc-style `error` pseudo-terminal in grammar rules)
- [ ] **Template-based code generation** (generate parser code in Python/C/JS)
- [ ] **LR(1) table construction** for maximum power (not just LALR)
- [ ] **Incremental parsing** for editor/IDE integration
- [ ] **Grammar equivalence checking** (is grammar A equivalent to grammar B?)
- [ ] **Conflict visualization** with interactive state diagrams
- [ ] **Multi-line comment support** in BNF loader (/* ... */)
- [ ] **Named token values** (extract sub-parts of matched tokens)
- [ ] **PEG parser** mode for ordered-choice grammars
- [ ] **Parser generator as a service** (HTTP API for table generation)
- [ ] **Grammar testing utilities** (property-based testing for grammars)

### Completed Milestones

- ✅ v1.0: Core LALR(1) table generation and parsing
- ✅ v2.0: SLR comparison, precedence/associativity, JSON serialization, BNF directives
- ✅ v2.1: Bug fixes (FIRST epsilon, SLR conflict detection, %prec directive, quote stripping)
- ✅ v3.0: Configurable lexer, error recovery, grammar transformations, visualization, config files, pyproject.toml

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style,
testing guidelines, and architecture details.

---

## Changelog

### v3.0.0 — Comprehensive Improvement

**New Modules:**
- `lexer.py` — Configurable regex-based lexer with longest-match, priorities,
  keyword/symbol helpers, line/column tracking, streaming generator, and
  builder from config dicts
- `error_recovery.py` — Panic-mode error recovery with synchronization tokens,
  multi-error collection, and configurable max-errors limit
- `transform.py` — Grammar transformations: left-recursion removal, left
  factoring (with first-symbol grouping), unreachable production removal,
  useless symbol elimination, and grammar summary
- `visualize.py` — Graphviz DOT output with lookahead display, HTML table
  export, and human-readable conflict reports with suggestions
- `config.py` — JSON configuration management for lexer, parser, logging,
  with save/load/roundtrip support and relative path resolution

**CLI Enhancements:**
- Added `visualize` action for Graphviz DOT generation
- Added `config` action for config-file-driven parsing
- Added `--lookaheads`, `--horizontal`, `--config-file` flags

**Project Infrastructure:**
- Added `pyproject.toml` with package metadata, entry point, and pytest config
- Added `CONTRIBUTING.md` with development guidelines
- Added `LICENSE` (MIT)
- Added GitHub Actions CI workflow
- Added 4 new example files: `lexer_demo.py`, `recovery_demo.py`,
  `transform_demo.py`, `visualize_demo.py`
- Added `parser_config.json` example config

**Test Suite:**
- Added 57 new tests (total: 130, all passing)
- New test files: `test_lexer.py` (14), `test_error_recovery.py` (7),
  `test_transform.py` (16), `test_visualize.py` (10), `test_config.py` (10)

**Code Quality:**
- Type hints throughout new modules
- Comprehensive docstrings on all public classes and functions
- Logging via Python `logging` module in all new modules
- Fixed left-factoring to group alternatives by first symbol
- Fixed error recovery to prevent infinite loops on end-of-input

### v2.0.0 — Enhanced

- SLR(1) table builder for comparison
- Precedence & associativity declarations (%left, %right, %nonassoc)
- BNF directives (%token, %start, %prec)
- JSON table serialization
- 16 new enhanced feature tests

### v1.0.0 — Initial Release

- Core LALR(1) parser generation via DeRemer-Pennello propagation
- Grammar with nullable, FIRST, FOLLOW computation
- LR(0) automaton construction
- Table-driven LR parser with semantic actions
- BNF grammar loader
- CLI with 10 subcommands

---

## Known Issues (Resolved)

### Bug 1: FIRST set not including epsilon for epsilon productions
**Status**: Fixed in v1.0. The `_compute_first` method skipped epsilon
productions (`body = ()`) instead of adding `EPSILON` to the FIRST set.
Added explicit handling for empty productions.

### Bug 2: SLR(1) table missing reduce→shift conflict detection
**Status**: Fixed in v2.1. The `SLRTable._set_action` method only
recorded `shift→reduce` conflicts but missed `reduce→shift` conflicts
(where the reduce action was inserted first). This meant the classic
non-SLR grammar appeared conflict-free when loaded from BNF. Added the
missing `elif existing[0] == "reduce" and action[0] == "shift"` branch
with proper conflict reporting.

### Bug 3: `%prec` directive adding fake terminal to production body
**Status**: Fixed in v2.1. The BNF loader's `_tokenize_rhs` function
did not recognize the `%prec` directive, so `%prec UMINUS` was parsed
as two additional symbols in the production body. The fix detects
`%prec TERMINAL` at the end of an alternative, strips it from the
symbol list, and stores it as a precedence override.

### Bug 4: BNF loader not stripping quotes from precedence terminals
**Status**: Fixed in v2.1. When `%left '+' '-'` was parsed, the quoted
terminal names were stored with quotes in the precedence table while
the grammar stored them without. Added quote-stripping for precedence
directive arguments.

### Bug 5: Left-factoring only worked when ALL alternatives shared a prefix
**Status**: Fixed in v3.0. The original `left_factor` function required
all alternatives of a non-terminal to share a common prefix. Fixed to
group alternatives by their first symbol and factor each group
independently.

### Bug 6: Error recovery infinite loop on end-of-input
**Status**: Fixed in v3.0. The panic-mode recovery could enter an
infinite loop when the state stack was emptied and the remaining input
was just the EOF token. Fixed by checking for `$` before reinitializing
the state stack and advancing past `$` in the recovery function.

---

## License

MIT