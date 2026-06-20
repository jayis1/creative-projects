"""datalog-engine — a Datalog deductive database engine.

Public API
----------
Engine
    The core evaluation engine. Load facts + rules, query, and
    introspect derived relations.
Parser
    Low-level Datalog parser (tokenize + parse into AST terms).
parse
    Convenience function: parse a Datalog program string and return
    a list of statements (facts, rules, queries).
"""

from .engine import Engine
from .parser import Parser, parse, Token, TokenType
from .ast import (
    Term,
    Variable,
    Constant,
    Atom,
    Literal,
    Rule,
    Fact,
    Query,
    Program,
)

__all__ = [
    "Engine",
    "Parser",
    "parse",
    "Token",
    "TokenType",
    "Term",
    "Variable",
    "Constant",
    "Atom",
    "Literal",
    "Rule",
    "Fact",
    "Query",
    "Program",
]

__version__ = "1.0.0"