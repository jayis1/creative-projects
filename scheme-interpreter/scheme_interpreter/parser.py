"""Parser for Scheme.

Converts a token stream from the lexer into nested Scheme data (s-expressions).
The parser is a simple recursive-descent parser.  Quasiquote forms are expanded
into ``cons``, ``list``, and ``append`` calls at parse time.
"""

from __future__ import annotations

from fractions import Fraction
from typing import List, Optional

from .lexer import Token, tokenize
from .types import Symbol, Pair, Nil, Bool, Char, Vector, Unspecified, EOF


class ParseError(Exception):
    """Raised on syntax errors."""

    def __init__(self, message: str, token: Optional[Token] = None):
        if token:
            super().__init__(f"ParseError at line {token.line}, col {token.col}: {message}")
        else:
            super().__init__(f"ParseError: {message}")


class Parser:
    """Parses tokens into Scheme data."""

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def _peek(self) -> Token:
        return self.tokens[self.pos]

    def _next(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _expect(self, ttype: str) -> Token:
        tok = self._peek()
        if tok.type != ttype:
            raise ParseError(f"expected {ttype}, got {tok.type}", tok)
        return self._next()

    # ------------------------------------------------------------------

    def parse_all(self) -> list:
        """Parse all top-level forms and return them as a list."""
        forms = []
        while self._peek().type != "EOF":
            forms.append(self.parse_datum())
        return forms

    def parse_datum(self):
        """Parse a single datum."""
        tok = self._peek()
        t = tok.type
        if t == "LPAREN" or t == "LBRACKET":
            return self._parse_list()
        elif t == "VECTOR_PAREN":
            return self._parse_vector()
        elif t == "QUOTE":
            self._next()
            return Pair(Symbol("quote"), Pair(self.parse_datum(), Nil))
        elif t == "QUASIQUOTE":
            self._next()
            return self._expand_quasiquote(self.parse_datum(), 1)
        elif t == "UNQUOTE":
            self._next()
            return Pair(Symbol("unquote"), Pair(self.parse_datum(), Nil))
        elif t == "UNQUOTE_SPLICING":
            self._next()
            return Pair(Symbol("unquote-splicing"), Pair(self.parse_datum(), Nil))
        elif t == "DATUM_COMMENT":
            self._next()
            self.parse_datum()  # discard next datum
            return self.parse_datum()
        elif t == "INT":
            self._next()
            return tok.value
        elif t == "FLOAT":
            self._next()
            return tok.value
        elif t == "RATIONAL":
            self._next()
            return tok.value
        elif t == "STRING":
            self._next()
            return tok.value
        elif t == "BOOLEAN":
            self._next()
            return Bool(tok.value)
        elif t == "CHAR":
            self._next()
            return Char(tok.value)
        elif t == "SYMBOL":
            self._next()
            return Symbol(tok.value)
        elif t == "RPAREN" or t == "RBRACKET":
            raise ParseError("unexpected closing delimiter", tok)
        elif t == "EOF":
            raise ParseError("unexpected end of input", tok)
        else:
            raise ParseError(f"unexpected token type {t}", tok)

    def _parse_list(self):
        open_tok = self._next()  # consume ( or [
        items = []
        tail = Nil
        while True:
            tok = self._peek()
            if tok.type in ("RPAREN", "RBRACKET"):
                self._next()
                break
            if tok.type == "EOF":
                raise ParseError("unexpected end of input inside list", tok)
            if tok.type == "SYMBOL" and tok.value == ".":
                self._next()
                tail = self.parse_datum()
                close = self._peek()
                if close.type not in ("RPAREN", "RBRACKET"):
                    raise ParseError("expected ) after dotted tail", close)
                self._next()
                break
            if tok.type == "DATUM_COMMENT":
                self._next()
                self.parse_datum()
                continue
            items.append(self.parse_datum())
        # Build the pair chain
        result = tail
        for item in reversed(items):
            result = Pair(item, result)
        return result

    def _parse_vector(self):
        self._next()  # consume #(
        items = []
        while True:
            tok = self._peek()
            if tok.type == "RPAREN":
                self._next()
                break
            if tok.type == "EOF":
                raise ParseError("unexpected end of input inside vector", tok)
            items.append(self.parse_datum())
        return Vector(items)

    # ------------------------------------------------------------------
    # quasiquote expansion

    def _expand_quasiquote(self, datum, depth: int):
        from .types import Pair, Nil, Symbol
        if not isinstance(datum, Pair):
            return Pair(Symbol("quote"), Pair(datum, Nil))
        head = datum.car
        if isinstance(head, Symbol):
            if head.name == "unquote":
                if depth == 1:
                    return datum.cdr.car  # the unquoted form
                else:
                    return Pair(Symbol("list"),
                               Pair(Pair(Symbol("unquote"), Pair(self._expand_quasiquote(datum.cdr.car, depth - 1), Nil)), Nil))
            elif head.name == "quasiquote":
                return Pair(Symbol("list"),
                            Pair(Pair(Symbol("quasiquote"),
                                      Pair(self._expand_quasiquote(datum.cdr.car, depth + 1), Nil)), Nil))
        # Check for unquote-splicing
        if isinstance(head, Pair) and isinstance(head.car, Symbol) and head.car.name == "unquote-splicing":
            if depth == 1:
                return Pair(Symbol("append"),
                           Pair(head.cdr.car,
                                Pair(self._expand_quasiquote_list(datum.cdr, depth), Nil)))
            else:
                return Pair(Symbol("list"),
                           Pair(Pair(Symbol("unquote-splicing"),
                                     Pair(self._expand_quasiquote(head.cdr.car, depth - 1), Nil)),
                                Pair(self._expand_quasiquote_list(datum.cdr, depth), Nil)))
        return Pair(Symbol("cons"),
                    Pair(self._expand_quasiquote(head, depth),
                         Pair(self._expand_quasiquote_list(datum.cdr, depth), Nil)))

    def _expand_quasiquote_list(self, datum, depth: int):
        from .types import Nil
        if datum is Nil:
            return Pair(Symbol("quote"), Pair(Nil, Nil))
        return self._expand_quasiquote(datum, depth)


def parse(source: str) -> list:
    """Tokenize and parse Scheme source, returning a list of top-level forms."""
    tokens = tokenize(source)
    # Add EOF sentinel
    from .lexer import Token as T
    tokens.append(T("EOF", None, 0, 0))
    return Parser(tokens).parse_all()