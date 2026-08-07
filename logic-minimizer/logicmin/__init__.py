"""
logicmin — A boolean logic minimization toolkit.

Public API
----------
* QuineMcCluskey — exact two-level minimizer (prime implicants + Petrick's method)
* Espresso — heuristic two-level minimizer (expand + irredundant + reduce)
* BooleanFunction — minterm/dontcare representation, truth tables, eval
* MultiOutputMinimizer — shared-implicant minimization across several outputs
* Factorizer — multi-level factoring of SOP forms (algebraic extraction)
* parse_truth_table, parse_minterms — convenience constructors

Example
-------
>>> from logicmin import QuineMcCluskey, BooleanFunction
>>> qm = QuineMcCluskey(n_vars=4)
>>> f = BooleanFunction(n_vars=4, minterms=[4,8,10,11,12,15], dontcare=[9,14])
>>> result = qm.minimize(f)
>>> result.sop
'AB\'C + AC + B\'D'
"""

from .boolean import BooleanFunction, TruthTable, Implicant, minterm_to_cube
from .quine_mccluskey import QuineMcCluskey, MinimizationResult
from .petrick import PetrickSolver, Product, Term
from .espresso import Espresso
from .multi_output import MultiOutputMinimizer, MultiOutputResult
from .factorizer import Factorizer, FactoredForm
from .pos import POSMinimizer, POSResult
from .kmap import KarnaughMap, gray_code
from .benchmark import Benchmark, BenchmarkResult
from .config import Config
from .exceptions import (
    LogicMinError, ParseError, MinimizationError,
    InvalidFunctionError, PetrickExpansionError,
)
from .parser import parse_truth_table, parse_minterms, parse_sop, parse_pla
from .cli import main

__all__ = [
    "QuineMcCluskey",
    "MinimizationResult",
    "Espresso",
    "BooleanFunction",
    "TruthTable",
    "Implicant",
    "minterm_to_cube",
    "PetrickSolver",
    "Product",
    "Term",
    "MultiOutputMinimizer",
    "MultiOutputResult",
    "Factorizer",
    "FactoredForm",
    "POSMinimizer",
    "POSResult",
    "KarnaughMap",
    "gray_code",
    "Benchmark",
    "BenchmarkResult",
    "Config",
    "LogicMinError",
    "ParseError",
    "MinimizationError",
    "InvalidFunctionError",
    "PetrickExpansionError",
    "parse_truth_table",
    "parse_minterms",
    "parse_sop",
    "parse_pla",
    "main",
]

__version__ = "1.0.0"