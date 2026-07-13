"""LALR(1) parser generator package.

A from-scratch implementation of LALR(1) parser table generation with
an LR parser driver, BNF grammar loader, and CLI.

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
"""

from .grammar import Grammar, Production, EPSILON
from .table import LALRTable, LR0Automaton, LALR1Builder, LR0Item, LALR1Item
from .parser import Parser, ParseError, Token
from .bnf_loader import load_bnf, GrammarParseError

__version__ = "1.0.0"
__all__ = [
    "Grammar",
    "Production",
    "EPSILON",
    "LALRTable",
    "LR0Automaton",
    "LALR1Builder",
    "LR0Item",
    "LALR1Item",
    "Parser",
    "ParseError",
    "Token",
    "load_bnf",
    "GrammarParseError",
]