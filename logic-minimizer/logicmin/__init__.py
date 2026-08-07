"""
logicmin — A boolean logic minimization toolkit.

Public API
----------
* QuineMcCluskey — exact two-level minimizer (prime implicants + Petrick's method)
* Espresso — heuristic two-level minimizer (expand + irredundant + reduce)
* BooleanFunction — minterm/dontcare representation, truth tables, eval
* MultiOutputMinimizer — shared-implicant minimization across several outputs
* Factorizer — multi-level factoring of SOP forms (algebraic extraction)
* POSMinimizer — product-of-sums minimization via De Morgan duality
* BDDManager — Reduced Ordered Binary Decision Diagrams (ITE, SAT count, SOP)
* KarnaughMap — K-map rendering with cover highlighting
* Benchmark — QM vs Espresso comparison suite
* Config — JSON/TOML/YAML configuration system
* BatchProcessor — batch minimization of many functions
* PLAData — full PLA format reader/writer
* DCAssignmentResult — don't-care assignment optimization
* Sensitivity analysis, boolean difference, unate classification
* HTML visualization (truth tables, K-maps, full reports)
* JSON serialization for functions and results

Example
-------
>>> from logicmin import QuineMcCluskey, BooleanFunction
>>> qm = QuineMcCluskey(n_vars=4)
>>> f = BooleanFunction(n_vars=4, minterms=[4,8,10,11,12,15], dontcare=[9,14])
>>> result = qm.minimize(f)
>>> result.sop
'AB\\'C + AC + B\\'D'
"""

from .boolean import (
    BooleanFunction, TruthTable, Implicant,
    minterm_to_cube, cube_to_minterms, cube_covers, can_merge, var_names,
)
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
from .bdd import BDDManager, BDDNode, build_bdd, bdd_sop
from .analysis import (
    boolean_difference, sensitivity, all_sensitivities,
    is_unate, unate_profile, on_set_size, off_set_size,
    hamming_distance_matrix, minterm_adjacency,
)
from .pla import PLAData, parse_pla_full, write_pla
from .dc_optimize import assign_dontcares, minimize_with_dc_optimization, DCAssignmentResult
from .htmlviz import (
    truth_table_html, kmap_html, kmap_with_cover_html, full_report_html,
)
from .batch import (
    BatchProcessor, BatchEntry, BatchSummary,
    batch_from_pla_file, batch_summary, batch_to_json, batch_from_json,
)
from .serialize import (
    serialize, function_to_json, function_from_json,
    result_to_json, pos_result_to_json, multi_result_to_json,
    save_function, load_function, save_result, save_multi_result,
)

__all__ = [
    # Core
    "QuineMcCluskey",
    "MinimizationResult",
    "Espresso",
    "BooleanFunction",
    "TruthTable",
    "Implicant",
    "minterm_to_cube",
    "cube_to_minterms",
    "cube_covers",
    "can_merge",
    "var_names",
    # Petrick
    "PetrickSolver",
    "Product",
    "Term",
    # Multi-output
    "MultiOutputMinimizer",
    "MultiOutputResult",
    # Factorizer
    "Factorizer",
    "FactoredForm",
    # POS
    "POSMinimizer",
    "POSResult",
    # K-map
    "KarnaughMap",
    "gray_code",
    # Benchmark
    "Benchmark",
    "BenchmarkResult",
    # Config
    "Config",
    # Exceptions
    "LogicMinError",
    "ParseError",
    "MinimizationError",
    "InvalidFunctionError",
    "PetrickExpansionError",
    # Parsers
    "parse_truth_table",
    "parse_minterms",
    "parse_sop",
    "parse_pla",
    # CLI
    "main",
    # BDD
    "BDDManager",
    "BDDNode",
    "build_bdd",
    "bdd_sop",
    # Analysis
    "boolean_difference",
    "sensitivity",
    "all_sensitivities",
    "is_unate",
    "unate_profile",
    "on_set_size",
    "off_set_size",
    "hamming_distance_matrix",
    "minterm_adjacency",
    # PLA
    "PLAData",
    "parse_pla_full",
    "write_pla",
    # DC optimization
    "assign_dontcares",
    "minimize_with_dc_optimization",
    "DCAssignmentResult",
    # HTML viz
    "truth_table_html",
    "kmap_html",
    "kmap_with_cover_html",
    "full_report_html",
    # Batch
    "BatchProcessor",
    "BatchEntry",
    "BatchSummary",
    "batch_from_pla_file",
    "batch_summary",
    "batch_to_json",
    "batch_from_json",
    # Serialization
    "serialize",
    "function_to_json",
    "function_from_json",
    "result_to_json",
    "pos_result_to_json",
    "multi_result_to_json",
    "save_function",
    "load_function",
    "save_result",
    "save_multi_result",
]

__version__ = "2.0.0"