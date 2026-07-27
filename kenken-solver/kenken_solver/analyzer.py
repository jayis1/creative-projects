"""Puzzle analysis and difficulty estimation.

The :class:`PuzzleAnalyzer` computes several metrics that characterise a
KenKen puzzle:

* **Cage statistics** — number of cages, average/max cage size, singleton count.
* **Operator distribution** — count of each operator type.
* **Difficulty score** — weighted combination of grid size, average cage size,
  operator mix, and singleton count.
* **Difficulty category** — ``easy`` (≤15), ``medium`` (≤30), ``hard`` (>30).
* **Solver complexity** — node count and backtrack count for the first solution.
"""

from __future__ import annotations

import logging
from typing import Dict

from kenken_solver.puzzle import KenKenPuzzle
from kenken_solver.solver import KenKenSolver

logger = logging.getLogger(__name__)


class PuzzleAnalyzer:
    """Analyzes puzzle properties and difficulty.

    Parameters
    ----------
    puzzle:
        The :class:`~kenken_solver.puzzle.KenKenPuzzle` to analyze.
    """

    def __init__(self, puzzle: KenKenPuzzle) -> None:
        self.puzzle = puzzle
        self.n: int = puzzle.size

    def analyze(self) -> dict:
        """Return a dictionary of analysis metrics."""
        cages = self.puzzle.cages
        n = self.n
        # Basic stats
        num_cages = len(cages)
        cage_sizes = [c.size for c in cages]
        avg_cage_size = sum(cage_sizes) / num_cages if num_cages else 0
        max_cage_size = max(cage_sizes) if cage_sizes else 0
        num_singletons = sum(1 for c in cages if c.size == 1)
        # Operator distribution
        op_counts: Dict[str, int] = {}
        for c in cages:
            op_counts[c.op] = op_counts.get(c.op, 0) + 1
        # Difficulty heuristics
        # 1. Larger cages → harder (more combinations to check)
        # 2. *, / → harder than +, -
        # 3. Fewer singletons → harder
        # 4. Larger grid → harder
        difficulty_score = 0
        difficulty_score += n * 2  # base grid size
        difficulty_score += int(avg_cage_size * 3)
        difficulty_score += op_counts.get("*", 0) * 3
        difficulty_score += op_counts.get("/", 0) * 4
        difficulty_score += op_counts.get("-", 0) * 2
        difficulty_score -= num_singletons * 2
        # Categorize
        if difficulty_score <= 15:
            category = "easy"
        elif difficulty_score <= 30:
            category = "medium"
        else:
            category = "hard"
        # Solver complexity: count solver nodes for one solution
        solver = KenKenSolver(self.puzzle, max_solutions=1)
        solver.solve()
        node_count = solver.stats["nodes"]
        backtrack_count = solver.stats["backtracks"]
        logger.debug(
            "analyze(): score=%d category=%s nodes=%d backtracks=%d",
            difficulty_score,
            category,
            node_count,
            backtrack_count,
        )
        return {
            "size": n,
            "num_cages": num_cages,
            "avg_cage_size": round(avg_cage_size, 2),
            "max_cage_size": max_cage_size,
            "num_singletons": num_singletons,
            "operator_distribution": op_counts,
            "difficulty_score": difficulty_score,
            "difficulty_category": category,
            "solver_nodes": node_count,
            "solver_backtracks": backtrack_count,
        }


__all__ = ["PuzzleAnalyzer"]