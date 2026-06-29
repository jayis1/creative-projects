# Forth Interpreter

A stack-based Forth language interpreter implemented from scratch in pure Python.

## Description

This project implements a fully functional Forth interpreter supporting integer and float arithmetic, stack manipulation, variables, constants, values, arrays, colon definitions, and all major control-flow constructs (IF/ELSE/THEN, BEGIN/UNTIL, BEGIN/WHILE/REPEAT, AGAIN, DO/LOOP, DO/+LOOP, LEAVE, EXIT, RECURSE, CASE/OF/ENDOF/ENDCASE). The interpreter features a compilation mode where colon definitions are compiled into an intermediate representation and executed via a bytecode-like VM with jump instructions.

## How It Works

### Architecture

The interpreter is organized around a single `ForthInterpreter` class that holds:

- **Data stack** — the main operand stack for all computations
- **Return stack** — used for loop state and temporary storage (`>R`/`R>`)
- **Dictionary** — maps word names to `Word` objects (native built-ins or compiled user definitions)
- **Variable storage** — named cells holding mutable values (variables, values, and arrays)
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

Immediate words (IF, ELSE, THEN, BEGIN, UNTIL, WHILE, REPEAT, AGAIN, DO, LOOP, +LOOP, LEAVE, RECURSE, CASE, OF, ENDOF, ENDCASE, .") execute during compilation to emit these instructions and manage fixup positions via the return stack.

### Execution

The `_execute_body` method is a simple bytecode interpreter that walks the instruction list, maintaining an instruction pointer (IP). Control-flow instructions modify the IP. The `_ExitBody` exception handles the `EXIT` word for early return.

### Native Word Protocol

Built-in words are Python callables with the signature `(interp, tokens, idx) -> Any`. Regular built-ins return `None` (or any non-`_NextIdx` value) to indicate "advance to the next token." Defining words (VARIABLE, CONSTANT, etc.) that consume extra tokens return `_NextIdx(new_idx)` to jump the token pointer forward.

### Built-in Words

| Category | Words |
|----------|-------|
| Stack | DUP, DROP, SWAP, OVER, ROT, -ROT, NIP, TUCK, ?DUP, DEPTH, PICK, ROLL |
| Double stack | 2DUP, 2DROP, 2SWAP, 2OVER |
| Return stack | >R, R>, R@ |
| Arithmetic | +, -, *, /, MOD, /MOD, NEGATE, ABS, MIN, MAX, **, 1+, 1-, 2+, 2-, 2*, 2/ |
| Float | F+, F-, F*, F/, FSQRT, FSIN, FCOS, FTAN, FLOG, FEXP, FLOOR, CEIL, ROUND |
| Comparison | =, <>, <, >, <=, >=, 0=, 0<>, 0<, 0> |
| Bitwise | AND, OR, XOR, INVERT, LSHIFT, RSHIFT, NOT |
| I/O | ., EMIT, CR, SPACE, BL, .S, TYPE, DUMP |
| Memory | !, @, +!, []!, []@ |
| Defining | : ; VARIABLE, CONSTANT, VALUE, TO, ARRAY |
| Control flow | IF, ELSE, THEN, BEGIN, UNTIL, WHILE, REPEAT, AGAIN, DO, LOOP, +LOOP, LEAVE, EXIT, RECURSE |
| Case | CASE, OF, ENDOF, ENDCASE |
| Loop index | I, J |
| Strings | ." (compiled string printing) |
| Utility | WORDS, SEE, FORGET, BYE, TRUE, FALSE, SP@, CELLS, CELL+, ALLOT |

## Usage

### Interactive REPL

```bash
python3 -m forth
```

```
Forth Interpreter v2.0 — type BYE to exit, WORDS for word list
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
python3 -m forth -f examples/primes.fs
python3 -m forth -f examples/bubble-sort.fs
```

### Python API

```python
from forth import ForthInterpreter
import io

out = io.StringIO()
interp = ForthInterpreter(output=out)
interp.eval(': SQUARE DUP * ; 5 SQUARE . CR')
print(out.getvalue())  # "25 \n"
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

### Prime Numbers

```forth
: PRIME?
    DUP 2 < IF DROP FALSE EXIT THEN
    DUP 2 = IF DROP TRUE EXIT THEN
    DUP 2 MOD 0 = IF DROP FALSE EXIT THEN
    DUP 3 BEGIN
        2DUP >
    WHILE
        2DUP MOD 0 =
        IF 2DROP FALSE EXIT THEN
        2 +
    REPEAT
    2DROP TRUE ;
: .PRIMES 30 2 DO I PRIME? IF I . THEN LOOP ;
.PRIMES CR
```
Output: `2 3 5 7 11 13 17 19 23 29`

### Bubble Sort with Arrays

```forth
ARRAY DATA 10
42 0 DATA []!
17 1 DATA []!
\ ... more elements ...
VARIABLE TEMP
: BUBBLE-PASS 9 0 DO I DATA []@ I 1+ DATA []@ > IF
    I DATA []@ TEMP ! I 1+ DATA []@ I DATA []! TEMP @ I 1+ DATA []!
THEN LOOP ;
: BUBBLE 9 0 DO BUBBLE-PASS LOOP ;
BUBBLE
```

### Compiled String Printing

```forth
: GREET ." Hello, World!" ;
GREET CR
```
Output: `Hello, World!`

## Installation

```bash
pip install -e .
```

Or run directly without installation:

```bash
python3 -m forth -e '100 2 / . CR'
```

## Testing

```bash
python3 -m pytest tests/test_forth.py -v
```

102 tests covering arithmetic, floats, stack ops, comparisons, bitwise, variables, arrays, control flow, CASE/OF, strings, error handling, and the primes example.

## Known Issues (Resolved)

### Bug 1: CASE/OF/ENDOF/ENDCASE — bogus literal instruction (Fixed)
The `OF` word pushed a `("lit", "of-check")` instruction into the compiled body, corrupting the data stack at runtime. Additionally, `ENDCASE`'s DROP instruction was not jumped over by matching OF clauses, causing a stack underflow. Fixed by removing the bogus literal and correctly fixing up ENDOF jump targets to skip past ENDCASE's DROP.

### Bug 2: `_arr_store` dead code (Fixed)
The `[]!` word contained confusing dead code (`if isinstance(arr, list) and not isinstance(arr[0], list) if arr else True: pass`) that served no purpose. Replaced with a proper type check that raises an error if the target is not an array.

### Bug 3: `_reset_state` didn't clear `current_name` (Fixed)
After a compilation error, `current_name` was not cleared. This could cause `RECURSE` in a subsequent definition to accidentally call the failed word's name. Fixed by clearing `current_name` in `_reset_state`.

### Bug 4: `@` and `!` didn't validate scalar vs array access (Fixed)
Using `@` on an array variable would push the entire list, and `!` on an array would overwrite it with a single value. Fixed by checking that the variable is a scalar (single-cell) before allowing `@`/`!` access, with a helpful error message directing the user to `[]@`/`[]!`.

### Bug 5: Duplicate `."` registration (Fixed)
The `."` word was registered twice — first as a no-op lambda, then as the real implementation. While the second registration overrode the first, the duplicate was confusing dead code. Removed the no-op registration.

## Project Structure

```
forth-interpreter/
├── forth/
│   ├── __init__.py       # Package init, exports ForthInterpreter
│   ├── __main__.py        # CLI entry point
│   └── interpreter.py     # Core interpreter implementation
├── examples/
│   ├── primes.fs          # Prime number sieve
│   └── bubble-sort.fs     # Bubble sort with arrays
├── tests/
│   └── test_forth.py      # Comprehensive pytest suite (89 tests)
├── pyproject.toml         # Project metadata
├── README.md              # This file
└── test_quick.py          # Quick test script
```