r"""Recursive-descent parser for the mini lambda calculus.

Grammar (with precedence levels)::

    expr      := let | if | lambda | binop
    let       := 'let' ['rec'] IDENT '=' expr 'in' expr
    if        := 'if' expr 'then' expr 'else' expr
    lambda    := ('\' | 'λ') IDENT+ '.' expr
    binop     := cmp ( ('&&' | '||') cmp )*          # level 1 (lowest)
    cmp       := add ( ('==' | '!=' | '<' | '>' | '<=' | '>=') add )?   # non-assoc
    add       := mul ( ('+' | '-') mul )*            # left-assoc
    mul       := app ( ('*' | '/') app )*            # left-assoc
    unary     := '-' unary | app                     # prefix minus
    app       := atom (atom)*
    atom      := INT | BOOL | IDENT | '(' expr (',' expr)* ')'

Operator-precedence levels (highest binds tightest):

    1  &&  ||          (right-assoc)
    2  == != < > <= >= (non-assoc, chainable via desugaring to nested)
    3  +  -            (left-assoc)
    4  *  /            (left-assoc)
    5  application     (left-assoc)

Infix operators desugar to left-associative applications of a variable
named by the operator symbol, e.g. ``a + b``  ⟶  ``((+) a) b``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

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


@dataclass(frozen=True)
class ETuple:
    items: tuple  # of Expr


# ---------------------------------------------------------------------------
# Operator precedence tables
# ---------------------------------------------------------------------------

# (operators, associativity)  — listed lowest-precedence first
# associativity: 'left' | 'right' | 'non'
_PRECEDENCE = [
    ({"&&", "||"}, "right"),
    ({"==", "!=", "<", ">", "<=", ">="}, "left"),
    ({"+", "-"}, "left"),
    ({"*", "/"}, "left"),
]


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

    def _peek_op(self) -> Optional[str]:
        """If the current token is an OP, return its value; else None."""
        t = self._peek()
        if t.kind == "OP":
            return t.value
        return None

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
        return self._parse_binop(0)

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

    # -- operator precedence climbing ------------------------------------
    def _parse_binop(self, level: int) -> object:
        if level >= len(_PRECEDENCE):
            return self._parse_unary()
        ops, assoc = _PRECEDENCE[level]
        if assoc == "right":
            left = self._parse_binop(level + 1)
            op = self._peek_op()
            while op is not None and op in ops:
                self._advance()
                right = self._parse_binop(level)
                left = self._mk_app_op(op, left, right)
                op = self._peek_op()
            return left
        else:
            left = self._parse_binop(level + 1)
            op = self._peek_op()
            while op is not None and op in ops:
                self._advance()
                right = self._parse_binop(level + 1)
                left = self._mk_app_op(op, left, right)
                op = self._peek_op()
            return left

    @staticmethod
    def _mk_app_op(op: str, left: object, right: object) -> EApp:
        """Desugar ``left op right`` into ``((op) left) right``."""
        return EApp(EApp(EVar(op), left), right)

    def _parse_unary(self) -> object:
        """Parse a prefix unary operator (currently only ``-``).

        ``-x`` desugars to ``neg x`` (the built-in ``neg : Int -> Int``).
        Unary minus binds tighter than all binary operators but looser than
        application, so ``- f x`` parses as ``- (f x)`` and ``- - 5``
        parses as ``- (- 5)``.
        """
        op = self._peek_op()
        if op == "-":
            self._advance()
            inner = self._parse_unary()
            return EApp(EVar("neg"), inner)
        return self._parse_app()

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
            # could be () unit, (expr), (expr, expr, ...) tuple,
            # or (expr,) single-element tuple (trailing comma)
            if self._peek_kind() == "RPAREN":
                self._advance()
                return ETuple(())  # unit value
            first = self.parse_expr()
            if self._peek_kind() == "COMMA":
                items = [first]
                while self._peek_kind() == "COMMA":
                    self._advance()
                    # Allow trailing comma: (a, b, ) — stop if next is RPAREN
                    if self._peek_kind() == "RPAREN":
                        break
                    items.append(self.parse_expr())
                self._expect("RPAREN")
                return ETuple(tuple(items))
            self._expect("RPAREN")
            return first
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