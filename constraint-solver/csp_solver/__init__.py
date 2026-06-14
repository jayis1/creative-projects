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
  Cryptarithm, Latin Square, Magic Square, and more
- Configuration management (JSON/YAML/TOML)
- Progress tracking and logging
- Visualization and rendering
- Serialization (JSON export/import)
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
from .problems_extra import (
    job_shop_csp,
    format_schedule,
    knights_tour_csp,
    graph_csp_from_edges,
)
from .backtrack import BacktrackingSolver
from .ac3 import ac3, ac3_queue, node_consistency, domain_reduction
from .config import SolverConfig
from .logging_utils import SolverProgress, setup_logging
from .visualization import (
    render_sudoku,
    render_queens,
    render_graph_coloring,
    render_cryptarithm,
    render_latin_square,
    render_magic_square,
    render_search_tree,
)
from .serialization import (
    export_csp,
    export_solution,
    save_csp,
    save_solution,
    import_csp,
    load_csp,
)

__version__ = "2.0.0"

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
    "job_shop_csp",
    "knights_tour_csp",
    "graph_csp_from_edges",
    # Formatters (original)
    "format_sudoku_solution",
    "format_queens_solution",
    "format_cryptarithm_solution",
    "format_latin_square",
    "format_magic_square",
    "format_schedule",
    # Pre-defined graphs
    "AUSTRALIA_EDGES",
    "US_REGIONS_EDGES",
    # Configuration
    "SolverConfig",
    # Logging & Progress
    "SolverProgress",
    "setup_logging",
    # Visualization
    "render_sudoku",
    "render_queens",
    "render_graph_coloring",
    "render_cryptarithm",
    "render_latin_square",
    "render_magic_square",
    "render_search_tree",
    # Serialization
    "export_csp",
    "export_solution",
    "save_csp",
    "save_solution",
    "import_csp",
    "load_csp",
]