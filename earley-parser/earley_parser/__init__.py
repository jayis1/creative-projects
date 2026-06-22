"""earley-parser: Earley chart parser for general context-free grammars.

A comprehensive parsing toolkit supporting:
- Earley algorithm (recognition + SPPF tree extraction)
- CYK algorithm (for CNF grammars)
- LL(1) analysis (table construction, conflict detection)
- Grammar analysis (nullable, FIRST, FOLLOW, productivity, reachability)
- Ambiguity detection
- Regex tokenizer
- BNF grammar file loader
- CLI with 10 subcommands
- JSON/YAML/TOML configuration
- Parse forest export (JSON, DOT, Lisp S-expressions)

Quick start::

    from earley_parser import Grammar, EarleyParser

    g = Grammar.from_rules("E", [
        ("E", ("E", "+", "E")),
        ("E", ("E", "*", "E")),
        ("E", ("(", "E", ")")),
        ("E", ("id",)),
    ])
    p = EarleyParser(g)
    print(p.parse(["id", "+", "id", "*", "id"]))  # True

    trees = p.trees(["id", "+", "id", "*", "id"])
    print(f"{len(trees)} parse tree(s)")
    for t in trees:
        print(t.pretty())
"""
from __future__ import annotations

from .grammar import (
    Grammar, GrammarLoader, GrammarStats, Symbol, EMPTY,
)
from .parser import (
    Item, Chart, ParseNode, ParseForest, EarleyParser,
)
from .tokenizer import TokenSpec, Token, Tokenizer
from .errors import EarleyError, ParseError, GrammarError, TokenizerError
from .cyk import CNFGrammar, CYKParser, CNFProduction
from .analysis import (
    LL1Table, is_ll1, detect_ambiguity, is_ambiguous,
    GrammarComparator, compute_bracket_depth, grammar_summary,
)
from .config import ParserConfig, load_config, save_config

__version__ = "2.0.0"
__author__ = "Creative Coder Pipeline"
__license__ = "MIT"

__all__ = [
    # Core
    "Grammar", "GrammarLoader", "GrammarStats", "Symbol", "EMPTY",
    "Item", "Chart", "ParseNode", "ParseForest", "EarleyParser",
    "Tokenizer", "TokenSpec", "Token",
    # Errors
    "EarleyError", "ParseError", "GrammarError", "TokenizerError",
    # CYK
    "CNFGrammar", "CYKParser", "CNFProduction",
    # Analysis
    "LL1Table", "is_ll1", "detect_ambiguity", "is_ambiguous",
    "GrammarComparator", "compute_bracket_depth", "grammar_summary",
    # Config
    "ParserConfig", "load_config", "save_config",
    # Metadata
    "__version__",
]