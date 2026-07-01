"""
Benchmarking utilities for the nonogram solver.

Run a suite of benchmarks against preset puzzles, generated puzzles, or
custom files to measure solver performance.

Usage::

    from nonogram.benchmark import BenchmarkSuite

    suite = BenchmarkSuite()
    results = suite.run_all()
    print(results.summary())
    for r in results:
        print(r)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional

from nonogram.board import Board
from nonogram.solver import Solver
from nonogram.generator import Generator
from nonogram.presets import PRESETS, get_preset
from nonogram.analyzer import DifficultyAnalyzer

logger = logging.getLogger("nonogram.benchmark")


@dataclass
class BenchmarkResult:
    """A single benchmark measurement."""
    name: str
    grid_size: str
    solved: bool
    iterations: int
    backtracks: int
    elapsed: float
    difficulty: Optional[str] = None

    def __str__(self) -> str:
        status = "✓" if self.solved else "✗"
        diff = f" [{self.difficulty}]" if self.difficulty else ""
        return (
            f"{status} {self.name:<25} {self.grid_size:<8} "
            f"iters={self.iterations:<6} bt={self.backtracks:<6} "
            f"{self.elapsed:.4f}s{diff}"
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "grid_size": self.grid_size,
            "solved": self.solved,
            "iterations": self.iterations,
            "backtracks": self.backtracks,
            "elapsed": round(self.elapsed, 6),
            "difficulty": self.difficulty,
        }


@dataclass
class BenchmarkSuite:
    """Run and collect benchmark results.

    Parameters
    ----------
    solver : Solver, optional
        A pre-configured solver instance.
    warmup : bool
        If True, run each benchmark once to warm up caches before measuring.
    """

    solver: Solver = field(default_factory=Solver)
    warmup: bool = True
    results: List[BenchmarkResult] = field(default_factory=list)

    def benchmark_preset(self, name: str) -> BenchmarkResult:
        """Benchmark solving a preset puzzle by name."""
        # Warm up.
        if self.warmup:
            warm_board = Board(
                get_preset(name).row_clues,
                get_preset(name).col_clues,
            )
            self.solver.solve(warm_board)

        board = get_preset(name)
        # Fresh board with just clues.
        test = Board(board.row_clues, board.col_clues)
        self.solver.iterations = 0
        self.solver.backtracks = 0
        start = time.perf_counter()
        result = self.solver.solve(test)
        elapsed = time.perf_counter() - start

        # Get difficulty.
        analyzer = DifficultyAnalyzer()
        try:
            diff = analyzer.grade(Board(board.row_clues, board.col_clues))
        except Exception:
            diff = None

        return BenchmarkResult(
            name=f"preset:{name}",
            grid_size=f"{board.width}×{board.height}",
            solved=result.solved,
            iterations=result.iterations,
            backtracks=result.backtracks,
            elapsed=elapsed,
            difficulty=diff,
        )

    def benchmark_generated(
        self, width: int, height: int, seed: Optional[int] = None,
        density: float = 0.55,
    ) -> BenchmarkResult:
        """Benchmark solving a generated puzzle."""
        gen = Generator(seed=seed)
        board = gen.generate(width, height, density=density, unique=True)
        test = Board(board.row_clues, board.col_clues)
        self.solver.iterations = 0
        self.solver.backtracks = 0
        start = time.perf_counter()
        result = self.solver.solve(test)
        elapsed = time.perf_counter() - start
        return BenchmarkResult(
            name=f"generated:{width}x{height}(seed={seed})",
            grid_size=f"{width}×{height}",
            solved=result.solved,
            iterations=result.iterations,
            backtracks=result.backtracks,
            elapsed=elapsed,
        )

    def run_all(self) -> List[BenchmarkResult]:
        """Run all preset benchmarks and a few generated ones."""
        self.results.clear()
        # All presets.
        for name, _, _, _, _ in PRESETS:
            logger.info("Benchmarking preset: %s", name)
            try:
                r = self.benchmark_preset(name)
                self.results.append(r)
            except Exception as e:
                logger.error("Failed to benchmark %s: %s", name, e)
                self.results.append(BenchmarkResult(
                    name=f"preset:{name}", grid_size="?",
                    solved=False, iterations=0, backtracks=0,
                    elapsed=0.0,
                ))
        # A couple generated benchmarks.
        for size in (5, 10, 15):
            for seed in (42, 100):
                logger.info("Benchmarking generated %dx%d seed=%d", size, size, seed)
                try:
                    r = self.benchmark_generated(size, size, seed=seed)
                    self.results.append(r)
                except Exception as e:
                    logger.error("Failed: %s", e)
        return self.results

    def summary(self) -> str:
        """Print a summary table of all results."""
        if not self.results:
            return "No benchmark results. Call run_all() first."
        lines = ["Nonogram Solver Benchmarks", "=" * 70]
        for r in self.results:
            lines.append(str(r))
        solved = sum(1 for r in self.results if r.solved)
        total_time = sum(r.elapsed for r in self.results)
        lines.append("-" * 70)
        lines.append(f"Solved: {solved}/{len(self.results)}  "
                     f"Total time: {total_time:.4f}s")
        return "\n".join(lines)

    def to_json(self) -> str:
        """Serialise results to JSON."""
        import json
        return json.dumps(
            [r.to_dict() for r in self.results], indent=2
        )