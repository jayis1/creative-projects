"""LALR(1) parser generator package.

A from-scratch implementation of LALR(1) parser table generation with
an LR parser driver, BNF grammar loader, SLR(1) comparison, precedence/
associativity resolution, JSON table serialization, configurable lexer,
error recovery, grammar transformations, visualization, configuration
management, and CLI.

Quick start::

    from lalr import Grammar, LALRTable, Parser, Token

    grammar = Grammar([
        ("expr", ["expr", "+", "term"]),
        ("expr", ["term"]),
        ("term", ["term", "*", "factor"]),
        ("term", ["factor"]),
        ("factor", ["(", "expr", ")"]),
        ("factor", ["NUMBER"]),
    ])
    table = LALRTable(grammar)
    parser = Parser(grammar, table)
    result = parser.parse([
        Token("NUMBER", 42),
        Token("+"),
        Token("NUMBER", 8),
        Token("*"),
        Token("NUMBER", 3),
    ])

With a configurable lexer::

    from lalr import Lexer, TokenSpec

    lexer = Lexer()
    lexer.add_spec(TokenSpec("NUMBER", r"\\d+", action=int))
    lexer.add_spec(TokenSpec("PLUS", r"\\+"))
    lexer.set_skip(r"[ \\t\\n]+")
    tokens = lexer.lex("42 + 8")

With error recovery::

    from lalr.error_recovery import RecoveringParser

    parser = RecoveringParser(grammar, table=table, sync_tokens={";"})
    errors = []
    result = parser.parse(tokens, on_error=errors.append)
"""

from .grammar import Grammar, Production, EPSILON
from .table import LALRTable, LR0Automaton, LALR1Builder, LR0Item, LALR1Item
from .slr_table import SLRTable
from .precedence import PrecedenceTable, Precedence
from .parser import Parser, ParseError, Token
from .bnf_loader import load_bnf, load_bnf_full, GrammarParseError
from .lexer import Lexer, TokenSpec, LexError, LexerBuilder
from .config import LALRConfig, setup_logging

__version__ = "3.0.0"
__all__ = [
    # Core
    "Grammar",
    "Production",
    "EPSILON",
    "LALRTable",
    "SLRTable",
    "LR0Automaton",
    "LALR1Builder",
    "LR0Item",
    "LALR1Item",
    "PrecedenceTable",
    "Precedence",
    "Parser",
    "ParseError",
    "Token",
    # BNF loader
    "load_bnf",
    "load_bnf_full",
    "GrammarParseError",
    # Lexer
    "Lexer",
    "TokenSpec",
    "LexError",
    "LexerBuilder",
    # Config
    "LALRConfig",
    "setup_logging",
]