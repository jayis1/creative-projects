# Forth Interpreter

A stack-based Forth language interpreter implemented from scratch in pure Python.

## Description

This project implements a fully functional Forth interpreter supporting integer and float arithmetic, stack manipulation, variables, constants, values, colon definitions, and all major control-flow constructs (IF/ELSE/THEN, BEGIN/UNTIL, BEGIN/WHILE/REPEAT, DO/LOOP, DO/+LOOP, LEAVE). The interpreter features a compilation mode where colon definitions are compiled into an intermediate representation and executed via a bytecode-like VM with jump instructions.

## How It Works

### Architecture

The interpreter is organized around a single `ForthInterpreter` class that holds:

- **Data stack** — the main operand stack for all computations
- **Return stack** — used for loop state and temporary storage (`>R`/`R>`)
- **Dictionary** — maps word names to `Word` objects (native built-ins or compiled user definitions)
- **Variable storage** — named cells holding mutable values
- **Compilation state** — when `:` starts a definition, the interpreter switches to compile mode

### Compilation

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

Immediate words (IF, ELSE, THEN, BEGIN, UNTIL, WHILE, REPEAT, DO, LOOP, +LOOP, LEAVE, RECURSE) execute during compilation to emit these instructions and manage fixup positions via the return stack.

### Execution

The `_execute_body` method is a simple bytecode interpreter that walks the instruction list, maintaining an instruction pointer (IP). Control-flow instructions modify the IP. The `_ExitBody` exception handles the `EXIT` word for early return.

### Built-in Words

| Category | Words |
|----------|-------|
| Stack | DUP, DROP, SWAP, OVER, ROT, -ROT, NIP, TUCK, ?DUP, DEPTH |
| Double stack | 2DUP, 2DROP, 2SWAP, 2OVER |
| Return stack | >R, R>, R@ |
| Arithmetic | +, -, *, /, MOD, /MOD, NEGATE, ABS, MIN, MAX, ** |
| Float | F+, F-, F*, F/, FSQRT, FSIN, FCOS, FTAN, FLOG, FEXP, FLOOR, CEIL, ROUND |
| Comparison | =, <>, <, >, <=, >=, 0=, 0<>, 0<, 0> |
| Bitwise | AND, OR, XOR, INVERT, LSHIFT, RSHIFT, NOT |
| I/O | ., EMIT, CR, SPACE, BL, .S, TYPE |
| Memory | !, @, +! |
| Defining | : ; VARIABLE, CONSTANT, VALUE, TO |
| Control flow | IF, ELSE, THEN, BEGIN, UNTIL, WHILE, REPEAT, AGAIN, DO, LOOP, +LOOP, LEAVE, EXIT, RECURSE |
| Loop index | I, J |
| Utility | WORDS, SEE, FORGET, BYE, TRUE, FALSE |

## Usage

### Interactive REPL

```bash
python3 -m forth
```

```
Forth Interpreter v1.0 — type BYE to exit
ok 3 4 + . CR
7
ok
```

### Evaluate a code string

```bash
python3 -m forth -e '5 DUP * . CR'
25
```

### Execute a file

```bash
python3 -m forth -f program.fs
```

### Python API

```python
from forth import ForthInterpreter

interp = ForthInterpreter()
interp.eval(': SQUARE DUP * ; 5 SQUARE . CR')
# Output: 25
```

## Examples

### Factorial (recursive)

```forth
: FACT DUP 1 > IF DUP 1 - RECURSE * THEN ;
5 FACT . CR
```
Output: `120`

### Fibonacci (recursive)

```forth
: FIB DUP 2 < IF EXIT THEN DUP 1 - RECURSE SWAP 2 - RECURSE + ;
10 FIB . CR
```
Output: `55`

### Variables and Loops

```forth
VARIABLE SUM 0 SUM !
10 0 DO I SUM @ + SUM ! LOOP
SUM @ . CR
```
Output: `45`

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

## Installation

```bash
pip install -e .
```

Or run directly without installation:

```bash
python3 -m forth -e '100 2 / . CR'
```

## Project Structure

```
forth-interpreter/
├── forth/
│   ├── __init__.py       # Package init, exports ForthInterpreter
│   ├── __main__.py        # CLI entry point
│   └── interpreter.py     # Core interpreter implementation
├── pyproject.toml         # Project metadata
├── README.md              # This file
└── test_quick.py          # Quick test suite
```