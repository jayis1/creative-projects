"""
Constraint Satisfaction Problem (CSP) Solver
=============================================

A comprehensive CSP solver implementing:
- Arc Consistency (AC-3) algorithm
- Backtracking search with constraint propagation
- MRV (Minimum Remaining Values) heuristic
- LCV (Least Constraining Value) heuristic
- Forward checking
- MAC (Maintaining Arc Consistency)
- Constraint propagation with unit propagation
- Support for binary and n-ary constraints
- Built-in problem generators for Sudoku, N-Queens, Graph Coloring, and Cryptarithms
"""

from .csp import CSP, Variable, Constraint
from .solver import CSPSolver, SolveResult
from .problems import (
    sudoku_csp,
    n_queens_csp,
    graph_coloring_csp,
    cryptarithm_csp,
)
from .backtrack import BacktrackingSolver
from .ac3 import ac3, ac3_queue

__version__ = "1.0.0"

__all__ = [
    "CSP",
    "Variable",
    "Constraint",
    "CSPSolver",
    "SolveResult",
    "BacktrackingSolver",
    "ac3",
    "ac3_queue",
    "sudoku_csp",
    "n_queens_csp",
    "graph_coloring_csp",
    "cryptarithm_csp",
]