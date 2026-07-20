"""Benchmarking utilities for comparing TSP algorithms.

Provides :class:`BenchmarkResult` and :class:`BenchmarkSuite` for running
multiple algorithms on one or more instances, computing quality ratios against
an optimal baseline, and exporting results as formatted text, JSON, or CSV.
"""

from __future__ import annotations

import csv
import io
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union

from .instance import TSPInstance, generate_instance
from .logging_util import get_logger
from .tour import Tour
from .solver import solve, list_algorithms

_log = get_logger(__name__)


@dataclass
class BenchmarkResult:
    """Result of a single algorithm run.

    Attributes
    ----------
    algorithm : str
        Algorithm name.
    length : float
        Tour length (``inf`` if the algorithm errored).
    time_s : float
        Wall-clock time in seconds.
    optimal_length : Optional[float]
        Optimal tour length (if known), used to compute ratio and gap.
    refine : Optional[str]
        Refinement method applied.
    seed : Optional[int]
        RNG seed used.
    n : Optional[int]
        Number of cities in the instance.
    instance_name : Optional[str]
        Name of the instance.
    error : Optional[str]
        Error message if the algorithm failed.
    """

    algorithm: str
    length: float
    time_s: float
    optimal_length: Optional[float] = None
    refine: Optional[str] = None
    seed: Optional[int] = None
    n: Optional[int] = None
    instance_name: Optional[str] = None
    error: Optional[str] = None

    @property
    def ratio(self) -> Optional[float]:
        """Ratio of this tour's length to the optimal (1.0 = optimal)."""
        if self.optimal_length and self.optimal_length > 0 and self.length != float("inf"):
            return self.length / self.optimal_length
        return None

    @property
    def gap_pct(self) -> Optional[float]:
        """Optimality gap in percent (0% = optimal)."""
        r = self.ratio
        if r is not None:
            return (r - 1.0) * 100.0
        return None

    def to_dict(self) -> dict:
        return {
            "algorithm": self.algorithm,
            "length": round(self.length, 4) if self.length != float("inf") else None,
            "time_s": round(self.time_s, 6),
            "ratio": round(self.ratio, 4) if self.ratio is not None else None,
            "gap_pct": round(self.gap_pct, 4) if self.gap_pct is not None else None,
            "refine": self.refine,
            "seed": self.seed,
            "n": self.n,
            "instance_name": self.instance_name,
            "error": self.error,
        }


