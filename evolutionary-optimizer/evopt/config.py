"""Configuration management for EvOpt.

Supports loading algorithm and problem configurations from YAML or JSON files,
making experiments reproducible and parameter sweeps easy.

Example YAML config::

    algorithm:
      name: ga
      params:
        population_size: 100
        max_generations: 200
        crossover_rate: 0.9
        mutation_rate: 0.05
        elite_size: 2
    problem:
      name: rastrigin
      params:
        dims: 5
    seed: 42
    verbose: false
    callbacks:
      - type: stagnation
        params: {patience: 30}
      - type: adaptive_mutation_rate
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

try:
    import yaml  # type: ignore
    _HAS_YAML = True
except ImportError:  # pragma: no cover
    _HAS_YAML = False


class ConfigError(Exception):
    """Raised when a configuration file is invalid or cannot be loaded."""


# ---------------------------------------------------------------------------
# Registry of known algorithms and problems (kept in sync with cli.py)
# ---------------------------------------------------------------------------

# Lazy import-safe registry: names -> factory callables
_ALGORITHM_REGISTRY: Dict[str, Any] = {}
_PROBLEM_REGISTRY: Dict[str, Any] = {}
_CALLBACK_REGISTRY: Dict[str, Any] = {}


def _ensure_registries():
    """Populate registries on first use (avoids circular imports)."""
    if _ALGORITHM_REGISTRY:
        return
    from .algorithms.ga import GeneticAlgorithm
    from .algorithms.es import EvolutionStrategy
    from .algorithms.de import DifferentialEvolution
    from .algorithms.pso import ParticleSwarmOptimizer
    from .algorithms.nsga2 import NSGA2
    from .algorithms.island_model import IslandModelGA
    from .algorithms.memetic import MemeticAlgorithm
    from .algorithms.cmaes import CMAES
    from .algorithms.simulated_annealing import SimulatedAnnealing

    _ALGORITHM_REGISTRY.update({
        "ga": GeneticAlgorithm,
        "es": EvolutionStrategy,
        "de": DifferentialEvolution,
        "pso": ParticleSwarmOptimizer,
        "nsga2": NSGA2,
        "island": IslandModelGA,
        "memetic": MemeticAlgorithm,
        "cmaes": CMAES,
        "sa": SimulatedAnnealing,
    })

    from .problems.sphere import Sphere
    from .problems.rastrigin import Rastrigin
    from .problems.rosenbrock import Rosenbrock
    from .problems.benchmarks import Ackley, Griewank, Schwefel, Michalewicz, Zakharov
    from .problems.tsp import TSP
    from .problems.knapsack import Knapsack
    from .problems.multi_objective import ZDT1, ZDT2

    _PROBLEM_REGISTRY.update({
        "sphere": Sphere,
        "rastrigin": Rastrigin,
        "rosenbrock": Rosenbrock,
        "ackley": Ackley,
        "griewank": Griewank,
        "schwefel": Schwefel,
        "michalewicz": Michalewicz,
        "zakharov": Zakharov,
        "tsp": TSP,
        "knapsack": Knapsack,
        "zdt1": ZDT1,
        "zdt2": ZDT2,
    })

    from .utils.callbacks import (
        MaxGenerations, FitnessThreshold, Stagnation,
        TimeLimit, Convergence, AdaptiveMutationRate, AdaptiveInertia,
    )

    _CALLBACK_REGISTRY.update({
        "max_generations": MaxGenerations,
        "fitness_threshold": FitnessThreshold,
        "stagnation": Stagnation,
        "time_limit": TimeLimit,
        "convergence": Convergence,
        "adaptive_mutation_rate": AdaptiveMutationRate,
        "adaptive_inertia": AdaptiveInertia,
    })


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_config(path: Union[str, Path]) -> Dict[str, Any]:
    """Load a configuration dict from a YAML or JSON file.

    The file extension determines the parser:
        *.yaml, *.yml -> YAML
        *.json       -> JSON

    Args:
        path: Path to the config file.

    Returns:
        Parsed configuration dictionary.

    Raises:
        ConfigError: If the file cannot be read or parsed.
        FileNotFoundError: If the file does not exist.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {p}")

    suffix = p.suffix.lower()
    text = p.read_text(encoding="utf-8")

    if suffix in (".yaml", ".yml"):
        if not _HAS_YAML:
            raise ConfigError(
                "PyYAML is required to load YAML config files. "
                "Install with: pip install pyyaml"
            )
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise ConfigError(f"YAML parse error in {p}: {exc}") from exc
    elif suffix == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"JSON parse error in {p}: {exc}") from exc
    else:
        raise ConfigError(
            f"Unsupported config format: '{suffix}'. Use .yaml, .yml, or .json"
        )

    if not isinstance(data, dict):
        raise ConfigError(f"Config file must contain a mapping at the top level, got {type(data).__name__}")
    return data


