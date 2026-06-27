"""simplex-solver: exact linear & integer programming via the Simplex method.

Public API
----------
.. autosummary::

    LPProblem
    LPResult
    LPStatus
    SimplexSolver
    MILPSolver
    SearchStrategy
    SolverConfig
    solve
    solve_milp
    read_mps
    write_mps
    read_lp
    write_lp
    format_result
"""

from .problem import LPProblem, LPResult, LPStatus
from .simplex import SimplexSolver, Tableau
from .integer import MILPSolver, SearchStrategy
from .mps import read_mps, write_mps
from .formatting import read_lp, write_lp, format_result, format_tableau
from .config import SolverConfig, load_config, save_config
from .cli import main

__version__ = "2.0.0"
__all__ = [
    "LPProblem",
    "LPResult",
    "LPStatus",
    "SimplexSolver",
    "Tableau",
    "MILPSolver",
    "SearchStrategy",
    "SolverConfig",
    "load_config",
    "save_config",
    "read_mps",
    "write_mps",
    "read_lp",
    "write_lp",
    "format_result",
    "format_tableau",
    "solve",
    "solve_milp",
    "main",
    "__version__",
]


def solve(problem: LPProblem, **kwargs) -> LPResult:
    """Convenience wrapper: solve a linear program and return the result."""
    return SimplexSolver(**kwargs).solve(problem)


def solve_milp(problem: LPProblem, **kwargs) -> LPResult:
    """Convenience wrapper: solve a mixed-integer program via branch-and-bound."""
    return MILPSolver(**kwargs).solve(problem)