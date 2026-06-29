# 🚀 Forth Interpreter

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 140](https://img.shields.io/badge/tests-140%20passing-brightgreen.svg)](#testing)
[![Words: 120+](https://img.shields.io/badge/words-120%2B-orange.svg)](#built-in-words)

> A stack-based Forth language interpreter implemented from scratch in pure Python — with compilation to bytecode IR, 120+ built-in words, full control flow, exception handling, string operations, arrays, file inclusion, and a modular architecture.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Interactive REPL](#interactive-repl)
  - [Command-Line Interface](#command-line-interface)
  - [Python API](#python-api)
  - [Configuration Files](#configuration-files)
- [Built-in Words](#built-in-words)
- [Examples](#examples)
- [Architecture](#architecture)
- [Testing](#testing)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Changelog](#changelog)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## Overview

This project implements a fully functional Forth interpreter supporting:

- **Integer and float arithmetic** — `+`, `-`, `*`, `/`, `MOD`, `F+`, `FSQRT`, `FSIN`, ...
- **Stack manipulation** — `DUP`, `DROP`, `SWAP`, `OVER`, `ROT`, `PICK`, `ROLL`, `2DUP`, ...
- **Variables, constants, values, and arrays** — `VARIABLE`, `CONSTANT`, `VALUE`, `ARRAY`, `[]!`, `[]@`
- **Colon definitions** compiled to bytecode IR — `: SQUARE DUP * ;`
- **All major control flow** — `IF/ELSE/THEN`, `BEGIN/UNTIL`, `BEGIN/WHILE/REPEAT`, `DO/LOOP`, `DO/+LOOP`, `LEAVE`, `EXIT`, `RECURSE`, `CASE/OF/ENDOF/ENDCASE`
- **String operations** — `."`, `STRLEN`, `STRCAT`, `CMP-STR`, `SUBSTR`, `CHAR`, `[CHAR]`, `C"`
- **Memory operations** — `!`, `@`, `+!`, `ERASE`, `FILL`, `MOVE`
- **Exception handling** — `CATCH`, `THROW`, `ABORT`, `ABORT"`
- **File inclusion** — `INCLUDE`
- **Bitwise operations** — `AND`, `OR`, `XOR`, `INVERT`, `LSHIFT`, `RSHIFT`
- **Random number generation** — `SEED`, `RANDOM`
- **Interactive REPL** with error recovery
- **Configurable** stack and recursion limits

## Installation

```bash
# From the forth-interpreter directory:
pip install -e .

# With development dependencies (pytest, pyyaml):
pip install -e ".[dev]"
```

Or run directly without installation:

```bash
python3 -m forth -e '5 DUP * . CR'
```

## Quick Start

```
$ python3 -m forth
Forth Interpreter v3.0.0 — type BYE to exit, WORDS for word list
ok 3 4 + . CR
7
ok : SQUARE DUP * ; 5 SQUARE . CR
25
ok 10 0 DO I . LOOP CR
0 1 2 3 4 5 6 7 8 9
ok BYE
```

## Usage

### Interactive REPL

```bash
python3 -m forth
```

The REPL supports multi-line definitions, error recovery, and all built-in words:

```
ok : FACT DUP 1 > IF DUP 1- RECURSE * THEN ;
ok 5 FACT . CR
120
ok WORDS
```

### Command-Line Interface

```bash
# Evaluate a code string
python3 -m forth -e '5 DUP * . CR'

# Execute a file
python3 -m forth -f examples/primes.fs
python3 -m forth -f examples/fibonacci.fs

# Start REPL with no banner
python3 -m forth --no-banner

# With debug logging
python3 -m forth -f program.fs --debug

# With a config file
python3 -m forth -c config.json -e '42 . CR'

# Print version
python3 -m forth --version

# Custom stack size and recursion limit
python3 -m forth --stack-size 50000 --max-recursion 1000
```

**CLI Flags:**

| Flag | Description |
|------|-------------|
| `-e CODE` | Evaluate Forth code string |
| `-f FILE` | Execute a Forth source file |
| `-i` | Start interactive REPL |
| `-c CONFIG` | Path to JSON/YAML config file |
| `--debug` | Enable debug logging |
| `--no-banner` | Suppress the REPL banner |
| `--stack-size N` | Maximum data-stack depth (default: 10000) |
| `--max-recursion N` | Maximum recursion depth (default: 500) |
| `--version` | Print version and exit |

### Python API

```python
from forth import ForthInterpreter
import io

# Basic usage
out = io.StringIO()
interp = ForthInterpreter(output=out)
interp.eval(': SQUARE DUP * ; 5 SQUARE . CR')
print(out.getvalue())  # "25 \n"

# With custom limits
interp = ForthInterpreter(max_recursion=1000, max_stack=50000)

# Error handling
try:
    interp.eval('1 0 / .')
except Exception as e:
    print(f"Forth error: {e}")

# Access the stack directly
interp.eval('1 2 3')
print(interp.stack)  # [1, 2, 3]
```

### Configuration Files

JSON or YAML config files can override interpreter defaults:

```json
{
    "max_recursion": 1000,
    "max_stack": 50000,
    "debug": false,
    "no_banner": false
}
```

```bash
python3 -m forth -c config.json -i
```

## Built-in Words

The interpreter includes **120+ built-in words** organized by category. See
[docs/word-reference.md](docs/word-reference.md) for the complete reference.

| Category | Words |
|----------|-------|
| Stack | `DUP` `DROP` `SWAP` `OVER` `ROT` `-ROT` `NIP` `TUCK` `?DUP` `DEPTH` `PICK` `ROLL` `2DUP` `2DROP` `2SWAP` `2OVER` `WITHIN` `BOUNDS` |
| Return stack | `>R` `R>` `R@` |
| Arithmetic | `+` `-` `*` `/` `MOD` `/MOD` `NEGATE` `ABS` `MIN` `MAX` `**` `1+` `1-` `2+` `2-` `2*` `2/` |
| Float | `F+` `F-` `F*` `F/` `FSQRT` `FSIN` `FCOS` `FTAN` `FLOG` `FEXP` `FLOOR` `CEIL` `ROUND` `FABS` `FNEGATE` `FATAN` `FASIN` `FACOS` `FATAN2` `F**` `PI` `E` |
| Comparison | `=` `<>` `<` `>` `<=` `>=` `0=` `0<>` `0<` `0>` |
| Bitwise | `AND` `OR` `XOR` `INVERT` `LSHIFT` `RSHIFT` `NOT` |
| I/O | `.` `.R` `U.` `EMIT` `CR` `SPACE` `SPACES` `BL` `.S` `.S!` `TYPE` `DUMP` |
| Memory | `!` `@` `+!` `SP@` `CELLS` `CELL+` `ALLOT` `ERASE` `FILL` `MOVE` |
| Defining | `:` `;` `VARIABLE` `CONSTANT` `VALUE` `TO` `CREATE` `2VARIABLE` |
| Control flow | `IF` `ELSE` `THEN` `BEGIN` `UNTIL` `WHILE` `REPEAT` `AGAIN` `DO` `LOOP` `+LOOP` `LEAVE` `EXIT` `RECURSE` `UNLOOP` `I` `J` |
| Case | `CASE` `OF` `ENDOF` `ENDCASE` |
| Arrays | `ARRAY` `[]!` `[]@` `ARRAY-SIZE` |
| Strings | `."` `.(` `C"` `STRLEN` `STRCAT` `CMP-STR` `SUBSTR` `CHAR` `[CHAR]` |
| Exceptions | `THROW` `CATCH` `ABORT` `ABORT"` |
| Utility | `WORDS` `WORDS-COUNT` `SEE` `FORGET` `BYE` `TRUE` `FALSE` `RESET` `VERSION` `TIME` `CLOCK` `SEED` `RANDOM` |
| File ops | `INCLUDE` |

## Examples

The `examples/` directory contains several demonstration programs:

### Factorial (recursive)

```forth
: FACT DUP 1 > IF DUP 1 - RECURSE * THEN ;
5 FACT . CR
```
Output: `120`

### Fibonacci (recursive + iterative)

```forth
\ Recursive
: FIB DUP 2 < IF EXIT THEN DUP 1 - RECURSE SWAP 2 - RECURSE + ;
10 FIB . CR

\ Iterative (more efficient)
: FIB-ITER 0 1 ROT 0 DO OVER + SWAP LOOP SWAP DROP ;
30 FIB-ITER . CR
```

### Prime Numbers

```forth
: PRIME?
    DUP 2 < IF DROP FALSE EXIT THEN
    DUP 2 = IF DROP TRUE EXIT THEN
    DUP 2 MOD 0 = IF DROP FALSE EXIT THEN
    DUP 3 BEGIN 2DUP > WHILE
        2DUP MOD 0 = IF 2DROP FALSE EXIT THEN 2 +
    REPEAT 2DROP TRUE ;
: .PRIMES 30 2 DO I PRIME? IF I . THEN LOOP ;
.PRIMES CR
```
Output: `2 3 5 7 11 13 17 19 23 29`

### Bubble Sort with Arrays

```forth
ARRAY DATA 10
42 0 DATA []!  17 1 DATA []!  99 2 DATA []!  5 3 DATA []!
73 4 DATA []!  28 5 DATA []!  56 6 DATA []!  3 7 DATA []!
81 8 DATA []!  34 9 DATA []!

VARIABLE TEMP
: BUBBLE-PASS 9 0 DO I DATA []@ I 1+ DATA []@ > IF
    I DATA []@ TEMP ! I 1+ DATA []@ I DATA []! TEMP @ I 1+ DATA []!
THEN LOOP ;
: BUBBLE 9 0 DO BUBBLE-PASS LOOP ;
BUBBLE
```
Output: `3 5 17 28 34 42 56 73 81 99`

### CASE/OF/ENDOF/ENDCASE

```forth
: GRADE
    CASE
        0 OF ." F" ENDOF
        1 OF ." D" ENDOF
        2 OF ." C" ENDOF
        3 OF ." B" ENDOF
        4 OF ." A" ENDOF
        ." ?"
    ENDCASE ;
3 GRADE CR   \ Output: B
```

### String Operations

```forth
"hello" STRLEN . CR          \ 5
"world" "hello " STRCAT TYPE CR  \ hello world
"foo" "foo" CMP-STR . CR     \ -1 (true)
2 3 "hello" SUBSTR TYPE CR    \ llo
```

### Exception Handling

```forth
: DANGER 42 THROW ;
CATCH DANGER . CR    \ 42 (caught the throw)
: SAFE 99 . ;
CATCH SAFE . CR      \ 99 0 (no throw, code=0)
```

### Variables and Loops

```forth
VARIABLE SUM 0 SUM !
10 0 DO I SUM @ + SUM ! LOOP
SUM @ . CR    \ 45
```

### Nested Loops

```forth
: TABLE 3 0 DO 3 0 DO I J 10 * + . LOOP CR LOOP ;
TABLE
```
Output:
```
0 1 2
10 11 12
20 21 22
```

### GCD (Euclidean algorithm)

```forth
: GCD BEGIN ?DUP WHILE SWAP MOD REPEAT ;
48 18 GCD . CR
```
Output: `6`

## Architecture

The interpreter is organized into a modular package:

```
forth-interpreter/
├── forth/
│   ├── __init__.py          # Public API exports
│   ├── __main__.py           # Entry point for python -m forth
│   ├── core.py              # Core interpreter engine
│   │                        #   - Stack machine (data + return stacks)
│   │                        #   - Dictionary (word lookup)
│   │                        #   - Tokenizer (comments, strings, special words)
│   │                        #   - Compiler (token → bytecode IR)
│   │                        #   - VM (bytecode execution with control flow)
│   │                        #   - Recursion and stack limits
│   ├── cli.py               # CLI with argparse, config, logging
│   └── builtins/            # Built-in word set (modular)
│       ├── __init__.py       # register_all() — ties everything together
│       ├── _helpers.py       # Shared type aliases
│       ├── stack_ops.py      # DUP, DROP, SWAP, OVER, ROT, PICK, ROLL, ...
│       ├── arithmetic.py     # +, -, *, /, MOD, NEGATE, ABS, MIN, MAX, ...
│       ├── float_ops.py      # F+, F-, F*, F/, FSQRT, FSIN, FCOS, ...
│       ├── comparison.py     # =, <>, <, >, <=, >=, 0=, 0<>, ...
│       ├── bitwise.py        # AND, OR, XOR, INVERT, LSHIFT, RSHIFT
│       ├── io_ops.py         # ., EMIT, CR, SPACE, .S, TYPE, DUMP, .R
│       ├── memory.py         # !, @, +!, ERASE, FILL, MOVE
│       ├── defining.py       # VARIABLE, CONSTANT, VALUE, TO, CREATE
│       ├── control_flow.py   # IF/ELSE/THEN, BEGIN/UNTIL, DO/LOOP, ...
│       ├── case_ops.py       # CASE/OF/ENDOF/ENDCASE
│       ├── arrays.py         # ARRAY, []!, []@, ARRAY-SIZE
│       ├── strings.py        # .", STRLEN, STRCAT, CMP-STR, SUBSTR, ...
│       ├── utility.py        # WORDS, SEE, FORGET, BYE, VERSION, RANDOM, ...
│       ├── exceptions.py     # CATCH, THROW, ABORT, ABORT"
│       └── file_ops.py       # INCLUDE
├── examples/                 # Example Forth programs
│   ├── primes.fs             # Prime number sieve
│   ├── bubble-sort.fs        # Bubble sort with arrays
│   ├── fibonacci.fs         # Recursive + iterative Fibonacci
│   ├── arrays.fs             # Array operations demo
│   ├── strings.fs            # String operations demo
│   ├── exceptions.fs         # Exception handling demo
│   └── quicksort.fs          # Quicksort (bubble sort variant)
├── tests/                    # Comprehensive pytest suite
│   ├── test_forth.py         # Core tests (59 tests)
│   ├── test_bugs.py          # Bug hunt tests (16 tests)
│   └── test_new_features.py  # New feature tests (38 tests)
├── docs/                     # Documentation
│   ├── architecture.md       # Architecture overview
│   └── word-reference.md      # Complete word reference
├── .github/workflows/        # CI config
│   └── forth-interpreter.yml # GitHub Actions (Python 3.10-3.13)
├── pyproject.toml            # Project metadata + packaging
├── test_quick.py             # Quick test script (27 tests)
├── CONTRIBUTING.md           # Contribution guide
├── LICENSE                   # MIT License
└── README.md                 # This file
```

### How It Works

#### Compilation

When `: NAME ... ;` is encountered, the interpreter enters compile mode. Tokens are compiled into an instruction list using tuples:

- `("lit", value)` — push a literal value
- `("call", wordname)` — call a word
- `("if", target)` — pop flag; if zero, jump to target
- `("jump", target)` — unconditional jump
- `("until", target)` — pop flag; if zero, jump back to target
- `("while", target)` — pop flag; if zero, jump past REPEAT
- `("do", target)` — pop limit and start; push loop state to return stack
- `("loop", target)` — increment index; if within bounds, jump to body start
- `("plusloop", target)` — add increment; if boundary not crossed, jump to body start
- `("leave", target)` — exit loop; jump past LOOP

Immediate words (IF, ELSE, THEN, BEGIN, UNTIL, WHILE, REPEAT, AGAIN, DO, LOOP, +LOOP, LEAVE, RECURSE, CASE, OF, ENDOF, ENDCASE, .") execute during compilation to emit these instructions and manage fixup positions via the return stack.

#### Execution

The `_execute_body` method is a simple bytecode interpreter that walks the instruction list, maintaining an instruction pointer (IP). Control-flow instructions modify the IP. The `_ExitBody` exception handles the `EXIT` word for early return.

#### Native Word Protocol

Built-in words are Python callables with the signature `(interp, tokens, idx) -> Any`. Regular built-ins return `None` to indicate "advance to the next token." Defining words (VARIABLE, CONSTANT, etc.) return `_NextIdx(new_idx)` to jump the token pointer forward.

#### Tokenizer

The tokenizer handles `\` line comments, `( ... )` block comments (nested), and `"..."` string literals. Special consuming words (`."`, `C"`, `ABORT"`) read text until the next `"`, and `.( ` reads until `)`.

## Testing

```bash
# Run the full test suite (140 tests)
python3 -m pytest tests/ -v

# Run a specific test class
python3 -m pytest tests/test_forth.py::TestArithmetic -v

# Run with coverage
python3 -m pytest tests/ --cov=forth --cov-report=term-missing

# Run the quick test script
python3 test_quick.py
```

**140 tests** covering:
- Arithmetic (16 tests) — integer and float operations
- Stack manipulation (16 tests) — DUP, DROP, SWAP, PICK, ROLL, etc.
- Comparison (10 tests) — =, <>, <, >, 0=, 0<>, etc.
- Bitwise (6 tests) — AND, OR, XOR, LSHIFT, RSHIFT
- Variables and arrays (8 tests) — VARIABLE, CONSTANT, VALUE, ARRAY
- Control flow (14 tests) — IF/ELSE/THEN, BEGIN/UNTIL, DO/LOOP, RECURSE
- CASE/OF (3 tests) — CASE/OF/ENDOF/ENDCASE
- Strings (6 tests) — .", TYPE, string literals
- Errors (5 tests) — unknown word, stack underflow, division by zero
- Utility (6 tests) — WORDS, .S, SEE, DUMP
- Primes example (1 test) — full prime sieve
- Bug fixes (16 tests) — regression tests for all fixed bugs
- New features (38 tests) — string ops, float ops, exceptions, memory ops, arrays, utility, CREATE, UNLOOP, recursion limits, INCLUDE

## Known Issues (Resolved)

### Bug 1: CASE/OF/ENDOF/ENDCASE — bogus literal instruction (Fixed)
The `OF` word pushed a `("lit", "of-check")` instruction into the compiled body, corrupting the data stack at runtime. Additionally, `ENDCASE`'s DROP instruction was not jumped over by matching OF clauses, causing a stack underflow. Fixed by removing the bogus literal and correctly fixing up ENDOF jump targets to skip past ENDCASE's DROP.

### Bug 2: `_arr_store` dead code (Fixed)
The `[]!` word contained confusing dead code that served no purpose. Replaced with a proper type check that raises an error if the target is not an array.

### Bug 3: `_reset_state` didn't clear `current_name` (Fixed)
After a compilation error, `current_name` was not cleared. This could cause `RECURSE` in a subsequent definition to accidentally call the failed word's name. Fixed by clearing `current_name` in `_reset_state`.

### Bug 4: `@` and `!` didn't validate scalar vs array access (Fixed)
Using `@` on an array variable would push the entire list, and `!` on an array would overwrite it with a single value. Fixed with scalar validation and helpful error messages directing users to `[]@`/`[]!`.

### Bug 5: Duplicate `."` registration (Fixed)
The `."` word was registered twice — first as a no-op lambda, then as the real implementation. Removed the no-op registration.

## Changelog

### v3.0.0 — Comprehensive Improvement
- **Architecture**: Split monolithic 1229-line `interpreter.py` into 15 modular files under `forth/core.py`, `forth/cli.py`, and `forth/builtins/` package
- **New words** (40+ added):
  - Strings: `STRLEN`, `STRCAT`, `CMP-STR`, `SUBSTR`, `CHAR`, `[CHAR]`, `C"`, `.(`
  - Float: `FABS`, `FNEGATE`, `FATAN`, `FASIN`, `FACOS`, `FATAN2`, `F**`, `PI`, `E`
  - Memory: `ERASE`, `FILL`, `MOVE`
  - Arrays: `ARRAY-SIZE`
  - Defining: `CREATE`, `2VARIABLE`
  - Control flow: `UNLOOP`
  - Exceptions: `THROW`, `CATCH`, `ABORT`, `ABORT"`, `ABORT-MESSAGE`
  - I/O: `.R`, `U.`, `SPACES`
  - Utility: `WITHIN`, `BOUNDS`, `WORDS-COUNT`, `RESET`, `VERSION`, `TIME`, `CLOCK`, `SEED`, `RANDOM`
  - File: `INCLUDE`
- **CLI**: Full argparse with `--version`, `--debug`, `--config`, `--no-banner`, `--stack-size`, `--max-recursion`
- **Config files**: JSON and YAML support
- **Logging**: Python logging integration with `--debug` flag
- **Tokenizer**: Enhanced to properly handle `."`, `C"`, `ABORT"`, `.( ` consuming words
- **Recursion limit**: Configurable max recursion depth (default 500) with graceful error
- **Stack overflow protection**: Configurable max stack depth (default 10,000)
- **Type hints**: Throughout all modules
- **Tests**: Added 38 new feature tests (140 total, all passing)
- **Documentation**: Architecture docs, complete word reference, CONTRIBUTING.md
- **CI**: GitHub Actions workflow for Python 3.10-3.13
- **Examples**: Added strings, fibonacci, arrays, exceptions demos
- **License**: MIT License added
- **Packaging**: Proper `pyproject.toml` with optional dependencies

### v2.0.0 — Enhanced
- Added 100+ words including PICK/ROLL, CASE/OF, arrays, string printing, DUMP
- Error recovery in eval()
- Comprehensive pytest suite (89 tests)

### v1.0.0 — Initial Release
- Forth interpreter with 80+ words, compilation to bytecode IR, control flow, REPL

## Roadmap

- [ ] **Forth 2012 standard compliance** — implement more ANS Forth standard words
- [ ] **Execution tokens (XT)** — proper `EXECUTE`, `'`, `>BODY`, `BODY>`
- [ ] **Local variables** — `LOCALS|` support
- [ ] **Word lists / vocabularies** — namespace support
- [ ] **Save/Load image** — persist dictionary state to disk
- [ ] **Compiler hooks** — `POSTPONE`, `COMPILE,`, `[`, `]`
- [ ] **Number formatting** — `<#` `#` `#S` `#>` picture output
- [ ] **Double-cell arithmetic** — `D+`, `D-`, `D*`, `D/`
- [ ] **Block I/O** — `BLOCK`, `BUFFER`, `UPDATE`, `SAVE-BUFFERS`
- [ ] **Threading model** — cooperative multitasking with `TASK`
- [ ] **Disassembler** — pretty-print compiled bytecode
- [ ] **Performance** — optimize hot paths with dispatch table

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, architecture overview, and contribution guidelines.

## License

[MIT License](LICENSE) — Copyright (c) 2026 creative-projects