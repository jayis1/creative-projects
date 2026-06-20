"""datalog-engine — a Datalog deductive database engine.

A from-scratch implementation of Datalog with semi-naive evaluation,
stratified negation, hash-indexed joins, arithmetic/string/type-check
built-ins, aggregation, JSON I/O, retraction, introspection, an
interactive REPL, and configuration-file support.

Public API
----------
Engine
    The core evaluation engine. Load facts + rules, query, and
    introspect derived relations.
Parser / parse
    Low-level Datalog parser (tokenize + parse into AST terms).
EngineConfig / load_config
    Configuration management (JSON/TOML/YAML config files).

Example
-------
    >>> from datalog import Engine
    >>> e = Engine()
    >>> e.add_source("edge(a,b). path(X,Y) :- edge(X,Y). path(X,Y) :- edge(X,Z), path(Z,Y).")
    >>> e.query("path(a,Y)")
    [{'Y': 'b'}]
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
from .config import EngineConfig, load_config
from .errors import (
    DatalogError,
    StratificationError,
    SafetyError,
    ConfigurationError,
    QueryError,
)
from .output import format_results, format_binding

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
    "EngineConfig",
    "load_config",
    "DatalogError",
    "StratificationError",
    "SafetyError",
    "ConfigurationError",
    "QueryError",
    "format_results",
    "format_binding",
]

__version__ = "2.0.0"