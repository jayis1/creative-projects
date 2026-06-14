"""
Constraint Satisfaction Problem (CSP) Solver
=============================================

A comprehensive CSP solver implementing:
- Arc Consistency (AC-3) algorithm with optimized revise
- Backtracking search with constraint propagation
- MRV (Minimum Remaining Values) heuristic
- LCV (Least Constraining Value) heuristic
- Degree heuristic (tiebreaker for MRV)
- Forward checking
- MAC (Maintaining Arc Consistency)
- Strategy comparison utility
- Built-in problem generators for Sudoku, N-Queens, Graph Coloring,
  Cryptarithm, Latin Square, and Magic Square
"""

from .csp import CSP, Variable, Constraint
from .solver import CSPSolver, SolveResult, compare_strategies
from .problems import (
    sudoku_csp,
    generate_sudoku,
    n_queens_csp,
    count_n_queens_solutions,
    graph_coloring_csp,
    cryptarithm_csp,
    latin_square_csp,
    magic_square_csp,
    format_sudoku_solution,
    format_queens_solution,
    format_cryptarithm_solution,
    format_latin_square,
    format_magic_square,
    AUSTRALIA_EDGES,
    US_REGIONS_EDGES,
)
from .backtrack import BacktrackingSolver
from .ac3 import ac3, ac3_queue, node_consistency, domain_reduction

__version__ = "1.1.0"

__all__ = [
    # Core classes
    "CSP",
    "Variable",
    "Constraint",
    # Solvers
    "CSPSolver",
    "SolveResult",
    "BacktrackingSolver",
    "compare_strategies",
    # AC-3 functions
    "ac3",
    "ac3_queue",
    "node_consistency",
    "domain_reduction",
    # Problem generators
    "sudoku_csp",
    "generate_sudoku",
    "n_queens_csp",
    "count_n_queens_solutions",
    "graph_coloring_csp",
    "cryptarithm_csp",
    "latin_square_csp",
    "magic_square_csp",
    # Formatters
    "format_sudoku_solution",
    "format_queens_solution",
    "format_cryptarithm_solution",
    "format_latin_square",
    "format_magic_square",
    # Pre-defined graphs
    "AUSTRALIA_EDGES",
    "US_REGIONS_EDGES",
]