# bytecode-vm-lang

## MiniLang — A Statically-Typed Language with a Bytecode VM

MiniLang is a complete, self-contained programming language implementation built from scratch in pure Python. It features a full compiler pipeline: lexer → Pratt parser → type checker → AST optimizer → bytecode compiler → stack-based virtual machine with a mark-and-sweep garbage collector.

### Architecture

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

### Language Features

- **Types**: `int`, `string`, `bool`, `unit`, `array<T>`, `fn(P...) -> R`
- **Variables**: `let` (mutable) and `const` (immutable) declarations with optional type annotations
- **Functions**: first-class declarations with type-checked parameters and return types, recursion supported
- **Control flow**: `if`/`else`, `while`, `for i in start..end`, `break`, `continue`, `return`
- **Expressions**: arithmetic (`+ - * / %`), comparison (`< <= > >= == !=`), logical (`&& || !` with short-circuit evaluation), unary (`- !`)
- **Arrays**: literal `[1, 2, 3]`, indexing `arr[i]`, index assignment `arr[i] = x`, `len()`, `push()`
- **Builtins**: `print(x)`, `len(x)`, `push(arr, x)`, `str(x)`, `int(x)`
- **Comments**: line `// comment` and block `/* comment */`
- **Strings**: with escape sequences `\n \t \r \\ \" \0`

### Bytecode VM

The VM is a stack-based interpreter with:
- **34 opcodes** covering literals, locals, arrays, arithmetic, comparisons, logic, control flow, calls, and builtins
- **Call frames** with independent operand stacks and locals arrays
- **Mark-and-sweep garbage collector** that traces through all live frames' roots (locals + stacks)
- **Step limit** protection against infinite loops (configurable, default 10M steps)
- **Short-circuit evaluation** for `&&` and `||` via jump instructions

### Optimizer

The AST-level optimizer performs:
1. **Constant folding** — evaluates `2 + 3` → `5` at compile time
2. **Dead-code elimination** — removes statements after unconditional `return`/`break`/`continue`
3. **Jump threading** — collapses `JUMP → JUMP` chains in bytecode

### Usage

```bash
# Run a program
python -m minilang run examples/fibonacci.ml

# Disassemble bytecode
python -m minilang dis examples/fibonacci.ml

# Type-check only
python -m minilang check examples/fibonacci.ml

# Start REPL
python -m minilang repl
```

### Python API

```python
from minilang import compile_program, VM

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
```

### Example Program

```minilang
// sieve.ml — sieve of Eratosthenes
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

### Project Structure

```
bytecode-vm-lang/
├── minilang/
│   ├── __init__.py     # Public API
│   ├── errors.py       # Error hierarchy with source locations
│   ├── lexer.py        # Hand-written scanner (tokens, keywords, operators)
│   ├── ast.py          # AST node definitions (frozen dataclasses)
│   ├── parser.py       # Recursive-descent / Pratt parser
│   ├── types.py        # Type checker with bidirectional inference
│   ├── optimizer.py    # Constant folding + dead-code elimination
│   ├── bytecode.py     # Instruction set + disassembler
│   ├── compiler.py     # AST → bytecode codegen
│   ├── vm.py           # Stack-based VM with mark-and-sweep GC
│   └── cli.py          # Command-line interface (run/dis/check/repl)
├── tests/
│   └── test_minilang.py
├── examples/
│   ├── fibonacci.ml
│   ├── bubblesort.ml
│   └── primes.ml
└── pyproject.toml
```