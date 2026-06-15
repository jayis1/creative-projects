# Contributing to regex-engine

Thank you for your interest in contributing! This document provides guidelines for contributing to the regex-engine project.

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/jayis1/creative-projects.git
   cd creative-projects/regex-engine
   ```

2. **Install development dependencies:**
   ```bash
   pip install pytest
   ```

3. **Run the test suite:**
   ```bash
   # Using the original test runner
   python3 tests.py

   # Using pytest
   python3 -m pytest tests/test_regex_engine.py -v
   ```

## Project Structure

```
regex-engine/
├── regex_engine/          # Main package
│   ├── __init__.py        # Module-level API and version
│   ├── __main__.py        # python -m regex_engine support
│   ├── parser.py          # Recursive descent parser → AST
│   ├── compiler.py        # Thompson's construction: AST → NFA
│   ├── nfa.py             # NFA state and fragment definitions
│   ├── matcher.py         # Thompson's two-list NFA simulation
│   ├── pattern.py         # High-level Pattern interface
│   └── cli.py             # Command-line interface
├── tests/
│   └── test_regex_engine.py  # Comprehensive pytest test suite
├── tests.py               # Original test runner (106 tests)
├── examples/              # Usage examples
├── pyproject.toml         # Package configuration
├── LICENSE                # MIT License
├── CONTRIBUTING.md         # This file
└── README.md              # Project documentation
```

## How to Contribute

### Reporting Bugs

1. Check existing issues to avoid duplicates
2. Create a new issue with:
   - Clear description of the bug
   - Minimal reproduction steps
   - Expected vs. actual behavior
   - Python version and OS

### Adding Features

1. **Fork** the repository
2. **Create a branch** for your feature: `git checkout -b feature/my-feature`
3. **Write code** following the existing style
4. **Add tests** for your feature
5. **Run all tests** to ensure nothing is broken
6. **Commit** with a descriptive message

### Code Style

- Follow PEP 8 for Python code
- Use type hints for function signatures
- Add docstrings to all public functions and classes
- Keep functions focused and small
- Use descriptive variable names

### Testing

- All new features must have tests
- All bug fixes must have regression tests
- Run both test suites before submitting:
  ```bash
  python3 tests.py                    # Original 106 tests
  python3 -m pytest tests/ -v         # Comprehensive pytest suite
  ```

### Architecture Notes

The regex engine has three main phases:

1. **Parsing** (`parser.py`): Recursive descent parser converts a regex pattern string into an AST. The parser uses operator precedence (alternation < concatenation < quantifier).

2. **Compilation** (`compiler.py` + `nfa.py`): Thompson's construction converts the AST into an NFA with O(m) states. Each AST node compiles to a constant number of states. The NFA uses five state types: CHAR, SPLIT, MATCH, ANCHOR_START, ANCHOR_END, GROUP_START, GROUP_END.

3. **Simulation** (`matcher.py`): Thompson's two-list algorithm simulates the NFA in O(nm) time. This guarantees no exponential backtracking, even on pathological inputs.

When adding features, consider which phase(s) need changes:

- **New syntax** → Parser + Compiler
- **New matching semantics** → Matcher
- **New API methods** → Pattern + Matcher
- **New state types** → NFA + Compiler + Matcher

## License

By contributing, you agree that your contributions will be licensed under the MIT License.