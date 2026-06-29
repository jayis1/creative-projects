"""Result objects and experiment utilities for EvOpt.

Provides:
    - :class:`Result`: A rich result object wrapping an algorithm run with
      statistics, history, best solution, and export helpers.
    - :class:`Experiment`: Run multiple algorithm × problem combinations and
      aggregate results for comparison.
    - :func:`parameter_sweep`: Grid-search over algorithm parameters.

Example::

    from evopt import GeneticAlgorithm, Sphere
    from evopt.results import Result, Experiment

    ga = GeneticAlgorithm(Sphere(dims=3), population_size=50, max_generations=100, seed=42)
    ga.run()
    result = Result.from_algorithm(ga)
    print(result.summary())
    result.to_json("ga_sphere.json")
"""

from __future__ import annotations

import json
import time
import csv
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Sequence

from .core import Individual


@dataclass
class Result:
    """Encapsulates the outcome of a single optimization run.

    Attributes:
        algorithm_name: Name of the algorithm used.
        problem_name: Name of the problem solved.
        best_fitness: Best fitness value found.
        best_genome: Best genome (solution) found.
        time_seconds: Wall-clock time of the run.
        generations: Number of generations executed.
        seed: Random seed used.
        history: Per-generation statistics list.
        statistics_summary: Summary statistics dict.
        termination_reason: Why the algorithm stopped.
        metadata: Extra key-value pairs.
    """

    algorithm_name: str = ""
    problem_name: str = ""
    best_fitness: Optional[float] = None
    best_genome: Optional[List[Any]] = None
    time_seconds: float = 0.0
    generations: int = 0
    seed: Optional[int] = None
    history: List[Dict[str, Any]] = field(default_factory=list)
    statistics_summary: Dict[str, Any] = field(default_factory=dict)
    termination_reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_algorithm(cls, algorithm, problem_name: str = "",
                       algorithm_name: str = "", time_seconds: Optional[float] = None,
                       extra_metadata: Optional[Dict[str, Any]] = None) -> "Result":
        """Build a Result from a completed algorithm instance.

        Args:
            algorithm: A BaseAlgorithm instance (after ``run()`` was called).
            problem_name: Name of the problem (for labeling).
            algorithm_name: Name of the algorithm (for labeling).
            time_seconds: Optional elapsed time. If None, uses 0.0.
            extra_metadata: Additional metadata to merge in.
        """
        best = algorithm.best_individual
        best_fitness = best.fitness if best else None
        best_genome = list(best.genome) if best else None

        return cls(
            algorithm_name=algorithm_name or algorithm.__class__.__name__,
            problem_name=problem_name,
            best_fitness=best_fitness,
            best_genome=best_genome,
            time_seconds=time_seconds or 0.0,
            generations=algorithm.generation,
            seed=algorithm.seed,
            history=list(algorithm.history),
            statistics_summary=dict(algorithm.statistics.summary()),
            termination_reason=algorithm.termination_reason,
            metadata=dict(extra_metadata or {}),
        )

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def summary(self) -> str:
        """Return a human-readable one-line summary string."""
        fit_str = f"{self.best_fitness:.6g}" if self.best_fitness is not None else "N/A"
        return (
            f"{self.algorithm_name} on {self.problem_name}: "
            f"fitness={fit_str}, gens={self.generations}, "
            f"time={self.time_seconds:.3f}s, seed={self.seed}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict (JSON-compatible)."""
        d = asdict(self)
        # Round floats in history for compactness
        return d

    def to_json(self, path: Union[str, Path], indent: int = 2) -> None:
        """Save the result as a JSON file.

        Args:
            path: Output file path.
            indent: JSON indentation (default 2).
        """
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=indent, default=str),
                     encoding="utf-8")

    def to_csv(self, path: Union[str, Path]) -> None:
        """Save the per-generation history as a CSV file.

        Args:
            path: Output file path.
        """
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if not self.history:
            p.write_text("", encoding="utf-8")
            return
        keys = list(self.history[0].keys())
        with open(p, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for row in self.history:
                writer.writerow(row)

    def __repr__(self) -> str:
        return f"Result({self.summary()})"


# ---------------------------------------------------------------------------
# Experiment: run multiple configurations
# ---------------------------------------------------------------------------

@dataclass
class Experiment:
    """Run and aggregate multiple optimization runs.

    Example::

        exp = Experiment(name="my_benchmark")
        exp.add("ga", "sphere", {"population_size": 50, "max_generations": 100}, seed=42)
        exp.add("de", "sphere", {"population_size": 50, "max_generations": 100}, seed=42)
        results = exp.run(repeats=5)
        exp.report()
        exp.save_results("results/")
    """

    name: str = "experiment"
    configs: List[Dict[str, Any]] = field(default_factory=list)
    results: List[Result] = field(default_factory=list)

    def add(self, algorithm: str, problem: str, params: Optional[Dict[str, Any]] = None,
            seed: Optional[int] = None, label: str = "") -> None:
        """Add a configuration to the experiment.

        Args:
            algorithm: Algorithm name (e.g., "ga", "de", "pso").
            problem: Problem name (e.g., "sphere", "rastrigin").
            params: Algorithm parameters.
            seed: Random seed (None = random).
            label: Optional human-readable label for this config.
        """
        self.configs.append({
            "algorithm": algorithm,
            "problem": problem,
            "params": params or {},
            "seed": seed,
            "label": label or f"{algorithm}_{problem}",
        })

    def run(self, repeats: int = 1, verbose: bool = False) -> List[Result]:
        """Execute all configurations, optionally with multiple repeats.

        Args:
            repeats: Number of independent runs per configuration (with different seeds).
            verbose: Print progress.

        Returns:
            List of :class:`Result` objects.
        """
        from .config import _ensure_registries
        _ensure_registries()
        from .config import _ALGORITHM_REGISTRY, _PROBLEM_REGISTRY

        self.results = []
        for cfg in self.configs:
            alg_name = cfg["algorithm"].lower()
            prob_name = cfg["problem"].lower()
            params = dict(cfg["params"])
            base_seed = cfg["seed"]

            if alg_name not in _ALGORITHM_REGISTRY:
                raise ValueError(f"Unknown algorithm: {alg_name}")
            if prob_name not in _PROBLEM_REGISTRY:
                raise ValueError(f"Unknown problem: {prob_name}")

            alg_cls = _ALGORITHM_REGISTRY[alg_name]
            prob_cls = _PROBLEM_REGISTRY[prob_name]

            for r in range(repeats):
                seed = base_seed if base_seed is not None else None
                if repeats > 1 and base_seed is not None:
                    seed = base_seed + r  # deterministic per-run seeds

                # Build problem fresh each time
                problem = self._build_problem(prob_cls, params)
                # Build algorithm
                alg_params = {k: v for k, v in params.items()
                              if k not in ("dims", "cities", "items", "seed")}
                alg_params["seed"] = seed
                alg_params["verbose"] = verbose
                try:
                    algo = alg_cls(problem, **alg_params)
                except TypeError as e:
                    if verbose:
                        print(f"  Skipping {alg_name}/{prob_name}: {e}")
                    continue

                t0 = time.time()
                algo.run()
                elapsed = time.time() - t0
                result = Result.from_algorithm(
                    algo, problem_name=prob_name, algorithm_name=alg_name,
                    time_seconds=elapsed,
                    extra_metadata={"label": cfg["label"], "repeat": r},
                )
                self.results.append(result)
                if verbose:
                    print(f"  {result.summary()}")
        return self.results

    def _build_problem(self, prob_cls, params: Dict[str, Any]):
        """Build a problem instance, extracting problem-specific params."""
        # Extract problem-specific params
        prob_params = {}
        if "dims" in params:
            prob_params["dims"] = params["dims"]
        elif "cities" in params:
            return prob_cls.random_cities(n=params["cities"], seed=params.get("seed", 42))
        elif "items" in params:
            instance, _ = prob_cls.random_items(n=params["items"], seed=params.get("seed", 42))
            return instance
        return prob_cls(**prob_params) if prob_params else prob_cls()

    def report(self) -> str:
        """Print and return a summary table of all results."""
        if not self.results:
            return "(no results)"
        lines = [f"Experiment: {self.name}", "=" * 70]
        # Group by algorithm+problem
        from collections import defaultdict
        groups = defaultdict(list)
        for r in self.results:
            key = (r.algorithm_name, r.problem_name)
            groups[key].append(r)
        lines.append(f"{'Algorithm':<12} {'Problem':<12} {'Best':>14} {'Mean':>14} {'Std':>10} {'Time(s)':>8}")
        lines.append("-" * 70)
        for (alg, prob), rs in sorted(groups.items()):
            fits = [r.best_fitness for r in rs if r.best_fitness is not None]
            times = [r.time_seconds for r in rs]
            if fits:
                best = min(fits)
                mean = sum(fits) / len(fits)
                std = (sum((f - mean) ** 2 for f in fits) / max(len(fits) - 1, 1)) ** 0.5
                avg_time = sum(times) / len(times)
                lines.append(f"{alg:<12} {prob:<12} {best:>14.6g} {mean:>14.6g} {std:>10.4g} {avg_time:>8.3f}")
        table = "\n".join(lines)
        print(table)
        return table

    def save_results(self, directory: Union[str, Path]) -> None:
        """Save all results as individual JSON files in the given directory.

        Args:
            directory: Output directory (created if needed).
        """
        d = Path(directory)
        d.mkdir(parents=True, exist_ok=True)
        for i, r in enumerate(self.results):
            filename = f"{r.algorithm_name}_{r.problem_name}_{i:03d}.json"
            r.to_json(d / filename)
        # Also save a combined summary
        summary_path = d / "summary.json"
        summary = {
            "name": self.name,
            "num_configs": len(self.configs),
            "num_results": len(self.results),
            "results": [r.to_dict() for r in self.results],
        }
        summary_path.write_text(json.dumps(summary, indent=2, default=str),
                                encoding="utf-8")


# ---------------------------------------------------------------------------
# Parameter sweep
# ---------------------------------------------------------------------------

def parameter_sweep(algorithm: str, problem: str,
                    param_grid: Dict[str, List[Any]],
                    fixed_params: Optional[Dict[str, Any]] = None,
                    repeats: int = 3, seed: int = 42,
                    verbose: bool = False) -> Experiment:
    """Run a grid search over algorithm parameters.

    Args:
        algorithm: Algorithm name.
        problem: Problem name.
        param_grid: Dict mapping parameter name -> list of values to try.
        fixed_params: Parameters held constant across all runs.
        repeats: Independent runs per parameter combination.
        seed: Base random seed.
        verbose: Print progress.

    Returns:
        An :class:`Experiment` with all results.

    Example::

        from evopt.results import parameter_sweep
        exp = parameter_sweep(
            "ga", "rastrigin",
            param_grid={"mutation_rate": [0.01, 0.05, 0.1, 0.2],
                         "crossover_rate": [0.7, 0.85, 0.95]},
            fixed_params={"dims": 5, "population_size": 50, "max_generations": 100},
            repeats=3,
        )
        exp.report()
    """
    import itertools

    fixed_params = fixed_params or {}
    keys = list(param_grid.keys())
    value_lists = [param_grid[k] for k in keys]

    exp = Experiment(name=f"sweep_{algorithm}_{problem}")
    for combo in itertools.product(*value_lists):
        params = dict(fixed_params)
        params.update(dict(zip(keys, combo)))
        label = "_".join(f"{k}={v}" for k, v in zip(keys, combo))
        exp.add(algorithm, problem, params=params, seed=seed, label=label)

    exp.run(repeats=repeats, verbose=verbose)
    return exp