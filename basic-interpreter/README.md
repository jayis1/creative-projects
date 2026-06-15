# BASIC Interpreter

A full-featured interpreter for a classic BASIC programming language dialect, written in pure Python with no external dependencies.

## Features

- **Line-numbered programs** with `GOTO`, `GOSUB`, and `RETURN`
- **Control flow**: `IF...THEN...ELSE`, `FOR...NEXT`, `WHILE...WEND`
- **Variables**: numeric and string (with `$` suffix), implicit declaration (default 0/empty)
- **Arrays**: 1D and 2D via `DIM`, auto-extending on out-of-bounds access
- **I/O**: `PRINT`, `INPUT`, `READ`/`DATA`/`RESTORE`
- **User-defined functions**: `DEF FN name(params) = expression`
- **Built-in functions**: 25+ including math, string, and utility functions
- **Operators**: arithmetic, comparison, logical (`AND`, `OR`, `NOT`), string concatenation
- **Statements**: `LET`, `SWAP`, `ON...GOTO`/`ON...GOSUB`, `REM`, `END`, `STOP`
- **Terminal control**: `CLS`, `COLOR`, `LOCATE`
- **REPL mode** with `RUN`, `LIST`, `NEW` commands
- **Safety**: configurable max iteration limit to prevent infinite loops

## How It Works

### Architecture

The interpreter follows a classic three-stage pipeline:

1. **Lexer** — Tokenizes BASIC source lines into tokens (keywords, numbers, strings, operators, identifiers)
2. **Parser** — Recursive-descent parser builds an AST from tokens with proper operator precedence
3. **Interpreter** — Tree-walking evaluator executes the AST against a runtime environment

### Key Design Decisions

- **PC Management**: The program counter (`pc`) is an index into sorted line numbers. Jump instructions set `pc = target - 1`; the main loop detects when `pc` has been modified and adds +1, so execution lands on the target line. Normal flow simply increments `pc` by 1.
- **FOR/NEXT Loop Stack**: FOR pushes loop metadata (variable, stop, step, pc) onto a stack. NEXT increments the loop variable, checks the condition, and either loops back or pops the entry.
- **WHILE/WEND Matching**: Resolved at load time by scanning the program structure, so WEND can efficiently jump back to the matching WHILE.
- **GOSUB/RETURN**: Uses a call stack of line indices. GOSUB pushes the current pc; RETURN pops it.
- **User Functions (DEF FN)**: Stored as AST nodes. When called, parameters are temporarily set in the variable table, the body expression is evaluated, and parameters are restored.
- **DATA/READ/RESTORE**: All DATA values are collected at load time in line-number order. READ consumes from a pointer; RESTORE resets the pointer to 0.
- **Arrays**: Auto-allocated on first access with generous defaults (11 elements for 1D). Arrays auto-extend if accessed out of bounds.
- **Type Conventions**: Variables ending in `$` are strings; others are numeric. Undeclared numeric variables default to 0; string variables default to `""`. Comparisons return -1 (true) or 0 (false) following BASIC convention.

### Operator Precedence (low to high)

1. `OR`
2. `AND`
3. `NOT`
4. `=`, `<>`, `<`, `>`, `<=`, `>=`
5. `+`, `-`
6. `*`, `/`
7. `\` (integer division), `MOD`
8. `^` (exponentiation, right-associative)
9. Unary `-`, `+`
10. Function calls, parenthesized expressions, literals, variables

## Usage

### Run a program file
```bash
python3 basic.py program.bas
```

### Evaluate a one-liner
```bash
python3 basic.py -e "PRINT 2+2"
python3 basic.py -e 'PRINT "Hello, World!"'
```

### Interactive REPL
```bash
python3 basic.py
```

REPL commands:
- `RUN` — Execute the current program
- `LIST` — Display all program lines
- `NEW` — Clear the program
- `QUIT` / `EXIT` — Leave the REPL

### Trace mode
```bash
python3 basic.py --trace program.bas
```

### Example Programs

The `examples/` directory contains several demonstration programs:

| File | Description |
|------|-------------|
| `hello.bas` | Hello World |
| `fibonacci.bas` | Fibonacci sequence (20 terms) |
| `sort.bas` | Bubble sort using arrays and DATA/READ |
| `gosub.bas` | GOSUB/RETURN with nested subroutines |
| `collatz.bas` | Collatz conjecture using WHILE/WEND |
| `deffn.bas` | User-defined functions (DEF FN) |
| `strings.bas` | String manipulation functions |
| `mandelbrot.bas` | ASCII Mandelbrot set renderer |
| `guess.bas` | Number guessing game (requires interactive input) |

## Supported Language Reference

### Statements
| Statement | Syntax | Description |
|----------|--------|-------------|
| LET | `LET var = expr` | Assignment (keyword optional) |
| PRINT | `PRINT expr [;|,] ...` | Output with formatting |
| INPUT | `INPUT ["prompt";] var, ...` | Read user input |
| IF | `IF expr THEN stmts [ELSE stmts]` | Conditional |
| FOR | `FOR var = start TO stop [STEP step]` | Loop init |
| NEXT | `NEXT [var]` | Loop increment |
| WHILE | `WHILE expr` | While loop |
| WEND | `WEND` | End while loop |
| GOTO | `GOTO linenum` | Unconditional jump |
| GOSUB | `GOSUB linenum` | Subroutine call |
| RETURN | `RETURN` | Return from subroutine |
| DIM | `DIM var(size), ...` | Declare arrays |
| READ | `READ var, ...` | Read from DATA |
| DATA | `DATA val, ...` | Define data values |
| RESTORE | `RESTORE` | Reset DATA pointer |
| DEF FN | `DEF FN name(params) = expr` | Define function |
| ON | `ON expr GOTO line, ...` | Computed goto |
| SWAP | `SWAP var1, var2` | Exchange variables |
| REM | `REM comment` | Comment |
| END | `END` | Terminate program |
| STOP | `STOP` | Breakpoint |

### Built-in Functions
| Function | Description |
|----------|-------------|
| `ABS(x)` | Absolute value |
| `INT(x)` | Floor (largest integer ≤ x) |
| `RND(x)` | Random number [0,1); x<0 seeds, x=0 repeats |
| `SQR(x)` | Square root |
| `SIN(x)`, `COS(x)`, `TAN(x)` | Trigonometric (radians) |
| `ATN(x)` | Arc tangent |
| `LOG(x)` | Natural logarithm |
| `EXP(x)` | Exponential |
| `LEN(s$)` | String length |
| `LEFT$(s$, n)` | Left substring |
| `RIGHT$(s$, n)` | Right substring |
| `MID$(s$, start [, len])` | Substring (1-indexed) |
| `CHR$(n)` | Character from ASCII code |
| `ASC(s$)` | ASCII code of first character |
| `STR$(n)` | Number to string |
| `VAL(s$)` | String to number |
| `INSTR([start,] haystack$, needle$)` | Find substring |
| `STRING$(n, char)` | Repeat character |
| `TAB(n)`, `SPC(n)` | Print positioning |

### Operators
| Operator | Description |
|----------|-------------|
| `+`, `-`, `*`, `/` | Arithmetic |
| `^` | Exponentiation |
| `\` | Integer division |
| `MOD` | Modulo |
| `=`, `<>`, `<`, `>`, `<=`, `>=` | Comparison (return -1 or 0) |
| `AND`, `OR`, `NOT` | Logical |
| `+` | String concatenation |