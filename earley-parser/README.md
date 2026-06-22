# earley-parser

An implementation of the **Earley parsing algorithm** — a general
context-free-grammar (CFG) parser that works on *any* CFG, including
ambiguous and (with nullable handling) certain left-recursive forms,
in O(n³) worst-case time and O(n²) for unambiguous grammars.

## What it does

Given a context-free grammar and a token stream, the parser decides
whether the input is in the language of the grammar (recognition). The
algorithm uses three classic operations:

| Operation | Purpose |
|-----------|---------|
| **Predict** | If the next symbol is a non-terminal *N*, add items for every production of *N* to the current chart. |
| **Scan**    | If the next symbol is a terminal matching the current input token, advance the dot and add the item to the next chart. |
| **Complete**| If an item is complete (dot at the end), advance any earlier item in the origin chart that was waiting for this non-terminal. |

Nullable non-terminals are handled via fixed-point computation, so
epsilon productions and implicit nullable rules are supported.

## Files

| File | Description |
|------|-------------|
| `earley.py` | Core engine: `Grammar`, `Item`, `Chart`, `EarleyParser`, and a demo. |

## Usage

```python
from earley import Grammar, EarleyParser

g = Grammar.from_rules(
    start="E",
    rules=[
        ("E", ("E", "+", "E")),
        ("E", ("E", "*", "E")),
        ("E", ("(", "E", ")")),
        ("E", ("id",)),
    ],
)

p = EarleyParser(g)
print(p.parse(["id", "+", "id", "*", "id"]))   # True
print(p.parse(["id", "+"]))                     # False
```

Run the built-in demo:

```bash
python3 earley.py
```

Output:
```
✓  id
✓  id + id
✓  id + id * id
✓  ( id + id ) ) * id
✗  id +
✗  + id
```

## How it works

Each Earley *item* is a dotted rule `(LHS → α • β, origin)`, where `origin`
records the input position at which recognition of this non-terminal began.
The parser maintains one *chart* per input position (0 … n). It processes
items in order within each chart, applying predict / scan / complete as
appropriate. After processing, the parse **succeeds** iff the final chart
contains a complete item for the start symbol with origin 0.

## Grammar format

A grammar is built via `Grammar.from_rules(start, rules)` where `rules`
is a list of `(lhs, rhs_tuple)` pairs. Repeated LHS entries accumulate
into alternatives. Epsilon is represented by an empty tuple `()`.
Terminals are any symbols that never appear on a LHS.