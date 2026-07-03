# Contributing to rl-solver

Thank you for your interest in contributing to rl-solver! This document
provides guidelines and instructions for contributing.

## Development Setup

```bash
git clone https://github.com/jayis1/creative-projects
cd creative-projects/rl-solver
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install pytest
```

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run the smoke test
python smoke_test.py

# Run a specific test class
python -m pytest tests/test_comprehensive.py::TestPlanners -v
```

## Code Style

- Use type hints (`from __future__ import annotations` for forward references)
- Follow PEP 8 with 4-space indentation
- Add docstrings to all public functions and classes
- Keep functions focused; prefer small, composable units
- Use descriptive variable names

## Adding New Algorithms

1. **Planners**: Add to `advanced_planners.py` (or `planners.py` for core
   DP). Return `(V, pi, info)` tuple. Add to `__init__.py` exports and CLI.

2. **Learners**: Inherit from `_BaseLearner` (in `learners.py`) or implement
   the `run_episode`/`train`/`greedy_policy` interface. Override `_update`
   for TD-style methods. Add to `__init__.py` and CLI `learner_classes`.

3. **Environments**: Add a `make_*` factory function in `extra_environments.py`
   (or `environments.py`). Register in `EXTENDED_PRESETS`. Return an `MDP`
   instance.

4. **Tests**: Add tests in `tests/test_comprehensive.py` covering the new
   feature. Ensure all existing tests still pass.

## Pull Request Process

1. Ensure all tests pass: `python -m pytest tests/`
2. Run the smoke test: `python smoke_test.py`
3. Update the README if you've added user-facing features
4. Write clear commit messages

## Architecture

```
rl_solver/
├── mdp.py              # MDP & GridWorld core
├── planners.py         # Core DP (VI, PI, MPI, policy eval)
├── advanced_planners.py # LP, Gauss-Seidel, Prioritized Sweeping, RTDP
├── learners.py         # One-step RL (Q, SARSA, Double Q, MC)
├── nstep.py            # n-step & TD(λ) methods
├── advanced_learners.py # Dyna-Q, R-Max, Boltzmann, Gradient Q
├── environments.py     # 7 core preset MDPs
├── extra_environments.py # 5 additional environments
├── analysis.py         # Simulation & comparison tools
├── visualization.py    # ASCII visualization
├── config.py           # Config system & serialization
├── logging_utils.py    # Structured logging
├── cli.py              # argparse CLI
└── __init__.py         # Public API
```