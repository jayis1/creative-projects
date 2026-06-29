# Forth Interpreter — Architecture Documentation

## Overview

The Forth interpreter is a stack-based language interpreter implemented in
pure Python. It compiles Forth source code into a bytecode-like intermediate
representation (IR) and executes it via a simple virtual machine.

## Core Components

### `forth/core.py` — The Engine

The `ForthInterpreter` class is the heart of the interpreter. It manages:

- **Data stack** (`List[Any]`) — the main operand stack for all computations
- **Return stack** (`List[Any]`) — used for loop state and temporary storage
- **Dictionary** (`Dict[str, Word]`) — maps word names to `Word` objects
- **Variable storage** (`Dict[str, List[Any]]`) — named cells holding mutable values
- **Compilation state** — when `:` starts a definition, the interpreter switches to compile mode

### Compilation

When `: NAME ... ;` is encountered, the interpreter enters compile mode.
Tokens are compiled into an instruction list using tuples:

| Instruction | Format | Description |
|------------|--------|-------------|
| `lit` | `("lit", value)` | Push a literal value |
| `call` | `("call", wordname)` | Call a word |
| `if` | `("if", target)` | Pop flag; if zero, jump to target |
| `jump` | `("jump", target)` | Unconditional jump |
| `until` | `("until", target)` | Pop flag; if zero, jump back to target |
| `while` | `("while", target)` | Pop flag; if zero, jump past REPEAT |
| `do` | `("do", target)` | Pop limit and start; push loop state |
| `loop` | `("loop", target)` | Increment index; if within bounds, jump to body |
| `plusloop` | `("plusloop", target)` | Add increment; if boundary not crossed, jump |
| `leave` | `("leave", target)` | Exit loop; jump past LOOP |

Immediate words (IF, ELSE, THEN, BEGIN, etc.) execute during compilation to
emit these instructions and manage fixup positions via the return stack.

### Execution

The `_execute_body` method is a bytecode interpreter that walks the
instruction list, maintaining an instruction pointer (IP). Control-flow
instructions modify the IP. The `_ExitBody` exception handles the `EXIT`
word for early return.

Recursion depth is tracked and limited to prevent Python stack overflow.

### Tokenizer

The tokenizer handles:
- `\` line comments
- `( ... )` block comments (nested)
- `"..."` string literals (returned as a single token with quotes)
- Special consuming words: `."`, `C"`, `ABORT"` (read until next `"`)
- Special consuming word: `.( ` (read until `)`)

### Built-in Word Registration

Built-in words are registered via the `forth/builtins/` package, which
splits the word set by category. Each module exposes a `register_*` function
that takes the interpreter and registers the relevant words.

### Native Word Protocol

Built-in words are Python callables with the signature:
```
(interpreter, tokens, token_index) -> Any
```

- Regular built-ins return `None` (or any non-`_NextIdx` value) to indicate
  "advance to the next token."
- Defining words (VARIABLE, CONSTANT, etc.) that consume extra tokens return
  `_NextIdx(new_idx)` to jump the token pointer forward.
- Immediate words execute during compilation instead of being compiled.

## CLI

The `forth/cli.py` module provides the command-line interface with:
- `argparse` for flags: `-e`, `-f`, `-i`, `-c`, `--debug`, `--no-banner`, `--version`
- JSON/YAML config file support
- Python logging integration
- Configurable stack size and recursion limits