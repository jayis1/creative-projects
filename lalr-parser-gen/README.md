# lalr-parser-gen

A from-scratch LALR(1) parser generator written in pure Python (no dependencies).

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
- **JSON table serialization** for saving/loading pre-computed parse tables
- **CLI** with 10 subcommands for table inspection, conflict analysis, SLR comparison, and parsing

LALR(1) is more powerful than SLR(1) (it handles grammars where SLR would
report spurious conflicts) while producing tables as compact as LR(0).

## How It Works

### 1. Grammar → LR(0) Automaton

The grammar is augmented with `S' → S$`. The LR(0) automaton is built by
computing the **closure** and **goto** of item sets:

- **Closure**: For each item `A → α•Bβ`, add all items `B → •γ`.
- **GOTO**: For each symbol `X`, advance all items with `•X` and take closure.

### 2. LALR(1) Lookahead Propagation

LALR(1) lookaheads are computed using the DeRemer-Pennello algorithm:

1. **Spontaneous generation**: For item `A → α•Bβ` with lookahead `la`,
   the item `B → •γ` gets `FIRST(β la)` as spontaneous lookaheads.
2. **Propagation**: Lookaheads flow from `A → α•Bβ` to:
   - `A → αB•β` in the GOTO state (kernel item propagation)
   - `B → •γ` in the same state (when `β` is nullable)

The propagation iterates to a fixed point until no new lookaheads appear.

### 3. Table Construction

For each state:
- **Shift**: If `A → α•aβ` with lookahead `a`, set `ACTION[s, a] = shift`.
- **Reduce**: If `A → α•` with lookahead `a`, set `ACTION[s, a] = reduce(A → α)`.
- **Accept**: If `S' → S•` with `$`, set `ACTION[s, $] = accept`.
- **Goto**: If `A → α•Bβ` and `GOTO[s, B] = s'`, set `GOTO[s, B] = s'`.

Conflicts (shift/reduce, reduce/reduce) are detected and reported. When
precedence declarations are available, shift/reduce conflicts are resolved
automatically using yacc-style rules.

### 4. Precedence & Associativity

Precedence levels are declared with `%left`, `%right`, and `%nonassoc`:
- Higher levels bind tighter
- A production's precedence = precedence of its rightmost terminal
- On a shift/reduce conflict:
  - Terminal prec > production prec → shift
  - Terminal prec < production prec → reduce
  - Equal: left → reduce, right → shift, nonassoc → error

### 5. SLR(1) Comparison

The SLR(1) builder uses FOLLOW sets for reduce lookaheads. Running
`--action=slr-compare` shows whether a grammar is LALR(1)-only or both
LALR(1) and SLR(1), making it an excellent educational tool.

## Usage

### Programmatic API

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

### BNF Grammar Files with Precedence

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

# Save/load pre-computed tables
python -m lalr.cli examples/expr.bnf --action=save-table -o table.json
python -m lalr.cli examples/expr.bnf --action=load-table --table-file=table.json --input="NUMBER + NUMBER"

# Parse an input string
python -m lalr.cli examples/expr.bnf --action=parse --input="NUMBER + NUMBER * NUMBER"
```

## Examples

- `examples/expr.bnf` — Arithmetic expression grammar
- `examples/expr_prec.bnf` — Ambiguous expression grammar with precedence
- `examples/classic-lalr.bnf` — The classic LALR(1)-but-not-SLR(1) grammar
- `examples/json.bnf` — JSON grammar definition
- `examples/calculator.py` — Full calculator with semantic actions
- `examples/json_parser.py` — Complete JSON parser with dict/list construction

## The Classic LALR(1) Grammar

The grammar `S → L=R | R`, `L → *R | id`, `R → L` is the textbook example
of a grammar that is **LALR(1) but not SLR(1)**. SLR(1) would use FOLLOW(R)
which includes `=` (from `S → L=R`), causing a shift/reduce conflict when
seeing `=` in the state with `R → L•`. LALR(1) correctly distinguishes the
contexts and reports no conflicts.

Run the comparison:
```bash
python -m lalr.cli examples/classic-lalr.bnf --action=slr-compare
# Output: "Grammar is LALR(1) but NOT SLR(1) — LALR is more powerful."
```

## Project Structure

```
lalr-parser-gen/
├── lalr/
│   ├── __init__.py       # Package exports
│   ├── grammar.py        # Grammar, Production, FIRST/FOLLOW/nullable
│   ├── table.py          # LR0Automaton, LALR1Builder, LALRTable (with JSON serialization)
│   ├── slr_table.py      # SLRTable for comparison
│   ├── precedence.py     # PrecedenceTable for conflict resolution
│   ├── parser.py         # Parser driver, Token, ParseError
│   ├── bnf_loader.py     # BNF grammar loader with precedence directives
│   └── cli.py            # Command-line interface (10 subcommands)
├── tests/
│   ├── test_lalr.py      # 30 core tests
│   └── test_enhanced.py  # 16 enhanced feature tests
├── examples/
│   ├── expr.bnf          # Arithmetic grammar
│   ├── expr_prec.bnf     # Ambiguous grammar with precedence
│   ├── classic-lalr.bnf  # Classic non-SLR LALR grammar
│   ├── json.bnf          # JSON grammar
│   ├── calculator.py     # Calculator demo
│   └── json_parser.py    # JSON parser demo
└── README.md
```

## Testing

```bash
PYTHONPATH=. python -m pytest tests/ -v
# 73 tests, all passing
```

## Known Issues (Resolved)

### Bug 1: FIRST set not including epsilon for epsilon productions
**Status**: Fixed in Phase 1. The `_compute_first` method skipped epsilon
productions (`body = ()`) instead of adding `EPSILON` to the FIRST set.
Added explicit handling for empty productions.

### Bug 2: SLR(1) table missing reduce→shift conflict detection
**Status**: Fixed in Phase 3. The `SLRTable._set_action` method only
recorded `shift→reduce` conflicts but missed `reduce→shift` conflicts
(where the reduce action was inserted first). This meant the classic
non-SLR grammar appeared conflict-free when loaded from BNF. Added the
missing `elif existing[0] == "reduce" and action[0] == "shift"` branch
with proper conflict reporting.

### Bug 3: `%prec` directive adding fake terminal to production body
**Status**: Fixed in Phase 3. The BNF loader's `_tokenize_rhs` function
did not recognize the `%prec` directive, so `%prec UMINUS` was parsed
as two additional symbols (`%prec` and `UMINUS`) in the production body.
This caused `UMINUS` to appear as a spurious terminal in the grammar
and corrupted the production structure. The fix:
- `_tokenize_rhs` now detects `%prec TERMINAL` at the end of a production
  alternative, strips it from the symbol list, and returns the override
  terminal name separately.
- `load_bnf_full` stores the override in a `prec_overrides` dict.
- `PrecedenceTable` gained `add_production_override()` and
  `production_precedence()` now checks overrides before falling back to
  the rightmost-terminal rule.
- BNF precedence directives (`%left`, `%right`, `%nonassoc`) now strip
  quotes from terminal names (e.g. `'+'` → `+`).

### Bug 4: BNF loader not stripping quotes from precedence terminals
**Status**: Fixed in Phase 3. When `%left '+' '-'` was parsed, the
quoted terminal names were stored as `'+''` and `'-'` (with quotes)
in the precedence table, while the grammar stored them as `+` and `-`
(without quotes). This mismatch meant `has_precedence('+')` returned
`False`, so no conflicts were resolved. Added quote-stripping for
precedence directive arguments.

## License

MIT