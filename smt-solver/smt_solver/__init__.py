"""
smt-solver: A DPLL(T)-based Satisfiability Modulo Theories solver.

Provides:
  - CDCL SAT engine with VSIDS branching
  - Theory of Uninterpreted Functions with Equality (EUF) via congruence closure
  - Theory of Linear Real Arithmetic (LRA) via Fourier-Motzkin elimination
  - DPLL(T) integration with theory propagation
  - SMT-LIB v2 subset parser
  - Model generation
  - CLI interface

>>> from smt_solver import Solver
>>> s = Solver()
>>> s.declare_const("x", REAL)
>>> s.assert_term(Gt(Var("x", REAL), NumConst(5.0)))
>>> s.assert_term(Lt(Var("x", REAL), NumConst(10.0)))
>>> s.check()
'sat'
"""

from .solver import Solver, SMTResult, Model, SolverStatistics
from .ast import (
    Term, Var, App, BoolConst, NumConst, StrConst, Sort,
    BOOL, REAL, INT, STRING,
    And, Or, Not, Implies, Iff, Eq, Lt, Le, Gt, Ge,
    Add, Sub, Mul, Neg, Ite,
    collect_vars, is_atom, pre_order,
)
from .exceptions import SMTError, ParseError, TheoryError, TypeCheckError

__version__ = "2.0.0"
__all__ = [
    "Solver", "SMTResult", "Model", "SolverStatistics",
    "Term", "Var", "App", "BoolConst", "NumConst", "StrConst",
    "Sort", "BOOL", "REAL", "INT", "STRING",
    "And", "Or", "Not", "Implies", "Iff", "Eq", "Lt", "Le", "Gt", "Ge",
    "Add", "Sub", "Mul", "Neg", "Ite",
    "collect_vars", "is_atom", "pre_order",
    "SMTError", "ParseError", "TheoryError", "TypeCheckError",
]