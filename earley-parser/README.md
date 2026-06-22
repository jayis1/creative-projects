# earley-parser

An implementation of the **Earley parsing algorithm** — a general
context-free-grammar (CFG) parser that works on *any* CFG, including
ambiguous grammars, in O(n³) worst-case time and O(n²) for unambiguous
grammars.

## Features

- **Recognition**: determine whether a token stream belongs to a grammar's language
- **Parse tree extraction**: build all parse trees (SPPF-style), handling ambiguity
- **Ambiguity detection**: multiple trees returned for ambiguous inputs
- **Structured error reporting**: position, unexpected token, and expected token set
- **Nullable handling**: epsilon productions via fixed-point computation
- **FIRST sets**: computed for all symbols
- **Grammar validation**: detects unproductive non-terminals, missing start symbols, conflicts
- **BNF grammar loader**: parse `.bnf` files with a simple syntax
- **Regex tokenizer**: configurable token specs with skip support
- **CLI**: `recognize`, `tree`, `check`, `demo` subcommands
- **19 tests** covering recognition, tree extraction, ambiguity, errors, tokenizer, loader

## How it works

The Earley algorithm uses three classic operations per chart position:

| Operation | Purpose |
|-----------|---------|
| **Predict** | If the next symbol is a non-terminal *N*, add items for every production of *N* to the current chart. |
| **Scan**    | If the next symbol is a terminal matching the current input token, advance the dot and add the item to the next chart. |
| **Complete**| If an item is complete (dot at the end), advance any earlier item in the origin chart that was waiting for this non-terminal. |

Each Earley *item* is a dotted rule `(LHS → α • β, origin)`, where `origin`
records the input position at which recognition of this non-terminal began.
The parser maintains one *chart* per input position (0 … n).

### Tree extraction

After recognition, parse trees are extracted by enumerating all ways to split
each item's span `[origin, end]` into sub-segments matching the RHS symbols.
Completed child items are found via an indexed lookup in each chart. A *path*
set detects cycles (for grammars with nullable cycles), and a *memo* cache
avoids redundant recomputation across branches.

For ambiguous grammars, multiple complete start items and multiple split
points produce multiple trees — each representing a valid derivation.

### Error reporting

On parse failure, the parser identifies the furthest chart position reached
and computes the set of terminals that could have continued the parse (using
FIRST sets of pending non-terminals). This gives users actionable feedback
like: `Parse error at position 2: unexpected EOF; expected one of: (, id`.

## Files

| File | Description |
|------|-------------|
| `earley.py` | Core engine: `Grammar`, `Item`, `Chart`, `EarleyParser`, `ParseNode`, `Tokenizer`, `GrammarLoader`, CLI |
| `test_earley.py` | 19 tests covering all features |
| `examples/expr.bnf` | Ambiguous expression grammar |
| `examples/balance.bnf` | Balanced parentheses grammar with epsilon |

## Usage

### Basic recognition

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

### Parse tree extraction

```python
trees = p.trees(["id", "+", "id", "*", "id"], max_trees=10)
print(f"{len(trees)} parse tree(s)")
for t in trees:
    print(t.pretty())
```

Output:
```
2 parse tree(s)

--- Tree 1 ---
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

--- Tree 2 ---
E  [0:5]
  E  [0:1]
    id  [0:1]
  +  [1:2]
  E  [2:5]
    E  [2:3]
      id  [2:3]
    *  [3:4]
    E  [4:5]
      id  [4:5]
```

### Error reporting

```python
result = p.parse_or_error(["id", "+"])
if isinstance(result, ParseError):
    print(result)
    # Parse error at position 2: unexpected EOF; expected one of: (, id
```

### Tokenizer

```python
from earley import Tokenizer, TokenSpec

tok = Tokenizer([
    TokenSpec("NUM", r"[0-9]+"),
    TokenSpec("PLUS", r"\+"),
    TokenSpec("STAR", r"\*"),
    TokenSpec("LPAREN", r"\("),
    TokenSpec("RPAREN", r"\)"),
    TokenSpec("WS", r"\s+", skip=True),
])

tokens = tok.tokenize("3 + 4 * (2 + 1)")
# ['NUM', 'PLUS', 'NUM', 'STAR', 'LPAREN', 'NUM', 'PLUS', 'NUM', 'RPAREN']
```

### BNF grammar files

```bnf
# expr.bnf
start ::= <E>

<E> ::= <E> "+" <E>
      | <E> "*" <E>
      | "(" <E> ")"
      | "id"
```

```python
from earley import GrammarLoader

with open("expr.bnf") as f:
    g = GrammarLoader.load(f.read())
```

### CLI

```bash
# Recognize
python3 earley.py recognize --grammar examples/expr.bnf id + id '*' id

# Show parse trees
python3 earley.py tree --grammar examples/expr.bnf --max 3 id + id '*' id

# Validate a grammar
python3 earley.py check examples/expr.bnf

# Run the built-in demo
python3 earley.py demo
```

## Known Issues (Resolved)

| # | Bug | Fix |
|---|-----|-----|
| 1 | **Memo caches truncated tree lists** — when `max_trees` was hit during tree extraction, the memo cached the incomplete result. Subsequent calls with a larger `max_trees` would receive the stale truncated list, missing valid parse trees. | Only cache results in the memo when `len(nodes_list) < max_trees` (i.e., the enumeration was not truncated). |
| 2 | **Tokenizer infinite loop on zero-length regex matches** — a token spec like `[0-9]*` could match the empty string at a non-digit character, causing `i` to never advance and the tokenizer to hang forever. | Detect zero-length matches (`m.end() == i`) and skip to the next token spec, falling through to the error/whitespace handler if no spec matches non-empty. |
| 3 | **Empty grammar file causes IndexError** — `GrammarLoader.load("")` would access `rules[0]` on an empty list, raising an unhelpful `IndexError`. | Added an explicit check: `if not rules: raise ValueError("Grammar file contains no production rules.")`. |
| 4 | **Parse tree node sharing across trees** — the memo cache returned the same `ParseNode` objects for common sub-trees, so modifying one parse tree would corrupt sibling trees that shared those nodes. | Deep-copy all children when assembling a completed tree in `split()`, ensuring each tree in the result has its own independent set of `ParseNode` objects. |
| 5 | **Dead code in `validate()`** — a loop over RHS symbols that did nothing (`pass` statement) and an unused `nullable` variable. | Removed the dead loop and unused variable. |
| 6 | **Dead code in `GrammarLoader.load()`** — a terminal-collecting loop that assigned to a local `terminals` variable but never used it (the real collection happened in a second loop). | Removed the redundant first loop. |

## Grammar format

### Programmatic (`Grammar.from_rules`)

A grammar is built from `(lhs, rhs_tuple)` pairs. Repeated LHS entries
accumulate into alternatives. Epsilon is represented by an empty tuple `()`.
Terminals are any symbols that never appear on a LHS.

### BNF files (`GrammarLoader`)

Symbols in angle brackets `<name>` are non-terminals. Quoted strings are
terminals. `|` separates alternatives. Empty alternative means epsilon.
The first production's LHS is the start symbol, or use `start ::= <X>` to
declare it explicitly. `#` starts a comment.