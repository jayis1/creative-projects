"""
prolog-engine: A mini-Prolog logic programming engine in pure Python.

Implements unification, backtracking search, built-in predicates,
and a comprehensive standard library — all from scratch.

Quick start::

    >>> from prolog_engine import create_engine
    >>> engine = create_engine()
    >>> engine.load_source('parent(tom, bob). parent(tom, liz).')
    >>> results = engine.query('?- parent(tom, X).')
    >>> for r in results:
    ...     print(engine.format_solution(r))
    X = bob
    X = liz
"""

from prolog_engine.lexer import Token, TokenType, Lexer
from prolog_engine.parser import Parser
from prolog_engine.ast_nodes import (
    Atom, Variable, Number, String, Compound, Clause, Query,
    Program,
)
from prolog_engine.unifier import Unifier, Substitution
from prolog_engine.engine import Engine, EngineError, EvaluationError
from prolog_engine.builtins import register_builtins
from prolog_engine.config import EngineConfig
from prolog_engine.errors import (
    PrologError,
    LexerError,
    ParseError,
    UnificationError,
    InstantiationError,
    TypeError as PrologTypeError,
    ExistenceError,
    PermissionError,
)

__version__ = "2.0.0"

__all__ = [
    # Core classes
    "Engine",
    "EngineConfig",
    "Lexer",
    "Parser",
    "Unifier",
    "Substitution",
    # AST nodes
    "Atom",
    "Variable",
    "Number",
    "String",
    "Compound",
    "Clause",
    "Query",
    "Program",
    # Tokens
    "Token",
    "TokenType",
    # Errors
    "EngineError",
    "EvaluationError",
    "PrologError",
    "LexerError",
    "ParseError",
    "UnificationError",
    "InstantiationError",
    "PrologTypeError",
    "ExistenceError",
    "PermissionError",
    # Builtins
    "register_builtins",
    # Convenience
    "create_engine",
]


def create_engine(
    max_depth: int = 1000,
    max_solutions: int = 10000,
    trace: bool = False,
    config: EngineConfig | None = None,
) -> Engine:
    """Create a fresh Engine with all built-in predicates registered.

    Args:
        max_depth: Maximum inference depth to prevent infinite loops.
        max_solutions: Maximum number of solutions before raising an error.
        trace: Enable trace mode for debugging.
        config: Optional EngineConfig to apply (overrides other args).

    Returns:
        A configured Engine instance with built-ins registered.
    """
    if config is not None:
        engine = Engine(
            max_depth=config.max_depth,
            max_solutions=config.max_solutions,
            trace=config.trace,
        )
    else:
        engine = Engine(
            max_depth=max_depth,
            max_solutions=max_solutions,
            trace=trace,
        )
    register_builtins(engine)
    return engine