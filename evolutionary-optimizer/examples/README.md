# EvOpt Examples

This directory contains usage examples demonstrating EvOpt's features.

## Files

- [`01_basic_usage.py`](01_basic_usage.py) — Solve benchmark problems with different algorithms
- [`02_multi_objective.py`](02_multi_objective.py) — NSGA-II with hypervolume/IGD indicators
- [`03_config_files.py`](03_config_files.py) — Run experiments from YAML/JSON config files
- [`04_batch_experiments.py`](04_batch_experiments.py) — Compare algorithms and parameter sweeps
- [`05_custom_problem.py`](05_custom_problem.py) — Define your own optimization problem
- [`06_cmaes_advanced.py`](06_cmaes_advanced.py) — CMA-ES on ill-conditioned problems
- [`07_simulated_annealing.py`](07_simulated_annealing.py) — SA with custom cooling schedules

## Running

```bash
cd evolutionary-optimizer
pip install -e ".[dev]"   # or: pip install -e . pytest numpy pyyaml
python examples/01_basic_usage.py
```