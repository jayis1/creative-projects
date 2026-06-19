# Contributing to MiniLang

Thank you for your interest in improving MiniLang! This guide covers the
basics of getting set up and contributing effectively.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/bytecode-vm-lang

# Create a virtual environment (optional but recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e .

# Run tests
python -m pytest tests/ -v

# Run the REPL
python -m minilang repl
```

## Project Architecture

MiniLang has a classic compiler pipeline:

```
Source → Lexer → Parser → Type Checker → [Optimizer] → Compiler → VM
```

| Module        | Responsibility                                  |
|---------------|--------------------------------------------------|
| `lexer.py`    | Tokenizes source code into a token stream        |
| `parser.py`   | Recursive-descent / Pratt parser → AST           |
| `ast.py`      | Frozen dataclass AST node definitions            |
| `types.py`    | Bidirectional type inference and checking        |
| `optimizer.py`| AST-level constant folding + dead-code elimination|
| `bytecode.py` | Instruction set (34+ opcodes) + disassembler      |
| `compiler.py` | AST → bytecode codegen with jump-and-patch       |
| `vm.py`       | Stack-based interpreter with mark-and-sweep GC   |
| `value.py`    | Runtime value representation (tagged union)      |
| `errors.py`   | Error hierarchy with source locations             |
| `cli.py`      | Command-line interface (run/dis/check/repl/benchmark/explain) |

## How to Add a New Builtin

1. **VM** (`vm.py`): Add the implementation function and register it in
   `_register_builtins()`.
2. **Type Checker** (`types.py`): Add the builtin name to `BUILTINS` dict
   and add type-checking logic in `_check_call()`.
3. **Compiler** (`compiler.py`): Add the name to `BUILTIN_NAMES`.
4. **Tests**: Add tests in `tests/test_bugfixes_and_features.py`.
5. **README**: Document the new builtin in the builtins table.
6. **Examples**: Add a usage example if the builtin is significant.

## How to Add a New Language Feature

1. **Lexer** (`lexer.py`): Add the new token kind and keyword mapping.
2. **AST** (`ast.py`): Add new AST node dataclasses if needed.
3. **Parser** (`parser.py`): Add the parsing logic in the appropriate
   precedence level.
4. **Type Checker** (`types.py`): Add type-checking for the new node.
5. **Compiler** (`compiler.py`): Add codegen for the new node.
6. **Optimizer** (`optimizer.py`): Add optimization if applicable.
7. **Tests**: Comprehensive tests for the feature.
8. **README**: Document the feature and add an example.

## Coding Standards

- Use `python3` (not `python`).
- Follow existing code style (type hints, docstrings, frozen dataclasses).
- Every function should have a docstring.
- Add type hints to all public APIs.
- Write tests for every new feature or bug fix.
- Ensure all tests pass before submitting: `python -m pytest tests/ -v`.

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test class
python -m pytest tests/test_bugfixes_and_features.py::TestStringBuiltins -v

# Run with coverage (if pytest-cov installed)
python -m pytest tests/ --cov=minilang --cov-report=term-missing
```

## Bug Reports

When filing a bug report, please include:
1. The MiniLang source code that triggers the bug.
2. The expected output.
3. The actual output (including error messages).
4. The Python version and OS.