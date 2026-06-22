# Contributing to autograd-engine

Thank you for your interest in contributing! This project is part of the
`creative-projects` monorepo and welcomes improvements of all kinds.

## Getting Started

1. **Clone the repo:**
   ```bash
   git clone https://github.com/jayis1/creative-projects.git
   cd creative-projects/autograd-engine
   ```

2. **Set up a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

3. **Run the tests:**
   ```bash
   python -m pytest tests/ -v
   python test_enhanced.py
   ```

## Code Style

- Use **type hints** on all public functions and methods.
- Add **docstrings** to all public classes and functions (Google or
  NumPy style — be consistent within a file).
- Keep the **zero-dependency** constraint for the core package. Optional
  features (YAML config, graphviz rendering) may use optional dependencies
  guarded by try/except imports.
- Aim for **pure Python standard library** only in `autograd_engine/`.

## Adding a New Activation Function

1. Add the function to `autograd_engine/activations.py` — it should take a
   `Value` and return a `Value`, with a proper `_backward` closure.
2. Register it in `ACTIVATION_REGISTRY`.
3. Add a test in `tests/test_activations.py` that checks both forward and
   backward passes (use `numerical_grad_check`).
4. Update the README's activation table.

## Adding a New Optimizer

1. Subclass `Optimizer` in `autograd_engine/train.py`.
2. Implement `step()`.
3. Add tests in `tests/test_train.py` that verify convergence on XOR.
4. Add to the config system in `autograd_engine/config.py` if it should be
   selectable from config files.

## Running Tests

```bash
# All tests
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=autograd_engine --cov-report=term-missing

# Run a specific test file
python -m pytest tests/test_engine.py -v

# Run the CLI commands as smoke tests
python -m autograd_engine.cli info
python -m autograd_engine.cli demo
python -m autograd_engine.cli grad-check
```

## Pull Request Checklist

- [ ] All tests pass (`pytest tests/ -v`)
- [ ] New features have tests
- [ ] Type hints added to new code
- [ ] Docstrings added/updated
- [ ] README updated if needed
- [ ] No new runtime dependencies (or clearly marked as optional)