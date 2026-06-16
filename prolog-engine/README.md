# Mini-Prolog Engine

A complete logic programming engine implementing a subset of Prolog in pure Python, featuring Robinson's unification with occurs-check, backtracking search, predicate indexing, and ~50 built-in predicates.

## Features

- **Robinson's unification** with occurs-check to prevent infinite terms
- **Backtracking search** with depth-first SLD resolution
- **Predicate indexing** for efficient clause lookup by name/arity
- **50+ built-in predicates** covering unification, type checking, control flow, arithmetic, lists, term inspection, dynamic database, and meta-logical operations
- **Standard Prolog syntax**: clauses, queries, lists, infix operators (=, \=, is, <, >, =<, >=, ==, \==, =..)
- **Arithmetic with operator precedence**: `X is 3 + 4 * 2.` correctly evaluates to 11
- **Dynamic database**: assertz/1, asserta/1, retract/1, clause/2
- **Meta-logical**: findall/3, bagof/3, setof/3, copy_term/2
- **Cut (!)** for pruning choice points
- **Negation as failure** (not/1, \+/1)
- **Tracing mode** for debugging
- **Max depth protection** against infinite loops
- **REPL** for interactive exploration
- **Comprehensive test suite** (109 tests)

## How It Works

### Architecture

The engine follows the standard Prolog execution model:

1. **Lexer** — Tokenizes Prolog source into atoms, variables, numbers, strings, operators, and punctuation. Handles line/block comments, quoted atoms, string escapes, and the `=..` univ operator as a special multi-character token.

2. **Parser** — Uses precedence-climbing for infix operators. Supports:
   - Clauses (facts and rules with `:-`)
   - Queries (`?-`)
   - Lists (`[a, b, c]`, `[H|T]`)
   - All standard infix operators with correct precedence and associativity
   - Compound terms with nested arguments

3. **Unifier** — Implements Robinson's unification algorithm with occurs-check. Terms unify recursively: atoms unify if equal, variables bind to terms (unless the term contains the variable — occurs-check), and compounds unify if names, arities, and all arguments unify.

4. **Engine** — Performs depth-first SLD resolution with backtracking:
   - Goals are solved left-to-right
   - Clauses are tried in database order
   - Variable renaming (standardizing apart) prevents variable capture
   - Predicate indexing maps `name/arity` to clause positions for O(1) lookup
   - Cut (!) prunes alternative solutions
   - Depth limit prevents infinite recursion

5. **Built-ins** — 50+ predicates registered as Python generators that yield substitutions for successful proofs and return (yield nothing) for failure.

### Built-in Predicates

| Category | Predicates |
|----------|-----------|
| Unification | `=/2`, `\=/2`, `==/2`, `\==/2` |
| Arithmetic | `is/2`, `</2`, `>/2`, `=</2`, `>=/2`, `between/3`, `succ/2`, `plus/3` |
| Type checking | `var/1`, `nonvar/1`, `atom/1`, `number/1`, `compound/1`, `integer/1`, `float/1`, `string/1`, `atomic/1`, `ground/1` |
| Control flow | `true/0`, `fail/0`, `!/0`, `not/1`, `\+/1`, `once/1`, `forall/2`, `repeat/0` |
| Lists | `length/2`, `member/2`, `append/3`, `reverse/2`, `nth0/3`, `nth1/3`, `last/2`, `sort/2`, `msort/2` |
| Term inspection | `functor/3`, `arg/3`, `copy_term/2`, `=../2` |
| Dynamic DB | `assertz/1`, `asserta/1`, `retract/1`, `clause/2` |
| Meta-logical | `findall/3`, `bagof/3`, `setof/3` |
| I/O | `write/1`, `writeln/1`, `nl/0`, `write_canonical/1` |

### Arithmetic Functions

Supported in `is/2` expressions: `+`, `-`, `*`, `/`, `//` (integer division), `mod`, `rem`, `**` (power), `abs`, `max`, `min`, `sqrt`, `floor`, `ceil`, `round`.

## Installation

```bash
cd prolog-engine
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

### Command-Line REPL

```bash
prolog-repl                          # Start with empty database
prolog-repl program.pl               # Load a Prolog source file
prolog-repl -q "program.pl" "query"  # Load file and run query
```

### Python API

```python
from prolog_engine.engine import Engine
from prolog_engine.builtins import register_builtins

engine = Engine()
register_builtins(engine)

# Load Prolog source
engine.load_source("""
    parent(tom, bob).
    parent(tom, liz).
    parent(bob, ann).
    grandparent(X, Z) :- parent(X, Y), parent(Y, Z).
""")

