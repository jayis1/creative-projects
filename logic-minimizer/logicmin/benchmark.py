"""
Benchmark and comparison utilities.

Compare QM vs. Espresso on random or specified functions, reporting literal
cost, prime count, and timing.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .boolean import BooleanFunction
from .quine_mccluskey import MinimizationResult, QuineMcCluskey
from .espresso import Espresso
from .pos import POSMinimizer


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""

    n_vars: int
    n_minterms: int
    n_dontcare: int
    method: str
    sop: str
    n_terms: int
    n_literals: int
    elapsed_ms: float
    exact: bool

    def __repr__(self) -> str:
        return (
            f"BenchmarkResult({self.method}, vars={self.n_vars}, "
            f"terms={self.n_terms}, lits={self.n_literals}, "
            f"time={self.elapsed_ms:.1f}ms)"
        )


class Benchmark:
    """Benchmark QM and Espresso minimizers."""

    def __init__(
        self,
        n_vars: int,
        n_trials: int = 10,
        seed: Optional[int] = None,
    ) -> None:
        self.n_vars = n_vars
        self.n_trials = n_trials
        self.rng = random.Random(seed)

    def random_function(self, dc_prob: float = 0.1) -> BooleanFunction:
        """Generate a random boolean function."""
        universe = list(range(1 << self.n_vars))
        self.rng.shuffle(universe)
        n_dc = int(len(universe) * dc_prob)
        dc = set(universe[:n_dc])
        rest = universe[n_dc:]
        # roughly half the remaining are minterms
        threshold = self.rng.randint(1, max(1, len(rest) - 1))
        minterms = set(rest[:threshold])
        return BooleanFunction(
            n_vars=self.n_vars, minterms=minterms, dontcare=dc, name="bench"
        )

    def run(
        self, func: Optional[BooleanFunction] = None
    ) -> List[BenchmarkResult]:
        """Run benchmark on a given or random function."""
        if func is None:
            func = self.random_function()
        results: List[BenchmarkResult] = []
        # QM
        qm = QuineMcCluskey(self.n_vars)
        t0 = time.perf_counter()
        r_qm = qm.minimize(func)
        t1 = time.perf_counter()
        results.append(BenchmarkResult(
            n_vars=self.n_vars,
            n_minterms=len(func.minterms),
            n_dontcare=len(func.dontcare),
            method="quine-mccluskey",
            sop=r_qm.sop,
            n_terms=r_qm.n_terms,
            n_literals=r_qm.n_literals,
            elapsed_ms=(t1 - t0) * 1000,
            exact=True,
        ))
        # Espresso
        esp = Espresso(self.n_vars)
        t0 = time.perf_counter()
        r_esp = esp.minimize(func)
        t1 = time.perf_counter()
        results.append(BenchmarkResult(
            n_vars=self.n_vars,
            n_minterms=len(func.minterms),
            n_dontcare=len(func.dontcare),
            method="espresso",
            sop=r_esp.sop,
            n_terms=r_esp.n_terms,
            n_literals=r_esp.n_literals,
            elapsed_ms=(t1 - t0) * 1000,
            exact=False,
        ))
        # POS (if off-set is non-trivial)
        if func.minterms and len(func.minterms) < (1 << self.n_vars):
            pos_min = POSMinimizer(self.n_vars)
            t0 = time.perf_counter()
            r_pos = pos_min.minimize(func)
            t1 = time.perf_counter()
            results.append(BenchmarkResult(
                n_vars=self.n_vars,
                n_minterms=len(func.minterms),
                n_dontcare=len(func.dontcare),
                method="pos-dual",
                sop=r_pos.pos,
                n_terms=r_pos.n_clauses,
                n_literals=r_pos.n_literals,
                elapsed_ms=(t1 - t0) * 1000,
                exact=True,
            ))
        return results

    def run_trials(self) -> List[List[BenchmarkResult]]:
        """Run ``n_trials`` random benchmarks."""
        all_results: List[List[BenchmarkResult]] = []
        for _ in range(self.n_trials):
            all_results.append(self.run())
        return all_results

    @staticmethod
    def format_results(results: Sequence[BenchmarkResult]) -> str:
        """Format benchmark results as an ASCII table."""
        lines = [
            f"{'Method':<20} {'Vars':>4} {'Terms':>6} {'Lits':>5} {'Time(ms)':>10}",
            "-" * 50,
        ]
        for r in results:
            lines.append(
                f"{r.method:<20} {r.n_vars:>4} {r.n_terms:>6} "
                f"{r.n_literals:>5} {r.elapsed_ms:>10.2f}"
            )
        return "\n".join(lines)