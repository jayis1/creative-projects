"""
smt-solver: A DPLL(T)-based Satisfiability Modulo Theories solver.

Provides:
  - CDCL SAT engine with VSIDS branching
  - Theory of Uninterpreted Functions with Equality (EUF) via congruence closure
  - Theory of Linear Real Arithmetic (LRA) via Simplex
  - DPLL(T) integration with theory propagation
  - SMT-LIB v2 subset parser
  - Model generation
  - CLI interface

>>> from smt_solver import Solver
>>> s = Solver()
>>> s.parse_and_assert("(assert (> x 5.0))")
>>> s.parse_and_assert("(assert (< x 10.0))")
>>> s.check()
'sat'
"""

from .solver import Solver, SMTResult
from .ast import (
    Term, Var, App, BoolConst, NumConst, Sort, BOOL, REAL, INT,
    And, Or, Not, Implies, Iff, Eq, Lt, Le, Gt, Ge,
    Add, Sub, Mul, Neg, Ite,
)
from .exceptions import SMTError, ParseError, TheoryError

__version__ = "1.0.0"
__all__ = [
    "Solver", "SMTResult",
    "Term", "Var", "App", "BoolConst", "NumConst", "Sort", "BOOL", "REAL", "INT",
    "And", "Or", "Not", "Implies", "Iff", "Eq", "Lt", "Le", "Gt", "Ge",
    "Add", "Sub", "Mul", "Neg", "Ite",
    "SMTError", "ParseError", "TheoryError",
]