# Run a query
results = engine.query("?- grandparent(tom, X).")
for result in results:
    print(engine.format_solution(result))
# Output: X = ann
```

### Example Programs

**Fibonacci:**
```prolog
fib(0, 0).
fib(1, 1).
fib(N, R) :- N > 1, N1 is N - 1, N2 is N - 2, fib(N1, R1), fib(N2, R2), R is R1 + R2.

% Query: ?- fib(6, X).  →  X = 8
```

**Quicksort:**
```prolog
qsort([], []).
qsort([H|T], Sorted) :-
    partition(H, T, Less, Greater),
    qsort(Less, SortedLess),
    qsort(Greater, SortedGreater),
    append(SortedLess, [H|SortedGreater], Sorted).

partition(_, [], [], []).
partition(Pivot, [H|T], [H|Less], Greater) :- H =< Pivot, partition(Pivot, T, Less, Greater).
partition(Pivot, [H|T], Less, [H|Greater]) :- H > Pivot, partition(Pivot, T, Less, Greater).

% Query: ?- qsort([3, 1, 4, 1, 5], R).  →  R = [1, 1, 3, 4, 5]
```

**Dynamic Programming:**
```prolog
% Add facts at runtime
?- assertz(likes(alice, bob)).
?- assertz(likes(bob, carol)).

% Query the dynamic database
?- likes(X, Y).
% X = alice, Y = bob
% X = bob, Y = carol

% Introspect
?- clause(likes(X, Y), Body).
```

**Findall:**
```prolog
num(1). num(2). num(3). num(4). num(5).
square(X, Y) :- num(X), Y is X * X.

% Query: ?- findall(Y, square(X, Y), Squares).
% Squares = [1, 4, 9, 16, 25]
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## Implementation Notes

- **Occurs-check**: The unifier always performs occurs-check, preventing creation of infinite terms (cyclic structures). This is safer but slightly slower than Prolog systems that skip it.
- **Cut semantics**: Cut (!) in the current implementation prunes all alternative solutions for the current goal, similar to standard Prolog.
- **Depth limit**: Default max depth is 1000 to prevent infinite loops. Override with `engine._max_depth = N`.
- **Variable renaming**: Each clause is renamed (standardized apart) before resolution to prevent variable capture between different rule applications.
- **Atom vs 0-arity compound**: Atoms and 0-arity compounds are handled interchangeably in goal resolution.
- **Generator-based builtins**: All builtins are Python generators that yield substitutions for success and return (yield nothing) for failure, naturally integrating with the backtracking engine.

## Known Issues (Resolved)

The following bugs were found and fixed during development:

1. **Anonymous variable reuse** — Multiple `_` in the same query were treated as the same variable instead of independent variables. **Fix**: Parser generates unique internal names (`__anon_N`) for each `_`.

2. **Unary minus not supported** — `X is -3.` would fail to parse because `-` was only treated as an infix operator. **Fix**: Added unary minus/plus handling in `_parse_primary()`.

3. **Integer division rounding** — Python's `//` rounds toward -infinity, but Prolog's `//` rounds toward zero. For example, `7 // -2` gave -4 (Python) instead of -3 (Prolog). **Fix**: Changed to use `int(a / b)` which rounds toward zero.

4. **Division by zero swallowed** — The `is/2` builtin caught all exceptions including `EngineError`, silently swallowing division-by-zero errors. **Fix**: Introduced `EvaluationError` (subclass of `EngineError`) for non-evaluable expressions, which is caught as failure. Real `EngineError` (division by zero, depth exceeded) now propagates correctly.

5. **Bare `except Exception` masking errors** — All arithmetic builtins used bare `except Exception` which could mask real programming errors. **Fix**: Replaced with specific exception handling: `EvaluationError` → fail, `EngineError` → propagate.

6. **Atom-as-rule-head resolution bug** — Rules with atom heads (e.g., `loop :- loop.`) were treated as facts in the Atom goal handler, skipping the body. **Fix**: Added proper fact/rule dispatch for atom goals.

7. **`=..` (univ) operator not parseable** — The `=..` operator couldn't be tokenized because `.` was lexed separately. **Fix**: Added special multi-character token handling in the lexer for `=..`.

8. **Dead code** — `matching_keys` variable was computed but never used in the engine's compound goal resolution. **Fix**: Removed.

9. **`rem` operator semantics** — `rem` used Python's `%` which differs from Prolog's `rem` for negative numbers. **Fix**: Changed to compute remainder from toward-zero division.

## License

MIT