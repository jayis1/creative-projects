# lalr-parser-gen

A from-scratch LALR(1) parser generator written in pure Python (no dependencies).

## Overview

This project implements a complete LALR(1) parser generator, including:

- **Grammar representation** with nullable, FIRST, and FOLLOW set computation
- **LR(0) automaton** construction (canonical collection of item sets)
- **LALR(1) lookahead computation** via the DeRemer-Pennello propagation algorithm
- **ACTION/GOTO table** construction with conflict detection
- **Table-driven LR parser** with semantic actions
- **BNF grammar loader** for loading grammars from text files
- **CLI** for table inspection, conflict analysis, and parsing

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

Conflicts (shift/reduce, reduce/reduce) are detected and reported.

### 4. Parsing

The parser maintains a state stack and value stack. For each input token:
- **Shift**: Push the token value and new state.
- **Reduce**: Pop `|body|` values, apply the semantic action, push result.
- **Accept**: Return the final semantic value.

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

### BNF Grammar Files

```bnf
// examples/expr.bnf
%start expr

expr   : expr '+' term
       | term
       ;

term   : term '*' factor
       | factor
       ;

factor : '(' expr ')'
       | NUMBER
       ;
```

```python
from lalr import load_bnf, LALRTable, Parser

grammar = load_bnf(open("examples/expr.bnf").read())
table = LALRTable(grammar)
```

### CLI

```bash
# Show table summary and conflicts
python -m lalr.cli examples/expr.bnf --action=table

# Check for conflicts only
python -m lalr.cli examples/classic-lalr.bnf --action=conflicts

# Dump full ACTION/GOTO tables
python -m lalr.cli examples/expr.bnf --action=dump -o table.txt

# Dump all states with LALR(1) lookaheads
python -m lalr.cli examples/expr.bnf --action=states

# Show FIRST and FOLLOW sets
python -m lalr.cli examples/expr.bnf --action=first-follow

# Parse an input string
python -m lalr.cli examples/expr.bnf --action=parse --input="NUMBER + NUMBER * NUMBER"
```

## Examples

- `examples/expr.bnf` — Arithmetic expression grammar
- `examples/classic-lalr.bnf` — The classic LALR(1)-but-not-SLR(1) grammar
- `examples/calculator.py` — Full calculator with semantic actions

## The Classic LALR(1) Grammar

The grammar `S → L=R | R`, `L → *R | id`, `R → L` is the textbook example
of a grammar that is **LALR(1) but not SLR(1)**. SLR(1) would use FOLLOW(R)
which includes `=` (from `S → L=R`), causing a shift/reduce conflict when
seeing `=` in state with `R → L•`. LALR(1) correctly distinguishes the
contexts and reports no conflicts.

## Project Structure

```
lalr-parser-gen/
├── lalr/
│   ├── __init__.py       # Package exports
│   ├── grammar.py        # Grammar, Production, FIRST/FOLLOW/nullable
│   ├── table.py          # LR0Automaton, LALR1Builder, LALRTable
│   ├── parser.py         # Parser driver, Token, ParseError
│   ├── bnf_loader.py     # BNF grammar file loader
│   └── cli.py            # Command-line interface
├── tests/
│   └── test_lalr.py      # 30 tests
├── examples/
│   ├── expr.bnf          # Arithmetic grammar
│   ├── classic-lalr.bnf  # Classic non-SLR LALR grammar
│   └── calculator.py     # Calculator demo
└── README.md
```

## Testing

```bash
PYTHONPATH=. python -m pytest tests/ -v
```

## License

MIT