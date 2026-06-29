# Contributing to the Forth Interpreter

Thank you for your interest in contributing! This document describes how to
set up a development environment and the conventions for submitting changes.

## Development Setup

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/forth-interpreter

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"
```

## Running Tests

```bash
# Run the full test suite
python3 -m pytest tests/ -v

# Run a specific test class
python3 -m pytest tests/test_forth.py::TestArithmetic -v

# Run with coverage
python3 -m pytest tests/ --cov=forth --cov-report=term-missing
```

## Architecture Overview

The interpreter is organised into a modular package:

```
forth/
├── __init__.py          # Public API exports
├── __main__.py           # Entry point for python -m forth
├── core.py              # Core interpreter engine (stack, dictionary, compiler, VM)
├── cli.py               # CLI with argparse, config, logging
└── builtins/            # Built-in word set (one module per category)
    ├── __init__.py       # register_all() — ties everything together
    ├── _helpers.py       # Shared type aliases
    ├── stack_ops.py      # DUP, DROP, SWAP, OVER, ROT, PICK, ROLL, etc.
    ├── arithmetic.py     # +, -, *, /, MOD, /MOD, NEGATE, ABS, MIN, MAX, etc.
    ├── float_ops.py      # F+, F-, F*, F/, FSQRT, FSIN, FCOS, etc.
    ├── comparison.py     # =, <>, <, >, <=, >=, 0=, 0<>, etc.
    ├── bitwise.py        # AND, OR, XOR, INVERT, LSHIFT, RSHIFT
    ├── io_ops.py         # ., EMIT, CR, SPACE, .S, TYPE, DUMP, .R
    ├── memory.py         # !, @, +!, ERASE, FILL, MOVE
    ├── defining.py       # VARIABLE, CONSTANT, VALUE, TO, CREATE
    ├── control_flow.py   # IF/ELSE/THEN, BEGIN/UNTIL, DO/LOOP, etc.
    ├── case_ops.py       # CASE/OF/ENDOF/ENDCASE
    ├── arrays.py         # ARRAY, []!, []@, ARRAY-SIZE
    ├── strings.py        # .", STRLEN, STRCAT, CMP-STR, SUBSTR, CHAR, [CHAR]
    ├── utility.py        # WORDS, SEE, FORGET, BYE, TRUE, FALSE, VERSION
    ├── exceptions.py     # CATCH, THROW, ABORT, ABORT"
    └── file_ops.py       # INCLUDE
```

## Adding a New Built-in Word

1. Identify the appropriate module in `forth/builtins/`.
2. Add the word registration inside the `register_*` function.
3. Add a test in `tests/test_new_features.py` (or the appropriate test file).
4. Update the word table in `README.md`.
5. Run tests: `python3 -m pytest tests/ -v`

Example:

```python
# In forth/builtins/arithmetic.py
def _square(i, t, n):
    """SQUARE ( n -- n*n )"""
    v = i.pop()
    i.push(v * v)
i.reg("SQUARE", _square, doc="Square top")
```

## Coding Conventions

- Use **type hints** throughout.
- Add **docstrings** to all public functions and classes.
- Follow the **Forth stack comment convention**: `( input -- output )`.
- Keep built-in words as **small focused functions**.
- Test before committing: `python3 -m pytest tests/ -v`.
- Use `python3` (not `python`) for all commands.

## Commit Messages

Follow this format:

```
Add <feature>: <brief description>
Enhance <feature>: <what changed>
Fix <bug>: <what was wrong>
```

## Pull Request Checklist

- [ ] All tests pass: `python3 -m pytest tests/ -v`
- [ ] New features have tests
- [ ] README.md updated if needed
- [ ] Code follows existing style conventions
- [ ] No hardcoded secrets or credentials