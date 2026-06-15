# BASIC Language Interpreter

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-3.0.0-green.svg)](https://github.com/jayis1/creative-projects)

A full-featured interpreter for a classic BASIC dialect, written in pure Python with no external dependencies. Supports a comprehensive subset of Microsoft BASICA/GW-BASIC, including line-numbered programs, structured constructs, arrays, file I/O, and over 40 built-in functions.

```
   ____  ____  ____  ___  ____  ___ 
  | __ )|  _ \|  _ \|_ _||  _ \/ __|
  |  _ \| |_) | |_) ||| | | | \__ \
  | |_) |  _ <|  _ < | | | |_| |__) |
  |____/|_| \_\_| \_\___||____/|___/
  
  A modern Python interpreter for a classic language.
```

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
  - [Running Programs](#running-programs)
  - [One-Liner Mode](#one-liner-mode)
  - [Interactive REPL](#interactive-repl)
  - [Configuration](#configuration)
- [Language Reference](#language-reference)
  - [Variables](#variables)
  - [Operators](#operators)
  - [Control Flow](#control-flow)
  - [Built-in Functions](#built-in-functions)
  - [File I/O](#file-io)
  - [Error Handling](#error-handling)
- [Architecture](#architecture)
- [Examples](#examples)
- [Testing](#testing)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [License](#license)

## Features

### Core Language
- **Line-numbered programs** with `GOTO`, `GOSUB`/`RETURN`
- **Variables**: numeric (`X`, `COUNT%`) and string (`NAME$`) types with automatic conversion
- **Arrays**: 1D and 2D via `DIM`, auto-expanding with default 11-element size
- **Operators**: arithmetic (`+`, `-`, `*`, `/`, `\`, `MOD`, `^`), comparison (`=`, `<>`, `<`, `>`, `<=`, `>=`)
- **Logical operators**: `AND`, `OR`, `NOT`, `XOR`, `EQV`, `IMP`
- **String operations**: concatenation with `+`, comparison

### Control Flow
- `IF...THEN...ELSE` (single-line and multi-statement)
- `FOR...NEXT` with optional `STEP` (including negative step)
- `WHILE...WEND` loops
- `DO...LOOP` with `WHILE`/`UNTIL` pre- and post-conditions
- `SELECT CASE` with `IS`, `TO` range, `CASE ELSE`, `END SELECT`
- `ON...GOTO` / `ON...GOSUB` computed branching
- `ON ERROR GOTO` / `RESUME` error handling

### I/O
- `PRINT` with `;` (compact), `,` (zone-tab) separators
- `PRINT USING` formatted output (`#`, `&`, `!`, `\...\` format fields)
- `INPUT` with optional prompt
- `LINE INPUT` for reading full lines
- `READ`/`DATA`/`RESTORE` for static data
- File I/O: `OPEN`/`CLOSE`/`PRINT#`/`INPUT#`/`LINE INPUT#`

### Built-in Functions

| Category | Functions |
|----------|-----------|
| Math | `ABS`, `INT`, `FIX`, `SGN`, `SQR`, `SIN`, `COS`, `TAN`, `ATN`, `LOG`, `EXP`, `RND`, `CINT`, `CSNG`, `CDBL` |
| String | `LEN`, `LEFT$`, `RIGHT$`, `MID$`, `CHR$`, `ASC`, `STR$`, `VAL`, `LCASE$`, `UCASE$`, `LTRIM$`, `RTRIM$`, `STRING$`, `INSTR` |
| I/O | `TAB`, `SPC` |
| System | `DATE$`, `TIME$`, `INKEY$`, `TIMER`, `FRE`, `PEEK`, `ENVIRON$` |
| User | `DEF FN` — define your own functions |

### Statements
`LET`, `PRINT`, `INPUT`, `LINE INPUT`, `IF/THEN/ELSE`, `FOR/TO/STEP/NEXT`, `WHILE/WEND`, `DO/LOOP`, `SELECT CASE`, `GOTO`, `GOSUB`, `RETURN`, `DIM`, `ERASE`, `READ`, `DATA`, `RESTORE`, `DEF FN`, `REM`, `END`, `STOP`, `ON...GOTO/GOSUB`, `ON ERROR GOTO`, `RESUME`, `SWAP`, `CLS`, `COLOR`, `LOCATE`, `BEEP`, `OPEN`, `CLOSE`, `PRINT#`, `INPUT#`

### Interactive REPL
Enhanced REPL with commands:
- **RUN** — execute loaded program
- **LIST** [start[-end]] — list program lines
- **NEW** — clear program and variables
- **SAVE** filename — save to file
- **LOAD** filename — load from file
- **EDIT** line — edit a line
- **DELETE** line|start-end — delete line(s)
- **QUIT** — exit
- **HELP** — show command reference

## Quick Start

```bash
# Run a BASIC program
python -m basic_interpreter examples/hello.bas

# One-liner
python -m basic_interpreter -e 'PRINT "Hello, World!"'

# Interactive REPL
python -m basic_interpreter

# With tracing
python -m basic_interpreter --trace examples/fibonacci.bas
```

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/basic-interpreter

# Create a virtual environment (optional but recommended)
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install in development mode
pip install -e ".[dev]"
```

### Direct Usage (No Install)

```bash
# Add src/ to Python path and run directly
cd basic-interpreter
PYTHONPATH=src python3 -m basic_interpreter program.bas
```

### Requirements

- Python 3.11 or later
- No external dependencies (only standard library)

## Usage

### Running Programs

```bash
# Run a BASIC program from a file
basic-interpreter program.bas

# Or using the module
python -m basic_interpreter program.bas
```

### One-Liner Mode

```bash
# Quick evaluation of a single statement
basic-interpreter -e 'PRINT 2^10'
basic-interpreter -e 'FOR I = 1 TO 10 : PRINT I; " "; : NEXT I'
```

### Interactive REPL

```bash
$ basic-interpreter
BASIC Interpreter v3.0
Type HELP for a list of commands.
> 10 PRINT "Hello, World!"
> RUN
Hello, World!
OK
> LIST
10 PRINT "Hello, World!"
> SAVE hello.bas
Saved 1 lines to hello.bas
> QUIT
Goodbye!
```

### Configuration

Create a `config.toml` file:

```toml
[interpreter]
max_iterations = 10000000
zone_width = 14
trace = false
# random_seed = 42
```

Run with config:

```bash
basic-interpreter --config config.toml program.bas
```

### Command-Line Options

```
usage: basic-interpreter [-h] [-e STATEMENT] [--trace] [--max-iter N]
                          [--config FILE] [-v] [file]

BASIC Language Interpreter v3.0

positional arguments:
  file                  BASIC source file to run

options:
  -e, --eval STATEMENT  Evaluate a one-liner BASIC statement
  --trace               Trace line-by-line execution
  --max-iter N          Maximum iteration count (default: 10,000,000)
  --config FILE         Path to configuration file (TOML/JSON)
  -v, --version         Show version number
  -h, --help            Show this help message
```

## Language Reference

### Variables

```basic
10 LET X = 42          ' Numeric variable
20 LET NAME$ = "BASIC" ' String variable (ends with $)
30 LET COUNT% = 10      ' Integer variable (ends with %)
40 LET A(5) = 100      ' Array element
50 LET M(3, 4) = 7     ' 2D array element
```

### Operators

| Priority | Operator | Description |
|----------|----------|-------------|
| 1 (highest) | `^` | Exponentiation |
| 2 | `-` (unary) | Negation |
| 3 | `*`, `/` | Multiplication, Division |
| 4 | `\` | Integer Division |
| 5 | `MOD` | Modulo |
| 6 | `+`, `-` | Addition, Subtraction |
| 7 | `=`, `<>`, `<`, `>`, `<=`, `>=` | Comparison |
| 8 | `NOT` | Logical NOT |
| 9 | `AND` | Logical AND |
| 10 | `OR` | Logical OR |
| 11 | `XOR` | Logical XOR |
| 12 | `EQV` | Logical Equivalence |
| 13 (lowest) | `IMP` | Logical Implication |

### Control Flow

#### IF...THEN...ELSE

```basic
10 IF X > 10 THEN PRINT "big" ELSE PRINT "small"
20 IF SCORE >= 90 THEN PRINT "A" ELSE IF SCORE >= 80 THEN PRINT "B" ELSE PRINT "C"
```

#### FOR...NEXT

```basic
10 FOR I = 1 TO 10
20   PRINT I;
30 NEXT I

40 FOR J = 10 TO 1 STEP -1
50   PRINT J;
60 NEXT J
```

#### WHILE...WEND

```basic
10 LET X = 1
20 WHILE X < 100
30   LET X = X * 2
40 WEND
50 PRINT X
```

#### DO...LOOP

```basic
10 DO WHILE X < 10
20   LET X = X + 1
30 LOOP

10 DO
20   LET X = X + 1
30 LOOP UNTIL X >= 10
```

#### SELECT CASE

```basic
10 INPUT "Enter a number: "; N
20 SELECT CASE N
30   CASE 1
40     PRINT "One"
50   CASE 2 TO 5
60     PRINT "Two through five"
70   CASE IS > 10
80     PRINT "Greater than ten"
90   CASE ELSE
100    PRINT "Six through ten"
110 END SELECT
```

### Built-in Functions

```basic
10 PRINT ABS(-5)         ' 5
20 PRINT INT(3.7)        ' 3
30 PRINT SQR(16)         ' 4
40 PRINT LEFT$("Hello", 3)  ' Hel
50 PRINT MID$("Hello", 2, 3) ' ell
60 PRINT INSTR("Hello", "ll") ' 3
70 PRINT STRING$(5, "*")  ' *****
```

### File I/O

```basic
10 OPEN "data.txt" FOR OUTPUT AS #1
20 PRINT# 1, "Hello from file"
30 CLOSE #1

40 OPEN "data.txt" FOR INPUT AS #2
50 INPUT# 2, A$
60 CLOSE #2
70 PRINT A$
```

### Error Handling

```basic
10 ON ERROR GOTO 100
20 LET X = 1 / 0        ' This would cause division by zero
30 PRINT "Continuing..."
40 END
100 PRINT "Error caught!"
110 RESUME 30
```

## Architecture

The interpreter follows a classic three-phase design with modular components:

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐
│   Lexer     │────▶│   Parser    │────▶│   Interpreter     │
│ (lexer.py)  │     │ (parser.py) │     │ (interpreter.py)  │
└─────────────┘     └─────────────┘     └──────────────────┘
      │                   │                      │
   Tokenizes          Builds AST           Tree-walking
   source lines       with precedence       evaluator with
   into Token          climbing for          line-number
   objects             expressions            management

                     ┌──────────────┐
                     │ AST Nodes    │
                     │ (ast_nodes.py)│
                     └──────────────┘

                     ┌──────────────┐
                     │ Config       │
                     │ (config.py)  │
                     └──────────────┘

                     ┌──────────────┐
                     │ CLI / REPL   │
                     │ (cli.py)     │
                     └──────────────┘
```

1. **Lexer** (`lexer.py`) — Tokenizes source lines, recognizing keywords, numbers, strings, operators
2. **Parser** (`parser.py`) — Recursive-descent parser building an AST with precedence climbing for expressions
3. **AST Nodes** (`ast_nodes.py`) — Dataclass definitions for all statement and expression node types
4. **Interpreter** (`interpreter.py`) — Tree-walking evaluator with line-number management for control flow
5. **Config** (`config.py`) — Dataclass for interpreter configuration options
6. **CLI** (`cli.py`) — Command-line interface with argparse, REPL, and configuration file support
7. **Errors** (`errors.py`) — Custom exception hierarchy

Multi-line constructs (`WHILE/WEND`, `DO/LOOP`, `SELECT CASE`) are resolved at load time by building cross-reference tables, enabling efficient jumps during execution.

### Key Design Decisions

- **O(1) line number lookup**: Line numbers are stored in a dictionary (`_line_to_idx`) for constant-time GOTO/GOSUB resolution
- **Truncated integer division**: The `\` operator uses `int(a/b)` for BASIC-compatible truncation toward zero
- **BASIC-compatible MOD**: Uses `a - (a \ b) * b` to follow dividend sign convention
- **SELECT CASE fall-through prevention**: Tracks `_active_select_end` and `_active_select_matched` to skip past END SELECT
- **Resource cleanup**: Files are properly closed on program reload and interpreter destruction

## Examples

See the `examples/` directory for complete programs:

| Example | Description |
|---------|-------------|
| `hello.bas` | Hello World |
| `fibonacci.bas` | Fibonacci sequence |
| `guess.bas` | Number guessing game |
| `sort.bas` | Bubble sort |
| `gosub.bas` | Subroutine demonstration |
| `collatz.bas` | Collatz conjecture |
| `deffn.bas` | User-defined functions |
| `strings.bas` | String manipulation |
| `mandelbrot.bas` | ASCII Mandelbrot set renderer |
| `primes.bas` | Sieve of Eratosthenes |
| `bottles.bas` | 99 Bottles of Beer |
| `diamond.bas` | Numeric diamond pattern |
| `quadratic.bas` | Quadratic equation solver |

### Quick Examples

**Fibonacci sequence:**
```basic
10 LET A = 0
20 LET B = 1
30 FOR I = 1 TO 20
40   PRINT A; " ";
50   LET C = A + B
60   LET A = B
70   LET B = C
80 NEXT I
```

**File I/O:**
```basic
10 OPEN "output.txt" FOR OUTPUT AS #1
20 FOR I = 1 TO 10
30   PRINT# 1, "Line "; I
40 NEXT I
50 CLOSE #1
```

## Testing

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run the full test suite
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=basic_interpreter --cov-report=term-missing

# Run a specific test
pytest tests/test_core.py -v -k "test_for_next"

# Run just the arithmetic tests
pytest tests/test_core.py -v -k "TestArithmetic"
```

### Test Categories

| Category | Description | Count |
|----------|-------------|-------|
| Arithmetic | Math operations, operator precedence | 12 |
| Variables | Assignment, types, SWAP | 5 |
| Control Flow | IF, FOR, WHILE, DO, GOTO, GOSUB | 14 |
| SELECT CASE | Multi-way branching, fall-through | 4 |
| Functions | Built-in math, string, system functions | 14 |
| Arrays | DIM, ERASE, 1D/2D, auto-expand | 4 |
| Data/Read | READ, DATA, RESTORE | 2 |
| File I/O | OPEN, CLOSE, PRINT#, INPUT#, APPEND | 2 |
| Logical Ops | AND, OR, NOT, XOR, EQV, IMP | 7 |
| Error Handling | ON ERROR GOTO, RESUME | 1 |
| Bug Fixes | Fall-through, integer div, MOD, format, etc. | 6 |
| Edge Cases | Empty programs, string concat, etc. | 4 |

## Known Issues (Resolved)

The following bugs were found and fixed during the bug hunt phase:

| # | Bug | Impact | Fix |
|---|-----|--------|-----|
| 1 | **SELECT CASE fall-through** | After matching a CASE, execution continued into subsequent CASE/END SELECT branches | Added `_active_select_end` and `_active_select_matched` tracking to skip to END SELECT when encountering a non-matched CASE line |
| 2 | **File resource leak** | Open file handles were not closed when loading a new program or when the interpreter was destroyed | Added file cleanup in `load()` and `__del__()` destructor |
| 3 | **Integer division rounds wrong** | `\` operator used Python floor division (`//`) which rounds toward negative infinity; BASIC should truncate toward zero | Changed to `int(a / b)` for truncation toward zero; e.g., `-7 \ 2` = `-3` not `-4` |
| 4 | **MOD follows wrong sign** | Python `%` follows divisor sign; BASIC MOD should follow dividend sign | Changed to `a - (a \ b) * b` formula; e.g., `-7 MOD 2` = `-1` not `1` |
| 5 | **_format_value misses int type** | Logical operators return Python `int` (0, -1) but `_format_value` only handled `float`, missing the leading/trailing spaces | Extended check to `isinstance(val, (int, float))` |
| 6 | **O(n) line number lookup** | `GOTO`/`GOSUB`/`ON GOTO`/`RESUME` all used `sorted_lines.index()` — O(n) per call | Added `_line_to_idx` dict for O(1) lookup, replaced all 6 occurrences |

## Roadmap

- [ ] **SUB/FUNCTION procedures** — Named subroutines with local variables
- [ ] **EXIT FOR** — Exit a FOR loop early
- [ ] **Multi-line IF/END IF** — Block-style IF statements
- [ ] **Screen functions** — SCREEN$, CSRLIN, POS functions
- [ ] **Sound** — SOUND and PLAY statements for music
- [ ] **Graphics** — Circle, Line, PSET, DRAW for terminal graphics
- [ ] **Binary file I/O** — GET/PUT statements for binary file access
- [ ] **Debugging mode** — Step-by-step execution with breakpoints
- [ ] **WebAssembly build** — Run in browser via Pyodide
- [ ] **Comprehensive error messages** — Line and column numbers in error messages

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this project.

## Changelog

### v3.0.0 (2026-06-15) — Comprehensive Improvement Release

**Architecture:**
- Split monolithic `basic.py` (2863 lines) into modular package:
  - `lexer.py` — Tokenizer (Token types, Lexer)
  - `parser.py` — Recursive-descent parser
  - `ast_nodes.py` — AST dataclass definitions
  - `interpreter.py` — Tree-walking execution engine
  - `config.py` — Configuration dataclass
  - `cli.py` — CLI with argparse, REPL, config file support
  - `errors.py` — Custom exception hierarchy
  - `__init__.py` — Package entry point
  - `__main__.py` — Module entry point (`python -m basic_interpreter`)

**New Features:**
- Installable package with `pyproject.toml` and `pip install -e .`
- Configuration file support (TOML/JSON) via `--config` flag
- `InterpreterConfig` dataclass for programmatic configuration
- `HELP` command in REPL
- Comprehensive pytest test suite (replacing ad-hoc test scripts)
- GitHub Actions CI workflow
- Type hints throughout all modules
- Logging support (`logging` module)
- 5 new example programs (primes, bottles, diamond, quadratic, hanoi)

**Documentation:**
- Dramatically expanded README with badges, table of contents, architecture diagrams
- CONTRIBUTING.md with development setup instructions
- LICENSE (MIT)
- Inline docstrings for all public classes and methods

**Bug Fixes (from Phase 3):**
- SELECT CASE fall-through prevention
- File resource leak cleanup
- Integer division truncation toward zero
- MOD dividend-sign convention
- `_format_value` handling Python `int` type
- O(1) line number lookup via `_line_to_idx` dictionary

### v2.0.0 — Enhanced Features

- DO...LOOP with WHILE/UNTIL pre/post conditions
- SELECT CASE with IS, TO range, CASE ELSE
- ERASE statement for array deallocation
- XOR, EQV, IMP logical operators
- LINE INPUT statement
- DATE$, TIME$ system functions
- LCASE$, UCASE$, LTRIM$, RTRIM$ string functions
- SGN, FIX, CSNG, CDBL math functions
- ENVIRON$, FRE system functions
- File I/O: OPEN/CLOSE/PRINT#/INPUT# with INPUT/OUTPUT/APPEND modes
- ON ERROR GOTO / RESUME error handling
- BEEP, COLOR, CLS, LOCATE terminal control
- PRINT USING format templates
- Enhanced REPL (SAVE, LOAD, EDIT, DELETE commands)

### v1.0.0 — Initial Release

- Core BASIC interpreter with lexer, parser, and tree-walking interpreter
- Line-numbered programs, GOTO, GOSUB/RETURN
- IF/THEN/ELSE, FOR/NEXT, WHILE/WEND
- LET, PRINT, INPUT, DIM, READ/DATA/RESTORE
- DEF FN, REM, END, STOP
- Built-in math and string functions
- Interactive REPL

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.