@dataclass
class BenchmarkSuite:
    """Run multiple algorithms on one or more instances and collect results.

    Example
    -------
    >>> suite = BenchmarkSuite()
    >>> inst = generate_instance(15, seed=42)
    >>> suite.run(inst, seed=42)
    >>> print(suite.summary())
    >>> suite.to_csv("results.csv")
    """

    results: List[BenchmarkResult] = field(default_factory=list)

    def run(
        self,
        instance: TSPInstance,
        algorithms: Optional[List[str]] = None,
        *,
        refine: Optional[str] = None,
        seed: Optional[int] = None,
        repetitions: int = 1,
        optimal_algorithm: str = "held_karp",
        skip_optimal_if_large: bool = True,
        optimal_length: Optional[float] = None,
    ) -> List[BenchmarkResult]:
        """Run algorithms on *instance* and append results.

        Parameters
        ----------
        instance : TSPInstance
        algorithms : list of str, optional
            Algorithm names to run. Defaults to all available.
        refine : str, optional
            Local search refinement to apply after each algorithm.
        seed : int, optional
            RNG seed for stochastic algorithms.
        repetitions : int
            Number of times to run each algorithm (for averaging).
        optimal_algorithm : str
            Algorithm to use as the optimal baseline (default: held_karp).
        skip_optimal_if_large : bool
            If True, skip the optimal computation for n > 20.
        optimal_length : float, optional
            If provided, use this as the optimal length instead of computing it.
        """
        if algorithms is None:
            algorithms = list_algorithms()

        # Compute optimal if not given
        if optimal_length is None and (not skip_optimal_if_large or instance.n <= 20):
            try:
                opt_tour = solve(instance, optimal_algorithm, seed=seed)
                optimal_length = opt_tour.length
            except (ValueError, Exception):
                pass  # Skip if infeasible

        for algo in algorithms:
            for rep in range(repetitions):
                try:
                    t0 = time.perf_counter()
                    tour = solve(instance, algo, refine=refine, seed=seed)
                    elapsed = time.perf_counter() - t0
                    result = BenchmarkResult(
                        algorithm=algo,
                        length=tour.length,
                        time_s=elapsed,
                        optimal_length=optimal_length,
                        refine=refine,
                        seed=seed,
                        n=instance.n,
                        instance_name=instance.name,
                    )
                    self.results.append(result)
                except Exception as exc:  # noqa: BLE001
                    _log.debug("Algorithm %s failed: %s", algo, exc)
                    self.results.append(BenchmarkResult(
                        algorithm=algo,
                        length=float("inf"),
                        time_s=0.0,
                        optimal_length=optimal_length,
                        refine=refine,
                        seed=seed,
                        n=instance.n,
                        instance_name=instance.name,
                        error=str(exc),
                    ))
        return self.results

    def run_instances(
        self,
        instances: Sequence[TSPInstance],
        algorithms: Optional[List[str]] = None,
        **kwargs,
    ) -> List[BenchmarkResult]:
        """Run the benchmark over multiple instances."""
        for inst in instances:
            self.run(inst, algorithms, **kwargs)
        return self.results

    def summary(self) -> str:
        """Return a formatted table summary of all results."""
        lines = []
        header = f"{'Algorithm':<28} {'Length':>12} {'Ratio':>8} {'Gap%':>8} {'Time(s)':>10}"
        lines.append(header)
        lines.append("-" * len(header))
        # Group by algorithm, average over repetitions
        by_algo: Dict[str, List[BenchmarkResult]] = {}
        for r in self.results:
            by_algo.setdefault(r.algorithm, []).append(r)
        for algo in sorted(by_algo.keys()):
            runs = by_algo[algo]
            avg_len = statistics.mean(r.length for r in runs if r.length != float("inf"))
            avg_time = statistics.mean(r.time_s for r in runs)
            ratio = runs[0].ratio
            gap = runs[0].gap_pct
            ratio_str = f"{ratio:.4f}" if ratio is not None else "N/A"
            gap_str = f"{gap:.2f}%" if gap is not None else "N/A"
            if runs[0].error:
                lines.append(f"{algo:<28} {'ERROR':>12} {'':>8} {'':>8} {avg_time:>10.4f}")
            else:
                lines.append(f"{algo:<28} {avg_len:>12.2f} {ratio_str:>8} {gap_str:>8} {avg_time:>10.4f}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {"results": [r.to_dict() for r in self.results]}

    def to_json(self, path: Optional[Union[str, Path]] = None) -> str:
        """Serialize results to JSON.  If *path* is given, also write to file."""
        import json
        data = json.dumps(self.to_dict(), indent=2)
        if path:
            Path(path).write_text(data)
        return data

    def to_csv(self, path: Optional[Union[str, Path]] = None) -> str:
        """Serialize results to CSV.  If *path* is given, also write to file."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "algorithm", "length", "time_s", "ratio", "gap_pct",
            "refine", "seed", "n", "instance_name", "error",
        ])
        for r in self.results:
            writer.writerow([
                r.algorithm,
                r.length if r.length != float("inf") else "",
                round(r.time_s, 6),
                round(r.ratio, 4) if r.ratio is not None else "",
                round(r.gap_pct, 4) if r.gap_pct is not None else "",
                r.refine or "",
                r.seed if r.seed is not None else "",
                r.n if r.n is not None else "",
                r.instance_name or "",
                r.error or "",
            ])
        data = output.getvalue()
        if path:
            Path(path).write_text(data)
        return data

    def best(self) -> Optional[BenchmarkResult]:
        """Return the result with the shortest tour (excluding errors)."""
        valid = [r for r in self.results if r.length != float("inf")]
        if not valid:
            return None
        return min(valid, key=lambda r: r.length)

    def fastest(self) -> Optional[BenchmarkResult]:
        """Return the result with the shortest runtime."""
        if not self.results:
            return None
        return min(self.results, key=lambda r: r.time_s)

    def clear(self) -> None:
        """Clear all results."""
        self.results.clear()