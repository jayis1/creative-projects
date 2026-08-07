"""
Batch processing for multiple boolean functions.

Provides utilities for processing many functions at once:

* ``BatchProcessor`` — minimize a list of functions with the same minimizer.
* ``batch_from_pla_file(path)`` — load a PLA file and minimize each output.
* ``batch_to_json(results)`` / ``batch_from_json(text)`` — serialize results.
* ``BatchSummary`` — summary statistics across a batch.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from .boolean import BooleanFunction, cube_covers
from .quine_mccluskey import QuineMcCluskey, MinimizationResult
from .espresso import Espresso
from .pos import POSMinimizer, POSResult
from .pla import parse_pla_full


@dataclass
class BatchEntry:
    """Result of minimizing a single function in a batch."""

    name: str
    n_vars: int
    n_minterms: int
    n_dontcare: int
    method: str
    sop: str
    n_terms: int
    n_literals: int
    elapsed_ms: float
    correct: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "n_vars": self.n_vars,
            "n_minterms": self.n_minterms,
            "n_dontcare": self.n_dontcare,
            "method": self.method,
            "sop": self.sop,
            "n_terms": self.n_terms,
            "n_literals": self.n_literals,
            "elapsed_ms": round(self.elapsed_ms, 3),
            "correct": self.correct,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BatchEntry":
        return cls(**d)


@dataclass
class BatchSummary:
    """Summary statistics for a batch run."""

    n_functions: int = 0
    total_terms: int = 0
    total_literals: int = 0
    total_time_ms: float = 0.0
    avg_terms: float = 0.0
    avg_literals: float = 0.0
    all_correct: bool = True
    methods_used: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"BatchSummary(n={self.n_functions}, terms={self.total_terms}, "
            f"lits={self.total_literals}, time={self.total_time_ms:.1f}ms)"
        )


class BatchProcessor:
    """Process a batch of boolean functions with a specified minimizer.

    Parameters
    ----------
    minimizer : str
        "qm", "espresso", or "pos".
    n_vars : int, optional
        Expected number of variables (for validation).  If None, inferred
        from each function.
    use_petrick : bool
        Use Petrick's method (for QM/POS).
    """

    def __init__(
        self,
        minimizer: str = "qm",
        use_petrick: bool = True,
        espresso_max_iter: int = 50,
    ) -> None:
        if minimizer not in ("qm", "espresso", "pos"):
            raise ValueError(f"unknown minimizer {minimizer!r}")
        self.minimizer = minimizer
        self.use_petrick = use_petrick
        self.espresso_max_iter = espresso_max_iter

    def process(self, func: BooleanFunction) -> BatchEntry:
        """Minimize a single function and return a :class:`BatchEntry`."""
        t0 = time.perf_counter()
        result = self._minimize(func)
        t1 = time.perf_counter()
        # Verify correctness
        correct = True
        sop_cubes = result.sop_cubes if isinstance(result, MinimizationResult) else []
        if sop_cubes:
            for m in func.minterms:
                if not any(cube_covers(c, m) for c in sop_cubes):
                    correct = False
                    break
            if correct:
                off = set(range(1 << func.n_vars)) - func.minterms - func.dontcare
                for m in off:
                    if any(cube_covers(c, m) for c in sop_cubes):
                        correct = False
                        break
        if isinstance(result, MinimizationResult):
            sop = result.sop
            n_terms = result.n_terms
            n_lits = result.n_literals
            method = result.method
        elif isinstance(result, POSResult):
            sop = result.pos
            n_terms = result.n_clauses
            n_lits = result.n_literals
            method = result.method
        else:
            sop = str(result)
            n_terms = 0
            n_lits = 0
            method = "unknown"
        return BatchEntry(
            name=func.name,
            n_vars=func.n_vars,
            n_minterms=len(func.minterms),
            n_dontcare=len(func.dontcare),
            method=method,
            sop=sop,
            n_terms=n_terms,
            n_literals=n_lits,
            elapsed_ms=(t1 - t0) * 1000,
            correct=correct,
        )

    def process_batch(self, functions: Sequence[BooleanFunction]) -> List[BatchEntry]:
        """Minimize a list of functions."""
        return [self.process(f) for f in functions]

    def _minimize(self, func: BooleanFunction):
        """Run the configured minimizer."""
        if self.minimizer == "qm":
            qm = QuineMcCluskey(func.n_vars, use_petrick=self.use_petrick)
            return qm.minimize(func)
        elif self.minimizer == "espresso":
            esp = Espresso(func.n_vars, max_iter=self.espresso_max_iter)
            return esp.minimize(func)
        elif self.minimizer == "pos":
            pm = POSMinimizer(func.n_vars, use_petrick=self.use_petrick)
            return pm.minimize(func)
        else:
            raise ValueError(f"unknown minimizer {self.minimizer!r}")
def batch_from_pla_file(path: str, minimizer: str = "qm") -> List[BatchEntry]:
    """Load a PLA file, minimize each output, and return batch entries."""
    with open(path) as fh:
        text = fh.read()
    pla = parse_pla_full(text)
    functions = pla.to_functions()
    processor = BatchProcessor(minimizer=minimizer)
    return processor.process_batch(functions)


def batch_summary(entries: Sequence[BatchEntry]) -> BatchSummary:
    """Compute summary statistics for a batch."""
    if not entries:
        return BatchSummary()
    total_terms = sum(e.n_terms for e in entries)
    total_lits = sum(e.n_literals for e in entries)
    total_time = sum(e.elapsed_ms for e in entries)
    methods = list(set(e.method for e in entries))
    return BatchSummary(
        n_functions=len(entries),
        total_terms=total_terms,
        total_literals=total_lits,
        total_time_ms=total_time,
        avg_terms=total_terms / len(entries),
        avg_literals=total_lits / len(entries),
        all_correct=all(e.correct for e in entries),
        methods_used=methods,
    )


def batch_to_json(entries: Sequence[BatchEntry]) -> str:
    """Serialize batch entries to JSON."""
    data = {
        "entries": [e.to_dict() for e in entries],
        "summary": {
            "n_functions": len(entries),
            "total_terms": sum(e.n_terms for e in entries),
            "total_literals": sum(e.n_literals for e in entries),
            "all_correct": all(e.correct for e in entries),
        },
    }
    return json.dumps(data, indent=2)


def batch_from_json(text: str) -> List[BatchEntry]:
    """Deserialize batch entries from JSON."""
    data = json.loads(text)
    return [BatchEntry.from_dict(e) for e in data.get("entries", [])]