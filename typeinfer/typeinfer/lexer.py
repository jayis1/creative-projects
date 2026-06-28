"""Hand-written lexer for the mini lambda calculus.

Tokens
------
* ``INT``      – integer literal (e.g. ``42``)
* ``STRING``   – string literal (e.g. ``"hello"``)
* ``BOOL``     – ``true`` / ``false``
* ``IDENT``    – identifier (also operator names like ``+``, ``==``)
* ``OP``       – an operator symbol (``+ - * / < > <= >= == != && ||``)
* ``LAMBDA``   – ``\\`` or ``λ``
* ``DOT``      – ``.``
* ``COLON``    – ``:``  (used in type annotations)
* ``BAR``      – ``|``  (used in case alternatives)
* ``ARROW2``   – ``->`` in type annotations (reuses ARROW)
* ``LET``      – ``let``
* ``REC``      – ``rec``
* ``IN``       – ``in``
* ``AND``      – ``and`` (parallel let bindings)
* ``IF`` / ``THEN`` / ``ELSE``
* ``DATA``     – ``data``  (algebraic data type declarations)
* ``MATCH``    – ``match``
* ``WITH``     – ``with``
* ``ARROW``    – ``->``
* ``EQ``       – ``=``
* ``COMMA``    – ``,``
* ``LPAREN`` / ``RPAREN``
* ``LBRACK`` / ``RBRACK``  – ``[`` / ``]``  (list literals)
* ``EOF``
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


KEYWORDS = {
    "let": "LET",
    "rec": "REC",
    "in": "IN",
    "and": "AND",
    "if": "IF",
    "then": "THEN",
    "else": "ELSE",
    "true": "BOOL",
    "false": "BOOL",
    "data": "DATA",
    "match": "MATCH",
    "with": "WITH",
}

# Multi-char operators must be tried before single-char ones.
_OPERATORS = ["->", "==", "!=", "<=", ">=", "&&", "||", "+", "-", "*", "/", "<", ">"]


@dataclass
class Token:
    kind: str
    value: str
    pos: int

    def __repr__(self) -> str:  # pragma: no cover - debugging only
        return f"Token({self.kind!r}, {self.value!r}, pos={self.pos})"


class LexerError(Exception):
    """Raised on an invalid character during tokenisation."""


def _is_ident_start(c: str) -> bool:
    return c.isalpha() or c == "_"


def _is_ident_char(c: str) -> bool:
    return c.isalnum() or c in "_'"


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
        # comments: -- to end of line (only when not followed by >)
        #           # to end of line (Python/hash style)
        if c == "-" and i + 1 < n and source[i + 1] == "-":
            while i < n and source[i] != "\n":
                i += 1
            continue
        if c == "#":
            while i < n and source[i] != "\n":
                i += 1
            continue
        # string literals: "..."  with simple escape sequences
        if c == '"':
            j = i + 1
            chars: List[str] = []
            while j < n and source[j] != '"':
                if source[j] == "\\" and j + 1 < n:
                    esc = source[j + 1]
                    if esc == "n":
                        chars.append("\n")
                    elif esc == "t":
                        chars.append("\t")
                    elif esc == "r":
                        chars.append("\r")
                    elif esc == '"':
                        chars.append('"')
                    elif esc == "\\":
                        chars.append("\\")
                    elif esc == "0":
                        chars.append("\0")
                    else:
                        chars.append(esc)
                    j += 2
                else:
                    chars.append(source[j])
                    j += 1
            if j >= n:
                raise LexerError(f"Unterminated string literal starting at position {i}")
            tokens.append(Token("STRING", "".join(chars), i))
            i = j + 1
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
        # colon (type annotation)
        if c == ":":
            tokens.append(Token("COLON", c, i))
            i += 1
            continue
        # comma
        if c == ",":
            tokens.append(Token("COMMA", c, i))
            i += 1
            continue
        # operators — try longest match first.
        # This must come BEFORE the single-char checks for ``=`` and ``|``
        # so that multi-char operators like ``==``, ``!=``, ``&&``, ``||``
        # are matched as single OP tokens rather than being split.
        matched_op = None
        for op in _OPERATORS:
            if source.startswith(op, i):
                matched_op = op
                break
        if matched_op:
            # ARROW is its own token kind for clarity
            kind = "ARROW" if matched_op == "->" else "OP"
            tokens.append(Token(kind, matched_op, i))
            i += len(matched_op)
            continue
        # bar (case alternative separator) — must come AFTER operator
        # matching so that ``||`` is tokenised as a single OP, not two BARs.
        if c == "|":
            tokens.append(Token("BAR", c, i))
            i += 1
            continue
        # equals (used in let; not an operator here).
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
        # brackets (list literals)
        if c == "[":
            tokens.append(Token("LBRACK", c, i))
            i += 1
            continue
        if c == "]":
            tokens.append(Token("RBRACK", c, i))
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
        if _is_ident_start(c):
            j = i
            while j < n and _is_ident_char(source[j]):
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