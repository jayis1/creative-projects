"""
CDCL SAT Solver — Conflict-Driven Clause Learning with VSIDS and Restarts.

A fully-featured SAT solver implemented in pure Python, supporting the standard
DIMACS CNF input format and a rich set of solving strategies.

Modules:
    solver    — Core CDCL solver engine
    generator — CNF instance generator for benchmarking
    utils     — DIMACS I/O and utility functions
    config    — Solver configuration
"""

from cdcl_sat.solver import Solver, SolverStats
from cdcl_sat.generator import (
    generate_php,
    generate_random_cnf,
    generate_chain,
    generate_tseitin,
    generate_mutilated_chessboard,
)
from cdcl_sat.config import SolverConfig
from cdcl_sat.utils import read_dimacs_file, write_dimacs_model, solve_file

__version__ = "2.0.0"
__all__ = [
    "Solver",
    "SolverStats",
    "SolverConfig",
    "generate_php",
    "generate_random_cnf",
    "generate_chain",
    "generate_tseitin",
    "generate_mutilated_chessboard",
    "read_dimacs_file",
    "write_dimacs_model",
    "solve_file",
]