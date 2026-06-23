# Scheme Interpreter

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Tests](https://img.shields.io/badge/tests-215%20passing-brightgreen.svg)
![Version](https://img.shields.io/badge/version-2.0.0-orange.svg)

A from-scratch Scheme interpreter in pure Python (zero dependencies) implementing a substantial subset of **R5RS Scheme**, featuring tail-call optimization, first-class continuations, hygienic macros, a standard library, and 150+ built-in procedures.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [REPL](#repl)
  - [Running Scripts](#running-scripts)
  - [Command-Line Options](#command-line-options)
  - [Python API](#python-api)
- [Architecture](#architecture)
- [Standard Library](#standard-library)
- [Examples](#examples)
- [Testing](#testing)
- [Recent Improvements (v2.0)](#recent-improvements-v20)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

This is a complete, working Scheme interpreter written in pure Python with **no external dependencies**. It implements a large subset of the R5RS specification, including the hard parts: proper tail-call optimization (via a trampoline), `call/cc` first-class continuations, and hygienic `syntax-rules` macros with ellipsis pattern matching.

The interpreter was built from scratch in ~4,300 lines of Python and has been comprehensively tested with 215 passing tests covering every major feature.

## Features

### Core Language
- **Lexer**: Integers, floats, exact rationals (`3/4`), strings, symbols, booleans (`#t`/`#f`), characters (`#\a`, `#\space`), comments (line `;`, block `#| |#`, datum `#;`), quote/quasiquote/unquote, vectors, and prefixed numbers (`#b`, `#o`, `#d`, `#x`, `#e`, `#i`)
- **Parser**: Recursive-descent parser producing nested Scheme data structures; quasiquote expansion into `cons`/`list`/`append` at parse time
- **23 Special Forms**: `lambda`, `define`, `if`, `cond`, `case`, `let`, `let*`, `letrec`, `letrec*`, `begin`, `set!`, `and`, `or`, `when`, `unless`, `do`, `delay`, `quasiquote`, `define-syntax`, `let-syntax`, `letrec-syntax`, `rec`, `let-values`, `define-values`
- **Tail-Call Optimization**: Trampoline-based TCO prevents stack overflow on deep recursion — verified with 1,000,000-deep tail recursion
- **First-Class Continuations**: Full `call/cc` support via escape continuations (covers generators, early returns, escape patterns)
- **Hygienic Macros**: `define-syntax` with `syntax-rules` pattern matching, ellipsis (`...`) capture, literal handling, and systematic renaming
- **Closures & Lexical Scoping**: Proper lexical scoping with environment chains
- **Multiple Values**: `values` / `call-with-values` / `let-values` / `define-values`

### Standard Library (auto-loaded)
- **Higher-order**: `compose`, `negate`, `conjoin`, `disjoin`
- **Numeric**: `square`, `cube`, `average`, `inc`, `dec`
- **String**: `string-prefix?`, `string-suffix?`, `string-trim`, `string-reverse`
- **Streams**: `cons-stream`, `stream-car`, `stream-cdr`, `stream-map`, `stream-filter`, `stream-take`, `stream-for-each`, `stream-ref`
- **Sets**: `set-member`, `set-adjoin`, `set-union`, `set-intersection`, `set-difference`
- **Lists**: `list-of?`, `iota`, `list-tabulate`, `any`, `every`, `alist-cons`, `alist-copy`, `alist-delete`

### 150+ Built-in Procedures
Arithmetic (`+`, `-`, `*`, `/`, `modulo`, `remainder`, `quotient`, `abs`, `min`, `max`, `gcd`, `lcm`, `expt`, `sqrt`), comparisons (`<`, `>`, `<=`, `>=`, `=`), predicates (`number?`, `integer?`, `rational?`, `real?`, `exact?`, `inexact?`, `zero?`, `positive?`, `negative?`, `odd?`, `even?`, `null?`, `pair?`, `list?`, `boolean?`, `procedure?`, `char?`, `string?`, `vector?`, `symbol?`, `eof-object?`), pair/list operations (`cons`, `car`, `cdr`, `cadr`...`cddddr`, `list`, `length`, `reverse`, `append`, `list-ref`, `list-tail`, `member`, `memv`, `memq`, `assoc`, `assv`, `assq`, `map`, `for-each`, `filter`, `reduce`, `fold-left`, `fold-right`, `sort`, `list-copy`, `list-head`, `list-position`, `list-count`, `list-min`, `list-max`, `for-all`, `exists`, `zip`, `unfold`), string operations (`string-length`, `string-ref`, `substring`, `string-append`, `string->list`, `list->string`, `string->number`, `number->string`, `string->symbol`, `symbol->string`, `string=?`, `string<?`, `string>?`, `string<=?`, `string>=?`, `string-upcase`, `string-downcase`, `string-contains`, `string-split`, `string-join`, `string-repeat`, `string-starts-with?`, `string-ends-with?`, `string-replace`), character operations (`char->integer`, `integer->char`, `char=?`, `char<?`, `char>?`, `char-upcase`, `char-downcase`, `char-alphabetic?`, `char-numeric?`, `char-whitespace?`), vector operations (`make-vector`, `vector`, `vector-ref`, `vector-set!`, `vector-length`, `vector->list`, `list->vector`, `vector-fill!`), I/O (`display`, `write`, `newline`, `write-char`, `read`, `read-char`, `read-line`, `open-input-file`, `open-output-file`, `close-port`), math functions (`sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `log`, `exp`, `floor`, `ceiling`, `round`, `truncate`, `log2`, `log10`, `hypot`, `atan2`, `sign`, `degrees->radians`, `radians->degrees`), and more (`eq?`, `eqv?`, `equal?`, `not`, `apply`, `eval`, `force`, `values`, `call-with-values`, `call/cc`, `error`, `exit`, `load`, `trace`, `untrace`, `time`, `assert`, `random`, `gensym`, `identity`)

### Development Tools
- **Trace**: `(trace 'function-name)` prints entry/exit for each call
- **Time**: `(time '(+ 1 2))` measures execution time
- **Assert**: `(assert condition "message")` for runtime assertions
- **Load**: `(load "file.scm")` loads and evaluates a Scheme file
- **Logging**: Configurable via `SCHEME_LOG_LEVEL` environment variable or `--log-level` CLI flag

## Installation

```bash
# From the project directory
cd scheme-interpreter
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

This installs the `scheme` command-line tool.

## Quick Start

```bash
# Start the REPL
scheme

# Run a script
scheme examples/fibonacci.scm --no-repl

# Evaluate an expression
scheme -e '(+ 1 2 3)'

# Load stdlib + run a script
scheme -l mylib.scm script.scm
```

## Usage

### REPL

```bash
$ scheme
scheme> (+ 1 2 3)
6
scheme> (define (factorial n) (if (= n 0) 1 (* n (factorial (- n 1)))))
scheme> (factorial 10)
3628800
scheme> (map square (list 1 2 3 4 5))
(1 4 9 16 25)
scheme> (exit)
$
```

### Running Scripts

```bash
# Run a script and exit
scheme examples/fibonacci.scm --no-repl

# Run a script, then enter REPL
scheme examples/fibonacci.scm

# Evaluate an expression
scheme -e '(let ((x 10) (y 20)) (+ x y))'
```

### Command-Line Options

```
usage: scheme [-h] [file] [-e EXPR] [-l FILE] [--no-repl] [--no-stdlib]
              [--version] [--config FILE] [--log-level LEVEL]

positional arguments:
  file                  Scheme script to run

options:
  -e, --eval EXPR       Evaluate expression and print result
  -l, --load FILE       Load a Scheme file before evaluating
  --no-repl             Don't start REPL after running script
  --no-stdlib           Don't auto-load the standard library
  --version             Show version and exit
  --config FILE         Load a JSON/TOML configuration file
  --log-level LEVEL     Set logging verbosity (DEBUG/INFO/WARNING/ERROR/CRITICAL)
```

### Python API

```python
from scheme_interpreter import run

# Evaluate a Scheme expression
result = run('(+ 1 2 3)')
print(result)  # 6

# Use the standard library
result = run('(map square (list 1 2 3 4 5))')
print(result)  # (1 4 9 16 25)

# Streams (lazy sequences)
result = run('''
    (define (integers-from n) (cons-stream n (integers-from (+ n 1))))
    (define naturals (integers-from 1))
    (stream-take naturals 10)
''')
print(result)  # (1 2 3 4 5 6 7 8 9 10)
```

## Architecture

```
┌─────────────┐     ┌──────────┐     ┌──────────────┐
│  Source Code │────▶│  Lexer   │────▶│   Parser     │
│  (Scheme)    │    │ lexer.py │    │  parser.py   │
└─────────────┘     └──────────┘    └──────┬───────┘
                                           │ s-expressions
                                           ▼
┌─────────────────────────────────────────────────────┐
│                    Interpreter                       │
│                  interpreter.py                      │
│  ┌─────────────────────────────────────────────┐    │
│  │  Trampoline Loop (Tail-Call Optimization)    │    │
│  │  ┌─────────────────────────────────────┐    │    │
│  │  │  Special Forms Dispatch Table        │    │    │
│  │  │  (if, lambda, let, cond, case, ...) │    │    │
│  │  └─────────────────────────────────────┘    │    │
│  │  ┌─────────────────────────────────────┐    │    │
│  │  │  Macro Expander (syntax-rules)       │    │    │
│  │  │  macro_expander.py                   │    │    │
│  │  └─────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────┐    │
│  │  Environment Chain (lexical scoping)          │    │
│  │  environment.py                              │    │
│  └─────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────┐    │
│  │  Primitives (150+ built-in procedures)       │    │
│  │  primitives.py                              │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────┐
│  Standard Library (stdlib.scm)     │
│  Auto-loaded on startup            │
└─────────────────────────────────────┘
```

### How Tail-Call Optimization Works

The interpreter uses a **trampoline** pattern: instead of Python recursion, tail positions return a `TailCall(expr, env)` sentinel. The trampoline loop re-dispatches these without growing the Python stack:

```python
def _trampoline(self, expr, env):
    while True:
        result = self._eval_step(expr, env)
        if isinstance(result, TailCall):
            expr = result.expr
            env = result.env
            continue
        return result
```

This allows unbounded tail recursion — verified with 1,000,000-deep tail calls without stack overflow.

### How call/cc Works

`call/cc` is implemented via escape continuations: when a continuation is invoked, a `ContinuationInvoked` exception is raised with a unique tag. The `call/cc` handler catches it and returns the passed value:

```python
def call_cc(proc):
    tag = object()
    cont = Continuation(tag)
    try:
        return self._apply(proc, [cont])
    except ContinuationInvoked as ci:
        if ci.tag is tag:
            return ci.value
        raise
```

### How Macros Work

The `syntax-rules` macro system:
1. **Pattern matching**: Matches input forms against patterns with wildcards (`_`), literals, and ellipsis (`...`) for variable-arity capture
2. **Hygiene**: Pattern variables are renamed to avoid capture of identifiers introduced by the macro
3. **Template instantiation**: Templates are filled in with matched bindings, with ellipsis expansion

## Standard Library

The standard library (`stdlib.scm`) is automatically loaded on interpreter startup. It provides:

| Category | Functions |
|----------|-----------|
| **Composition** | `compose`, `negate`, `conjoin`, `disjoin` |
| **Numeric** | `square`, `cube`, `average`, `inc`, `dec` |
| **String** | `string-prefix?`, `string-suffix?`, `string-trim`, `string-reverse` |
| **Streams** | `cons-stream`, `stream-car`, `stream-cdr`, `stream-map`, `stream-filter`, `stream-take`, `stream-for-each`, `stream-ref` |
| **Sets** | `set-member`, `set-adjoin`, `set-union`, `set-intersection`, `set-difference` |
| **Lists** | `list-of?`, `iota`, `list-tabulate`, `any`, `every` |
| **Alists** | `alist-cons`, `alist-copy`, `alist-delete` |

To skip loading the standard library, use `--no-stdlib` or construct the interpreter with `load_stdlib=False`.

## Examples

### Fibonacci with TCO

```scheme
;; examples/fibonacci.scm
(define (fib n)
  (let loop ((i 0) (a 0) (b 1))
    (if (= i n) a (loop (+ i 1) b (+ a b)))))

(display "fib(30) = ") (display (fib 30)) (newline)
;; Output: fib(30) = 832040
```

### Infinite Streams (Sieve of Eratosthenes)

```scheme
;; examples/streams.scm
(define (integers-from n)
  (cons-stream n (integers-from (+ n 1))))

(define (sieve s)
  (cons-stream (stream-car s)
               (sieve (stream-filter
                        (lambda (x) (not (= (modulo x (stream-car s)) 0)))
                        (stream-cdr s)))))

(define primes (sieve (integers-from 2)))
(display (stream-take primes 20))
;; Output: (2 3 5 7 11 13 17 19 23 29 31 37 41 43 47 53 59 61 67 71)
```

### call/cc for Early Return

```scheme
;; examples/callcc.scm
(define (find pred lst)
  (call/cc
    (lambda (k)
      (for-each (lambda (x) (if (pred x) (k x) #f)) lst)
      #f)))

(display (find even? '(1 3 5 6 7)))
;; Output: 6
```

### Hygienic Macros

```scheme
;; examples/macros.scm
(define-syntax swap!
  (syntax-rules ()
    ((swap! a b)
     (let ((tmp a)) (set! a b) (set! b tmp)))))

(define-syntax while
  (syntax-rules ()
    ((while test body ...)
     (let loop () (if test (begin body ... (loop)) #f)))))
```

### Y Combinator

```scheme
(define Y
  (lambda (f)
    ((lambda (x) (f (lambda (v) ((x x) v))))
     (lambda (x) (f (lambda (v) ((x x) v)))))))

(define fact-y
  (Y (lambda (fact)
       (lambda (n) (if (= n 0) 1 (* n (fact (- n 1))))))))

(display (fact-y 5))
;; Output: 120
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=scheme_interpreter --cov-report=term-missing

# Run specific test class
pytest tests/test_v2.py::TestStreams -v
```

All 215 tests pass, covering:
- Lexer (integers, floats, rationals, strings, booleans, chars, comments, prefixes)
- Parser (atoms, lists, nested, dotted, vectors, quote, quasiquote)
- Arithmetic and comparisons
- Predicates (all type predicates, zero?, positive?, odd?, even?)
- Special forms (define, lambda, if, let, let*, letrec, cond, case, and, or, when, unless, do, delay/force, quasiquote)
- Tail-call optimization (1M-deep recursion, mutual recursion, named let)
- call/cc (basic, nested, early return)
- List operations (cons, car, cdr, map, filter, fold, sort, etc.)
- String and character operations
- Vector operations
- Macros (simple, swap!, ellipsis, while, with literals)
- Error handling
- Eq predicates (eq?, eqv?, equal?)
- Standard library (compose, negate, streams, sets, etc.)
- New special forms (rec, let-values, define-values)
- New builtins (trace, untrace, time, assert, load)
- Bug fixes (if/cond with or, apply with various types)

## Recent Improvements (v2.0)

### New Features
- **Standard library** (`stdlib.scm`): 30+ utility functions auto-loaded on startup
- **New special forms**: `rec` (recursive named expression), `let-values` (destructuring let), `define-values` (multiple value definition)
- **New builtins**: `load`, `trace`/`untrace`, `time`, `assert`, and 20+ new primitives (`zip`, `unfold`, `string-join`, `string-repeat`, `string-replace`, `sign`, `log2`, `log10`, `hypot`, `atan2`, `degrees->radians`, `radians->degrees`, `eof-object?`, etc.)
- **Enhanced CLI**: `--version`, `--config`, `--log-level`, `--no-stdlib` flags; JSON/TOML config file support
- **Logging**: Configurable via `SCHEME_LOG_LEVEL` environment variable or CLI flag
- **Python API**: `run()` convenience function and `repl()` entry point

### Bug Fixes
- **Critical: `if` with `or`/`and`** — The `if` and `cond` special forms used `_eval_step` instead of `seval` for test conditions, causing `TailCall` objects to be treated as truthy. Fixed by using `seval` (full trampoline) for condition evaluation.
- **`apply` with non-list arguments** — `apply` crashed when the last argument was not a Pair. Fixed to handle Vectors, Python lists, and single non-list arguments.
- **`_make_math` closure bug** — The loop variable `fname` was captured by reference instead of by value. Fixed by passing `fn_name` to the inner function.
- **`is_self_evaluating` broken reference** — Referenced undefined `UnspecifiedType` via a `if False else type(None)` hack. Fixed to use proper type checks.
- **`NilType` references** — Multiple `NilType if False else type(Nil)` patterns cleaned up to use proper `NilType`.
- **`scheme_eqv` Python bool handling** — Python `True`/`False` were being treated as Scheme numbers. Added explicit bool exclusion.
- **`scheme_equal` cross-type numeric** — `equal?` now handles `int` vs `Fraction` comparisons correctly.

### Code Quality
- Added comprehensive docstrings to all classes and public methods
- Added type hints throughout
- Improved error messages with context
- Added `CONTRIBUTING.md` with development setup guide
- Added `LICENSE` file
- 83 new tests covering all new features and bug fixes

## Roadmap

### Planned Features
- [ ] Full reified continuations (CPS conversion) for non-escape `call/cc`
- [ ] `cond-expand` for conditional compilation
- [ ] R6RS-style exception handling (`guard`, `raise`, `raise-continuable`)
- [ ] SRFI support (SRFI-1 lists, SRFI-13 strings, SRFI-69 hash tables)
- [ ] Module system (`define-library`, `import`, `export`)
- [ ] String ports (`open-input-string`, `open-output-string`)
- [ ] Binary I/O (`read-byte`, `write-byte`, `bytevector`)
- [ ] Proper tail recursion in `map`/`for-each` (currently uses Python loops)
- [ ] Compiler to bytecode for faster execution
- [ ] Source location tracking in error messages (line/col in ParseError)
- [ ] Interactive debugger for unhandled errors

### Known Limitations
- `call/cc` implements escape continuations only (no re-entry after return)
- `string-set!` is not supported (strings are immutable)
- No `eval` with custom environments (evaluates in global env)
- Macro expansion happens at evaluation time, not at definition time
- No numeric tower (complex numbers not supported)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, architecture overview, and coding standards.

## License

MIT License — see [LICENSE](LICENSE) for details.