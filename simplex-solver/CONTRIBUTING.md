# Contributing to simplex-solver

Thank you for your interest in improving simplex-solver! This document
covers the development workflow and conventions.

## Getting Started

```bash
# Clone the repository
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/simplex-solver

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e .
pip install pytest
```

## Development Workflow

1. **Create a branch** for your feature or fix:
   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Write code** following the existing style:
   - Use type hints on all public functions
   - Write docstrings (module, class, public methods)
   - Keep functions focused — one responsibility each
   - Prefer `Fraction` for exact arithmetic in the solver core

3. **Write tests** for new features:
   - Place tests in `tests/test_<module>.py`
   - Use `pytest` fixtures for common setup
   - Test both correctness (expected results) and edge cases
   - Verify that existing tests still pass: `pytest tests/ -v`

4. **Update documentation**:
   - Update the README if you add features or change the API
   - Add examples to `examples/` for new problem types
   - Update the changelog section in the README

5. **Commit and push**:
   ```bash
   git add -A
   git commit -m "feat: add Gomory mixed-integer cuts"
   git push origin feature/my-new-feature
   ```

## Code Style

- **Python version**: 3.10+ (uses `match`-compatible syntax, `|` union types)
- **Line length**: 100 characters max
- **Imports**: Standard library first, then third-party, then local
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes
- **Docstrings**: Google/Sphinx style with `Parameters`, `Returns`, `Raises`
- **Type hints**: Required on all public functions, encouraged on internal

## Testing

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run a specific test file
pytest tests/test_basic.py -v

# Run with coverage (if installed)
pip install pytest-cov
pytest tests/ --cov=simplex --cov-report=term-missing
```

## Pull Request Checklist

- [ ] All existing tests pass (`pytest tests/`)
- [ ] New tests written for new features
- [ ] Type hints added to new functions
- [ ] Docstrings written for new modules/classes/functions
- [ ] README updated if needed
- [ ] Examples added for new problem types
- [ ] No new linting errors (run `ruff check simplex/ tests/`)

## Reporting Bugs

When reporting a bug, please include:

1. The problem definition (JSON or MPS format)
2. The expected result
3. The actual result (including the full error traceback if applicable)
4. Python version and OS

## Architecture

See the README's "Architecture" section for an overview of the module
structure and how the solver works internally.

## License

By contributing, you agree that your contributions will be licensed under
the MIT License.