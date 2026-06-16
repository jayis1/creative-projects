# prolog-engine

A **mini-Prolog logic programming engine** implemented from scratch in pure Python. Features a complete unification algorithm with occurs-check, backtracking search, a standard library of built-in predicates, arithmetic evaluation, list operations, and an interactive REPL.

## How It Works

The engine implements the core components of a Prolog system:

1. **Lexer/Tokenizer** — Converts Prolog source text into tokens (atoms, variables, numbers, strings, punctuation, operators).
2. **Recursive-Descent Parser** — Parses tokens into an AST of clauses, queries, and terms (atoms, variables, numbers, compounds, lists).
3. **Unification Algorithm** — Robinson's unification with occurs-check, the heart of Prolog's pattern matching. Two terms unify if there exists a substitution making them identical.
4. **Backtracking Search Engine** — Depth-first search through the proof tree. For each goal, it tries all matching clauses in order; if a clause's body fails, it backtracks and tries the next clause.
5. **Variable Renaming** — Each clause use gets fresh variables (standardizing apart) to prevent accidental variable capture.
6. **Arithmetic Evaluation** — Evaluates `is/2` goals: `X is 3 + 4 * 2` binds X to 11.
7. **Built-in Predicates** — A library of ~30 built-ins for arithmetic comparison, type checking, list operations, I/O, and control flow.

### Architecture

```
Source → Lexer → Parser → AST (Clauses/Queries/Terms)
                                      ↓
                              Engine (backtracking search)
                                      ↕
                              Unifier (Robinson's algorithm)
                                      ↕
                              Builtins (arithmetic, lists, I/O, type checks)
```

## Usage

### Programmatic API

```python
from prolog_engine import create_engine

engine = create_engine()

# Load Prolog source
engine.load_source("""
    parent(tom, bob).
    parent(tom, liz).
    parent(bob, ann).
    parent(bob, pat).
    grandparent(X, Z) :- parent(X, Y), parent(Y, Z).
""")

# Query for all grandparents
for subst in engine.query("?- grandparent(tom, Z)."):
    z = subst.apply(engine.query("?- grandparent(tom, Z).")[0])  # simplified
    print(engine.format_solution(subst))
# Output: Z = ann ; Z = pat ;

# Arithmetic
engine.load_source("square(X, Y) :- Y is X * X.")
for subst in engine.query("?- square(5, R)."):
    print(engine.format_solution(subst))
# Output: R = 25

# Lists
engine.load_source("""
    last(X, [X]).
    last(X, [_|T]) :- last(X, T).
""")
for subst in engine.query("?- last(X, [a, b, c])."):
    print(engine.format_solution(subst))
# Output: X = c
```

### Command-Line Interface

```bash
# Install
pip install -e .

# Interactive REPL
prolog-engine -i

# Load a file and query
prolog-engine family.pl -q "?- grandparent(tom, X)."

# Load multiple files
prolog-engine kb1.pl kb2.pl -i
```

### REPL

```
?- parent(tom, bob).
Loaded 1 clause(s).

?- parent(tom, X).
X = bob ;
X = liz ;

?-
```

## Built-in Predicates

### Unification & Comparison
| Predicate | Description |
|-----------|-------------|
| `=/2` | Unification: `X = Y` |
| `\=/2` | Not unifiable |
| `is/2` | Arithmetic evaluation: `X is Expr` |
| `==/2` | Arithmetic equality |
| `\==/2` | Arithmetic inequality |
| `</2`, `=</2`, `>/2`, `>=/2` | Arithmetic comparisons |

### Type Checking
| Predicate | Description |
|-----------|-------------|
| `var/1` | Is it an uninstantiated variable? |
| `nonvar/1` | Is it instantiated? |
| `atom/1` | Is it an atom? |
| `number/1` | Is it a number? |
| `integer/1` | Is it an integer? |
| `float/1` | Is it a float? |
| `string/1` | Is it a string? |
| `compound/1` | Is it a compound term? |

### Control Flow
| Predicate | Description |
|-----------|-------------|
| `true/0` | Always succeeds |
| `fail/0` | Always fails |
| `!/0` | Cut (commit to current choice) |
| `not/1`, `\+/1` | Negation as failure |
| `repeat/0` | Infinite choice points |

### List Operations
| Predicate | Description |
|-----------|-------------|
| `length/2` | List length |
| `member/2` | List membership |
| `append/3` | List concatenation |

### Structural
| Predicate | Description |
|-----------|-------------|
| `functor/3` | Get term name/arity or construct |
| `arg/3` | Access nth argument of compound |

### I/O
| Predicate | Description |
|-----------|-------------|
| `write/1` | Write term |
| `writeln/1` | Write term + newline |
| `nl/0` | Print newline |

### Arithmetic Functions
Available in `is/2` expressions: `+`, `-`, `*`, `/`, `//` (integer div), `mod`, `rem`, `abs`, `max`, `min`, `**`/`^` (power), `pi`.

## Project Structure

```
prolog-engine/
├── prolog_engine/
│   ├── __init__.py       # Package exports + create_engine()
│   ├── lexer.py          # Tokenizer
│   ├── parser.py         # Recursive-descent parser
│   ├── ast_nodes.py      # AST nodes + term utilities
│   ├── unifier.py        # Robinson's unification algorithm
│   ├── engine.py         # Backtracking inference engine
│   ├── builtins.py       # ~30 built-in predicates
│   └── cli.py            # REPL and CLI
├── tests/
│   └── ...
├── pyproject.toml
└── README.md
```

## License

MIT