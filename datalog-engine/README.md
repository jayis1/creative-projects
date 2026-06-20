# datalog-engine

A from-scratch Datalog deductive database engine implementing bottom-up evaluation with the **semi-naive** delta strategy, **stratified negation**, hash-indexed joins, and built-in comparison predicates.

Datalog is a declarative logic programming language — a subset of Prolog without function symbols — widely used for program analysis, database queries, and rule-based reasoning. This engine parses a Datalog program (facts + rules), evaluates rules to a least fixpoint, and answers queries against the derived facts.

## Features

- **Semi-naive bottom-up evaluation** — uses delta relations to avoid re-deriving known facts, achieving efficient fixpoint computation for recursive rules.
- **Stratified negation** — supports `not` in rule bodies with automatic stratification via SCC analysis of the predicate dependency graph. Detects and rejects non-stratifiable programs.
- **Hash-indexed joins** — builds hash indexes on join columns for fast lookup during body evaluation.
- **Built-in comparison predicates** — `<`, `>`, `<=`, `>=`, `!=`, `==` usable in infix (`X > 3`) or prefix (`>(X, 3)`) form.
- **Safety checking** — enforces the Datalog safety condition (every variable in the head or in negated literals must appear in a positive body literal).
- **Hand-written tokenizer + recursive-descent parser** — no external parser dependencies.
- **Interactive REPL** — load facts/rules and issue queries interactively.
- **Zero dependencies** — pure Python standard library only.

## Installation

```bash
# No build step needed — just run from the directory:
cd datalog-engine
python3 -m datalog.cli --help

# Or import as a package:
python3 -c "from datalog import Engine; e = Engine(); e.add_source('edge(a,b). path(X,Y) :- edge(X,Y).'); print(e.query('path(X,Y)'))"
```

## Syntax

```
% Comments start with % (line) or /* ... */ (block)

% Facts: predicate with constant arguments, ending with .
parent(tom, bob).
parent(tom, liz).

% Rules: head :- body. (body is comma-separated literals)
ancestor(X, Y) :- parent(X, Y).
ancestor(X, Y) :- parent(X, Z), ancestor(Z, Y).

% Negation (must be stratified)
childless(X) :- person(X), not parent(X, Y).

% Built-in comparisons (infix or prefix)
adult(X) :- age(X, A), A >= 18.
adult(X) :- age(X, A), >=(A, 18).

% Queries: ?- atom.  (trailing . optional in CLI/REPL)
?- ancestor(tom, X).
```

**Naming conventions:**
- Variables: start with uppercase letter or underscore (`X`, `Person`, `_`)
- Constants: lowercase identifiers (`tom`), strings (`"hello"`), numbers (`42`, `3.14`), booleans (`true`, `false`)
- Predicates: lowercase identifiers (`parent`, `ancestor`)

## Usage

### As a library

```python
from datalog import Engine

e = Engine()
e.add_source("""
    edge(a, b). edge(b, c). edge(c, d).
    path(X, Y) :- edge(X, Y).
    path(X, Y) :- edge(X, Z), path(Z, Y).
""")

# Query for all nodes reachable from 'a'
results = e.query("path(a, X)")
for r in results:
    print(r)  # {'X': 'b'}, {'X': 'c'}, {'X': 'd'}

# Get the full extension of a predicate
print(e.relation("path"))
# [('a','b'), ('a','c'), ('a','d'), ('b','c'), ('b','d'), ('c','d')]

# Add facts programmatically
e.add_fact("edge", "d", "e")
```

### Command-line

```bash
# Load a file and run a query
python3 -m datalog.cli examples/family.dl -q "ancestor(tom, X)"

# Show a relation
python3 -m datalog.cli examples/graph.dl --show path

# Interactive REPL
python3 -m datalog.cli examples/family.dl --repl
```

### REPL

```
$ python3 -m datalog.cli --repl
datalog-engine REPL. Type :help for commands, :quit to exit.
dl> edge(a, b). edge(b, c).
dl> path(X, Y) :- edge(X, Y).
dl> path(X, Y) :- edge(X, Z), path(Z, Y).
dl> ?- path(a, X)
X = b
X = c
(2 answers)
dl> :preds
  edge/2
  path/2
dl> :quit
```

## How It Works

### 1. Parsing

The lexer tokenizes the source into identifiers, variables, strings, numbers, operators, and punctuation. The recursive-descent parser produces an AST of `Fact`, `Rule`, and `Query` nodes. Safety is checked at parse time.

### 2. Stratification

Before evaluation, the engine builds a predicate dependency graph with positive and negative edges (from rule bodies to rule heads). It computes strongly-connected components (SCCs) using Tarjan's algorithm. If a negative edge lies within an SCC, the program is rejected as non-stratifiable. SCCs are then topologically sorted into strata, with each stratum assigned a level equal to the longest path from a source SCC. Rules are grouped by their head predicate's stratum.

### 3. Semi-naive Evaluation

Strata are evaluated bottom-up in order. Within each stratum:

1. **Naive bootstrap**: evaluate all rules once against current (empty for IDB) relations to produce initial facts.
2. **Semi-naive iteration**: in each round, for every rule, evaluate the body with at least one positive body literal restricted to the *delta* (newly added tuples) of that predicate. New tuples are collected into new deltas. Repeat until no new tuples are derived.

This avoids re-deriving existing facts: only combinations involving at least one new tuple are considered.

### 4. Joins

Body literals are evaluated left-to-right. For each literal, the engine identifies which variables are already bound (from earlier literals), builds a hash index on those positions in the relation, and looks up matching tuples. Unification extends the binding with newly-bound variables.

### 5. Negation

Negated literals are evaluated only in higher strata (after the negated predicate is fully derived). A negated literal `not p(X)` succeeds for a binding if no tuple in `p` matches under that binding. Safety ensures all variables in negated literals are already bound.

## Examples

See `examples/family.dl` (family relationships with transitive ancestry) and `examples/graph.dl` (graph algorithms: transitive closure, cycle detection, source/sink identification).

## Project Structure

```
datalog-engine/
├── datalog/
│   ├── __init__.py      # Public API exports
│   ├── __main__.py      # CLI entry point
│   ├── ast.py           # AST nodes (Term, Variable, Constant, Atom, Literal, Rule, Fact, Query, Program)
│   ├── parser.py        # Lexer + recursive-descent parser
│   ├── engine.py        # Evaluation engine (stratification, semi-naive, joins, builtins)
│   └── cli.py           # Command-line interface + REPL
├── examples/
│   ├── family.dl        # Family relationship database
│   └── graph.dl         # Graph algorithms
└── README.md
```