# Contributing to Spreadsheet Engine

Thank you for your interest in contributing! This guide covers the basics.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/spreadsheet-engine

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"
pip install pyyaml

# Run tests
python3 -m pytest tests/ -v

# Run the example
python3 examples/budget.py
```

## Project Structure

```
spreadsheet-engine/
├── spreadsheet/              Main package
│   ├── __init__.py           Package exports
│   ├── cell.py              Cell model, error types, A1 helpers
│   ├── sheet.py             Sheet (2D grid of cells)
│   ├── engine.py            Core engine (recalc, deps, audit)
│   ├── parser.py            Recursive-descent formula parser
│   ├── functions.py         90+ built-in functions
│   ├── extended_functions.py Date/time, financial, info functions
│   ├── named_ranges.py      Named range manager
│   ├── config.py            YAML/JSON configuration
│   ├── optimizer.py         LRU cache, batch operations
│   ├── logging_utils.py     Structured logging
│   └── cli.py               Enhanced CLI (18 subcommands)
├── tests/                   Test suite
├── examples/                Usage examples
├── .github/workflows/       CI pipeline
├── pyproject.toml           Package metadata
├── LICENSE                  MIT license
└── README.md                Documentation
```

## How to Add a New Function

1. Define the function in `functions.py` or `extended_functions.py`:

```python
def fn_myfunc(args: List[Any]) -> float:
    _propagate_errors(args)
    nums = _num_args(args, "MYFUNC")
    if len(nums) != 1:
        raise SpreadsheetFuncError(CellError(ErrorType.VALUE, "MYFUNC needs 1 arg"))
    return nums[0] * 2
```

2. Register it in the `FUNCTIONS` dict:

```python
"MYFUNC": fn_myfunc,
```

3. Add tests in `tests/`:

```python
def test_myfunc(self):
    self.engine.set("S", "A1", "=MYFUNC(5)")
    self.engine.recalculate()
    assert self.engine.get("S", "A1") == 10.0
```

4. Run tests: `python3 -m pytest tests/ -v`

## Coding Standards

- Use type hints on all public functions
- Add docstrings to all new functions
- Handle edge cases: empty ranges, type mismatches, division by zero
- Propagate errors via `SpreadsheetFuncError` and `CellError`
- Write tests for every new feature or bug fix
- Follow existing code style (4-space indent, line length ~100)

## Testing

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/ --cov=spreadsheet --cov-report=term-missing

# Run a specific test file
python3 -m pytest tests/test_spreadsheet.py -v
```

## Pull Request Process

1. Create a feature branch from `main`
2. Write tests for your changes
3. Ensure all tests pass: `python3 -m pytest tests/ -v`
4. Update the README if you added new features
5. Commit with descriptive messages
6. Submit a PR with a clear description of changes

## Reporting Bugs

Include in your bug report:
- Python version
- Steps to reproduce
- Expected vs actual behavior
- Minimal code example