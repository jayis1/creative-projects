# Spreadsheet Engine

A from-scratch spreadsheet formula evaluation engine with dependency tracking and automatic recalculation.

## Overview

This project implements a fully functional spreadsheet engine in pure Python — no external dependencies. It includes:

- **Recursive-descent formula parser** with full operator precedence (comparison → concatenation → addition → multiplication → power → unary)
- **Cell references** in A1 notation (`A1`, `$B$2`, `Sheet2!C3`)
- **Range references** (`A1:B10`) expanded to cell lists for aggregate functions
- **Cross-sheet references** (`Sheet1!A1 + Sheet2!B2`)
- **60+ built-in functions** across math, statistics, logic, text, and lookup categories
- **Dependency graph** with topological-sort-based recalculation (Kahn's algorithm)
- **Circular reference detection** with `#CYCLE!` error reporting
- **Error propagation** (Excel-compatible: `#DIV/0!`, `#VALUE!`, `#REF!`, `#NAME?`, `#NUM!`, `#N/A`)
- **Multi-sheet workbooks** with named sheets
- **CSV import/export** and JSON serialization
- **CLI** with 11 subcommands

## How It Works

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

Tokens are produced by a regex-based tokenizer that recognizes numbers, strings, booleans, cell references (`A1`), identifiers (function names), operators, and delimiters.

### Dependency Tracking

When cells are set with formulas (`=A1+B1`), the engine extracts all cell references from the AST. A dependency graph is built where edges point from each formula cell to the cells it references. Recalculation uses **Kahn's algorithm** (topological sort) to evaluate cells in dependency order — cells with no formula dependencies first, then cells that depend on them, and so on.

### Cycle Detection

Cells not reachable in the topological sort (remaining with non-zero in-degree) are part of cycles. These are flagged with `#CYCLE!` errors. Additionally, a runtime eval-stack check catches cycles that might arise from dynamic references during evaluation.

## Usage

### Python API

```python
from spreadsheet import Engine

engine = Engine()
sheet = engine.add_sheet("Budget")

# Set values
engine.set("Budget", "A1", "5000")       # literal number
engine.set("Budget", "A2", "1200")
engine.set("Budget", "A3", "=A1+A2")     # formula

# Recalculate all sheets
engine.recalculate()

# Read results
print(engine.get("Budget", "A3"))       # 6200.0
```

### Ranges and Functions

```python
engine.set("S", "A1", "10")
engine.set("S", "A2", "20")
engine.set("S", "A3", "30")
engine.set("S", "B1", "=SUM(A1:A3)")        # 60
engine.set("S", "B2", "=AVERAGE(A1:A3)")   # 20
engine.set("S", "B3", "=MAX(A1:A3)")       # 30
engine.set("S", "B4", "=IF(A1>5, \"big\", \"small\")")  # "big"
```

### Cross-Sheet References

```python
engine.add_sheet("Data")
engine.set("Data", "A1", "42")
engine.set("Summary", "B1", "=Data!A1*2")  # 84
```

### Circular Reference Detection

```python
engine.set("S", "A1", "=B1")
engine.set("S", "B1", "=A1")
stats = engine.recalculate()
print(stats["cycles"])  # 1
# A1 and B1 now contain #CYCLE! errors
```

### CLI

```bash
# Evaluate a formula
spreadsheet eval Sheet1 "SUM(1,2,3,4,5)"

# Run a script file
spreadsheet run budget.script

# Import/export CSV
spreadsheet csv-import data.csv --sheet MySheet
spreadsheet csv-export MySheet -o output.csv

# Save/load as JSON
spreadsheet json-save -o state.json
spreadsheet json-load state.json
```

## Built-in Functions

### Math
`SUM`, `AVERAGE`, `PRODUCT`, `ABS`, `SQRT`, `POWER`, `EXP`, `LN`, `LOG`, `SIN`, `COS`, `TAN`, `ASIN`, `ACOS`, `ATAN`, `ATAN2`, `ROUND`, `FLOOR`, `CEILING`, `MOD`, `PI`, `RAND`, `MAX`, `MIN`

### Statistics
`COUNT`, `COUNTA`, `STDEV`, `VAR`, `MEDIAN`

### Logic
`IF`, `AND`, `OR`, `NOT`, `TRUE`, `FALSE`, `ISERROR`, `ISNUMBER`, `ISTEXT`, `ISBLANK`

### Text
`LEN`, `UPPER`, `LOWER`, `TRIM`, `CONCAT`, `CONCATENATE`, `LEFT`, `RIGHT`, `MID`, `REPLACE`, `SUBSTITUTE`, `VALUE`, `TEXT`, `FIND`

### Lookup/Error
`IFERROR`, `NA`

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

## Installation

```bash
pip install -e .
```

## Testing

```bash
python3 -m pytest tests/ -v
```

## License

MIT