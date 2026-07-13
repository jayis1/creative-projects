"""LALR(1) parser generator package.

A from-scratch implementation of LALR(1) parser table generation with
an LR parser driver, BNF grammar loader, SLR(1) comparison, precedence/
associativity resolution, JSON table serialization, and CLI.

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
from .slr_table import SLRTable
from .precedence import PrecedenceTable, Precedence
from .parser import Parser, ParseError, Token
from .bnf_loader import load_bnf, load_bnf_full, GrammarParseError

__version__ = "2.0.0"
__all__ = [
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
    "load_bnf",
    "load_bnf_full",
    "GrammarParseError",
]