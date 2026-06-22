# Language Reference

## BNF Grammar Format

The `GrammarLoader` parses a simple BNF-like syntax:

### Syntax Rules

- **Comments**: Lines starting with `#` are ignored.
- **Non-terminals**: Written as `<name>` where name matches
  `[A-Za-z_][A-Za-z0-9_]*`.
- **Terminals**: Written as quoted strings: `"..."` or `'...'`.
- **Productions**: `LHS ::= RHS` where `::=` is the production arrow.
- **Alternatives**: Separated by `|` on continuation lines.
- **Epsilon**: An empty alternative (just `|` at end of line) means ε.
- **Start symbol**: The first production's LHS, or declared explicitly
  with `start ::= <X>`.

### Example

```bnf
# Expression grammar
start ::= <E>

<E> ::= <E> "+" <E>
      | <E> "*" <E>
      | "(" <E> ")"
      | "id"
```

### Bare Words

Unquoted words that aren't non-terminals are treated as terminals:

```bnf
<E> ::= <E> + <E>
      | id
```

This is equivalent to the quoted version.

## Grammar API

### Building Grammars

```python
from earley_parser import Grammar

# From rules
g = Grammar.from_rules("E", [
    ("E", ("E", "+", "E")),
    ("E", ("id",)),
])

# From BNF text
from earley_parser import GrammarLoader
g = GrammarLoader.load(open("expr.bnf").read())

# From file
g = GrammarLoader.load_file("expr.bnf")
```

### Grammar Queries

```python
g.is_terminal("id")       # True
g.is_nonterminal("E")     # True
g.nullable()              # set of nullable non-terminals
g.first()                 # dict of FIRST sets
g.follow()                # dict of FOLLOW sets
g.productive()            # set of productive non-terminals
g.reachable()             # set of reachable non-terminals
g.validate()              # list of problems (empty if valid)
g.stats()                 # GrammarStats object
```

## Parser API

### Recognition

```python
from earley_parser import EarleyParser

p = EarleyParser(g)
p.parse(["id", "+", "id"])          # True/False
p.parse_or_error(["id", "+"])       # True or ParseError
```

### Tree Extraction

```python
trees = p.trees(["id", "+", "id", "*", "id"], max_trees=10)
forest = p.forest(["id", "+", "id", "*", "id"])

# Tree operations
tree = trees[0]
tree.pretty()              # text tree
tree.to_dict()             # dictionary
tree.to_json()             # JSON string
tree.yield_terminals()     # list of leaf terminals
tree.depth()               # tree depth
tree.count_nodes()         # total nodes
tree.walk()                # iterator over all nodes

# Forest operations
forest.is_ambiguous        # bool
forest.ambiguity_count     # int
forest.pretty()            # all trees as text
forest.to_json()           # JSON array
forest.to_dot()            # Graphviz DOT
forest.to_lisp()           # S-expression
forest.stats()             # dict with stats
```

### Diagnostics

```python
p.chart_stats()            # item count per chart
p.chart_dump()             # full chart dump
p.ambiguity_count(tokens)  # number of parse trees
p.is_ambiguous(tokens)     # True if >1 tree
```

## Tokenizer API

```python
from earley_parser import Tokenizer, TokenSpec

tok = Tokenizer([
    TokenSpec("NUM", r"[0-9]+"),
    TokenSpec("PLUS", r"\+"),
    TokenSpec("WS", r"\s+", skip=True),
])

tok.tokenize("12 + 34")            # ["NUM", "PLUS", "NUM"]
tok.tokenize_with_text("12 + 34")  # [("NUM", "12"), ("PLUS", "+"), ("NUM", "34")]
tok.tokenize_full("12 + 34")       # [Token("NUM", "12", 0), ...]
```

## Analysis API

```python
from earley_parser import LL1Table, is_ll1, detect_ambiguity, grammar_summary

table = LL1Table(g).build()
table.is_ll1         # bool
table.conflicts      # list of conflict strings
table.pretty()       # formatted table
table.get("E", "id") # production or None

is_ll1(g)                      # bool
detect_ambiguity(g, max_length=5)  # list of ambiguous inputs
grammar_summary(g)             # formatted string
```

## CYK API

```python
from earley_parser import CNFGrammar, CYKParser

cnf = CNFGrammar(start="S")
cnf.add_binary("S", "A", "B")   # S → A B
cnf.add_terminal("A", "a")      # A → a
cnf.add_terminal("B", "b")      # B → b
cnf.set_start_nullable()        # S → ε (optional)

p = CYKParser(cnf)
p.parse(["a", "b"])             # True
p.trees(["a", "b"])             # [ParseNode(...)]
```

## CLI

```bash
# Recognize
earley recognize --grammar examples/expr.bnf id + id '*' id

# Show parse trees
earley tree --grammar examples/expr.bnf --max 3 id + id '*' id

# Export forest as JSON
earley forest --grammar examples/expr.bnf --format json id

# Validate grammar
earley check examples/expr.bnf

# Analyze grammar
earley analyze --ambiguity examples/expr.bnf

# LL(1) table
earley ll1 examples/expr.bnf

# Chart dump
earley chart --grammar examples/expr.bnf id + id

# CYK parse
earley cyk examples/cnf.bnf a b

# Config-based parsing
earley config examples/config.json "id + id"

# Demo
earley demo
```