"""
prolog-engine: A mini-Prolog logic programming engine in pure Python.

Implements unification, backtracking search, built-in predicates,
and a comprehensive standard library — all from scratch.
"""

from prolog_engine.lexer import Token, TokenType, Lexer
from prolog_engine.parser import Parser
from prolog_engine.ast_nodes import (
    Atom, Variable, Number, String, Compound, Clause, Query,
    Program,
)
from prolog_engine.unifier import Unifier, Substitution
from prolog_engine.engine import Engine
from prolog_engine.builtins import register_builtins

__version__ = "1.0.0"

__all__ = [
    "Token", "TokenType", "Lexer",
    "Parser",
    "Atom", "Variable", "Number", "String", "Compound", "Clause", "Query",
    "Program",
    "Unifier", "Substitution",
    "Engine",
    "register_builtins",
]


def create_engine() -> Engine:
    """Create a fresh Engine with all built-in predicates registered."""
    engine = Engine()
    register_builtins(engine)
    return engine