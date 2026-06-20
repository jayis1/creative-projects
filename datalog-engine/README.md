# datalog-engine

A from-scratch Datalog deductive database engine implementing bottom-up evaluation with the **semi-naive** delta strategy, **stratified negation**, hash-indexed joins, **arithmetic built-ins**, fact/rule retraction, JSON state export/import, and an introspection API.

Datalog is a declarative logic programming language — a subset of Prolog without function symbols — widely used for program analysis, database queries, and rule-based reasoning. This engine parses a Datalog program (facts + rules), evaluates rules to a least fixpoint, and answers queries against the derived facts.

## Features

- **Semi-naive bottom-up evaluation** — uses delta relations to avoid re-deriving known facts, achieving efficient fixpoint computation for recursive rules.
- **Stratified negation** — supports `not` in rule bodies with automatic stratification via SCC analysis of the predicate dependency graph. Detects and rejects non-stratifiable programs.
- **Hash-indexed joins** — builds hash indexes on join columns for fast lookup during body evaluation.
- **Comparison built-ins** — `<`, `>`, `<=`, `>=`, `!=`, `==` usable in infix (`X > 3`) or prefix (`>(X, 3)`) form.
- **Arithmetic built-ins** — `add(X, Y, Z)`, `sub`, `mul`, `div`, `idiv`, `mod` — the third argument is bound to the result, enabling computed predicates.
- **Safety checking** — enforces the Datalog safety condition (every variable in the head or in negated literals must appear in a positive body literal).
- **Fact & rule retraction** — remove individual facts or rules with automatic re-evaluation on next query.
- **JSON export/import** — serialize EDB facts + rules to JSON for persistence and reloading.
- **Introspection API** — `explain()` shows stratum, rules, and extension size for any predicate; `rules()` lists loaded rules; `facts()` shows base facts.
- **Interactive REPL** — load facts/rules, issue queries, run meta-commands (`:preds`, `:explain`, `:rules`, `:export`, `:rel`, `:reset`).
- **Hand-written tokenizer + recursive-descent parser** — no external parser dependencies.
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

% Comparison built-ins (infix or prefix)
adult(X) :- age(X, A), A >= 18.
adult(X) :- age(X, A), >=(A, 18).

% Arithmetic built-ins (3-arg: inputs + output variable)
doubled(X, Y) :- num(X), mul(X, 2, Y).
total(X, Y, Z) :- add(X, Y, Z).

% Queries: ?- atom.  (trailing . optional in CLI/REPL)
?- ancestor(tom, X).
```

**Naming conventions:**
- Variables: start with uppercase letter or underscore (`X`, `Person`, `_`)
- Constants: lowercase identifiers (`tom`), strings (`"hello"`), numbers (`42`, `3.14`), booleans (`true`, `false`)
- Predicates: lowercase identifiers (`parent`, `ancestor`)

**Built-in predicates:**

| Predicate | Form | Description |
|-----------|------|-------------|
| `<`, `>`, `<=`, `>=`, `!=`, `==` | infix/prefix | Comparison (returns true/false) |
| `add(X, Y, Z)` | prefix | Z = X + Y |
| `sub(X, Y, Z)` | prefix | Z = X - Y |
| `mul(X, Y, Z)` | prefix | Z = X × Y |
| `div(X, Y, Z)` | prefix | Z = X / Y (float) |
| `idiv(X, Y, Z)` | prefix | Z = X // Y (integer) |
| `mod(X, Y, Z)` | prefix | Z = X % Y |

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

# Retract a fact
e.retract_fact("edge", "d", "e")

# Explain a predicate
print(e.explain("path"))
# Predicate: path/2
#   Type: IDB (derived)
#   Stratum: 1
#   Rules:
#     path(X, Y) :- edge(X, Y).
#     path(X, Y) :- edge(X, Z), path(Z, Y).
#   Extension: 5 tuple(s)

# JSON export/import
json_state = e.to_json()
e2 = Engine()
e2.from_json(json_state)
print(e2.query("path(a, X)"))
```

### Command-line

```bash
# Load a file and run a query
python3 -m datalog.cli examples/family.dl -q "ancestor(tom, X)"

# Run multiple queries
python3 -m datalog.cli examples/company.dl -q "well_paid(X)" -q "underpaid(X)"

# Show a relation
python3 -m datalog.cli examples/graph.dl --show path

# Explain a predicate
python3 -m datalog.cli examples/family.dl --explain ancestor

# Export state to JSON
python3 -m datalog.cli examples/graph.dl --export state.json

# Import JSON state and query
python3 -m datalog.cli --import state.json -q "path(a, X)"

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
X = 'b'
X = 'c'
(2 answers)
dl> :preds
  edge/2
  path/2
dl> :explain path
Predicate: path/2
  Type: IDB (derived)
  Stratum: 1
  Rules:
    path(X, Y) :- edge(X, Y).
    path(X, Y) :- edge(X, Z), path(Z, Y).
  Extension: 3 tuple(s)
dl> :export my_state.json
Exported to my_state.json
dl> :quit
```

## How It Works

### 1. Parsing

The lexer tokenizes the source into identifiers, variables, strings, numbers, operators, and punctuation. The recursive-descent parser produces an AST of `Fact`, `Rule`, and `Query` nodes. Safety is checked at parse time. Comparison operators are recognized both in infix (`X > 3`) and prefix (`>(X, 3)`) form.

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

### 6. Arithmetic Built-ins

Arithmetic predicates (`add`, `sub`, `mul`, `div`, `idiv`, `mod`) take three arguments: two inputs and one output. The output variable is bound to the result. If the output variable is already bound, the predicate acts as a check. Division by zero fails gracefully (returns no bindings).

## Examples

| File | Description |
|------|-------------|
| `examples/family.dl` | Family relationships with transitive ancestry, siblings (using `!=`), aunt/uncle |
| `examples/graph.dl` | Graph algorithms: transitive closure, cycle detection, source/sink, connected components |
| `examples/company.dl` | Company database with arithmetic (salary doubling), negation (worker vs. manager), management hierarchy |

## Project Structure

```
datalog-engine/
├── datalog/
│   ├── __init__.py      # Public API exports
│   ├── __main__.py      # CLI entry point (python -m datalog)
│   ├── ast.py           # AST nodes (Term, Variable, Constant, Atom, Literal, Rule, Fact, Query, Program)
│   ├── parser.py        # Lexer + recursive-descent parser
│   ├── engine.py        # Evaluation engine (stratification, semi-naive, joins, builtins, retraction, JSON I/O)
│   └── cli.py           # Command-line interface + REPL
├── examples/
│   ├── family.dl        # Family relationship database
│   ├── graph.dl         # Graph algorithms
│   └── company.dl       # Company database with arithmetic
└── README.md
```