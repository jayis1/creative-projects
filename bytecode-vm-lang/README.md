# MiniLang — A Statically-Typed Language with a Bytecode VM

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-107%20passing-brightgreen)
![Version](https://img.shields.io/badge/version-2.0.0-orange)

MiniLang is a complete, self-contained programming language implementation
built from scratch in pure Python. It features a full compiler pipeline:
**lexer → Pratt parser → type checker → AST optimizer → bytecode compiler →
stack-based virtual machine with mark-and-sweep garbage collector**.

No external dependencies. No C extensions. Just pure Python.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Usage](#cli-usage)
- [Language Reference](#language-reference)
- [Built-in Functions](#built-in-functions)
- [Python API](#python-api)
- [Architecture](#architecture)
- [Examples](#examples)
- [Testing](#testing)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [License](#license)

---

## Features

### Language
- **Static typing** with bidirectional type inference
- **Types**: `int`, `string`, `bool`, `unit`, `array<T>`, `fn(P...) -> R`
- **Variables**: `let` (mutable) and `const` (immutable) with optional type annotations
- **Functions**: first-class declarations with recursion, type-checked params/returns
- **Control flow**: `if`/`elif`/`else`, `while`, `for i in start..end`, `break`, `continue`, `return`
- **Expressions**: arithmetic, comparison, logical (short-circuit), unary
- **String operations**: concatenation, lexicographic comparison, escape sequences
- **Arrays**: literals, indexing, index assignment, `len()`, `push()`
- **Comments**: line `//` and block `/* */`
- **27 built-in functions** (see [Built-in Functions](#built-in-functions))

### Runtime
- **34+ bytecode opcodes** with stack-based execution
- **Mark-and-sweep garbage collector** with exponential threshold growth
- **Step limit** (10M default) — prevents infinite loops
- **Call depth limit** (512 default) — prevents stack overflow from deep recursion
- **Truncate-toward-zero integer division** (C/Java/Rust semantics)

### Tooling
- **CLI** with `run`, `dis` (disassemble), `check` (type-check), `repl`,
  `benchmark`, and `explain` subcommands
- **JSON config files** for VM tuning (max_steps, max_call_depth, optimize)
- **AST optimizer** with constant folding and dead-code elimination
- **107 tests** covering lexer, parser, type checker, VM, optimizer, CLI, and all features
- **GitHub Actions CI** with multi-Python-version testing
- **Installable** via pip (`pip install -e .`)

---

## Installation

### From source

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/bytecode-vm-lang
pip install -e .
```

### Without installation

```bash
cd creative-projects/bytecode-vm-lang
python -m minilang run examples/fibonacci.ml
```

---

## Quick Start

```bash
# Run a program
python -m minilang run examples/fibonacci.ml
# Output: 55
#         6765

# Type-check without running
python -m minilang check examples/fibonacci.ml
# Output: OK: no type errors.

# Disassemble bytecode
python -m minilang dis examples/fibonacci.ml

# Benchmark execution
python -m minilang benchmark examples/fibonacci.ml -n 100

# See the full compilation pipeline
python -m minilang explain examples/fibonacci.ml

# Start the REPL
python -m minilang repl
```

### Hello, World!

```minilang
print("Hello, World!");
```

### Factorial

```minilang
fn factorial(n: int) -> int {
    if n <= 1 { return 1; }
    return n * factorial(n - 1);
}
print(factorial(5));  // 120
```

---

## CLI Usage

```
usage: minilang [-h] [--version] {run,dis,check,repl,benchmark,explain} ...

MiniLang — a statically-typed language with a bytecode VM

options:
  -h, --help     show this help message and exit
  --version      show program's version number and exit

subcommands:
  run          Execute a MiniLang file
  dis          Disassemble a MiniLang file
  check        Type-check a MiniLang file
  repl         Start the interactive REPL
  benchmark    Benchmark execution time
  explain      Show full compilation pipeline
```

### `run` — Execute a program

```bash
python -m minilang run <file> [--debug] [--no-opt] [--config <config.json>]
```

### `benchmark` — Measure performance

```bash
python -m minilang benchmark <file> [-n <iterations>]

# Example output:
# Benchmark: examples/fibonacci.ml
#   Iterations:  100
#   Average:     295.011 ms
#   Min:         286.085 ms
#   Max:         314.865 ms
#   Throughput:  3 runs/s
```

### `explain` — Full pipeline inspection

Shows tokens, AST, type checker output, optimizer stats, compiled bytecode
stats, and VM execution results — all in one command.

### Config Files

JSON config files allow tuning the VM without code changes:

```json
{
  "max_steps": 5000000,
  "max_call_depth": 256,
  "debug": false,
  "optimize": true
}
```

```bash
python -m minilang run examples/fibonacci.ml --config examples/minilang.json
```

---

## Language Reference

### Variables

```minilang
let x: int = 42;       // mutable, with type annotation
let y = 10;             // mutable, type inferred
const PI = 314;         // immutable constant
const name: string = "MiniLang";
```

### Functions

```minilang
fn add(a: int, b: int) -> int {
    return a + b;
}

fn greet(name: string) -> string {
    return "Hello, " + name + "!";
}

// Recursion
fn fib(n: int) -> int {
    if n < 2 { return n; }
    return fib(n - 1) + fib(n - 2);
}
```

### Control Flow

```minilang
// If / Elif / Else
if x < 0 {
    print("negative");
} elif x == 0 {
    print("zero");
} elif x < 10 {
    print("small");
} else {
    print("large");
}

// While loop
let i = 0;
while i < 10 { i = i + 1; }

// For loop (range-based, exclusive end)
for i in 0..10 { print(i); }

// Break and continue
for i in 0..100 {
    if i == 5 { break; }
    if i % 2 == 0 { continue; }
    print(i);
}
```

### Expressions

```minilang
let a = 1 + 2 * 3;       // 7 (precedence)
let b = (1 + 2) * 3;     // 9
let c = 10 / 3;           // 3 (truncates toward zero)
let d = -7 / 2;           // -3 (not -4)
let e = "abc" < "abd";   // true (lexicographic)
let f = true && false;    // false (short-circuit)
let g = !true;            // false
```

### Arrays

```minilang
let arr = [1, 2, 3];
let x = arr[0];           // 1
arr[0] = 42;              // index assignment
push(arr, 4);             // append
let n = len(arr);         // 4
```

See [docs/language-reference.md](docs/language-reference.md) for the complete
reference.

---

## Built-in Functions

### General

| Function          | Description                        |
|-------------------|------------------------------------|
| `print(x)`        | Print value to stdout              |
| `len(x)`          | Length of array or string          |
| `str(x)`          | Convert any value to string        |
| `int(x)`          | Convert string/bool/int to int    |
| `typeof(x)`       | Get type name as string            |
| `assert(c, msg?)` | Assert condition (optional message)|

### Math

| Function       | Description                    |
|----------------|--------------------------------|
| `abs(x)`       | Absolute value                 |
| `max(a, b)`    | Maximum of two ints            |
| `min(a, b)`    | Minimum of two ints            |
| `randint(a,b)` | Random int in [a, b]           |
| `time()`       | Unix timestamp                 |

### String

| Function              | Description                     |
|-----------------------|---------------------------------|
| `upper(s)`            | Uppercase                       |
| `lower(s)`            | Lowercase                       |
| `contains(s, sub)`    | Check if s contains sub         |
| `slice(s, start, end)`| Substring [start, end)          |
| `charAt(s, i)`        | Character at index              |
| `split(s, sep)`       | Split string by separator       |

### Array

| Function            | Description                      |
|---------------------|----------------------------------|
| `push(arr, x)`      | Append to array                  |
| `pop(arr)`          | Remove and return last element   |
| `reverse(arr)`      | Reversed copy                    |
| `concat(a, b)`      | Concatenate two arrays           |
| `find(arr, x)`      | Find index of x (-1 if not found)|
| `sort(arr)`         | Sorted copy                      |
| `sum(arr)`          | Sum of int array                 |

---

## Python API

```python
from minilang import compile_program, VM

# Compile and run
program = compile_program("""
fn factorial(n: int) -> int {
    if n <= 1 { return 1; }
    return n * factorial(n - 1);
}
print(factorial(5));
""")

vm = VM(program)
vm.run()
print(vm.output)  # ['120']

# With optimizer
program = compile_program("print(2 + 3 * 4);", optimize_ast=True)
vm = VM(program)
vm.run()
print(vm.output)  # ['14']

# With custom limits
vm = VM(program, max_steps=1000, max_call_depth=50)
```

---

## Architecture

```
Source code
    │
    ▼
┌──────────┐     ┌──────────┐     ┌──────────────┐     ┌───────────┐
│  Lexer   │────▶│  Parser  │────▶│ Type Checker │────▶│ Optimizer │
│ (scanner)│     │ (Pratt)  │     │ (inference)  │     │ (folding) │
└──────────┘     └──────────┘     └──────────────┘     └───────────┘
                                                           │
                                                           ▼
┌──────────────────────────────────┐               ┌────────────┐
│             Bytecode VM           │◀──────────────│  Compiler  │
│  (stack-based + mark-sweep GC)    │               │ (codegen)  │
└──────────────────────────────────┘               └────────────┘
```

See [docs/architecture.md](docs/architecture.md) for a detailed explanation
of each pipeline stage.

### Project Structure

```
bytecode-vm-lang/
├── minilang/
│   ├── __init__.py     # Public API
│   ├── __main__.py     # python -m minilang entry point
│   ├── errors.py       # Error hierarchy with source locations
│   ├── lexer.py        # Hand-written scanner (tokens, keywords, operators)
│   ├── ast.py          # AST node definitions (frozen dataclasses)
│   ├── parser.py       # Recursive-descent / Pratt parser
│   ├── types.py        # Type checker with bidirectional inference
│   ├── optimizer.py    # Constant folding + dead-code elimination
│   ├── bytecode.py     # Instruction set (34+ opcodes) + disassembler
│   ├── compiler.py     # AST → bytecode codegen
│   ├── vm.py           # Stack-based VM with mark-and-sweep GC
│   ├── value.py        # Runtime value representation (tagged union)
│   └── cli.py          # CLI (run/dis/check/repl/benchmark/explain)
├── tests/
│   ├── test_minilang.py             # Core tests (48 tests)
│   └── test_bugfixes_and_features.py # Bug fixes + features (59 tests)
├── examples/
│   ├── fibonacci.ml      # Recursive Fibonacci
│   ├── bubblesort.ml     # Bubble sort with arrays
│   ├── primes.ml         # Sieve of Eratosthenes
│   ├── gcd.ml            # Euclid's GCD algorithm
│   ├── string_demo.ml    # String manipulation builtins
│   ├── array_demo.ml     # Array manipulation builtins
│   ├── elif_demo.ml      # elif chains and FizzBuzz
│   └── minilang.json     # Config file example
├── docs/
│   ├── language-reference.md  # Full language reference
│   └── architecture.md       # Internal architecture
├── .github/workflows/
│   └── bytecode-vm-lang.yml  # CI config (GitHub Actions)
├── CONTRIBUTING.md     # Contributing guide
├── LICENSE             # MIT License
├── pyproject.toml      # Package metadata
└── README.md           # This file
```

---

## Examples

### Fibonacci

```minilang
fn fib(n: int) -> int {
    if n < 2 { return n; }
    return fib(n - 1) + fib(n - 2);
}
print(fib(10));  // 55
print(fib(20));  // 6765
```

### Sieve of Eratosthenes

```minilang
fn sieve(n: int) -> array<int> {
    let is_prime = [];
    for i in 0..n { push(is_prime, 1); }
    for i in 2..n {
        if is_prime[i] == 1 {
            let j = i * i;
            while j < n {
                is_prime[j] = 0;
                j = j + i;
            }
        }
    }
    let primes = [];
    for i in 2..n {
        if is_prime[i] == 1 { push(primes, i); }
    }
    return primes;
}
let result = sieve(30);
print(len(result));  // 10
```

### String Processing

```minilang
fn capitalize(s: string) -> string {
    if len(s) == 0 { return ""; }
    return upper(charAt(s, 0)) + lower(slice(s, 1, len(s)));
}

let names = split("alice,bob,charlie", ",");
for i in 0..len(names) {
    print(capitalize(names[i]));
}
// Alice, Bob, Charlie
```

### Quicksort with Array Builtins

```minilang
fn quicksort(arr: array<int>) -> array<int> {
    if len(arr) <= 1 { return arr; }
    let pivot = arr[0];
    let less = [];
    let greater = [];
    for i in 1..len(arr) {
        if arr[i] < pivot { push(less, arr[i]); }
        else { push(greater, arr[i]); }
    }
    return concat(quicksort(less), concat([pivot], quicksort(greater)));
}
```

### FizzBuzz with Elif

```minilang
for i in 1..16 {
    if i % 15 == 0 { print("FizzBuzz"); }
    elif i % 3 == 0 { print("Fizz"); }
    elif i % 5 == 0 { print("Buzz"); }
    else { print(i); }
}
```

---

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test class
python -m pytest tests/test_bugfixes_and_features.py::TestStringBuiltins -v

# Run with short output
python -m pytest tests/ -q
```

All 107 tests pass:
- 48 core tests (lexer, parser, type checker, VM, optimizer)
- 59 feature/bugfix tests (nested loops, division, call depth, new builtins, elif, CLI)

---

## Known Issues (Resolved)

### Bug 1: Nested loop break/continue target loss (FIXED)

**Problem**: In `compiler.py`, `_break_targets` and `_continue_targets` were
flat lists that were reset to `[]` at the start of each loop. Break/continue
targets from an outer loop that appeared before an inner loop were lost when
the inner loop reset the list.

**Fix**: Replaced flat lists with a proper stack
`_loop_break_continue: list[tuple[list[int], list[int]]]`. Each loop pushes a
fresh `(break_targets, continue_targets)` pair, and pops it when done. This
ensures break/continue always target the innermost loop.

### Bug 2: Integer division truncation direction (FIXED)

**Problem**: Python's `//` truncates toward negative infinity (`-7 // 2 == -4`),
but most languages truncate toward zero (`-3`).

**Fix**: Added `_int_div` and `_int_mod` static methods in the VM that use
`abs()` division with sign handling. The optimizer's constant folder uses the
same logic via `_trunc_div()`.

### Bug 3: No call depth limit (FIXED)

**Problem**: Deep recursion caused a Python stack overflow before the step
limit triggered.

**Fix**: Added a `max_call_depth` parameter (default 512) to the VM. The CALL
handler increments `_call_depth` and raises a `VMError` if it exceeds the
limit. RETURN decrements it.

### Bug 4: GC array tracking (NOT A BUG — works correctly)

**Analysis**: Arrays are raw Python lists appended to `self.heap`. The GC's
`mark_value` marks by `id(v.payload)`, which correctly identifies array
objects. The type annotation says `list[Object]` but contains raw lists —
this is a type-annotation inaccuracy, not a correctness bug. The GC works
correctly because it uses `id()` for marking, not `isinstance`.

### Bug 5: Assignment expression efficiency (LOW PRIORITY)

**Analysis**: `Assign` compilation does `STORE_LOCAL` then `LOAD_LOCAL` (two
instructions) instead of a single `DUP_STORE` opcode. This is a minor
performance issue, not a correctness bug. The current approach is correct and
clear; a `DUP_TOP` + `STORE_LOCAL` optimization could be added in the future.

---

## Roadmap

- [ ] **Closures with captured upvalues** — first-class function values
- [ ] **String interpolation** — `"Hello, {name}!"`
- [ ] **Float type** — `float` type with floating-point arithmetic
- [ ] **Struct/record types** — user-defined data structures
- [ ] **Module system** — `import` and `export` for multi-file programs
- [ ] **Standard library** — collections, math, I/O modules
- [ ] **Native compilation** — transpile to C or LLVM IR
- [ ] **REPL with multiline support** — multi-statement input
- [ ] **Debugger** — breakpoints, step-through, variable inspection
- [ ] **DUP_TOP opcode** — optimize assignment expressions

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full contributing guide,
including how to add new builtins, language features, and the development
workflow.

```bash
# Quick start for contributors
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/bytecode-vm-lang
python -m pytest tests/ -v  # all tests should pass
```

---

## Changelog

### v2.0.0 — Comprehensive Improvement

**Bug Fixes:**
- Fixed nested loop break/continue target loss (Bug 1)
- Fixed integer division/modulo to truncate toward zero (Bug 2)
- Added call depth limit to prevent stack overflow (Bug 3)

**New Features:**
- `elif` keyword for cleaner conditional chains
- 18 new built-in functions:
  - String: `upper`, `lower`, `contains`, `slice`, `charAt`, `split`
  - Array: `pop`, `reverse`, `concat`, `find`, `sort`, `sum`
  - Utility: `typeof`, `time`, `randint`
- CLI `benchmark` subcommand for performance measurement
- CLI `explain` subcommand for full pipeline inspection
- JSON config file support (`--config`)
- `--no-opt` flag to disable the AST optimizer
- `python -m minilang` support via `__main__.py`
- Logging via Python `logging` module
- 3 new example programs (string_demo, array_demo, elif_demo)

**Infrastructure:**
- 59 new tests (107 total, all passing)
- GitHub Actions CI with multi-Python-version testing
- LICENSE (MIT)
- CONTRIBUTING.md
- docs/ directory with language reference and architecture docs
- Dramatically improved README with badges, TOC, examples, roadmap

### v1.0.0 — Initial Release

- Lexer, Pratt parser, type checker, optimizer, bytecode compiler, VM with GC
- 34 opcodes, 9 built-in functions
- CLI with run/dis/check/repl
- 48 tests, 4 examples

---

## License

MIT License — see [LICENSE](LICENSE).