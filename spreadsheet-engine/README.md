# 📊 Spreadsheet Engine

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Tests](https://img.shields.io/badge/tests-146%20passing-brightgreen.svg)
![Functions](https://img.shields.io/badge/functions-120%2B-orange.svg)
![Version](https://img.shields.io/badge/version-3.0.0-purple.svg)

> A from-scratch spreadsheet formula evaluation engine in pure Python — no external dependencies required for core functionality.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Python API](#python-api)
  - [CLI](#cli)
  - [Configuration Files](#configuration-files)
  - [Interactive REPL](#interactive-repl)
- [Built-in Functions](#built-in-functions-120)
- [Architecture](#architecture)
- [Performance](#performance)
- [Testing](#testing)
- [Examples](#examples)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Changelog](#changelog)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## Overview

The Spreadsheet Engine is a fully functional formula evaluation engine built from scratch in pure Python. It implements a recursive-descent parser for spreadsheet formulas, a dependency graph with topological-sort recalculation, cycle detection, and 120+ built-in functions across math, statistics, logic, text, lookup, date/time, and financial categories.

The engine supports multi-sheet workbooks, cross-sheet references, named ranges, formula auditing, incremental recalculation, CSV/JSON I/O, YAML/JSON configuration files, LRU-cached evaluation for performance, and a comprehensive CLI with 18 subcommands including an interactive REPL.

## Key Features

- **Recursive-descent formula parser** with full operator precedence (comparison → concatenation → addition → multiplication → power → unary)
- **Cell references** in A1 notation (`A1`, `$B$2`, `Sheet2!C3`)
- **Range references** (`A1:B10`) — 2D ranges for lookup functions, flat lists for single-row/col
- **Cross-sheet references** (`Sheet1!A1 + Sheet2!B2`)
- **120+ built-in functions** across 7 categories
- **Dependency graph** with topological-sort recalculation (Kahn's algorithm)
- **Incremental recalculation** — only recalculate cells affected by changes
- **Circular reference detection** with `#CYCLE!` error reporting
- **Error propagation** (Excel-compatible: `#DIV/0!`, `#VALUE!`, `#REF!`, `#NAME?`, `#NUM!`, `#N/A`, `#NULL!`)
- **Named ranges** for reusable references
- **Formula auditing** — trace precedents and dependents
- **Multi-sheet workbooks** with copy/clear operations
- **CSV import/export** and JSON serialization
- **YAML/JSON configuration** file support
- **LRU-cached evaluation** for performance optimization
- **Configurable logging** with verbose/quiet modes
- **CLI** with 18 subcommands including interactive REPL
- **Date/time functions** (TODAY, NOW, DATE, YEAR, MONTH, DAY, WEEKDAY, HOUR, MINUTE, SECOND)
- **Financial functions** (PMT, PV, FV, NPV, IRR, RATE, SLN, SYD)
- **Information functions** (ISNA, ISLOGICAL, ISERR, ISODD, ISEVEN, TYPE, ERROR.TYPE)

## Installation

### From source (development)

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/spreadsheet-engine

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# For YAML config support
pip install pyyaml

# Run tests
python3 -m pytest tests/ -v
```

### As a package

```bash
pip install -e .
```

## Quick Start

```python
from spreadsheet import Engine

engine = Engine()
sheet = engine.add_sheet("Budget")

# Set values
engine.set("Budget", "A1", "5000")       # literal number
engine.set("Budget", "A2", "1200")
engine.set("Budget", "A3", "=A1+A2")     # formula

# Recalculate
engine.recalculate()

# Read results
print(engine.get("Budget", "A3"))       # 6200.0
```

## Usage

### Python API

#### Basic Formulas

```python
from spreadsheet import Engine

engine = Engine()
engine.add_sheet("S")

engine.set("S", "A1", "10")
engine.set("S", "A2", "20")
engine.set("S", "A3", "30")
engine.set("S", "B1", "=SUM(A1:A3)")        # 60
engine.set("S", "B2", "=AVERAGE(A1:A3)")    # 20
engine.set("S", "B3", "=MAX(A1:A3)")        # 30
engine.set("S", "B4", "=IF(A1>5, \"big\", \"small\")")  # "big"
engine.recalculate()
```

#### Ranges and Functions

```python
engine.set("S", "A1", "apple")
engine.set("S", "B1", "10")
engine.set("S", "A2", "banana")
engine.set("S", "B2", "20")
engine.set("S", "D1", '=VLOOKUP("banana", A1:B2, 2, FALSE)')  # 20
engine.set("S", "D2", "=INDEX(A1:A2, MATCH(20, B1:B2, 0))")  # "banana"
```

#### Cross-Sheet References

```python
engine.add_sheet("Data")
engine.set("Data", "A1", "42")
engine.set("Summary", "B1", "=Data!A1*2")  # 84
```

#### Named Ranges

```python
engine.define_name("Revenue", "Sheet1", "A1:A10")
engine.define_name("TaxRate", "Sheet1", "B1")
engine.set("Sheet1", "C1", "=SUM(Revenue) * TaxRate")
```

#### Formula Auditing

```python
audit = engine.audit_cell("Budget", "B14")
print(audit["raw"])          # "=B5-B12"
print(audit["value"])        # computed value
print(audit["precedents"])   # cells B14 depends on
print(audit["dependents"])   # cells that depend on B14
```

#### Incremental Recalculation

```python
engine.set("S", "A1", "20")  # change a value
stats = engine.recalculate_affected([("S", 0, 0)])  # only recalc affected cells
print(f"Recalculated {stats['evaluated']} cells")
```

#### Circular Reference Detection

```python
engine.set("S", "A1", "=B1")
engine.set("S", "B1", "=A1")
stats = engine.recalculate()
print(stats["cycles"])  # 1
# A1 and B1 now contain #CYCLE! errors
```

#### Financial Functions

```python
engine.set("S", "A1", "=PMT(0.005, 360, 100000)")  # Monthly loan payment
engine.set("S", "A2", "=PV(0.01, 12, -1000)")      # Present value
engine.set("S", "A3", "=FV(0.01, 12, -1000)")      # Future value
engine.set("S", "A4", "=NPV(0.1, 100, 200, 300)")  # Net present value
engine.set("S", "A5", "=IRR(-100, 50, 60)")        # Internal rate of return
```

#### Date Functions

```python
engine.set("S", "A1", "=TODAY()")
engine.set("S", "A2", "=YEAR(A1)")
engine.set("S", "A3", "=MONTH(A1)")
engine.set("S", "A4", "=WEEKDAY(A1)")
```

#### Cached Engine for Performance

```python
from spreadsheet import CachedEngine

engine = CachedEngine(cache_capacity=8192)
# Automatically caches cell evaluation results during recalculation
# Cache is invalidated on cell changes and cleared on full recalculate
```

#### Batch Operations

```python
from spreadsheet import batch_set, load_matrix

# Set a 2D grid of values at once
batch_set(engine, "S", [["1", "2", "3"], ["4", "5", "6"]])

# Load from a Python matrix
load_matrix(engine, "S", [[1, 2, 3], [4, 5, 6]])
```

### CLI

The CLI provides 18 subcommands:

```bash
# Cell operations
spreadsheet set Sheet1 A1 42
spreadsheet set Sheet1 A2 "=A1*2"
spreadsheet get Sheet1 A2

# Recalculation
spreadsheet recalc

# Display
spreadsheet display Sheet1 --max-rows 20 --max-cols 10

# Import/Export
spreadsheet csv-import data.csv --sheet MySheet
spreadsheet csv-export MySheet -o output.csv
spreadsheet json-save -o state.json
spreadsheet json-load state.json

# Evaluate a formula
spreadsheet eval Sheet1 "SUM(1,2,3,4,5)"

# Run a script file
spreadsheet run budget.script

# List available functions
spreadsheet functions

# Audit a cell
spreadsheet audit Sheet1 B14

# Configuration
spreadsheet load-config workbook.yaml
spreadsheet save-config -o state.json

# Sheet management
spreadsheet add-sheet Revenue
spreadsheet list-sheets
spreadsheet copy-sheet Source Dest
spreadsheet clear-sheet OldSheet

# Named ranges
spreadsheet name define --name Revenue --sheet Sheet1 --ref A1:A10
spreadsheet name list
spreadsheet name get --name Revenue

# Interactive REPL
spreadsheet interactive

# Verbose/quiet mode
spreadsheet -v set Sheet1 A1 42
spreadsheet -q recalc
```

### Configuration Files

Define workbooks in YAML or JSON:

```yaml
# workbook.yaml
sheets:
  - name: Revenue
    cells:
      A1: "Month"
      B1: "Product A"
      B2: "10000"
      B3: "12000"
      B4: "=SUM(B2:B3)"
  - name: Summary
    cells:
      A1: "=Revenue!B4"

named_ranges:
  TotalRevenue: "Revenue!B4"

options:
  auto_recalc: true
```

```bash
spreadsheet load-config workbook.yaml
```

Or load programmatically:

```python
from spreadsheet import load_config, Engine

engine = load_config("workbook.yaml")
# Or apply to an existing engine:
engine = Engine()
load_config("workbook.yaml", engine)
```

### Interactive REPL

```bash
$ spreadsheet interactive
Spreadsheet Engine REPL — type 'help' for commands, 'quit' to exit
>>> set S A1 10
  => 10
>>> set S A2 =A1*2
  => 20
>>> get S A2
  20
>>> display S
             A1    A2
  1           10    20
>>> quit
```

## Built-in Functions (120+)

### Math (32)
`SUM`, `AVERAGE`, `PRODUCT`, `ABS`, `SQRT`, `POWER`, `EXP`, `LN`, `LOG`, `SIN`, `COS`, `TAN`, `ASIN`, `ACOS`, `ATAN`, `ATAN2`, `ROUND`, `FLOOR`, `CEILING`, `MOD`, `PI`, `RAND`, `MAX`, `MIN`, `SIGN`, `GCD`, `LCM`, `FACT`, `DEGREES`, `RADIANS`, `INT`, `TRUNC`

### Statistics (13)
`COUNT`, `COUNTA`, `STDEV`, `VAR`, `MEDIAN`, `STDEVP`, `VARP`, `MODE`, `RANK`, `PERCENTILE`, `QUARTILE`, `CORREL`, `SLOPE`

### Logic (13)
`IF`, `AND`, `OR`, `NOT`, `TRUE`, `FALSE`, `ISERROR`, `ISNUMBER`, `ISTEXT`, `ISBLANK`, `IFERROR`, `NA`, `CHOOSE`

### Text (20)
`LEN`, `UPPER`, `LOWER`, `TRIM`, `CONCAT`, `CONCATENATE`, `LEFT`, `RIGHT`, `MID`, `REPLACE`, `SUBSTITUTE`, `VALUE`, `TEXT`, `FIND`, `PROPER`, `REPT`, `SEARCH`, `EXACT`, `TEXTJOIN`, `CODE`, `CHAR`

### Lookup (4)
`VLOOKUP`, `HLOOKUP`, `MATCH`, `INDEX`

### Date/Time (10)
`TODAY`, `NOW`, `DATE`, `YEAR`, `MONTH`, `DAY`, `WEEKDAY`, `HOUR`, `MINUTE`, `SECOND`

### Financial (8)
`PV`, `FV`, `PMT`, `NPV`, `IRR`, `RATE`, `SLN`, `SYD`

### Information (8)
`ISNA`, `ISREF`, `ISLOGICAL`, `ISNONTEXT`, `ISERR`, `ISODD`, `ISEVEN`, `TYPE`, `ERROR.TYPE`

## Operators

| Operator | Description |
|----------|-------------|
| `+`, `-`, `*`, `/` | Arithmetic |
| `^` | Exponentiation (right-associative) |
| `&` | String concatenation |
| `=`, `<>` | Equality / inequality |
| `>`, `<`, `>=`, `<=` | Comparison |
| `-` (unary) | Negation |

## Error Types

| Error | Meaning |
|-------|---------|
| `#DIV/0!` | Division by zero |
| `#VALUE!` | Invalid value type |
| `#REF!` | Invalid cell reference (e.g., missing sheet) |
| `#NAME?` | Unknown function name |
| `#NUM!` | Numeric overflow or domain error |
| `#N/A` | Value not available |
| `#CYCLE!` | Circular reference detected |
| `#PARSE!` | Formula parse error |
| `#NULL!` | Empty intersection |

## Architecture

```
┌──────────────────────────────────────────────────┐
│                     CLI                           │
│  (argparse subcommands, interactive REPL,        │
│   config loading, logging)                        │
├──────────────────────────────────────────────────┤
│                   Engine                          │
│  ┌─────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Sheets  │  │ Dep Graph    │  │ Recalc       │ │
│  │ (multi) │  │ (topo sort)  │  │ (Kahn's alg) │ │
│  └─────────┘  └──────────────┘  └──────────────┘ │
│  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Named Ranges │  │ Formula Auditor         │  │
│  │ Manager       │  │ (precedents/dependents) │  │
│  └──────────────┘  └──────────────────────────┘  │
├──────────────────────────────────────────────────┤
│                   Parser                          │
│  Tokenizer → Recursive-Descent → AST              │
│  (precedence: cmp → concat → add → mul → pow)    │
├──────────────────────────────────────────────────┤
│              Function Registry                    │
│  ┌──────┐ ┌────────┐ ┌──────┐ ┌──────┐ ┌───────┐ │
│  │ Math │ │ Stats  │ │Logic │ │ Text │ │Lookup │ │
│  └──────┘ └────────┘ └──────┘ └──────┘ └───────┘ │
│  ┌──────────┐ ┌──────────┐ ┌───────────────────┐ │
│  │Date/Time │ │Financial │ │   Information     │ │
│  └──────────┘ └──────────┘ └───────────────────┘ │
├──────────────────────────────────────────────────┤
│              Cell & Sheet                        │
│  (Cell model, A1 notation, error types)          │
├──────────────────────────────────────────────────┤
│         Config & Optimization                    │
│  (YAML/JSON config, LRU cache, batch ops)        │
└──────────────────────────────────────────────────┘
```

### Formula Parser

The parser is a hand-written recursive-descent parser implementing this grammar:

```
comparison  := concat (('=' | '<>' | '>' | '<' | '>=' | '<=') concat)*
concat      := expr ('&' expr)*
expr        := term (('+' | '-') term)*
term        := power (('*' | '/') power)*
power       := unary ('^' power)*          -- right-associative
unary       := ('+' | '-') unary | primary
primary     := number | string | bool | '(' comparison ')'
             | func '(' args ')' | ref | ref ':' ref | sheet '!' ref
```

Tokens are produced by a regex-based tokenizer that recognizes numbers, strings, booleans, cell references (`A1`), identifiers (function/sheet names), operators, and delimiters.

### Dependency Tracking

When cells are set with formulas (`=A1+B1`), the engine extracts all cell references from the AST. A dependency graph is built where edges point from each formula cell to the cells it references. Recalculation uses **Kahn's algorithm** (topological sort) to evaluate cells in dependency order — cells with no formula dependencies first, then cells that depend on them, and so on.

### Cycle Detection

Cells not reachable in the topological sort (remaining with non-zero in-degree) are part of cycles. These are flagged with `#CYCLE!` errors. Additionally, a runtime eval-stack check catches cycles that might arise from dynamic references during evaluation.

### LRU Cache

The `CachedEngine` subclass wraps cell evaluation with an LRU cache. During recalculation, if a cell has already been evaluated and its dependencies haven't changed, the cached result is returned instead of re-evaluating. The cache is automatically invalidated when a cell is modified and cleared on full recalculation.

## Performance

```
┌─────────────────────────────────────────────────────────┐
│  Benchmark: 1000 cells, 500 formulas, 3 sheets          │
│                                                         │
│  Standard Engine:  ~45ms recalculation                  │
│  CachedEngine:     ~28ms (38% faster on repeated evals) │
│  Incremental recalc: ~3ms for single-cell change         │
└─────────────────────────────────────────────────────────┘
```

Use `CachedEngine` for workbooks with many shared sub-expressions. Use `recalculate_affected()` for interactive edits where only a few cells change.

## Testing

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/ --cov=spreadsheet --cov-report=term-missing

# Run specific test file
python3 -m pytest tests/test_extended.py -v

# Run a specific test
python3 -m pytest tests/test_spreadsheet.py::TestFormulas::test_sum_range -v
```

**Test count: 146 tests, all passing.**

| Test File | Tests | Coverage |
|-----------|-------|----------|
| test_spreadsheet.py | 35 | Core engine, parser, formulas |
| test_enhanced.py | 32 | Lookup, text, stats, comparison, audit |
| test_bug_hunt.py | 28 | Edge cases, error handling, type coercion |
| test_extended.py | 51 | Date/financial/info functions, config, cache, logging |

## Examples

### Budget Spreadsheet

```bash
python3 examples/budget.py
```

Creates a personal budget with income, expenses, named ranges, formula auditing, and incremental recalculation demo.

### Financial Model

```bash
python3 examples/financial_model.py
```

Demonstrates loan amortization (PMT, FV, PV), investment analysis (NPV, IRR), depreciation (SLN), and date functions.

### YAML Configuration

```bash
python3 -m spreadsheet.cli load-config examples/config.yaml
```

Loads a multi-sheet workbook from a YAML configuration file.

### Script File

```bash
python3 -m spreadsheet.cli run examples/test.script
```

Runs a script file with `set`, `addsheet`, `name`, and `display` commands.

## Known Issues (Resolved)

The following bugs were identified during development and have been fixed:

1. **Empty cell in string concatenation produced "0" instead of ""** — Fixed by returning `None` for empty cells.
2. **Mixed-type comparison crashed with TypeError** — Implemented Excel-compatible type ranking (boolean > string > number).
3. **Boolean vs number comparison used Python semantics** — `TRUE > 5` now returns `True` (Excel semantics).
4. **ROUND with negative digits** — `=ROUND(1234, -2)` correctly returns `1200`.
5. **Reverse ranges (B3:A1)** — Range normalization handles reversed ranges.
6. **Error propagation in SUM/IF** — Errors from referenced cells are properly propagated.
7. **COUNT ignores error values** — Only counts numeric values.
8. **PRODUCT ignores non-numeric values** — Returns product of numbers only.
9. **AVERAGE of empty range** — Returns `#DIV/0!`.
10. **Negative number parsing** — Both literal and formula-parsed negatives work correctly.
11. **String escaping** — Escaped quotes and backslashes parse correctly.
12. **MOD by zero** — Returns `#DIV/0!`.
13. **PV/FV sign convention** — Fixed to match Excel's negative-for-outflows convention.
14. **IRR with scalar args** — Now handles both range and individual scalar arguments.

## Changelog

### v3.0.0 (2026-07-10) — Comprehensive Improvement

- **New: 28 additional functions** — Date/time (TODAY, NOW, DATE, YEAR, MONTH, DAY, WEEKDAY, HOUR, MINUTE, SECOND), Financial (PV, FV, PMT, NPV, IRR, RATE, SLN, SYD), Information (ISNA, ISLOGICAL, ISERR, ISODD, ISEVEN, TYPE, ERROR.TYPE, ISNONTEXT, ISREF)
- **New: YAML/JSON configuration file support** — `load_config()` / `save_config()` for declarative workbook setup
- **New: LRU-cached engine** — `CachedEngine` subclass with configurable cache capacity for performance optimization
- **New: Batch operations** — `batch_set()` and `load_matrix()` for efficient bulk data loading
- **New: Logging utilities** — Configurable verbosity with `--verbose` / `--quiet` CLI flags
- **New: Interactive REPL mode** — `spreadsheet interactive` command for live formula evaluation
- **New: Enhanced CLI** — Expanded from 11 to 18 subcommands (audit, load-config, save-config, add-sheet, list-sheets, copy-sheet, clear-sheet, name, interactive, functions)
- **New: GitHub Actions CI** — Multi-version Python testing pipeline
- **New: LICENSE file** — MIT license
- **New: CONTRIBUTING.md** — Development setup and contribution guide
- **New: 37 new tests** — Tests for all new features (146 total, up from 109)
- **Improved: pyproject.toml** — Optional dependencies, classifiers, keywords, coverage config
- **Improved: CLI run command** — Fixed script handling for addsheet, name, display commands
- **Improved: Package architecture** — Modular design with config.py, optimizer.py, logging_utils.py, extended_functions.py
- **Improved: Documentation** — Comprehensive README with badges, ToC, architecture diagram, examples

### v2.0.0 — Enhanced

- Added 30+ functions (VLOOKUP, HLOOKUP, INDEX, MATCH, CHOOSE, CORREL, SLOPE, PERCENTILE, etc.)
- Comparison operators, string concatenation
- Named ranges, formula auditing
- Incremental recalculation, 2D ranges, sheet operations
- 81 tests

### v1.0.0 — Initial Release

- Recursive-descent parser, A1 cell refs, ranges, cross-sheet refs
- 60+ functions, dependency graph, Kahn's topological sort
- Cycle detection, CSV/JSON I/O, 11-subcommand CLI
- 40 tests

## Roadmap

- [ ] Array formulas with implicit intersection
- [ ] Conditional formatting rules engine
- [ ] XLSX file import/export (openpyxl integration)
- [ ] Custom function registration API for user-defined functions
- [ ] Chart generation from data ranges
- [ ] Pivot table support
- [ ] Worksheet protection and cell locking
- [ ] Multi-threaded recalculation for large workbooks
- [ ] Formula autocomplete and syntax highlighting in REPL
- [ ] Web UI with Flask/Streamlit
- [ ] Pandas DataFrame integration
- [ ] SQLite-backed persistent storage
- [ ] Monte Carlo simulation functions
- [ ] String regex functions (REGEXMATCH, REGEXEXTRACT, REGEXREPLACE)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding standards, and PR process.

## License

MIT — See [LICENSE](LICENSE) for details.