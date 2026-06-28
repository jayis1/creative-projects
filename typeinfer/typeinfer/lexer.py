r"""Hand-written lexer for the mini lambda calculus.

Tokens
------
* ``INT``      – integer literal (e.g. ``42``)
* ``BOOL``     – ``true`` / ``false``
* ``IDENT``    – identifier
* ``LAMBDA``   – ``\`` or ``λ``
* ``DOT``      – ``.``
* ``LET``      – ``let``
* ``REC``      – ``rec``
* ``IN``       – ``in``
* ``IF`` / ``THEN`` / ``ELSE``
* ``ARROW``    – ``->``  (used in type annotations, future)
* ``EQ``       – ``=``
* ``LPAREN`` / ``RPAREN``
* ``EOF``
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


KEYWORDS = {
    "let": "LET",
    "rec": "REC",
    "in": "IN",
    "if": "IF",
    "then": "THEN",
    "else": "ELSE",
    "true": "BOOL",
    "false": "BOOL",
}


@dataclass
class Token:
    kind: str
    value: str
    pos: int

    def __repr__(self) -> str:  # pragma: no cover
        return f"Token({self.kind!r}, {self.value!r}, pos={self.pos})"


class LexerError(Exception):
    """Raised on an invalid character during tokenisation."""


def tokenize(source: str) -> List[Token]:
    """Tokenise *source* into a list of `Token` objects (ending with EOF)."""
    tokens: List[Token] = []
    i = 0
    n = len(source)
    while i < n:
        c = source[i]
        # whitespace
        if c.isspace():
            i += 1
            continue
        # comments: -- to end of line
        if c == "-" and i + 1 < n and source[i + 1] == "-":
            while i < n and source[i] != "\n":
                i += 1
            continue
        # lambda
        if c == "\\" or c == "λ":
            tokens.append(Token("LAMBDA", c, i))
            i += 1
            continue
        # dot
        if c == ".":
            tokens.append(Token("DOT", c, i))
            i += 1
            continue
        # arrow ->  (must check before minus/single dash)
        if c == "-" and i + 1 < n and source[i + 1] == ">":
            tokens.append(Token("ARROW", "->", i))
            i += 2
            continue
        # equals
        if c == "=":
            tokens.append(Token("EQ", c, i))
            i += 1
            continue
        # parens
        if c == "(":
            tokens.append(Token("LPAREN", c, i))
            i += 1
            continue
        if c == ")":
            tokens.append(Token("RPAREN", c, i))
            i += 1
            continue
        # integers
        if c.isdigit():
            j = i
            while j < n and source[j].isdigit():
                j += 1
            tokens.append(Token("INT", source[i:j], i))
            i = j
            continue
        # identifiers / keywords
        if c.isalpha() or c == "_":
            j = i
            while j < n and (source[j].isalnum() or source[j] in "_'"):
                j += 1
            word = source[i:j]
            kw = KEYWORDS.get(word)
            if kw is not None:
                if kw == "BOOL":
                    tokens.append(Token("BOOL", word, i))
                else:
                    tokens.append(Token(kw, word, i))
            else:
                tokens.append(Token("IDENT", word, i))
            i = j
            continue
        raise LexerError(f"Unexpected character {c!r} at position {i}")
    tokens.append(Token("EOF", "", n))
    return tokens