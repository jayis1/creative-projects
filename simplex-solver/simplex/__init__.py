"""simplex-solver: exact linear & integer programming via the Simplex method.

Public API
----------
.. autosummary::

    LPProblem
    LPResult
    SimplexSolver
    MILPSolver
    solve
    solve_milp
"""

from .problem import LPProblem, LPResult, LPStatus
from .simplex import SimplexSolver
from .integer import MILPSolver
from .mps import read_mps, write_mps
from .cli import main

__version__ = "1.0.0"
__all__ = [
    "LPProblem",
    "LPResult",
    "LPStatus",
    "SimplexSolver",
    "MILPSolver",
    "read_mps",
    "write_mps",
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