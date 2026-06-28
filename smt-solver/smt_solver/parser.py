"""
SMT-LIB v2 subset parser (S-expressions → AST).

Supports:
  - declare-fun / declare-const
  - assert
  - check-sat / get-model
  - exit
  - let bindings
  - Boolean connectives: and, or, not, =>, =, xor, ite, distinct
  - Arithmetic: +, -, *, /, <, <=, >, >=
  - Uninterpreted function applications
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple, Dict, Any

from .ast import (
    Term, Var, App, BoolConst, NumConst, Sort,
    BOOL, REAL, INT,
    And, Or, Not, Implies, Iff, Eq, Lt, Le, Gt, Ge,
    Add, Sub, Mul, Neg, Ite,
)
from .exceptions import ParseError


# ---------------------------------------------------------------------------
# S-expression reader
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(
    r"""\s*(?:
          (?P<lparen>\()    |
          (?P<rparen>\))    |
          (?P<string>"(?:\\.|[^"\\])*") |
          (?P<comment>;[^\n]*) |
          (?P<symbol>[^\s()"]+)
        )""",
    re.VERBOSE,
)


def tokenize(text: str) -> List[str]:
    """Tokenize an SMT-LIB string into a flat token list."""
    tokens: List[str] = []
    pos = 0
    while pos < len(text):
        m = _TOKEN_RE.match(text, pos)
        if not m or m.end() == pos:
            # Skip whitespace if any remains
            if text[pos].isspace():
                pos += 1
                continue
            raise ParseError(f"Unexpected character at position {pos}: {text[pos]!r}")
        pos = m.end()
        if m.group("comment") is not None:
            continue
        if m.group("string") is not None:
            tokens.append(m.group("string"))
            continue
        if m.group("lparen") is not None:
            tokens.append("(")
            continue
        if m.group("rparen") is not None:
            tokens.append(")")
            continue
        if m.group("symbol") is not None:
            tokens.append(m.group("symbol"))
            continue
    return tokens


class SExpr:
    """A parsed S-expression: either a symbol (str) or a list of SExprs."""
    def __init__(self, kind: str, value=None, children=None):
        self.kind = kind  # 'symbol' or 'list'
        self.value = value  # str for symbol
        self.children = children or []  # list for list

    def __repr__(self):
        if self.kind == "symbol":
            return self.value
        return "(" + " ".join(repr(c) for c in self.children) + ")"


def parse_sexprs(tokens: List[str]) -> List[SExpr]:
    """Parse a flat token list into a list of top-level S-expressions."""
    result: List[SExpr] = []
    idx = 0

    def parse_one(i: int) -> Tuple[SExpr, int]:
        if i >= len(tokens):
            raise ParseError("Unexpected end of input")
        tok = tokens[i]
        if tok == "(":
            children: List[SExpr] = []
            i += 1
            while i < len(tokens) and tokens[i] != ")":
                child, i = parse_one(i)
                children.append(child)
            if i >= len(tokens):
                raise ParseError("Unmatched '('")
            i += 1  # skip ')'
            return SExpr("list", children=children), i
        elif tok == ")":
            raise ParseError("Unexpected ')'")
        else:
            return SExpr("symbol", value=tok), i + 1

    while idx < len(tokens):
        expr, idx = parse_one(idx)
        result.append(expr)
    return result


# ---------------------------------------------------------------------------
# Sort parser
# ---------------------------------------------------------------------------

_SORT_MAP = {
    "Bool": BOOL,
    "Real": REAL,
    "Int": INT,
}


def parse_sort(sexpr: SExpr) -> Sort:
    if sexpr.kind == "symbol":
        if sexpr.value in _SORT_MAP:
            return _SORT_MAP[sexpr.value]
        return Sort(sexpr.value)
    # list form: (Array Index Elem) etc — for now just handle simple
    if sexpr.children:
        name = sexpr.children[0].value if sexpr.children[0].kind == "symbol" else ""
        args = tuple(parse_sort(c) for c in sexpr.children[1:])
        return Sort(name, args)
    raise ParseError("Empty sort expression")


# ---------------------------------------------------------------------------
# AST builder
# ---------------------------------------------------------------------------

class _LetContext:
    """Tracks let-bound variables and declared sorts."""
    def __init__(self, parent=None):
        self.parent = parent
        self.bindings: Dict[str, Term] = {}

    def lookup(self, name: str) -> Optional[Term]:
        if name in self.bindings:
            return self.bindings[name]
        if self.parent:
            return self.parent.lookup(name)
        return None


class Parser:
    """Parses SMT-LIB command and term S-expressions into AST nodes."""

    # Symbols that are Boolean connectives
    _BOOL_OPS = {
        "and", "or", "not", "=>", "xor", "=", "distinct", "ite",
    }
    # Symbols that produce numeric values
    _ARITH_OPS = {"+", "-", "*", "/"}

    def __init__(self):
        self.declarations: Dict[str, Tuple[Sort, Tuple[Sort, ...]]] = {}
        # name -> (return_sort, arg_sorts)
        self.let_stack: List[_LetContext] = [_LetContext()]

    @property
    def let_ctx(self) -> _LetContext:
        return self.let_stack[-1]

    def declare_const(self, name: str, sort: Sort) -> Var:
        """Declare a constant (0-arity function = variable)."""
        self.declarations[name] = (sort, ())
        return Var(name, sort)

    def declare_fun(self, name: str, arg_sorts: Tuple[Sort, ...], ret_sort: Sort):
        """Declare an uninterpreted function symbol."""
        self.declarations[name] = (ret_sort, arg_sorts)

    def lookup_sort(self, name: str) -> Optional[Sort]:
        info = self.declarations.get(name)
        if info:
            return info[0]
        return None

    # ------------------------------------------------------------------
    # Term parsing
    # ------------------------------------------------------------------

    def parse_term(self, sexpr: SExpr) -> Term:
        if sexpr.kind == "symbol":
            return self._parse_symbol(sexpr.value)

        # list form
        children = sexpr.children
        if not children:
            raise ParseError("Empty term ()")

        head = children[0]
        if head.kind != "symbol":
            # Could be (let ...) or indexed identifier — but we only support simple
            raise ParseError(f"Expected symbol at head of term, got {head!r}")

        sym = head.value
        rest = children[1:]

        # Handle let
        if sym == "let":
            return self._parse_let(rest)

        # Handle quantifiers (not fully supported — treat as opaque)
        if sym in ("forall", "exists"):
            raise ParseError("Quantifiers not supported in this subset")

        # Boolean connectives
        if sym == "and":
            return And(*[self.parse_term(c) for c in rest])
        if sym == "or":
            return Or(*[self.parse_term(c) for c in rest])
        if sym == "not":
            if len(rest) != 1:
                raise ParseError("not expects 1 argument")
            return Not(self.parse_term(rest[0]))
        if sym == "=>":
            if len(rest) != 2:
                raise ParseError("=> expects 2 arguments")
            return Implies(self.parse_term(rest[0]), self.parse_term(rest[1]))
        if sym == "xor":
            if len(rest) < 2:
                raise ParseError("xor expects >= 2 arguments")
            terms = [self.parse_term(c) for c in rest]
            result = terms[0]
            for t in terms[1:]:
                result = App("xor", (result, t), BOOL)
            return result
        if sym == "=":
            if len(rest) == 2:
                return Eq(self.parse_term(rest[0]), self.parse_term(rest[1]))
            # Chain equalities: (= a b c) => (and (= a b) (= b c) ...)
            terms = [self.parse_term(c) for c in rest]
            parts = []
            for i in range(len(terms) - 1):
                parts.append(Eq(terms[i], terms[i + 1]))
            return And(*parts)
        if sym == "distinct":
            terms = [self.parse_term(c) for c in rest]
            parts = []
            for i in range(len(terms)):
                for j in range(i + 1, len(terms)):
                    parts.append(Not(Eq(terms[i], terms[j])))
            return And(*parts)
        if sym == "ite":
            if len(rest) != 3:
                raise ParseError("ite expects 3 arguments")
            cond = self.parse_term(rest[0])
            then_t = self.parse_term(rest[1])
            else_t = self.parse_term(rest[2])
            return Ite(cond, then_t, else_t)

        # Arithmetic
        if sym == "+":
            return Add(*[self.parse_term(c) for c in rest])
        if sym == "-":
            if len(rest) == 1:
                return Neg(self.parse_term(rest[0]))
            if len(rest) == 2:
                return Sub(self.parse_term(rest[0]), self.parse_term(rest[1]))
            # n-ary subtraction: a - b - c ...
            result = self.parse_term(rest[0])
            for c in rest[1:]:
                result = Sub(result, self.parse_term(c))
            return result
        if sym == "*":
            return Mul(*[self.parse_term(c) for c in rest])
        if sym == "/":
            if len(rest) != 2:
                raise ParseError("/ expects 2 arguments")
            return App("/", (self.parse_term(rest[0]), self.parse_term(rest[1])), REAL)
        if sym == "<":
            if len(rest) == 2:
                return Lt(self.parse_term(rest[0]), self.parse_term(rest[1]))
            terms = [self.parse_term(c) for c in rest]
            return And(*[Le(terms[i], terms[i + 1]) for i in range(len(terms) - 1)])
        if sym == "<=":
            if len(rest) == 2:
                return Le(self.parse_term(rest[0]), self.parse_term(rest[1]))
            terms = [self.parse_term(c) for c in rest]
            return And(*[Le(terms[i], terms[i + 1]) for i in range(len(terms) - 1)])
        if sym == ">":
            if len(rest) == 2:
                return Gt(self.parse_term(rest[0]), self.parse_term(rest[1]))
            terms = [self.parse_term(c) for c in rest]
            return And(*[Ge(terms[i], terms[i + 1]) for i in range(len(terms) - 1)])
        if sym == ">=":
            if len(rest) == 2:
                return Ge(self.parse_term(rest[0]), self.parse_term(rest[1]))
            terms = [self.parse_term(c) for c in rest]
            return And(*[Ge(terms[i], terms[i + 1]) for i in range(len(terms) - 1)])

        # Uninterpreted function application
        decl = self.declarations.get(sym)
        if decl is None:
            raise ParseError(f"Undeclared symbol: {sym}")
        ret_sort, arg_sorts = decl
        args = tuple(self.parse_term(c) for c in rest)
        if len(args) != len(arg_sorts):
            raise ParseError(
                f"{sym} expects {len(arg_sorts)} args, got {len(args)}"
            )
        return App(sym, args, ret_sort)

    def _parse_symbol(self, value: str) -> Term:
        # Boolean literals
        if value == "true":
            return BoolConst(True)
        if value == "false":
            return BoolConst(False)

        # let-bound variable?
        let_val = self.let_ctx.lookup(value)
        if let_val is not None:
            return let_val

        # Numeric literal
        num = _try_parse_number(value)
        if num is not None:
            return num

        # Declared constant (0-arity function)
        decl = self.declarations.get(value)
        if decl is not None:
            ret_sort, arg_sorts = decl
            if arg_sorts == ():
                return Var(value, ret_sort)

        raise ParseError(f"Undeclared symbol: {value}")

    def _parse_let(self, rest: List[SExpr]) -> Term:
        if len(rest) != 2:
            raise ParseError("let expects 2 parts: bindings and body")
        bindings_sexpr = rest[0]
        body_sexpr = rest[1]

        if bindings_sexpr.kind != "list":
            raise ParseError("let bindings must be a list")

        new_ctx = _LetContext(self.let_ctx)
        self.let_stack.append(new_ctx)
        try:
            for binding in bindings_sexpr.children:
                if binding.kind != "list" or len(binding.children) != 2:
                    raise ParseError(f"Invalid let binding: {binding!r}")
                name = binding.children[0]
                if name.kind != "symbol":
                    raise ParseError("let binding name must be a symbol")
                val_sexpr = binding.children[1]
                # Evaluate in parent context (standard let semantics)
                val = self.parse_term_with_context(val_sexpr, new_ctx.parent)
                new_ctx.bindings[name.value] = val
            return self.parse_term(body_sexpr)
        finally:
            self.let_stack.pop()

    def parse_term_with_context(self, sexpr: SExpr, ctx: _LetContext) -> Term:
        """Parse a term using a specific let-context (for let bindings)."""
        self.let_stack.append(ctx)
        try:
            return self.parse_term(sexpr)
        finally:
            self.let_stack.pop()

    # ------------------------------------------------------------------
    # Command parsing
    # ------------------------------------------------------------------

    def parse_command(self, sexpr: SExpr) -> dict:
        """Parse a top-level SMT-LIB command into a dict."""
        if sexpr.kind != "list" or not sexpr.children:
            raise ParseError("Expected a command list")

        cmd = sexpr.children[0]
        if cmd.kind != "symbol":
            raise ParseError("Command name must be a symbol")

        name = cmd.value
        args = sexpr.children[1:]

        if name == "declare-const":
            if len(args) != 2:
                raise ParseError("declare-const expects name and sort")
            var_name = args[0].value
            sort = parse_sort(args[1])
            self.declare_const(var_name, sort)
            return {"cmd": "declare-const", "name": var_name, "sort": sort}

        if name == "declare-fun":
            if len(args) != 3:
                raise ParseError("declare-fun expects name, arg sorts, return sort")
            fun_name = args[0].value
            if args[1].kind != "list":
                raise ParseError("declare-fun arg sorts must be a list")
            arg_sorts = tuple(parse_sort(c) for c in args[1].children)
            ret_sort = parse_sort(args[2])
            self.declare_fun(fun_name, arg_sorts, ret_sort)
            return {
                "cmd": "declare-fun", "name": fun_name,
                "arg_sorts": arg_sorts, "ret_sort": ret_sort,
            }

        if name == "assert":
            if len(args) != 1:
                raise ParseError("assert expects 1 argument")
            term = self.parse_term(args[0])
            return {"cmd": "assert", "term": term}

        if name == "check-sat":
            return {"cmd": "check-sat"}

        if name == "get-model":
            return {"cmd": "get-model"}

        if name == "exit":
            return {"cmd": "exit"}

        if name == "set-logic":
            if len(args) != 1:
                raise ParseError("set-logic expects 1 argument")
            return {"cmd": "set-logic", "logic": args[0].value}

        if name == "set-info":
            return {"cmd": "set-info", "args": args}

        if name == "push":
            return {"cmd": "push"}

        if name == "pop":
            return {"cmd": "pop"}

        if name == "reset":
            return {"cmd": "reset"}

        # Unknown command — skip gracefully
        return {"cmd": "unknown", "name": name}


def _try_parse_number(value: str) -> Optional[NumConst]:
    """Try to parse a numeric literal.  Returns NumConst or None."""
    # Integer
    try:
        ival = int(value)
        return NumConst(float(ival), is_int=True)
    except ValueError:
        pass

    # Float
    try:
        fval = float(value)
        # Determine if it looks like an integer literal vs real
        # SMT-LIB: 5 is Int, 5.0 is Real — but we treat all as Real by default
        is_int = "." not in value and "e" not in value.lower()
        if is_int:
            return NumConst(float(int(fval)), is_int=True)
        return NumConst(fval, is_int=False)
    except ValueError:
        pass

    # SMT-LIB decimal: could be fraction like 5/3 in some contexts
    # We handle simple fractions
    if "/" in value:
        parts = value.split("/")
        if len(parts) == 2:
            try:
                num = float(parts[0])
                den = float(parts[1])
                if den != 0:
                    return NumConst(num / den, is_int=False)
            except ValueError:
                pass

    return None


# ---------------------------------------------------------------------------
# High-level convenience
# ---------------------------------------------------------------------------

def parse_script(text: str) -> Tuple[Parser, List[dict]]:
    """Parse a full SMT-LIB script, returning the parser and commands."""
    tokens = tokenize(text)
    sexprs = parse_sexprs(tokens)
    parser = Parser()
    commands = [parser.parse_command(s) for s in sexprs]
    return parser, commands