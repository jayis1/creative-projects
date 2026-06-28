"""Recursive-descent parser for the mini lambda calculus.

Grammar (with precedence levels)::

    program   := stmt (NEWLINE stmt)*
    stmt      := data_decl | expr
    data_decl := 'data' TypeCon Constr* 'in' expr
    expr      := let | if | lambda | match | binop
    let       := 'let' ['rec'] binding ('and' binding)* 'in' expr
    binding   := IDENT [':' type] '=' expr
    if        := 'if' expr 'then' expr 'else' expr
    match     := 'match' expr 'with' ('|' alt)+ 
    alt       := pattern '->' expr
    pattern   := IDENT | CONSTR pattern* | '(' pattern (',' pattern)* ')' | INT | '_' 
    lambda    := ('\\' | 'λ') IDENT+ '.' expr
    binop     := cmp ( ('&&' | '||') cmp )*          # level 1 (lowest)
    cmp       := add ( ('==' | '!=' | '<' | '>' | '<=' | '>=') add )*  # left-assoc
    add       := mul ( ('+' | '-') mul )*            # left-assoc
    mul       := unary ( ('*' | '/') unary )*        # left-assoc
    unary     := '-' unary | app                     # prefix minus
    app       := atom (atom)*
    atom      := INT | STRING | BOOL | IDENT
               | '(' expr (',' expr)* ')'
               | '[' [expr (',' expr)*] ']'           # list literal
    type      := 'Int' | 'Bool' | 'String' | 'Unit'
               | TypeCon ('<' type (',' type)* '>')?
               | type '->' type
               | '(' type ')'

Operator-precedence levels (highest binds tightest):

    1  &&  ||          (right-assoc)
    2  == != < > <= >= (left-assoc)
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
class EString:
    value: str


@dataclass(frozen=True)
class EVar:
    name: str


@dataclass(frozen=True)
class ELam:
    param: str
    body: object  # Expr
    # Optional type annotation for the parameter.
    param_type: Optional[object] = None  # Type or None


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
    # Optional type annotation for the bound variable.
    var_type: Optional[object] = None  # Type or None


@dataclass(frozen=True)
class ELetMulti:
    """Parallel let bindings: let x = e1 and y = e2 in body."""
    bindings: tuple  # of (name, value, var_type)
    body: object  # Expr


@dataclass(frozen=True)
class EIf:
    cond: object
    then: object
    els: object


@dataclass(frozen=True)
class ETuple:
    items: tuple  # of Expr


@dataclass(frozen=True)
class EList:
    """List literal: [e1, e2, ...]"""
    items: tuple  # of Expr


@dataclass(frozen=True)
class EMatch:
    """Match expression: match expr with | pattern -> result ..."""
    scrutinee: object  # Expr
    alts: tuple  # of (Pattern, Expr)


# Pattern nodes for match expressions
@dataclass(frozen=True)
class PVar:
    name: str


@dataclass(frozen=True)
class PConstr:
    """Constructor pattern: Constr pat1 pat2 ..."""
    name: str
    args: tuple  # of Pattern


@dataclass(frozen=True)
class PInt:
    value: int


@dataclass(frozen=True)
class PString:
    value: str


@dataclass(frozen=True)
class PWild:
    """Wildcard pattern: _"""


@dataclass(frozen=True)
class PTuple:
    """Tuple pattern: (p1, p2, ...)"""
    items: tuple  # of Pattern


# Data type declaration (carried as AST but only meaningful in top-level)
@dataclass(frozen=True)
class EDataDecl:
    """data TypeName<a, b> = Constr1 ... | Constr2 ... in body"""
    type_name: str
    type_params: tuple  # of str
    constructors: tuple  # of (name, [arg_types] or None for inferred)
    body: object  # Expr


# ---------------------------------------------------------------------------
# Type-AST nodes (parsed types, resolved to types.Type structures)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TAnnNamed:
    """A named type like ``Int``, ``Bool``, or ``List<Int>``."""
    name: str
    args: tuple  # of TAnn


@dataclass(frozen=True)
class TAnnArrow:
    """Function type ``a -> b``."""
    param: object  # TAnn
    ret: object    # TAnn


@dataclass(frozen=True)
class TAnnVar:
    """A type variable name (used in data declarations)."""
    name: str


@dataclass(frozen=True)
class TAnnTuple:
    """Tuple type ``(a, b)``."""
    items: tuple  # of TAnn


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

    # -- top-level / statement -------------------------------------------
    def parse_program(self) -> object:
        """Parse a program, which may start with data declarations."""
        # Check for 'data' keyword
        if self._peek_kind() == "DATA":
            return self._parse_data_decl()
        return self.parse_expr()

    def _parse_data_decl(self):
        self._expect("DATA")
        # Parse type name with optional parameters: List<a, b>
        type_name = self._expect("IDENT").value
        type_params: List[str] = []
        # Optional type parameters (lowercase identifiers)
        while self._peek_kind() == "IDENT":
            name = self._advance().value
            # Only treat as type param if lowercase
            if name[0].islower() or name[0] == "_":
                type_params.append(name)
            else:
                # Not a type param — we need to re-process
                # This is a constructor name
                # Actually for data decl, we expect constructors after
                # Hmm, this is tricky. Let's use a different approach.
                # The data syntax is: data Name vars = Constr1 args | Constr2 args in body
                # But we can't easily distinguish. Let's require constructors start with uppercase.
                break

        self._expect("EQ")

        # Parse constructors separated by |
        constructors: List[Tuple[str, Optional[List[object]]]] = []
        # First constructor (no leading |)
        if self._peek_kind() == "BAR":
            self._advance()
        constructors.append(self._parse_constructor())

        while self._peek_kind() == "BAR":
            self._advance()
            constructors.append(self._parse_constructor())

        self._expect("IN")
        body = self.parse_expr()
        return EDataDecl(type_name, tuple(type_params), tuple(constructors), body)

    def _parse_constructor(self) -> Tuple[str, Optional[List[object]]]:
        """Parse a constructor: Name [arg_types]

        Type arguments are parsed until we hit ``|`` (next constructor),
        ``in`` (body), or any non-type token.
        """
        name = self._expect("IDENT").value
        arg_types: List[object] = []
        # Parse type arguments until we hit | or in or EOF
        while self._peek_kind() == "IDENT":
            arg_types.append(self._parse_type_atom())
            # Check for arrow in the type
            if self._peek_kind() == "ARROW":
                self._advance()
                arg_types.append(self._parse_type())

        return (name, arg_types if arg_types else None)

    # -- type parsing -----------------------------------------------------
    def _parse_type(self) -> object:
        """Parse a type annotation."""
        # arrow is right-associative
        left = self._parse_type_atom()
        if self._peek_kind() == "ARROW":
            self._advance()
            right = self._parse_type()
            return TAnnArrow(left, right)
        return left

    def _parse_type_atom(self) -> object:
        t = self._peek()
        if t.kind == "IDENT":
            self._advance()
            # Type variable (lowercase)
            if t.value[0].islower() or t.value[0] == "_":
                return TAnnVar(t.value)
            # Named type with optional args
            args: List[object] = []
            # Check for < ... > generics
            if self._peek_kind() == "OP" and self._peek().value == "<":
                self._advance()  # consume <
                args.append(self._parse_type())
                while self._peek_kind() == "COMMA":
                    self._advance()
                    args.append(self._parse_type())
                # expect > (tokenized as OP ">")
                if self._peek_kind() == "OP" and self._peek().value == ">":
                    self._advance()
                else:
                    raise ParserError(
                        f"Expected '>' in type args at pos {self._peek().pos}"
                    )
            return TAnnNamed(t.value, tuple(args))
        if t.kind == "LPAREN":
            self._advance()
            # could be (type) or (type, type, ...) tuple
            first = self._parse_type()
            if self._peek_kind() == "COMMA":
                items = [first]
                while self._peek_kind() == "COMMA":
                    self._advance()
                    items.append(self._parse_type())
                self._expect("RPAREN")
                return TAnnTuple(tuple(items))
            self._expect("RPAREN")
            return first
        if t.kind == "INT":
            self._advance()
            return TAnnNamed(t.value, ())
        raise ParserError(
            f"Expected type but got {t.kind} ({t.value!r}) at pos {t.pos}"
        )

    # -- productions ------------------------------------------------------
    def parse_expr(self) -> object:
        k = self._peek_kind()
        if k == "LET":
            return self._parse_let()
        if k == "IF":
            return self._parse_if()
        if k == "LAMBDA":
            return self._parse_lambda()
        if k == "MATCH":
            return self._parse_match()
        return self._parse_binop(0)

    def _parse_let(self) -> object:
        self._expect("LET")
        is_rec = False
        if self._peek_kind() == "REC":
            self._advance()
            is_rec = True

        # Parse first binding: name [: type] = expr
        bindings = [self._parse_binding(is_rec)]

        # Parallel let: and binding ...
        while self._peek_kind() == "AND":
            self._advance()
            bindings.append(self._parse_binding(is_rec))

        self._expect("IN")
        body = self.parse_expr()

        if len(bindings) == 1:
            name, value, var_type = bindings[0]
            return ELet(name, value, body, is_rec, var_type)
        return ELetMulti(tuple(bindings), body)

    def _parse_binding(self, is_rec: bool):
        name = self._expect("IDENT").value
        var_type = None
        if self._peek_kind() == "COLON":
            self._advance()
            var_type = self._parse_type()
        self._expect("EQ")
        value = self.parse_expr()
        return (name, value, var_type)

    def _parse_if(self) -> EIf:
        self._expect("IF")
        cond = self.parse_expr()
        self._expect("THEN")
        then = self.parse_expr()
        self._expect("ELSE")
        els = self.parse_expr()
        return EIf(cond, then, els)

    def _parse_match(self) -> EMatch:
        self._expect("MATCH")
        scrutinee = self.parse_expr()
        self._expect("WITH")
        alts: List[Tuple[object, object]] = []
        # Optional leading |
        if self._peek_kind() == "BAR":
            self._advance()
        alts.append(self._parse_alt())
        while self._peek_kind() == "BAR":
            self._advance()
            alts.append(self._parse_alt())
        if not alts:
            raise ParserError("match requires at least one alternative")
        return EMatch(scrutinee, tuple(alts))

    def _parse_alt(self) -> Tuple[object, object]:
        pat = self._parse_pattern()
        self._expect("ARROW")
        body = self.parse_expr()
        return (pat, body)

    def _parse_pattern(self) -> object:
        t = self._peek()
        if t.kind == "IDENT":
            self._advance()
            if t.value == "_":
                return PWild()
            # Uppercase = constructor, lowercase = variable
            if t.value[0].isupper():
                # Constructor pattern: Name pat1 pat2 ...
                args: List[object] = []
                while self._peek_kind() in ("IDENT", "INT", "STRING", "LPAREN", "LBRACK"):
                    args.append(self._parse_pattern_atom())
                return PConstr(t.value, tuple(args))
            return PVar(t.value)
        return self._parse_pattern_atom()

    def _parse_pattern_atom(self) -> object:
        t = self._peek()
        if t.kind == "INT":
            self._advance()
            return PInt(int(t.value))
        if t.kind == "STRING":
            self._advance()
            return PString(t.value)
        if t.kind == "IDENT":
            self._advance()
            if t.value == "_":
                return PWild()
            if t.value[0].isupper():
                args: List[object] = []
                while self._peek_kind() in ("IDENT", "INT", "STRING", "LPAREN", "LBRACK"):
                    args.append(self._parse_pattern_atom())
                return PConstr(t.value, tuple(args))
            return PVar(t.value)
        if t.kind == "LPAREN":
            self._advance()
            if self._peek_kind() == "RPAREN":
                self._advance()
                return PTuple(())
            first = self._parse_pattern()
            if self._peek_kind() == "COMMA":
                items = [first]
                while self._peek_kind() == "COMMA":
                    self._advance()
                    if self._peek_kind() == "RPAREN":
                        break
                    items.append(self._parse_pattern())
                self._expect("RPAREN")
                return PTuple(tuple(items))
            self._expect("RPAREN")
            return first
        raise ParserError(
            f"Unexpected token in pattern: {t.kind} ({t.value!r}) at pos {t.pos}"
        )

    def _parse_lambda(self) -> object:
        self._expect("LAMBDA")
        # support multi-arg: \x y z. body  desugars to \x. \y. \z. body
        params: List[Tuple[str, Optional[object]]] = []
        while self._peek_kind() == "IDENT":
            pname = self._advance().value
            ptype = None
            if self._peek_kind() == "COLON":
                self._advance()
                ptype = self._parse_type()
            params.append((pname, ptype))
        if not params:
            t = self._peek()
            raise ParserError(
                f"Expected parameter name after \\ but got {t.kind} at pos {t.pos}"
            )
        self._expect("DOT")
        body = self.parse_expr()
        for p, pt in reversed(params):
            body = ELam(p, body, pt)
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
        while self._peek_kind() in (
            "INT", "BOOL", "STRING", "IDENT", "LPAREN", "LBRACK"
        ):
            arg = self._parse_atom()
            fn = EApp(fn, arg)
        return fn

    def _parse_atom(self) -> object:
        t = self._peek()
        k = t.kind
        if k == "INT":
            self._advance()
            return EInt(int(t.value))
        if k == "STRING":
            self._advance()
            return EString(t.value)
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
        if k == "LBRACK":
            # List literal: [e1, e2, ...] or []
            self._advance()
            items: List[object] = []
            if self._peek_kind() == "RBRACK":
                self._advance()
                return EList(())
            items.append(self.parse_expr())
            while self._peek_kind() == "COMMA":
                self._advance()
                if self._peek_kind() == "RBRACK":
                    break
                items.append(self.parse_expr())
            self._expect("RBRACK")
            return EList(tuple(items))
        raise ParserError(
            f"Unexpected token {t.kind} ({t.value!r}) at pos {t.pos}"
        )


def parse(source: str) -> object:
    """Parse *source* into an AST.  Raises `ParserError` on syntax errors."""
    tokens = tokenize(source)
    p = _Parser(tokens)
    expr = p.parse_program()
    if p._peek_kind() != "EOF":
        t = p._peek()
        raise ParserError(
            f"Trailing tokens after expression: {t.kind} ({t.value!r}) at pos {t.pos}"
        )
    return expr