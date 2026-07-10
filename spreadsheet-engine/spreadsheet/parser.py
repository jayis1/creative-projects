"""
Recursive-descent formula parser and AST for spreadsheet formulas.

Grammar (simplified)
    expr     := term (('+' | '-') term)*
    term     := factor (('*' | '/') factor)*
    factor   := power ('^' power)*
    power    := unary
    unary    := ('+' | '-') unary | primary
    primary  := number | string | bool | '(' expr ')' | func '(' args ')' | ref | range
    ref      := [SheetName '!'] A1
    range    := ref ':' ref
    func     := IDENT

Tokens: NUMBER, STRING, IDENT, PLUS, MINUS, STAR, SLASH, CARET, LPAREN,
           RPAREN, COMMA, COLON, BANG
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------

TOKEN_RE = re.compile(
    r"""
    (?P<NUMBER>      \d+\.?\d*([eE][+-]?\d+)? | \.\d+([eE][+-]?\d+)?  )
  | (?P<STRING>      "(?:[^"\\]|\\.)*" )
  | (?P<REF>         \$?[A-Za-z]+\$?\d+ )
  | (?P<BOOL>         TRUE|FALSE|true|false )
  | (?P<IDENT>       [A-Za-z_][A-Za-z_0-9.]* )
  | (?P<GE>          >= )
  | (?P<LE>          <= )
  | (?P<NE>          <> )
  | (?P<GT>          > )
  | (?P<LT>          < )
  | (?P<EQ>          = )
  | (?P<AMP>         & )
  | (?P<PLUS>        \+ )
  | (?P<MINUS>       \- )
  | (?P<STAR>        \* )
  | (?P<SLASH>       / )
  | (?P<CARET>       \^ )
  | (?P<LPAREN>      \( )
  | (?P<RPAREN>      \) )
  | (?P<COMMA>       , )
  | (?P<COLON>       : )
  | (?P<BANG>        ! )
  | (?P<WS>          \s+ )
    """,
    re.VERBOSE,
)


@dataclass
class Token:
    type: str
    value: str
    pos: int

    def __repr__(self) -> str:
        return f"Token({self.type}, {self.value!r})"


def tokenize(text: str) -> List[Token]:
    """Tokenize a formula string (without leading '=')."""
    tokens: List[Token] = []
    pos = 0
    while pos < len(text):
        m = TOKEN_RE.match(text, pos)
        if not m:
            raise FormulaError(f"Unexpected character at position {pos}: {text[pos]!r}")
        kind = m.lastgroup or ""
        val = m.group()
        pos = m.end()
        if kind == "WS":
            continue
        tokens.append(Token(kind, val, m.start()))
    tokens.append(Token("EOF", "", len(text)))
    return tokens


class FormulaError(Exception):
    """Raised when parsing or evaluating a formula fails."""


# ---------------------------------------------------------------------------
# AST nodes
# ---------------------------------------------------------------------------

@dataclass
class Num:
    value: float

@dataclass
class Str:
    value: str

@dataclass
class Bool:
    value: bool

@dataclass
class UnaryOp:
    op: str
    operand: Any

@dataclass
class BinOp:
    op: str
    left: Any
    right: Any

@dataclass
class CellRef:
    sheet: Optional[str]   # None = current sheet
    row: int
    col: int
    raw: str = ""

@dataclass
class RangeRef:
    sheet: Optional[str]
    start: CellRef
    end: CellRef

@dataclass
class FuncCall:
    name: str
    args: List[Any]


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

# Function names that look like identifiers but should NOT be parsed as refs
_FUNCTION_NAMES = {
    # populated dynamically from the functions module — we accept any IDENT
    # followed by '(' as a function call.
}


class Parser:
    """Recursive-descent parser for spreadsheet formulas."""

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.i = 0

    @property
    def cur(self) -> Token:
        return self.tokens[self.i]

    def advance(self) -> Token:
        t = self.cur
        self.i += 1
        return t

    def expect(self, ttype: str) -> Token:
        if self.cur.type != ttype:
            raise FormulaError(f"Expected {ttype}, got {self.cur.type} ({self.cur.value!r})")
        return self.advance()

    # ---- entry ----

    # Comparison operators (lowest precedence): = <> > < >= <=
    _CMP_OPS = {"EQ": "=", "NE": "<>", "GT": ">", "LT": "<", "GE": ">=", "LE": "<="}

    def parse(self) -> Any:
        node = self.comparison()
        if self.cur.type != "EOF":
            raise FormulaError(f"Unexpected token after expression: {self.cur!r}")
        return node

    # comparison := expr (( '=' | '<>' | '>' | '<' | '>=' | '<=' ) expr)*
    def comparison(self) -> Any:
        node = self.concat()
        while self.cur.type in self._CMP_OPS:
            op = self._CMP_OPS[self.advance().type]
            right = self.concat()
            node = BinOp(op, node, right)
        return node

    # concat := expr ('&' expr)*  — string concatenation
    def concat(self) -> Any:
        node = self.expr()
        while self.cur.type == "AMP":
            self.advance()
            right = self.expr()
            node = BinOp("&", node, right)
        return node

    # expr := term (('+' | '-') term)*
    def expr(self) -> Any:
        node = self.term()
        while self.cur.type in ("PLUS", "MINUS"):
            op = self.advance().type
            right = self.term()
            node = BinOp("+" if op == "PLUS" else "-", node, right)
        return node

    # term := factor (('*' | '/') factor)*
    def term(self) -> Any:
        node = self.power()
        while self.cur.type in ("STAR", "SLASH"):
            op = self.advance().type
            right = self.power()
            node = BinOp("*" if op == "STAR" else "/", node, right)
        return node

    # power := unary ('^' power)*   (right-assoc)
    def power(self) -> Any:
        node = self.unary()
        if self.cur.type == "CARET":
            self.advance()
            right = self.power()  # right-assoc
            return BinOp("^", node, right)
        return node

    # unary := ('+' | '-') unary | primary
    def unary(self) -> Any:
        if self.cur.type == "MINUS":
            self.advance()
            return UnaryOp("-", self.unary())
        if self.cur.type == "PLUS":
            self.advance()
            return self.unary()
        return self.primary()

    # primary := number | string | bool | '(' expr ')' | func '(' args ')' | ref | range
    def primary(self) -> Any:
        t = self.cur

        if t.type == "NUMBER":
            self.advance()
            return Num(float(t.value))

        if t.type == "STRING":
            self.advance()
            # unescape simple escapes
            return Str(t.value[1:-1].replace('\\"', '"').replace("\\\\", "\\"))

        if t.type == "BOOL":
            self.advance()
            return Bool(t.value.upper() == "TRUE")

        if t.type == "LPAREN":
            self.advance()
            node = self.comparison()
            self.expect("RPAREN")
            return node

        # IDENT could be a function name (if followed by '(') or a sheet name (if followed by '!')
        if t.type == "IDENT":
            self.advance()
            if self.cur.type == "LPAREN":
                self.advance()
                args: List[Any] = []
                if self.cur.type != "RPAREN":
                    args.append(self.comparison())
                    while self.cur.type == "COMMA":
                        self.advance()
                        args.append(self.comparison())
                self.expect("RPAREN")
                return FuncCall(t.value.upper(), args)
            if self.cur.type == "BANG":
                # Cross-sheet reference: SheetName!A1 or SheetName!A1:B2
                self.advance()
                ref_tok = self.expect("REF")
                start = self._make_ref(t.value, ref_tok.value)
                if self.cur.type == "COLON":
                    self.advance()
                    end_tok = self.expect("REF")
                    end = self._make_ref(t.value, end_tok.value)
                    return RangeRef(t.value, start, end)
                return start
            # bare identifier — unknown
            raise FormulaError(f"Unknown identifier (not a function or sheet): {t.value!r}")

        # REF — cell reference or range, possibly cross-sheet (REF!REF)
        if t.type == "REF":
            # Check for cross-sheet reference: S1!A1 where S1 is a sheet-like name
            # Current token is REF (e.g. "S1"), next is BANG, then another REF
            nxt = self._peek(1)
            if nxt is not None and nxt.type == "BANG":
                sheet = self.advance().value  # consume the sheet-name REF
                self.advance()  # consume BANG
                return self._parse_ref_or_range(sheet)
            return self._parse_ref_or_range(None)

        raise FormulaError(f"Unexpected token: {t!r}")

    def _peek(self, offset: int) -> Optional[Token]:
        """Look ahead `offset` tokens without consuming."""
        idx = self.i + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return None

    def _parse_ref_or_range(self, sheet: Optional[str]) -> Any:
        """Parse a cell reference, optionally followed by ':ref' for a range."""
        ref_tok = self.expect("REF")
        start = self._make_ref(sheet, ref_tok.value)
        if self.cur.type == "COLON":
            self.advance()
            end_tok = self.expect("REF")
            end = self._make_ref(sheet, end_tok.value)
            return RangeRef(sheet, start, end)
        return start

    @staticmethod
    def _make_ref(sheet: Optional[str], raw: str) -> CellRef:
        """Convert a raw ref token like 'A1' or '$A$1' into a CellRef."""
        clean = raw.replace("$", "")
        from .cell import parse_a1
        row, col = parse_a1(clean)
        return CellRef(sheet, row, col, raw=raw)


def parse_formula(text: str) -> Any:
    """Parse a formula string (with or without leading '=') into an AST."""
    text = text.strip()
    if text.startswith("="):
        text = text[1:]
    tokens = tokenize(text)
    parser = Parser(tokens)
    return parser.parse()


def extract_refs(node: Any) -> List[Tuple[Optional[str], int, int]]:
    """Walk an AST and return all cell references as (sheet, row, col) tuples."""
    refs: List[Tuple[Optional[str], int, int]] = []
    _collect_refs(node, refs)
    return refs


def _collect_refs(node: Any, refs: list) -> None:
    if isinstance(node, CellRef):
        refs.append((node.sheet, node.row, node.col))
    elif isinstance(node, RangeRef):
        # expand range into individual cells
        r1, r2 = node.start.row, node.end.row
        c1, c2 = node.start.col, node.end.col
        r_lo, r_hi = min(r1, r2), max(r1, r2)
        c_lo, c_hi = min(c1, c2), max(c1, c2)
        for r in range(r_lo, r_hi + 1):
            for c in range(c_lo, c_hi + 1):
                refs.append((node.sheet, r, c))
    elif isinstance(node, UnaryOp):
        _collect_refs(node.operand, refs)
    elif isinstance(node, BinOp):
        _collect_refs(node.left, refs)
        _collect_refs(node.right, refs)
    elif isinstance(node, FuncCall):
        for a in node.args:
            _collect_refs(a, refs)