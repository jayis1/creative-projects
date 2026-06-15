# BASIC Language Interpreter

A full-featured interpreter for a classic BASIC dialect, written in pure Python with no external dependencies.

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

## Usage

```bash
# Run a BASIC program
python3 basic.py program.bas

# One-liner
python3 basic.py -e 'PRINT "Hello, World!"'

# Interactive REPL
python3 basic.py

# With tracing
python3 basic.py --trace program.bas
```

## Examples

See the `examples/` directory:

- **hello.bas** — Hello World
- **fibonacci.bas** — Fibonacci sequence
- **guess.bas** — Number guessing game
- **sort.bas** — Bubble sort
- **gosub.bas** — Subroutine demonstration
- **collatz.bas** — Collatz conjecture
- **deffn.bas** — User-defined functions
- **strings.bas** — String manipulation
- **mandelbrot.bas** — ASCII Mandelbrot set renderer

### SELECT CASE Example

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

### DO...LOOP Example

```basic
10 DO
20   INPUT "Guess (1-10): "; G
30   IF G = 7 THEN PRINT "Correct!": EXIT DO
40 LOOP UNTIL G = 7
```

### File I/O Example

```basic
10 OPEN "data.txt" FOR OUTPUT AS #1
20 PRINT# 1, "Hello from file"
30 CLOSE #1
40 OPEN "data.txt" FOR INPUT AS #2
50 INPUT# 2, A$
60 CLOSE #2
70 PRINT A$
```

## Architecture

The interpreter follows a classic three-phase design:

1. **Lexer** — Tokenizes source lines, recognizing keywords, numbers, strings, operators
2. **Parser** — Recursive-descent parser building an AST with precedence climbing for expressions
3. **Interpreter** — Tree-walking evaluator with line-number management for control flow

Multi-line constructs (`WHILE/WEND`, `DO/LOOP`, `SELECT CASE`) are resolved at load time by building cross-reference tables, enabling efficient jumps during execution.

## Testing

```bash
# Run original test suite (24 tests)
python3 test_basic.py

# Run enhanced feature tests (25 tests)
python3 test_enhanced.py

# Run bug fix verification tests (9 tests)
python3 test_bug_fixes.py

# Run all tests
python3 test_basic.py && python3 test_enhanced.py && python3 test_bug_fixes.py
```

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

## How It Works

1. Source lines are tokenized and parsed into statement ASTs
2. Line numbers are stored in a sorted dictionary with O(1) index lookup
3. Multi-line structures (WHILE/WEND, DO/LOOP, SELECT CASE) are matched at load time
4. The interpreter walks the program line by line, evaluating statements
5. Control flow statements (GOTO, GOSUB, etc.) modify the program counter
6. The `FOR` stack tracks loop variables and limits
7. The call stack manages GOSUB/RETURN nesting
8. Error handling via ON ERROR GOTO/RESUME intercepts runtime errors
9. SELECT CASE tracks the matched branch to prevent fall-through