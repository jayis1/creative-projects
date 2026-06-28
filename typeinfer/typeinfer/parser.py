"""Recursive-descent parser for the mini lambda calculus.

Grammar (roughly, precedence climbing for application)::

    expr   := let | if | lambda | app
    let    := 'let' ['rec'] IDENT '=' expr 'in' expr
    if     := 'if' expr 'then' expr 'else' expr
    lambda := ('\\' | 'λ') IDENT+ '.' expr     # multi-arg sugar
    app    := atom (atom)*
    atom   := INT | BOOL | IDENT | '(' expr ')'

The AST nodes are small frozen dataclasses defined below.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .lexer import tokenize, Token


# ---------------------------------------------------------------------------
# AST nodes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EInt:
    value: int


@dataclass(frozen=True)
class EBool:
    value: bool


@dataclass(frozen=True)
class EVar:
    name: str


@dataclass(frozen=True)
class ELam:
    param: str
    body: object  # Expr


@dataclass(frozen=True)
class EApp:
    fn: object    # Expr
    arg: object   # Expr


@dataclass(frozen=True)
class ELet:
    name: str
    value: object  # Expr
    body: object   # Expr
    is_rec: bool = False


@dataclass(frozen=True)
class EIf:
    cond: object
    then: object
    els: object


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class ParserError(Exception):
    """Raised on a syntax error."""


class _Parser:
    def __init__(self, tokens: List[Token]):
        self.toks = tokens
        self.i = 0

    # -- token helpers ----------------------------------------------------
    def _peek(self) -> Token:
        return self.toks[self.i]

    def _peek_kind(self) -> str:
        return self.toks[self.i].kind

    def _advance(self) -> Token:
        t = self.toks[self.i]
        self.i += 1
        return t

    def _expect(self, kind: str) -> Token:
        t = self._peek()
        if t.kind != kind:
            raise ParserError(
                f"Expected {kind} but got {t.kind} ({t.value!r}) at pos {t.pos}"
            )
        return self._advance()

    # -- productions ------------------------------------------------------
    def parse_expr(self) -> object:
        k = self._peek_kind()
        if k == "LET":
            return self._parse_let()
        if k == "IF":
            return self._parse_if()
        if k == "LAMBDA":
            return self._parse_lambda()
        return self._parse_app()

    def _parse_let(self) -> ELet:
        self._expect("LET")
        is_rec = False
        if self._peek_kind() == "REC":
            self._advance()
            is_rec = True
        name = self._expect("IDENT").value
        self._expect("EQ")
        value = self.parse_expr()
        self._expect("IN")
        body = self.parse_expr()
        return ELet(name, value, body, is_rec)

    def _parse_if(self) -> EIf:
        self._expect("IF")
        cond = self.parse_expr()
        self._expect("THEN")
        then = self.parse_expr()
        self._expect("ELSE")
        els = self.parse_expr()
        return EIf(cond, then, els)

    def _parse_lambda(self) -> object:
        self._expect("LAMBDA")
        # support multi-arg: \x y z. body  desugars to \x. \y. \z. body
        params: List[str] = []
        while self._peek_kind() == "IDENT":
            params.append(self._advance().value)
        if not params:
            t = self._peek()
            raise ParserError(
                f"Expected parameter name after \\ but got {t.kind} at pos {t.pos}"
            )
        self._expect("DOT")
        body = self.parse_expr()
        for p in reversed(params):
            body = ELam(p, body)
        return body

    def _parse_app(self) -> object:
        fn = self._parse_atom()
        while self._peek_kind() in ("INT", "BOOL", "IDENT", "LPAREN"):
            arg = self._parse_atom()
            fn = EApp(fn, arg)
        return fn

    def _parse_atom(self) -> object:
        t = self._peek()
        k = t.kind
        if k == "INT":
            self._advance()
            return EInt(int(t.value))
        if k == "BOOL":
            self._advance()
            return EBool(t.value == "true")
        if k == "IDENT":
            self._advance()
            return EVar(t.value)
        if k == "LPAREN":
            self._advance()
            e = self.parse_expr()
            self._expect("RPAREN")
            return e
        raise ParserError(
            f"Unexpected token {t.kind} ({t.value!r}) at pos {t.pos}"
        )


def parse(source: str) -> object:
    """Parse *source* into an AST.  Raises `ParserError` on syntax errors."""
    tokens = tokenize(source)
    p = _Parser(tokens)
    expr = p.parse_expr()
    if p._peek_kind() != "EOF":
        t = p._peek()
        raise ParserError(
            f"Trailing tokens after expression: {t.kind} ({t.value!r}) at pos {t.pos}"
        )
    return expr