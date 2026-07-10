# Spreadsheet Engine

A from-scratch spreadsheet formula evaluation engine with dependency tracking and automatic recalculation.

## Overview

This project implements a fully functional spreadsheet engine in pure Python — no external dependencies. It includes:

- **Recursive-descent formula parser** with full operator precedence (comparison → concatenation → addition → multiplication → power → unary)
- **Cell references** in A1 notation (`A1`, `$B$2`, `Sheet2!C3`)
- **Range references** (`A1:B10`) — 2D ranges returned as list-of-rows for lookup functions, flat lists for single-row/col ranges
- **Cross-sheet references** (`Sheet1!A1 + Sheet2!B2`)
- **90+ built-in functions** across math, statistics, logic, text, and lookup categories
- **Dependency graph** with topological-sort-based recalculation (Kahn's algorithm)
- **Incremental recalculation** — only recalculate cells affected by changes
- **Circular reference detection** with `#CYCLE!` error reporting
- **Error propagation** (Excel-compatible: `#DIV/0!`, `#VALUE!`, `#REF!`, `#NAME?`, `#NUM!`, `#N/A`)
- **Named ranges** for reusable references
- **Formula auditing** — trace precedents and dependents
- **Multi-sheet workbooks** with named sheets, copy/clear operations
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

Tokens are produced by a regex-based tokenizer that recognizes numbers, strings, booleans, cell references (`A1`), identifiers (function/sheet names), operators, and delimiters.

### Dependency Tracking

When cells are set with formulas (`=A1+B1`), the engine extracts all cell references from the AST. A dependency graph is built where edges point from each formula cell to the cells it references. Recalculation uses **Kahn's algorithm** (topological sort) to evaluate cells in dependency order — cells with no formula dependencies first, then cells that depend on them, and so on.

### Incremental Recalculation

`recalculate_affected(changed_cells)` only recalculates cells that transitively depend on the changed cells, using the reverse dependency graph to find affected formula cells and topologically sorting only that subset.

### Cycle Detection

Cells not reachable in the topological sort (remaining with non-zero in-degree) are part of cycles. These are flagged with `#CYCLE!` errors. Additionally, a runtime eval-stack check catches cycles that might arise from dynamic references during evaluation.

### Formula Auditing

The engine provides `trace_precedents` (cells this formula reads from) and `trace_dependents` (cells that read from this cell), plus a full `audit_cell` method returning a structured audit report.

### Named Ranges

Named ranges allow defining reusable names for cells or ranges (e.g., `Revenue` → `Sheet1!A1:A10`). Names are stored case-insensitively and can be managed programmatically.

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
engine.set("S", "B2", "=AVERAGE(A1:A3)")    # 20
engine.set("S", "B3", "=MAX(A1:A3)")        # 30
engine.set("S", "B4", "=IF(A1>5, \"big\", \"small\")")  # "big"
```

### VLOOKUP and INDEX/MATCH

```python
# Build a lookup table
engine.set("S", "A1", "apple")
engine.set("S", "B1", "10")
engine.set("S", "A2", "banana")
engine.set("S", "B2", "20")
engine.set("S", "D1", '=VLOOKUP("banana", A1:B2, 2, FALSE)')  # 20
engine.set("S", "D2", "=INDEX(A1:A2, MATCH(20, B1:B2, 0))")  # "banana"
```

### Cross-Sheet References

```python
engine.add_sheet("Data")
engine.set("Data", "A1", "42")
engine.set("Summary", "B1", "=Data!A1*2")  # 84
```

### Named Ranges

```python
engine.define_name("Revenue", "Sheet1", "A1:A10")
engine.define_name("TaxRate", "Sheet1", "B1")
engine.set("Sheet1", "C1", "=SUM(Revenue) * TaxRate")
```

### Formula Auditing

```python
audit = engine.audit_cell("Budget", "B14")
print(audit["raw"])          # "=B5-B12"
print(audit["value"])        # computed value
print(audit["precedents"])   # cells B14 depends on
print(audit["dependents"])   # cells that depend on B14
```

### Incremental Recalculation

```python
engine.set("S", "A1", "20")  # change a value
stats = engine.recalculate_affected([("S", 0, 0)])  # only recalc affected cells
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

## Built-in Functions (90+)

### Math
`SUM`, `AVERAGE`, `PRODUCT`, `ABS`, `SQRT`, `POWER`, `EXP`, `LN`, `LOG`, `SIN`, `COS`, `TAN`, `ASIN`, `ACOS`, `ATAN`, `ATAN2`, `ROUND`, `FLOOR`, `CEILING`, `MOD`, `PI`, `RAND`, `MAX`, `MIN`, `SIGN`, `GCD`, `LCM`, `FACT`, `DEGREES`, `RADIANS`, `INT`, `TRUNC`

### Statistics
`COUNT`, `COUNTA`, `STDEV`, `VAR`, `MEDIAN`, `STDEVP`, `VARP`, `MODE`, `RANK`, `PERCENTILE`, `QUARTILE`, `CORREL`, `SLOPE`

### Logic
`IF`, `AND`, `OR`, `NOT`, `TRUE`, `FALSE`, `ISERROR`, `ISNUMBER`, `ISTEXT`, `ISBLANK`, `IFERROR`, `NA`, `CHOOSE`

### Text
`LEN`, `UPPER`, `LOWER`, `TRIM`, `CONCAT`, `CONCATENATE`, `LEFT`, `RIGHT`, `MID`, `REPLACE`, `SUBSTITUTE`, `VALUE`, `TEXT`, `FIND`, `PROPER`, `REPT`, `SEARCH`, `EXACT`, `TEXTJOIN`, `CODE`, `CHAR`

### Lookup
`VLOOKUP`, `HLOOKUP`, `MATCH`, `INDEX`

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

## Known Issues (Resolved)

The following bugs were identified during the Phase 3 bug hunt and have been fixed:

1. **Empty cell in string concatenation produced "0" instead of ""** — `_resolve_ref` returned `0.0` for empty cells, causing `=A1 & "hello"` to produce `"0hello"` when A1 was empty. Fixed by returning `None` for empty cells, which `_coerce_num` treats as `0.0` for arithmetic and `_to_str_val` treats as `""` for concatenation.

2. **Mixed-type comparison crashed with TypeError** — Comparing a string with a number (e.g., `="5" > 3`) raised a Python `TypeError` caught as `#VALUE!`. Fixed by implementing Excel-compatible type ranking (boolean > string > number) in `_apply_comparison`, so cross-type comparisons return a boolean result without crashing.

3. **Boolean vs number comparison used Python semantics instead of Excel** — `TRUE > 5` returned `False` (Python treats `True` as `1`), but Excel considers booleans always greater than numbers. Fixed by the type-ranking system above.

4. **ROUND with negative digits worked correctly** — Verified that `=ROUND(1234, -2)` correctly returns `1200` via the `math.floor/factor` approach.

5. **Reverse ranges (B3:A1) handled correctly** — The range normalization (`min/max` of coordinates) ensures reversed ranges work properly. Verified with `=SUM(A3:A1)`.

6. **Error propagation in SUM verified** — SUM correctly propagates `#DIV/0!` errors from referenced cells instead of silently ignoring them.

7. **Error propagation in IF verified** — IF correctly propagates errors from the condition argument.

8. **COUNT ignores error values** — COUNT correctly counts only numeric values, not error cells.

9. **PRODUCT ignores non-numeric values** — `=PRODUCT(A1:A3)` with a string in the range correctly ignores it and returns the product of numbers.

10. **AVERAGE of empty range returns #DIV/0!** — Verified that AVERAGE with no numeric values raises the correct error.

11. **Negative number parsing** — Both literal `-42` and formula `=-42` parse correctly, including scientific notation like `-1.5e-3`.

12. **String escaping in formulas** — Escaped quotes (`\"`) and backslashes (`\\`) in string literals parse and evaluate correctly.

13. **MOD by zero returns #DIV/0!** — Verified that `=MOD(10, 0)` returns the correct error type.

14. **Unary minus on non-numeric string returns #VALUE!** — `=-"hello"` correctly returns a VALUE error instead of crashing.

15. **Function argument count validation** — Functions like ABS and SQRT correctly return errors when called with no arguments.

16. **Recalculate idempotency** — Calling `recalculate()` multiple times produces consistent results.

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