"""Benchmarking utilities for comparing TSP algorithms."""

from __future__ import annotations

import time
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable

from .instance import TSPInstance
from .tour import Tour
from .solver import solve, list_algorithms


@dataclass
class BenchmarkResult:
    """Result of a single algorithm run."""
    algorithm: str
    length: float
    time_s: float
    optimal_length: Optional[float] = None
    refine: Optional[str] = None
    seed: Optional[int] = None

    @property
    def ratio(self) -> Optional[float]:
        """Ratio of this tour's length to the optimal (1.0 = optimal)."""
        if self.optimal_length and self.optimal_length > 0:
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
            "length": round(self.length, 4),
            "time_s": round(self.time_s, 6),
            "ratio": round(self.ratio, 4) if self.ratio is not None else None,
            "gap_pct": round(self.gap_pct, 4) if self.gap_pct is not None else None,
            "refine": self.refine,
            "seed": self.seed,
        }


@dataclass
class BenchmarkSuite:
    """Run multiple algorithms on one or more instances and collect results."""
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
        """
        if algorithms is None:
            algorithms = list_algorithms()

        # Compute optimal if feasible
        optimal_length: Optional[float] = None
        if not skip_optimal_if_large or instance.n <= 20:
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
                    )
                    self.results.append(result)
                except Exception as exc:
                    # Record error as a result with inf length
                    self.results.append(BenchmarkResult(
                        algorithm=algo,
                        length=float("inf"),
                        time_s=0.0,
                        optimal_length=optimal_length,
                        refine=refine,
                        seed=seed,
                    ))
        return self.results

    def summary(self) -> str:
        """Return a formatted table summary of all results."""
        lines = []
        header = f"{'Algorithm':<25} {'Length':>12} {'Ratio':>8} {'Gap%':>8} {'Time(s)':>10}"
        lines.append(header)
        lines.append("-" * len(header))
        # Group by algorithm, average over repetitions
        by_algo: Dict[str, List[BenchmarkResult]] = {}
        for r in self.results:
            by_algo.setdefault(r.algorithm, []).append(r)
        for algo in sorted(by_algo.keys()):
            runs = by_algo[algo]
            avg_len = statistics.mean(r.length for r in runs)
            avg_time = statistics.mean(r.time_s for r in runs)
            ratio = runs[0].ratio
            gap = runs[0].gap_pct
            ratio_str = f"{ratio:.4f}" if ratio is not None else "N/A"
            gap_str = f"{gap:.2f}%" if gap is not None else "N/A"
            lines.append(f"{algo:<25} {avg_len:>12.2f} {ratio_str:>8} {gap_str:>8} {avg_time:>10.4f}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {"results": [r.to_dict() for r in self.results]}

    def best(self) -> Optional[BenchmarkResult]:
        """Return the result with the shortest tour."""
        if not self.results:
            return None
        return min(self.results, key=lambda r: r.length)

    def fastest(self) -> Optional[BenchmarkResult]:
        """Return the result with the shortest runtime."""
        if not self.results:
            return None
        return min(self.results, key=lambda r: r.time_s)