def save_config(config: Dict[str, Any], path: Union[str, Path]) -> None:
    """Save a configuration dict to a YAML or JSON file.

    Args:
        config: Configuration dictionary.
        path: Output path (extension determines format).
    """
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix in (".yaml", ".yml"):
        if not _HAS_YAML:
            raise ConfigError("PyYAML is required to save YAML config files.")
        text = yaml.safe_dump(config, default_flow_style=False, sort_keys=False)
    elif suffix == ".json":
        text = json.dumps(config, indent=2, default=str)
    else:
        raise ConfigError(f"Unsupported config format: '{suffix}'")
    p.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Building from config
# ---------------------------------------------------------------------------

def build_problem(config: Dict[str, Any]):
    """Construct a problem instance from a config dict.

    Expected structure::

        problem:
          name: rastrigin
          params: {dims: 5}
    """
    _ensure_registries()
    if "problem" not in config:
        raise ConfigError("Config missing 'problem' section")
    prob_cfg = config["problem"]
    name = prob_cfg.get("name")
    if not name:
        raise ConfigError("Problem config missing 'name'")
    name = name.lower()
    if name not in _PROBLEM_REGISTRY:
        raise ConfigError(f"Unknown problem '{name}'. Available: {sorted(_PROBLEM_REGISTRY)}")
    params = prob_cfg.get("params", {})
    cls = _PROBLEM_REGISTRY[name]
    try:
        return cls(**params)
    except TypeError as exc:
        raise ConfigError(f"Invalid params for problem '{name}': {exc}") from exc


def build_callbacks(callback_configs):
    """Build a list of callback instances from config."""
    _ensure_registries()
    callbacks = []
    for cb_cfg in callback_configs or []:
        cb_type = cb_cfg.get("type", "").lower()
        if cb_type not in _CALLBACK_REGISTRY:
            raise ConfigError(f"Unknown callback type '{cb_type}'. Available: {sorted(_CALLBACK_REGISTRY)}")
        params = cb_cfg.get("params", {})
        callbacks.append(_CALLBACK_REGISTRY[cb_type](**params))
    return callbacks


def build_algorithm(config: Dict[str, Any], problem=None, callbacks=None):
    """Construct an algorithm instance from a config dict.

    Expected structure::

        algorithm:
          name: ga
          params: {population_size: 100, max_generations: 200}
        problem:
          name: sphere
          params: {dims: 3}
        seed: 42
        callbacks: [...]

    Args:
        config: Configuration dict.
        problem: Optional pre-built problem (overrides config's problem section).
        callbacks: Optional pre-built callbacks list (overrides config's callbacks).
    """
    _ensure_registries()
    if "algorithm" not in config:
        raise ConfigError("Config missing 'algorithm' section")
    alg_cfg = config["algorithm"]
    name = alg_cfg.get("name")
    if not name:
        raise ConfigError("Algorithm config missing 'name'")
    name = name.lower()
    if name not in _ALGORITHM_REGISTRY:
        raise ConfigError(f"Unknown algorithm '{name}'. Available: {sorted(_ALGORITHM_REGISTRY)}")
    params = dict(alg_cfg.get("params", {}))

    # Seed and verbose can be top-level or inside algorithm params
    if "seed" in config and "seed" not in params:
        params["seed"] = config["seed"]
    if "verbose" in config and "verbose" not in params:
        params["verbose"] = config["verbose"]

    # Build problem if not provided
    if problem is None:
        problem = build_problem(config)

    # Build callbacks if not provided
    if callbacks is None:
        callbacks = build_callbacks(config.get("callbacks"))

    params["callbacks"] = callbacks
    cls = _ALGORITHM_REGISTRY[name]
    try:
        return cls(problem, **params)
    except TypeError as exc:
        raise ConfigError(f"Invalid params for algorithm '{name}': {exc}") from exc


def build_from_config(config: Dict[str, Any]):
    """Build problem + algorithm from a config dict. Returns (problem, algorithm)."""
    problem = build_problem(config)
    algorithm = build_algorithm(config, problem=problem)
    return problem, algorithm


# ---------------------------------------------------------------------------
# Convenience: create template configs
# ---------------------------------------------------------------------------

# Known problem-specific parameter names (not algorithm constructor args)
_PROBLEM_PARAMS = {"dims", "cities", "items", "m", "bounds"}


def default_config(algorithm: str = "ga", problem: str = "sphere", **overrides) -> Dict[str, Any]:
    """Return a default config dict for the given algorithm/problem, with overrides.

    Overrides that are problem-specific (``dims``, ``cities``, ``items``, ``bounds``,
    ``m``) are routed to the problem params; ``seed`` and ``verbose`` are top-level;
    everything else goes to the algorithm params.
    """
    cfg = {
        "algorithm": {"name": algorithm, "params": {}},
        "problem": {"name": problem, "params": {}},
        "seed": 42,
        "verbose": False,
    }
    for k, v in overrides.items():
        if k in ("seed", "verbose"):
            cfg[k] = v
        elif k == "callbacks":
            cfg["callbacks"] = v
        elif k in _PROBLEM_PARAMS:
            cfg["problem"]["params"][k] = v
        else:
            cfg["algorithm"]["params"][k] = v
    return cfg