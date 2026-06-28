# typeinfer — Hindley-Milner Type Inference Engine v2.0

![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)
![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)
![Tests: 200](https://img.shields.io/badge/tests-200-brightgreen.svg)
![Version: 2.0.0](https://img.shields.io/badge/version-2.0.0-orange.svg)

A from-scratch implementation of the **Hindley-Milner (HM) type inference
algorithm** (Algorithm W) for a small purely-functional lambda calculus.
The engine infers principal types for expressions containing lambdas,
let-bindings (with let-polymorphism), conditionals, pattern matching,
algebraic data types, list/string literals, type annotations, and recursive
definitions — all **without any external dependencies**.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Language Reference](#language-reference)
  - [Core Syntax](#core-syntax)
  - [Type Annotations](#type-annotations)
  - [Pattern Matching](#pattern-matching)
  - [Data Type Declarations](#data-type-declarations)
  - [List & String Literals](#list--string-literals)
  - [Parallel Let Bindings](#parallel-let-bindings)
  - [Operator Precedence](#operator-precedence)
- [Built-in Environment](#built-in-environment)
- [Architecture](#architecture)
- [Python API](#python-api)
- [CLI Reference](#cli-reference)
- [Configuration](#configuration)
- [Examples](#examples)
- [REPL](#repl)
- [Error Reporting](#error-reporting)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Changelog](#changelog)
- [Contributing](#contributing)
- [License](#license)

## Overview

`typeinfer` implements **Algorithm W**, the classic Hindley-Milner type
inference algorithm, from scratch. Given an expression in the mini-language,
it computes the **principal (most general) type** of that expression — or
reports a type error explaining why the expression is ill-typed.

The engine processes expressions through a complete pipeline:

```
Source code → Lexer → Parser → AST → Algorithm W → Type
```

**Key capabilities:**

| Feature | Status |
|---------|--------|
| Lambda calculus (multi-arg, curried) | ✅ |
| Let-polymorphism (generalisation/instantiation) | ✅ |
| Let-rec (recursive definitions) | ✅ |
| Conditionals (if-then-else) | ✅ |
| Tuples and unit `()` | ✅ |
| Pattern matching (match/with) | ✅ |
| Algebraic data type declarations | ✅ |
| Type annotations | ✅ |
| List literals `[1, 2, 3]` | ✅ |
| String literals `"hello"` | ✅ |
| Parallel let bindings | ✅ |
| Robinson unification with occurs-check | ✅ |
| Inference trace (--explain) | ✅ |
| Interactive REPL | ✅ |
| Config files (JSON/TOML/YAML) | ✅ |
| JSON output mode | ✅ |

## Installation

```bash
# From the repo (development mode)
cd typeinfer
pip install -e .

# Or just run directly with Python 3.8+
python -m typeinfer "λx. x"
```

No external dependencies are required. YAML config support needs
`pyyaml` (optional):

```bash
pip install pyyaml  # optional, for YAML config files
```

## Quick Start

```bash
# Identity function — the most general type
$ python -m typeinfer "λx. x"
a -> a

# Let-polymorphism: id used at Int and Bool
$ python -m typeinfer "let id = \x. x in (id 1, id true)"
Tuple<Int, Bool>

# Arithmetic with built-ins
$ python -m typeinfer -b "1 + 2 * 3"
Int

# Pattern matching
$ python -m typeinfer -b "match Just 5 with | Nothing -> 0 | Just n -> n"
Int

# Custom data types
$ python -m typeinfer -b "data Tree = Leaf | Node Tree Tree in Node Leaf Leaf"
Tree

# Step-by-step inference trace
$ python -m typeinfer -e "let id = \x. x in id 42"
  variable x : a
  lambda \x. ... : a -> a
  let id = ... : ∀ a. a -> a
  variable id : a -> a
  int literal 42 : Int
  application : Int
=> Int

# JSON output for tooling
$ python -m typeinfer --json -b "[1, 2, 3]"
{"type": "List<Int>"}
```

## Language Reference

### Core Syntax

| Construct | Syntax | Example |
|-----------|--------|---------|
| Integer literal | `42` | `42` |
| Boolean literal | `true` / `false` | `true` |
| String literal | `"..."` | `"hello"` |
| Variable | `x` | `x` |
| Lambda | `λx. body` or `\x. body` | `\x. x` |
| Multi-arg lambda | `\x y z. body` (sugar) | `\x y. x` |
| Application | `f x` | `(\x. x) 42` |
| Let | `let x = e1 in e2` | `let id = \x. x in id 5` |
| Let-rec | `let rec f = \x. ... in ...` | `let rec f = \n. f n in f` |
| If | `if c then a else b` | `if true then 1 else 2` |
| Tuple | `(a, b, ...)` | `(1, true)` |
| Unit | `()` | `()` |
| List literal | `[e1, e2, ...]` | `[1, 2, 3]` |
| Empty list | `[]` | `[]` |
| Operators | `+ - * / < > <= >= == != && \|\|` | `1 + 2 * 3` |
| Unary minus | `-e` | `-5 + 3` |
| Comments | `--` or `#` to end of line | `-- comment` |

### Type Annotations

Type annotations allow you to explicitly specify types for lambda parameters
and let bindings. The inferred type is checked against the annotation and
an error is raised if they don't match.

```
\x: Int. x + 1           -- annotated lambda parameter
let x: Int = 5 in x + 1  -- annotated let binding
\f: Int -> Int. f 5      -- function type annotation
\x: (Int, Bool). x       -- tuple type annotation
\x: List<Int>. x          -- generic type annotation
\x: String. length x     -- string type annotation
```

Supported annotation types:
- `Int`, `Bool`, `String`, `Unit`
- `List<Type>`, `Maybe<Type>`, `Either<Type, Type>`
- `Type -> Type` (function types, right-associative)
- `(Type, Type, ...)` (tuple types)
- Lowercase identifiers are type variables

### Pattern Matching

Pattern matching deconstructs values using constructors and binds variables:

```
match expr with
| pattern1 -> result1
| pattern2 -> result2
| ...
```

Pattern types:
| Pattern | Syntax | Example |
|---------|--------|---------|
| Variable | `x` | `match x with \| y -> y` |
| Wildcard | `_` | `match x with \| _ -> 42` |
| Constructor | `Constr args...` | `match xs with \| Cons x _ -> x` |
| Integer | `42` | `match n with \| 0 -> 1 \| _ -> 0` |
| String | `"hello"` | `match s with \| "hi" -> 0 \| _ -> 1` |
| Tuple | `(p1, p2, ...)` | `match p with \| (a, b) -> a` |

Example:
```
match Cons 1 Nil with
| Nil -> 0
| Cons x _ -> x
```

### Data Type Declarations

Define your own algebraic data types:

```
data TypeName params = Constr1 arg_types | Constr2 arg_types | ... in body
```

Examples:
```
data Tree = Leaf | Node Tree Tree in Node Leaf Leaf
data Color = Red | Green | Blue in match Red with | Red -> 1 | _ -> 0
data Box a = MkBox a in MkBox 5
```

### List & String Literals

List literals are desugared to `Cons`/`Nil` applications:

```
[1, 2, 3]   -- List<Int>
[]          -- List<a> (polymorphic empty list)
[true, false]  -- List<Bool>
```

String literals have type `String` and support escape sequences:
```
"hello"     -- String
"hello\n"  -- with newline escape
"a\tb"     -- with tab escape
```

### Parallel Let Bindings

Multiple bindings in a single `let` are evaluated in parallel (each
binding is in scope only in the body, not in other bindings):

```
let x = 1 and y = 2 and z = 3 in x + y + z
```

### Operator Precedence

| Level | Operators | Associativity |
|-------|-----------|---------------|
| 1 | `&&` `\|\|` | right |
| 2 | `==` `!=` `<` `>` `<=` `>=` | left |
| 3 | `+` `-` | left |
| 4 | `*` `/` | left |
| 5 | application | left |
| 6 | unary `-` | prefix |

Infix operators desugar to applications: `a + b` → `((+) a) b`.

## Built-in Environment

When `--builtins` is passed (or `use_builtins=True` in Python), the
following identifiers are available:

| Category | Names | Type |
|----------|-------|------|
| Arithmetic | `+ - * /` | `Int -> Int -> Int` |
| Comparison | `< > <= >=` | `Int -> Int -> Bool` |
| Equality | `== !=` | `∀a. a -> a -> Bool` |
| Boolean | `&& \|\| not` | `Bool -> Bool -> Bool` / `Bool -> Bool` |
| Negation | `neg` | `Int -> Int` |
| List ADT | `Nil` / `Cons` | `∀a. List<a>` / `∀a. a -> List<a> -> List<a>` |
| Maybe ADT | `Nothing` / `Just` | `∀a. Maybe<a>` / `∀a. a -> Maybe<a>` |
| Either ADT | `Left` / `Right` | `∀a b. a -> Either<a,b>` / `∀a b. b -> Either<a,b>` |
| String | `length concat append reverse toUpper toLower substring charAt` | various |
| Pair | `fst` / `snd` | `∀a b. (a,b) -> a` / `∀a b. (a,b) -> b` |
| IO | `print printS printB read readS` | various |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Source Code                        │
│                   "λx. x + 1"                        │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│                    Lexer (lexer.py)                  │
│  Tokenises source into a list of Token objects.     │
│  Handles: keywords, identifiers, integers, strings,  │
│  operators, comments (-- and #), escape sequences.   │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│                   Parser (parser.py)                  │
│  Recursive-descent parser with operator-precedence  │
│  climbing. Builds AST of Expr nodes.                │
│  Handles: let/let-rec, parallel let, if, lambda,    │
│  match, data declarations, type annotations,        │
│  tuples, lists, operator desugaring.                │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│               Inference Engine (inference.py)         │
│  Algorithm W — walks AST, produces type equations.  │
│  • Generalisation at let sites                      │
│  • Instantiation at use sites                        │
│  • Pattern matching type inference                   │
│  • Data type declaration processing                  │
│  • Type annotation checking                          │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│            Unification Engine (unify.py)              │
│  Robinson-style unification with occurs-check.       │
│  • Substitution composition                          │
│  • Environment application                           │
│  • Occurs-check (prevents infinite types)             │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│                   Inferred Type                        │
│                   "Int -> Int"                        │
└─────────────────────────────────────────────────────┘
```

### Module Structure

```
typeinfer/
├── typeinfer/
│   ├── __init__.py      # public API re-exports
│   ├── __main__.py      # CLI (argparse) + REPL
│   ├── config.py        # config system (JSON/TOML/YAML)
│   ├── types.py         # Type representations + annotation resolution
│   ├── lexer.py         # tokenizer
│   ├── parser.py        # recursive-descent parser + AST nodes + patterns
│   ├── unify.py         # Robinson unification + substitutions
│   ├── inference.py     # Algorithm W + pattern match inference
│   └── primitives.py    # built-in typing environments
├── tests/
│   ├── test_typeinfer.py  # core tests (98)
│   ├── test_bugs.py       # bug-hunt tests (11)
│   └── test_features.py   # new feature tests (91)
├── examples/
│   ├── 01_identity.tc
│   ├── 02_let_polymorphism.tc
│   ├── 03_recursion.tc
│   ├── 04_type_annotations.tc
│   ├── 05_pattern_matching.tc
│   ├── 06_data_types.tc
│   ├── 07_lists_and_strings.tc
│   ├── 08_parallel_let.tc
│   └── api_demo.py
├── .github/workflows/ci.yml
├── CONTRIBUTING.md
├── LICENSE
├── pyproject.toml
└── README.md
```

## Python API

```python
from typeinfer import (
    infer, infer_with_trace, type_to_string,
    INT, BOOL, STRING, UNIT,
    Config, load_config,
)

# Basic inference
print(type_to_string(infer(r"\x. x")))            # a -> a
print(type_to_string(infer(r"let id = \x. x in (id 1, id true)")))
# Tuple<Int, Bool>

# With built-in primitives
print(type_to_string(infer(r"\x. x + 1", use_builtins=True)))   # Int -> Int
print(type_to_string(infer("[1, 2, 3]", use_builtins=True)))    # List<Int>
print(type_to_string(infer('"hello"', use_builtins=True)))      # String

# Type annotations
print(type_to_string(infer(r"\x: Int. x + 1", use_builtins=True)))  # Int -> Int

# Pattern matching
print(type_to_string(infer(
    r"match Just 5 with | Nothing -> 0 | Just n -> n",
    use_builtins=True
)))  # Int

# Data types
print(type_to_string(infer(
    "data Tree = Leaf | Node Tree Tree in Node Leaf Leaf",
    use_builtins=True
)))  # Tree

# Inference trace
from typeinfer import infer_with_trace
t, steps = infer_with_trace(r"let id = \x. x in id 42")
for s in steps:
    print(s)
print("=>", type_to_string(t))

# Configuration
cfg = load_config("config.json")
t = infer("1 + 2", use_builtins=cfg.builtins)
```

## CLI Reference

```
usage: typeinfer [-h] [-b] [-e] [--ast] [--repl] [--file PATH]
                 [--json] [--config PATH] [--no-builtins] [--version]
                 [expression]

Hindley-Milner type inference engine (Algorithm W) for a small lambda calculus.

positional arguments:
  expression            Expression to infer (e.g. "λx. x")

options:
  -h, --help            show this help message and exit
  -b, --builtins        load built-in primitives
  -e, --explain         print step-by-step inference trace
  --ast                 print the parsed AST instead of the type
  --repl                start an interactive REPL
  --file, -f PATH       read expression from a file
  --json                output result as JSON
  --config PATH         load configuration from a JSON/TOML/YAML file
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        set the logging level
  --no-builtins         explicitly disable built-in primitives
  --version             print version and exit
```

### CLI Examples

```bash
# Basic inference
python -m typeinfer "\x. x"                     # a -> a
python -m typeinfer "let id = \x. x in id 42"    # Int

# With built-in primitives
python -m typeinfer -b "\x. x + 1"               # Int -> Int
python -m typeinfer -b "1 + 2 * 3"               # Int
python -m typeinfer -b "Cons 1 Nil"              # List<Int>
python -m typeinfer -b "[1, 2, 3]"               # List<Int>
python -m typeinfer -b '"hello"'                  # String

# Pattern matching
python -m typeinfer -b 'match Just 5 with | Nothing -> 0 | Just n -> n'  # Int

# Custom data types
python -m typeinfer -b 'data Tree = Leaf | Node Tree Tree in Leaf'  # Tree

# Type annotations
python -m typeinfer -b '\x: Int -> Int. x 5'     # (Int -> Int) -> Int

# Step-by-step trace
python -m typeinfer -e "let id = \x. x in id 42"

# Show the parsed AST
python -m typeinfer --ast "\x. x + 1"

# Read from file
python -m typeinfer --file program.tc

# JSON output
python -m typeinfer --json -b "[1, 2, 3]"        # {"type": "List<Int>"}

# With config file
python -m typeinfer --config .typeinfer.json "1 + 2"

# Interactive REPL
python -m typeinfer --repl

# Version
python -m typeinfer --version
```

## Configuration

Configuration files can be in JSON, TOML, or YAML format:

```json
{
  "builtins": true,
  "explain": false,
  "log_level": "WARNING",
  "max_type_vars": 10000
}
```

```toml
builtins = true
explain = false
log_level = "WARNING"
max_type_vars = 10000
```

```python
from typeinfer import Config, load_config, save_config

# Load from file
cfg = load_config("config.json")

# Create programmatically
cfg = Config(builtins=True, log_level="DEBUG")

# Save to file
save_config("config.toml", cfg)
```

Config options:
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `builtins` | bool | `true` | Load built-in primitives by default |
| `explain` | bool | `false` | Print inference trace by default |
| `log_level` | str | `"WARNING"` | Logging level |
| `data_types` | dict | `{}` | User-defined data types |
| `initial_env` | dict | `{}` | Custom type environment entries |
| `max_type_vars` | int | `10000` | Safety limit on fresh variable generation |

## Examples

See the `examples/` directory for usage demos:

| File | Description |
|------|-------------|
| `01_identity.tc` | Identity function |
| `02_let_polymorphism.tc` | Let-polymorphism |
| `03_recursion.tc` | Recursive functions |
| `04_type_annotations.tc` | Type annotations |
| `05_pattern_matching.tc` | Pattern matching (map function) |
| `06_data_types.tc` | Custom data types |
| `07_lists_and_strings.tc` | List and string literals |
| `08_parallel_let.tc` | Parallel let bindings |
| `api_demo.py` | Python API demonstration |

Run them:
```bash
python -m typeinfer -b --file examples/01_identity.tc
python examples/api_demo.py
```

## REPL

The interactive REPL supports these commands:

| Command | Action |
|---------|--------|
| `:t <expr>` | Infer and print the type |
| `:e <expr>` | Infer and print the trace + type |
| `:b` | Toggle built-in primitives on/off |
| `:c <file>` | Load a config file |
| `:h` | Show help |
| `:q` | Quit |

```
$ python -m typeinfer --repl
typeinfer 2.0.0 REPL
:q to quit, :t <expr> for type, :e <expr> for trace, :h for help
>>> :t \x. x
a -> a
>>> :t 1 + 2
Int
>>> :e let id = \x. x in id 42
  variable x : a
  lambda \x. ... : a -> a
  let id = ... : ∀ a. a -> a
  variable id : a -> a
  int literal 42 : Int
  application : Int
=> Int
>>> :q
```

## Error Reporting

The engine detects and reports:

- **Lexical errors** — invalid characters, unterminated strings.
- **Syntax errors** — unexpected / trailing tokens, missing keywords.
- **Unbound variables** — use of an identifier not in scope.
- **Type mismatches** — failure to unify two types (e.g. `1 + true`).
- **Occurs-check failures** — infinite types such as `\x. x x`.
- **Branch mismatches** — `if c then a else b` where `a` and `b` have
  different types, or `c` is not `Bool`.
- **Annotation mismatches** — type annotation doesn't match inferred type.
- **Pattern match errors** — inconsistent alternative types.
- **Config errors** — invalid config format or values.

Error messages include the types involved and the reason:
```
error: Cannot unify Int with Bool: different type constructors
error: Cannot unify a with a -> b: occurs check failed (infinite type)
error: Unbound variable: 'foo'
```

## Known Issues (Resolved)

The following bugs were found during the Phase 3 bug hunt and have been
fixed. Each fix is covered by tests in `tests/test_bugs.py`.

1. **Single-element tuple with trailing comma** — `(1,)` caused a parser
   error because the parser only supported tuples with ≥2 elements.
   *Fix*: the parser now allows a trailing comma after any tuple element.

2. **Unary minus not supported** — `-5` failed to parse because `-` was
   only treated as a binary operator.
   *Fix*: added a `_parse_unary` production that desugars prefix `-` into
   an application of `neg : Int -> Int`.

3. **Error reason lost in `_format_unify_error`** — the human-friendly
   error wrapper discarded the reason string from `UnificationError`.
   *Fix*: the reason is now extracted and appended.

4. **Trace printed raw type-variable ids** — the `--explain` trace for a
   polymorphic `let` displayed `∀0` instead of `∀ a`.
   *Fix*: the let trace now uses `scheme_to_string`.

5. **`scheme_to_string` inconsistent variable naming** — renumbered the
   type and then applied names to the *original* type.
   *Fix*: rewrote with a single consistent mapping.

## Changelog

### v2.0.0 — Comprehensive Improvement

**New Features:**
- **String literals** with escape sequences (`"hello\n"`)
- **List literals** (`[1, 2, 3]`, `[]`)
- **Pattern matching** (`match expr with | pattern -> result ...`)
  - Variable, wildcard, constructor, integer, string, tuple patterns
- **Algebraic data type declarations** (`data Tree = Leaf | Node Tree Tree in ...`)
- **Type annotations** for lambda parameters and let bindings
- **Parallel let bindings** (`let x = e1 and y = e2 in body`)
- **Either ADT** (`Left` / `Right`)
- **Pair primitives** (`fst` / `snd`)
- **IO primitives** (`print` / `read` typing)
- **String primitives** (`length`, `concat`, `reverse`, `toUpper`, etc.)
- **Config system** (JSON/TOML/YAML)
- **JSON output mode** for CLI
- **File input** (`--file`)
- **Logging** integration
- **`#` comments** (in addition to `--`)

**Improvements:**
- Migrated CLI from manual flag parsing to `argparse`
- Added `--config`, `--file`, `--json`, `--log-level`, `--no-builtins` flags
- REPL now supports `:c` (config load) and `:h` (help)
- Type annotation resolution system
- 102 new tests (200 total, up from 98)
- Example files and API demo script
- CONTRIBUTING.md and LICENSE
- GitHub Actions CI

### v1.0.0 — Initial Release
- Hindley-Milner Algorithm W
- Lexer, parser, unification, inference
- Let-polymorphism, let-rec
- Tuples, unit, ADT constructors
- Built-in primitives
- Inference trace, REPL, CLI
- 98 tests, 5 bugs fixed

## Roadmap

- [ ] Type class constraints (Eq, Ord, Show)
- [ ] List comprehensions
- [ ] Do-notation / monadic sugar
- [ ] Partial type signatures (wildcards in annotations)
- [ ] Exhaustiveness checking for pattern matches
- [ ] Type pretty-printing with minimal parentheses
- [ ] Source position tracking for better error messages
- [ ] WebAssembly/WASM backend (experimental)
- [ ] Interoperability with other type systems (System F, F<:)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

To run tests:
```bash
pip install -e .
pip install pytest
python -m pytest -v
```

## License

MIT — see [LICENSE](LICENSE).