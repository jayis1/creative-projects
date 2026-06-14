# Contributing to Reaction-Diffusion Simulator

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## How to Contribute

### Reporting Issues

- Use GitHub Issues to report bugs or request features
- Include steps to reproduce, expected behavior, and actual behavior
- Include your Python version and OS

### Submitting Changes

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes with tests
4. Ensure all tests pass: `python -m pytest tests/ -v`
5. Commit with a descriptive message
6. Push and create a Pull Request

### Development Setup

```bash
# Clone the repo
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/reaction-diffusion-sim

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test class
python -m pytest tests/test_rdsim.py::TestGrayScott -v

# Run with coverage (if pytest-cov installed)
python -m pytest tests/ -v --cov=rdsim
```

### Code Style

- Follow PEP 8 with max line length of 100 characters
- Use type hints for function signatures
- Write docstrings for all public functions and classes
- Use `logging` instead of `print` for diagnostic output

### Adding a New Model

1. Define reaction kinetics function in `rdsim/models.py`
2. Define default state and perturbation functions
3. Add to the `MODELS` dictionary
4. Add presets in `rdsim/presets.py`
5. Add tests in `tests/test_rdsim.py`
6. Update README.md with the new model

Example model structure:

```python
def my_model_react(u, v, params):
    """My model reaction kinetics."""
    param_a = params.get("a", 1.0)
    du = ...  # reaction term for u
    dv = ...  # reaction term for v
    return du, dv

def my_model_default_state(n, params=None):
    """Default initial state."""
    u = np.ones((n, n), dtype=np.float64)
    v = np.zeros((n, n), dtype=np.float64)
    return u, v

def my_model_perturbation():
    return {"type": "center_square", "size": 20, "u_val": 0.0, "v_val": 1.0}

MODELS["my-model"] = {
    "react": my_model_react,
    "defaults": {"Du": 0.1, "Dv": 0.2, "a": 1.0},
    "default_state": my_model_default_state,
    "perturbation": my_model_perturbation,
    "param_names": ["Du", "Dv", "a"],
    "description": "My custom model description",
    "stability_clamp": (0, 1),
}
```

### Adding a New Preset

1. Define the preset in the appropriate section of `rdsim/presets.py`
2. Include model, params, grid_size, dt, steps, perturbation, description
3. Add a test in `tests/test_rdsim.py`
4. Update the README table

### Pull Request Checklist

- [ ] All tests pass
- [ ] New features have corresponding tests
- [ ] Type hints added for new public APIs
- [ ] Docstrings added/updated
- [ ] README.md updated if needed
- [ ] No hardcoded secrets or credentials