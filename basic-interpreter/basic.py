#!/usr/bin/env python3
"""
A full-featured interpreter for a classic BASIC dialect.

Supports:
  - Line-numbered programs with GOTO / GOSUB / RETURN
  - IF...THEN...ELSE / FOR...NEXT / WHILE...WEND
  - LET, PRINT, INPUT, READ, DATA, RESTORE
  - DIM for arrays (1D and 2D)
  - DEF FN for user-defined functions
  - String and numeric operations
  - Built-in functions: ABS, INT, RND, SQR, SIN, COS, TAN, ATN, LOG, EXP, LEN, LEFT$, RIGHT$, MID$, CHR$, ASC, STR$, VAL, TAB, SPC
  - Logical operators: AND, OR, NOT
  - Comparison operators: =, <>, <, >, <=, >=
  - REM for comments, END statement
  - ON...GOTO / ON...GOSUB
  - SWAP statement
  - COLOR, CLS, LOCATE (terminal control)

Usage:
    python3 basic.py program.bas           # run a program
    python3 basic.py -e "PRINT 42"         # one-liner
    python3 basic.py                       # interactive REPL
"""

from __future__ import annotations

import math
import os
import random
import re
import sys
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Union


# ── Token types ──────────────────────────────────────────────────────────────

class TokenType(Enum):
    NUMBER = auto()
    STRING = auto()
    IDENT = auto()
    # Keywords
    LET = auto()
    PRINT = auto()
    INPUT = auto()
    IF = auto()
    THEN = auto()
    ELSE = auto()
    FOR = auto()
    TO = auto()
    STEP = auto()
    NEXT = auto()
    WHILE = auto()
    WEND = auto()
    GOTO = auto()
    GOSUB = auto()
    RETURN = auto()
    DIM = auto()
    READ = auto()
    DATA = auto()
    RESTORE = auto()
    DEF = auto()
    FN = auto()
    REM = auto()
    END = auto()
    STOP = auto()
    ON = auto()
    SWAP = auto()
    CLS = auto()
    COLOR = auto()
    LOCATE = auto()
    # Operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    CARET = auto()
    BACKSLASH = auto()    # integer division
    MOD = auto()
    EQ = auto()
    NE = auto()
    LT = auto()
    GT = auto()
    LE = auto()
    GE = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    SEMI = auto()
    COLON = auto()
    # Line number (only at start of line)
    LINENUM = auto()
    # EOF
    EOF = auto()


KEYWORDS = {
    "LET": TokenType.LET, "PRINT": TokenType.PRINT, "INPUT": TokenType.INPUT,
    "IF": TokenType.IF, "THEN": TokenType.THEN, "ELSE": TokenType.ELSE,
    "FOR": TokenType.FOR, "TO": TokenType.TO, "STEP": TokenType.STEP,
    "NEXT": TokenType.NEXT, "WHILE": TokenType.WHILE, "WEND": TokenType.WEND,
    "GOTO": TokenType.GOTO, "GOSUB": TokenType.GOSUB, "RETURN": TokenType.RETURN,
    "DIM": TokenType.DIM, "READ": TokenType.READ, "DATA": TokenType.DATA,
    "RESTORE": TokenType.RESTORE, "DEF": TokenType.DEF, "FN": TokenType.FN,
    "REM": TokenType.REM, "END": TokenType.END, "STOP": TokenType.STOP,
    "ON": TokenType.ON, "SWAP": TokenType.SWAP,
    "CLS": TokenType.CLS, "COLOR": TokenType.COLOR, "LOCATE": TokenType.LOCATE,
    "AND": TokenType.AND, "OR": TokenType.OR, "NOT": TokenType.NOT,
    "MOD": TokenType.MOD,
}


@dataclass
class Token:
    type: TokenType
    value: Any
    line: int = 0
    col: int = 0


# ── Lexer ────────────────────────────────────────────────────────────────────

class Lexer:
    """Tokenise a BASIC source line."""

    def __init__(self, text: str, line_num: int = 0):
        self.text = text
        self.pos = 0
        self.line_num = line_num
        self.tokens: List[Token] = []

    def _peek(self) -> str:
        if self.pos < len(self.text):
            return self.text[self.pos]
        return "\0"

    def _advance(self) -> str:
        ch = self.text[self.pos]
        self.pos += 1
        return ch

    def _skip_spaces(self):
        while self.pos < len(self.text) and self.text[self.pos] in " \t":
            self.pos += 1

    def _read_number(self) -> float:
        start = self.pos
        while self.pos < len(self.text) and (self.text[self.pos].isdigit() or self.text[self.pos] == "."):
            self.pos += 1
        # Handle E notation
        if self.pos < len(self.text) and self.text[self.pos] in "eE":
            self.pos += 1
            if self.pos < len(self.text) and self.text[self.pos] in "+-":
                self.pos += 1
            while self.pos < len(self.text) and self.text[self.pos].isdigit():
                self.pos += 1
        return float(self.text[start:self.pos])

    def _read_string(self) -> str:
        self._advance()  # skip opening quote
        result = []
        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch == '"':
                self._advance()  # skip closing quote
                # Handle "" as escaped quote inside string
                if self.pos < len(self.text) and self.text[self.pos] == '"':
                    result.append('"')
                    self._advance()
                    continue
                return "".join(result)
            result.append(ch)
            self._advance()
        # Unterminated string
        return "".join(result)

    def _read_ident(self) -> str:
        start = self.pos
        while self.pos < len(self.text) and (self.text[self.pos].isalnum() or self.text[self.pos] in "._$"):
            self.pos += 1
        return self.text[start:self.pos]

    def tokenize(self) -> List[Token]:
        # Check for line number at the start
        self._skip_spaces()
        if self.pos < len(self.text) and self.text[self.pos].isdigit():
            start = self.pos
            while self.pos < len(self.text) and self.text[self.pos].isdigit():
                self.pos += 1
            num_str = self.text[start:self.pos]
            # If followed by space/end, it's a line number
            self._skip_spaces()
            self.tokens.append(Token(TokenType.LINENUM, int(num_str), self.line_num, start))

        while self.pos < len(self.text):
            self._skip_spaces()
            if self.pos >= len(self.text):
                break

            ch = self.text[self.pos]
            col = self.pos

            # String literal
            if ch == '"':
                s = self._read_string()
                self.tokens.append(Token(TokenType.STRING, s, self.line_num, col))
                continue

            # Number
            if ch.isdigit() or (ch == "." and self.pos + 1 < len(self.text) and self.text[self.pos + 1].isdigit()):
                n = self._read_number()
                self.tokens.append(Token(TokenType.NUMBER, n, self.line_num, col))
                continue

            # Identifier / keyword
            if ch.isalpha() or ch == "_":
                ident = self._read_ident()
                upper = ident.upper()
                if upper in KEYWORDS:
                    tok_type = KEYWORDS[upper]
                    if tok_type == TokenType.REM:
                        # REM: rest of line is comment
                        self.tokens.append(Token(TokenType.REM, self.text[self.pos:], self.line_num, col))
                        break
                    self.tokens.append(Token(tok_type, upper, self.line_num, col))
                else:
                    self.tokens.append(Token(TokenType.IDENT, ident, self.line_num, col))
                continue

            # Two-character operators
            if ch == "<":
                self._advance()
                if self._peek() == ">":
                    self._advance()
                    self.tokens.append(Token(TokenType.NE, "<>", self.line_num, col))
                elif self._peek() == "=":
                    self._advance()
                    self.tokens.append(Token(TokenType.LE, "<=", self.line_num, col))
                else:
                    self.tokens.append(Token(TokenType.LT, "<", self.line_num, col))
                continue
            if ch == ">":
                self._advance()
                if self._peek() == "=":
                    self._advance()
                    self.tokens.append(Token(TokenType.GE, ">=", self.line_num, col))
                else:
                    self.tokens.append(Token(TokenType.GT, ">", self.line_num, col))
                continue

            # Single-character tokens
            simple = {
                "+": TokenType.PLUS, "-": TokenType.MINUS,
                "*": TokenType.STAR, "/": TokenType.SLASH,
                "^": TokenType.CARET, "\\": TokenType.BACKSLASH,
                "(": TokenType.LPAREN, ")": TokenType.RPAREN,
                ",": TokenType.COMMA, ";": TokenType.SEMI,
                ":": TokenType.COLON, "=": TokenType.EQ,
            }
            if ch in simple:
                self._advance()
                self.tokens.append(Token(simple[ch], ch, self.line_num, col))
                continue

            # Skip unknown characters
            self._advance()

        self.tokens.append(Token(TokenType.EOF, None, self.line_num, self.pos))
        return self.tokens


# ── AST nodes ────────────────────────────────────────────────────────────────

@dataclass
class NumberLit:
    value: float

@dataclass
class StringLit:
    value: str

@dataclass
class VarRef:
    name: str

@dataclass
class ArrayRef:
    name: str
    indices: list  # list of expressions

@dataclass
class FnCall:
    name: str
    args: list

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
class LetStmt:
    target: Any   # VarRef or ArrayRef
    value: Any

@dataclass
class PrintStmt:
    items: list   # list of (expr, separator) pairs; separator is ; or , or None

@dataclass
class InputStmt:
    prompt: Any   # string expression or None
    vars: list    # list of VarRef

@dataclass
class IfStmt:
    condition: Any
    then_part: list
    else_part: list

@dataclass
class ForStmt:
    var: VarRef
    start: Any
    stop: Any
    step: Any   # None means 1

@dataclass
class NextStmt:
    var: Optional[VarRef]

@dataclass
class WhileStmt:
    condition: Any
    body: list

@dataclass
class WendStmt:
    pass

@dataclass
class GotoStmt:
    line: int

@dataclass
class GosubStmt:
    line: int

@dataclass
class ReturnStmt:
    pass

@dataclass
class DimStmt:
    declarations: list  # list of (name, dims)

@dataclass
class ReadStmt:
    vars: list

@dataclass
class DataStmt:
    values: list

@dataclass
class RestoreStmt:
    pass

@dataclass
class DefFnStmt:
    name: str
    params: list
    body: Any   # expression

@dataclass
class EndStmt:
    pass

@dataclass
class StopStmt:
    pass

@dataclass
class RemStmt:
    text: str

@dataclass
class OnGotoStmt:
    expr: Any
    targets: list

@dataclass
class OnGosubStmt:
    expr: Any
    targets: list

@dataclass
class SwapStmt:
    var1: Any
    var2: Any

@dataclass
class ClsStmt:
    pass

@dataclass
class ColorStmt:
    fg: Any
    bg: Any = None

@dataclass
class LocateStmt:
    row: Any
    col: Any


# ── Parser ───────────────────────────────────────────────────────────────────

class Parser:
    """Recursive-descent parser for BASIC."""

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def _peek(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, None)

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _expect(self, tt: TokenType) -> Token:
        tok = self._advance()
        if tok.type != tt:
            raise BasicSyntaxError(f"Expected {tt.name}, got {tok.type.name} ({tok.value!r})")
        return tok

    def _match(self, *types: TokenType) -> Optional[Token]:
        if self._peek().type in types:
            return self._advance()
        return None

    # ── Program parsing ──

    def parse_program(self) -> Tuple[Dict[int, list], List[Any]]:
        """Parse entire program, return (line_stmts, immediate_stmts)."""
        lines: Dict[int, list] = {}
        immediate: List[Any] = []
        for raw_line in self._split_lines():
            lexer = Lexer(raw_line)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            linenum_tok = parser._match(TokenType.LINENUM)
            if linenum_tok:
                line_num = linenum_tok.value
                if parser._peek().type == TokenType.EOF:
                    # Empty line = delete
                    lines.pop(line_num, None)
                    continue
                stmts = parser._parse_stmts()
                lines[line_num] = stmts
            else:
                stmts = parser._parse_stmts()
                immediate.extend(stmts)
        return lines, immediate

    def _split_lines(self) -> List[str]:
        """Original text is stored; we handle line splitting externally."""
        return []

    def _parse_stmts(self) -> list:
        stmts = []
        stmts.append(self._parse_stmt())
        while self._match(TokenType.COLON):
            if self._peek().type == TokenType.EOF:
                break
            stmts.append(self._parse_stmt())
        return stmts

    def _parse_stmt(self) -> Any:
        tok = self._peek()

        if tok.type == TokenType.LET:
            return self._parse_let()
        if tok.type == TokenType.PRINT:
            return self._parse_print()
        if tok.type == TokenType.INPUT:
            return self._parse_input()
        if tok.type == TokenType.IF:
            return self._parse_if()
        if tok.type == TokenType.FOR:
            return self._parse_for()
        if tok.type == TokenType.NEXT:
            return self._parse_next()
        if tok.type == TokenType.WHILE:
            return self._parse_while()
        if tok.type == TokenType.WEND:
            self._advance()
            return WendStmt()
        if tok.type == TokenType.GOTO:
            return self._parse_goto()
        if tok.type == TokenType.GOSUB:
            return self._parse_gosub()
        if tok.type == TokenType.RETURN:
            self._advance()
            return ReturnStmt()
        if tok.type == TokenType.DIM:
            return self._parse_dim()
        if tok.type == TokenType.READ:
            return self._parse_read()
        if tok.type == TokenType.DATA:
            return self._parse_data()
        if tok.type == TokenType.RESTORE:
            self._advance()
            return RestoreStmt()
        if tok.type == TokenType.DEF:
            return self._parse_def_fn()
        if tok.type == TokenType.END:
            self._advance()
            return EndStmt()
        if tok.type == TokenType.STOP:
            self._advance()
            return StopStmt()
        if tok.type == TokenType.ON:
            return self._parse_on()
        if tok.type == TokenType.SWAP:
            return self._parse_swap()
        if tok.type == TokenType.CLS:
            self._advance()
            return ClsStmt()
        if tok.type == TokenType.COLOR:
            return self._parse_color()
        if tok.type == TokenType.LOCATE:
            return self._parse_locate()
        if tok.type == TokenType.REM:
            self._advance()
            return RemStmt(tok.value or "")

        # Implicit LET: assignment without LET keyword
        if tok.type == TokenType.IDENT:
            # Look ahead for = or (
            next_pos = self.pos + 1
            while next_pos < len(self.tokens) and self.tokens[next_pos].type in (TokenType.LPAREN,):
                # skip parens for array assignment like A(1)=5
                depth = 0
                while next_pos < len(self.tokens):
                    if self.tokens[next_pos].type == TokenType.LPAREN:
                        depth += 1
                    elif self.tokens[next_pos].type == TokenType.RPAREN:
                        depth -= 1
                        if depth == 0:
                            next_pos += 1
                            break
                    next_pos += 1
            if next_pos < len(self.tokens) and self.tokens[next_pos].type == TokenType.EQ:
                return self._parse_let(implicit=True)

        # Expression statement (e.g., function calls)
        expr = self._parse_expr()
        return expr

    def _parse_let(self, implicit=False) -> LetStmt:
        if not implicit:
            self._expect(TokenType.LET)
        target = self._parse_lvalue()
        self._expect(TokenType.EQ)
        value = self._parse_expr()
        return LetStmt(target, value)

    def _parse_lvalue(self):
        name_tok = self._expect(TokenType.IDENT)
        name = self._normalize_var(name_tok.value)
        if self._peek().type == TokenType.LPAREN:
            self._advance()
            indices = [self._parse_expr()]
            while self._match(TokenType.COMMA):
                indices.append(self._parse_expr())
            self._expect(TokenType.RPAREN)
            return ArrayRef(name, indices)
        return VarRef(name)

    def _parse_print(self) -> PrintStmt:
        self._expect(TokenType.PRINT)
        items = []
        if self._peek().type == TokenType.EOF or self._peek().type == TokenType.COLON:
            # PRINT alone prints a newline
            return PrintStmt([(None, None)])

        while True:
            if self._peek().type in (TokenType.SEMI, TokenType.COMMA):
                # leading separator for positioning
                sep = self._advance()
                items.append((None, sep.value))
                if self._peek().type == TokenType.EOF or self._peek().type == TokenType.COLON:
                    break
                continue

            expr = self._parse_expr()
            sep_tok = self._match(TokenType.SEMI, TokenType.COMMA)
            if sep_tok:
                items.append((expr, sep_tok.value))
                if self._peek().type == TokenType.EOF or self._peek().type == TokenType.COLON:
                    break
            else:
                items.append((expr, None))
                break
        return PrintStmt(items)

    def _parse_input(self) -> InputStmt:
        self._expect(TokenType.INPUT)
        prompt = None
        # Check for prompt string
        if self._peek().type == TokenType.STRING:
            prompt = StringLit(self._advance().value)
            if self._match(TokenType.SEMI):
                pass  # ; after prompt
            elif self._match(TokenType.COMMA):
                pass
        vars_ = []
        vars_.append(self._parse_lvalue())
        while self._match(TokenType.COMMA):
            vars_.append(self._parse_lvalue())
        return InputStmt(prompt, vars_)

    def _parse_if(self) -> IfStmt:
        self._expect(TokenType.IF)
        condition = self._parse_expr()
        self._expect(TokenType.THEN)
        # THEN can be followed by line number (GOTO) or statements
        if self._peek().type == TokenType.NUMBER:
            line_num = int(self._advance().value)
            then_part = [GotoStmt(line_num)]
        else:
            then_part = self._parse_stmts()
        else_part = []
        # Look for ELSE at current position
        if self._peek().type == TokenType.ELSE:
            self._advance()
            if self._peek().type == TokenType.NUMBER:
                line_num = int(self._advance().value)
                else_part = [GotoStmt(line_num)]
            else:
                else_part = self._parse_stmts()
        return IfStmt(condition, then_part, else_part)

    def _parse_for(self) -> ForStmt:
        self._expect(TokenType.FOR)
        var_tok = self._expect(TokenType.IDENT)
        var = VarRef(self._normalize_var(var_tok.value))
        self._expect(TokenType.EQ)
        start = self._parse_expr()
        self._expect(TokenType.TO)
        stop = self._parse_expr()
        step = None
        if self._match(TokenType.STEP):
            step = self._parse_expr()
        return ForStmt(var, start, stop, step)

    def _parse_next(self) -> NextStmt:
        self._expect(TokenType.NEXT)
        var = None
        if self._peek().type == TokenType.IDENT:
            var = VarRef(self._normalize_var(self._advance().value))
        return NextStmt(var)

    def _parse_while(self) -> WhileStmt:
        self._expect(TokenType.WHILE)
        condition = self._parse_expr()
        return WhileStmt(condition, [])

    def _parse_goto(self) -> GotoStmt:
        self._expect(TokenType.GOTO)
        line = int(self._expect(TokenType.NUMBER).value)
        return GotoStmt(line)

    def _parse_gosub(self) -> GosubStmt:
        self._expect(TokenType.GOSUB)
        line = int(self._expect(TokenType.NUMBER).value)
        return GosubStmt(line)

    def _parse_dim(self) -> DimStmt:
        self._expect(TokenType.DIM)
        decls = []
        name_tok = self._expect(TokenType.IDENT)
        self._expect(TokenType.LPAREN)
        dims = [int(self._expect(TokenType.NUMBER).value)]
        while self._match(TokenType.COMMA):
            dims.append(int(self._expect(TokenType.NUMBER).value))
        self._expect(TokenType.RPAREN)
        decls.append((self._normalize_var(name_tok.value), dims))
        while self._match(TokenType.COMMA):
            name_tok = self._expect(TokenType.IDENT)
            self._expect(TokenType.LPAREN)
            dims = [int(self._expect(TokenType.NUMBER).value)]
            while self._match(TokenType.COMMA):
                dims.append(int(self._expect(TokenType.NUMBER).value))
            self._expect(TokenType.RPAREN)
            decls.append((self._normalize_var(name_tok.value), dims))
        return DimStmt(decls)

    def _parse_read(self) -> ReadStmt:
        self._expect(TokenType.READ)
        vars_ = [self._parse_lvalue()]
        while self._match(TokenType.COMMA):
            vars_.append(self._parse_lvalue())
        return ReadStmt(vars_)

    def _parse_data(self) -> DataStmt:
        self._expect(TokenType.DATA)
        values = [self._parse_data_value()]
        while self._match(TokenType.COMMA):
            values.append(self._parse_data_value())
        return DataStmt(values)

    def _parse_data_value(self):
        tok = self._peek()
        if tok.type == TokenType.STRING:
            self._advance()
            return tok.value
        if tok.type == TokenType.MINUS:
            self._advance()
            n = self._expect(TokenType.NUMBER).value
            return -n
        if tok.type == TokenType.NUMBER:
            self._advance()
            return tok.value
        # Unquoted string in DATA
        if tok.type == TokenType.IDENT:
            self._advance()
            return tok.value
        raise BasicSyntaxError(f"Unexpected token in DATA: {tok}")

    def _parse_def_fn(self) -> DefFnStmt:
        self._expect(TokenType.DEF)
        self._expect(TokenType.FN)
        name_tok = self._expect(TokenType.IDENT)
        name = name_tok.value.upper()
        params = []
        if self._match(TokenType.LPAREN):
            if self._peek().type != TokenType.RPAREN:
                params.append(self._normalize_var(self._expect(TokenType.IDENT).value))
                while self._match(TokenType.COMMA):
                    params.append(self._normalize_var(self._expect(TokenType.IDENT).value))
            self._expect(TokenType.RPAREN)
        self._expect(TokenType.EQ)
        body = self._parse_expr()
        return DefFnStmt(name, params, body)

    def _parse_on(self):
        self._expect(TokenType.ON)
        expr = self._parse_expr()
        if self._match(TokenType.GOTO):
            targets = [int(self._expect(TokenType.NUMBER).value)]
            while self._match(TokenType.COMMA):
                targets.append(int(self._expect(TokenType.NUMBER).value))
            return OnGotoStmt(expr, targets)
        self._expect(TokenType.GOSUB)
        targets = [int(self._expect(TokenType.NUMBER).value)]
        while self._match(TokenType.COMMA):
            targets.append(int(self._expect(TokenType.NUMBER).value))
        return OnGosubStmt(expr, targets)

    def _parse_swap(self) -> SwapStmt:
        self._expect(TokenType.SWAP)
        v1 = self._parse_lvalue()
        self._expect(TokenType.COMMA)
        v2 = self._parse_lvalue()
        return SwapStmt(v1, v2)

    def _parse_color(self) -> ColorStmt:
        self._expect(TokenType.COLOR)
        fg = self._parse_expr()
        bg = None
        if self._match(TokenType.COMMA):
            bg = self._parse_expr()
        return ColorStmt(fg, bg)

    def _parse_locate(self) -> LocateStmt:
        self._expect(TokenType.LOCATE)
        row = self._parse_expr()
        col = None
        if self._match(TokenType.COMMA):
            col = self._parse_expr()
        return LocateStmt(row, col)

    # ── Expression parsing (precedence climbing) ──

    def _parse_expr(self) -> Any:
        return self._parse_or()

    def _parse_or(self) -> Any:
        left = self._parse_and()
        while self._peek().type == TokenType.OR:
            self._advance()
            right = self._parse_and()
            left = BinOp("OR", left, right)
        return left

    def _parse_and(self) -> Any:
        left = self._parse_not()
        while self._peek().type == TokenType.AND:
            self._advance()
            right = self._parse_not()
            left = BinOp("AND", left, right)
        return left

    def _parse_not(self) -> Any:
        if self._peek().type == TokenType.NOT:
            self._advance()
            operand = self._parse_not()
            return UnaryOp("NOT", operand)
        return self._parse_comparison()

    def _parse_comparison(self) -> Any:
        left = self._parse_add()
        comp_types = {TokenType.EQ: "=", TokenType.NE: "<>",
                      TokenType.LT: "<", TokenType.GT: ">",
                      TokenType.LE: "<=", TokenType.GE: ">="}
        if self._peek().type in comp_types:
            op = comp_types[self._peek().type]
            self._advance()
            right = self._parse_add()
            return BinOp(op, left, right)
        return left

    def _parse_add(self) -> Any:
        left = self._parse_mul()
        while self._peek().type in (TokenType.PLUS, TokenType.MINUS):
            op = "+" if self._peek().type == TokenType.PLUS else "-"
            self._advance()
            right = self._parse_mul()
            left = BinOp(op, left, right)
        return left

    def _parse_mul(self) -> Any:
        left = self._parse_intdiv()
        while self._peek().type in (TokenType.STAR, TokenType.SLASH):
            op = "*" if self._peek().type == TokenType.STAR else "/"
            self._advance()
            right = self._parse_intdiv()
            left = BinOp(op, left, right)
        return left

    def _parse_intdiv(self) -> Any:
        left = self._parse_mod()
        while self._peek().type == TokenType.BACKSLASH:
            self._advance()
            right = self._parse_mod()
            left = BinOp("\\", left, right)
        return left

    def _parse_mod(self) -> Any:
        left = self._parse_power()
        while self._peek().type == TokenType.MOD:
            self._advance()
            right = self._parse_power()
            left = BinOp("MOD", left, right)
        return left

    def _parse_power(self) -> Any:
        base = self._parse_unary()
        if self._peek().type == TokenType.CARET:
            self._advance()
            exp = self._parse_power()  # right-associative
            return BinOp("^", base, exp)
        return base

    def _parse_unary(self) -> Any:
        if self._peek().type == TokenType.MINUS:
            self._advance()
            operand = self._parse_unary()
            return UnaryOp("-", operand)
        if self._peek().type == TokenType.PLUS:
            self._advance()
            return self._parse_unary()
        return self._parse_primary()

    def _parse_primary(self) -> Any:
        tok = self._peek()

        # Number literal
        if tok.type == TokenType.NUMBER:
            self._advance()
            return NumberLit(tok.value)

        # String literal
        if tok.type == TokenType.STRING:
            self._advance()
            return StringLit(tok.value)

        # Parenthesized expression
        if tok.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_expr()
            self._expect(TokenType.RPAREN)
            return expr

        # FN user function
        if tok.type == TokenType.FN:
            self._advance()
            name_tok = self._expect(TokenType.IDENT)
            name = "FN" + name_tok.value.upper()
            self._expect(TokenType.LPAREN)
            args = []
            if self._peek().type != TokenType.RPAREN:
                args.append(self._parse_expr())
                while self._match(TokenType.COMMA):
                    args.append(self._parse_expr())
            self._expect(TokenType.RPAREN)
            return FnCall(name, args)

        # Identifier: variable or built-in function
        if tok.type == TokenType.IDENT:
            name = tok.value
            upper = name.upper()
            # Built-in functions
            builtin_funcs = {
                "ABS", "INT", "RND", "SQR", "SIN", "COS", "TAN", "ATN",
                "LOG", "EXP", "LEN", "LEFT$", "RIGHT$", "MID$",
                "CHR$", "ASC", "STR$", "VAL", "TAB", "SPC",
                "STRING$", "INSTR", "TIMER", "PEEK",
            }
            if upper in builtin_funcs:
                self._advance()
                self._expect(TokenType.LPAREN)
                args = []
                if self._peek().type != TokenType.RPAREN:
                    args.append(self._parse_expr())
                    while self._match(TokenType.COMMA):
                        args.append(self._parse_expr())
                self._expect(TokenType.RPAREN)
                return FnCall(upper, args)

            # Variable or array reference
            self._advance()
            norm = self._normalize_var(name)
            if self._peek().type == TokenType.LPAREN:
                self._advance()
                indices = [self._parse_expr()]
                while self._match(TokenType.COMMA):
                    indices.append(self._parse_expr())
                self._expect(TokenType.RPAREN)
                return ArrayRef(norm, indices)
            return VarRef(norm)

        raise BasicSyntaxError(f"Unexpected token: {tok.type.name} ({tok.value!r})")

    @staticmethod
    def _normalize_var(name: str) -> str:
        """Normalize variable name: uppercase, strip $/% type suffixes, keep them as part of name."""
        n = name.upper()
        return n


# ── Exceptions ───────────────────────────────────────────────────────────────

class BasicError(Exception):
    pass

class BasicSyntaxError(BasicError):
    pass

class BasicRuntimeError(BasicError):
    pass

class BasicStopException(Exception):
    """Raised by STOP statement for debugging."""
    pass


# ── Interpreter ─────────────────────────────────────────────────────────────

class Interpreter:
    """Execute BASIC programs."""

    def __init__(self, stdin=None, stdout=None):
        self.lines: Dict[int, list] = {}          # line_num -> [stmts]
        self.sorted_lines: List[int] = []          # sorted line numbers
        self.variables: Dict[str, Any] = {}        # variable store
        self.arrays: Dict[str, Any] = {}           # array store
        self.data_values: List[Any] = []           # all DATA values concatenated
        self.data_pointer: int = 0                 # current READ position
        self.call_stack: List[int] = []            # GOSUB return addresses (line numbers)
        self.for_stack: List[dict] = []            # FOR loop stack
        self.while_stack: List[Tuple[int, int, int, int]] = []  # (while_line_idx, while_stmt_idx, wend_line_idx, wend_stmt_idx)
        self.user_fns: Dict[str, DefFnStmt] = {}   # user-defined functions
        self.pc: int = 0                           # current index into sorted_lines
        self.running: bool = False
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout
        self.trace: bool = False
        self.max_iterations: int = 10_000_000
        self._iteration_count: int = 0
        self._color_stack: List[Tuple[str, str]] = []

    # ── Program loading ──

    def load(self, source: str):
        """Load and parse a BASIC program from source text."""
        self.lines.clear()
        self.data_values.clear()
        self.data_pointer = 0
        self.variables.clear()
        self.arrays.clear()
        self.call_stack.clear()
        self.for_stack.clear()
        self.while_stack.clear()
        self.user_fns.clear()

        immediate_stmts = []
        for raw_line in source.splitlines():
            raw_line = raw_line.rstrip()
            if not raw_line.strip():
                continue
            lexer = Lexer(raw_line)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            linenum_tok = parser._match(TokenType.LINENUM)
            if linenum_tok:
                line_num = linenum_tok.value
                if parser._peek().type == TokenType.EOF:
                    self.lines.pop(line_num, None)
                    continue
                stmts = parser._parse_stmts()
                self.lines[line_num] = stmts
            else:
                if parser._peek().type != TokenType.EOF:
                    stmts = parser._parse_stmts()
                    immediate_stmts.extend(stmts)

        self._rebuild()
        self._collect_data()
        self._resolve_while_wend()

        # Execute immediate mode statements
        if immediate_stmts:
            self.running = True
            self._exec_stmts(immediate_stmts)

    def _rebuild(self):
        self.sorted_lines = sorted(self.lines.keys())

    def _collect_data(self):
        """Collect all DATA values in line-number order."""
        self.data_values = []
        self.data_pointer = 0
        for ln in self.sorted_lines:
            for stmt in self.lines[ln]:
                if isinstance(stmt, DataStmt):
                    self.data_values.extend(stmt.values)

    def _resolve_while_wend(self):
        """Match WHILE and WEND statements and record their positions."""
        self.while_stack = []
        stack = []
        for i, ln in enumerate(self.sorted_lines):
            stmts = self.lines[ln]
            for j, stmt in enumerate(stmts):
                if isinstance(stmt, WhileStmt):
                    stack.append((i, j))
                elif isinstance(stmt, WendStmt):
                    if not stack:
                        raise BasicSyntaxError("WEND without matching WHILE")
                    wi, wj = stack.pop()
                    # Store the matching info in a lookup
                    self.while_stack.append((wi, wj, i, j))

    def _find_wend(self, while_line_idx: int) -> Optional[Tuple[int, int]]:
        for wi, wj, wendi, wendj in self.while_stack:
            if wi == while_line_idx:
                return (wendi, wendj)
        return None

    def _find_while(self, wend_line_idx: int) -> Optional[Tuple[int, int]]:
        for wi, wj, wendi, wendj in self.while_stack:
            if wendi == wend_line_idx:
                return (wi, wj)
        return None

    # ── Execution ── (run() is defined after all _exec_* methods)

    def _exec_stmts(self, stmts: list):
        for stmt in stmts:
            if not self.running:
                return
            self._exec_stmt(stmt)

    def _exec_stmt(self, stmt: Any):
        if isinstance(stmt, NumberLit) or isinstance(stmt, StringLit) or isinstance(stmt, BinOp) or isinstance(stmt, UnaryOp):
            # Expression statement — evaluate but discard result
            self._eval(stmt)
            return

        if isinstance(stmt, LetStmt):
            self._exec_let(stmt)
        elif isinstance(stmt, PrintStmt):
            self._exec_print(stmt)
        elif isinstance(stmt, InputStmt):
            self._exec_input(stmt)
        elif isinstance(stmt, IfStmt):
            self._exec_if(stmt)
        elif isinstance(stmt, ForStmt):
            self._exec_for(stmt)
        elif isinstance(stmt, NextStmt):
            self._exec_next(stmt)
        elif isinstance(stmt, WhileStmt):
            self._exec_while(stmt)
        elif isinstance(stmt, WendStmt):
            self._exec_wend(stmt)
        elif isinstance(stmt, GotoStmt):
            self._exec_goto(stmt)
        elif isinstance(stmt, GosubStmt):
            self._exec_gosub(stmt)
        elif isinstance(stmt, ReturnStmt):
            self._exec_return(stmt)
        elif isinstance(stmt, DimStmt):
            self._exec_dim(stmt)
        elif isinstance(stmt, ReadStmt):
            self._exec_read(stmt)
        elif isinstance(stmt, DataStmt):
            pass  # DATA is collected at load time
        elif isinstance(stmt, RestoreStmt):
            self.data_pointer = 0
        elif isinstance(stmt, DefFnStmt):
            self._exec_def_fn(stmt)
        elif isinstance(stmt, EndStmt):
            self.running = False
        elif isinstance(stmt, StopStmt):
            raise BasicStopException("STOP encountered")
        elif isinstance(stmt, RemStmt):
            pass
        elif isinstance(stmt, OnGotoStmt):
            self._exec_on_goto(stmt)
        elif isinstance(stmt, OnGosubStmt):
            self._exec_on_gosub(stmt)
        elif isinstance(stmt, SwapStmt):
            self._exec_swap(stmt)
        elif isinstance(stmt, ClsStmt):
            self.stdout.write("\033[2J\033[H")
            self.stdout.flush()
        elif isinstance(stmt, ColorStmt):
            self._exec_color(stmt)
        elif isinstance(stmt, LocateStmt):
            self._exec_locate(stmt)
        else:
            raise BasicRuntimeError(f"Unknown statement: {type(stmt).__name__}")

    def _exec_let(self, stmt: LetStmt):
        value = self._eval(stmt.value)
        if isinstance(stmt.target, VarRef):
            self.variables[stmt.target.name] = value
        elif isinstance(stmt.target, ArrayRef):
            name = stmt.target.name
            indices = [int(self._eval(idx)) for idx in stmt.target.indices]
            if name not in self.arrays:
                # Auto-allocate with generous default size (BASIC tradition)
                dim_count = len(indices)
                if dim_count == 1:
                    self.arrays[name] = [0.0] * (max(indices[0], 10) + 1)
                elif dim_count == 2:
                    self.arrays[name] = [[0.0] * (max(indices[1], 10) + 1) for _ in range(max(indices[0], 10) + 1)]
            arr = self.arrays[name]
            if len(indices) == 1:
                if indices[0] >= len(arr):
                    # Extend array
                    arr.extend([0.0] * (indices[0] - len(arr) + 1))
                arr[indices[0]] = value
            elif len(indices) == 2:
                if indices[0] >= len(arr):
                    while len(arr) <= indices[0]:
                        arr.append([0.0] * len(arr[0]) if arr else [0.0] * 11)
                if indices[1] >= len(arr[indices[0]]):
                    arr[indices[0]].extend([0.0] * (indices[1] - len(arr[indices[0]]) + 1))
                arr[indices[0]][indices[1]] = value
        else:
            raise BasicRuntimeError(f"Invalid LET target: {stmt.target}")

    def _exec_print(self, stmt: PrintStmt):
        end_newline = True
        zone_width = 14
        for expr, sep in stmt.items:
            if expr is not None:
                val = self._eval(expr)
                if isinstance(val, float):
                    if val == int(val) and abs(val) < 1e15:
                        self.stdout.write(" " + str(int(val)) + " ")
                    else:
                        self.stdout.write(" " + str(val) + " ")
                else:
                    self.stdout.write(str(val))
            if sep == ";":
                end_newline = False
            elif sep == ",":
                # Tab to next print zone
                # Approximate: move to next multiple of zone_width
                # We don't track column precisely, so just add spaces
                self.stdout.write("\t")
                end_newline = False
            else:
                end_newline = True
        if end_newline:
            self.stdout.write("\n")
        self.stdout.flush()

    def _exec_input(self, stmt: InputStmt):
        prompt = "? "
        if stmt.prompt:
            p = self._eval(stmt.prompt)
            prompt = str(p)
            if not prompt.endswith(" "):
                prompt += " "
        self.stdout.write(prompt)
        self.stdout.flush()
        try:
            line = self.stdin.readline()
            if not line:
                raise BasicRuntimeError("End of input")
            line = line.rstrip("\n\r")
        except EOFError:
            raise BasicRuntimeError("End of input")

        # Parse input values
        values = [v.strip() for v in line.split(",")]
        for i, var in enumerate(stmt.vars):
            raw = values[i] if i < len(values) else ""
            if isinstance(var, VarRef):
                name = var.name
                if name.endswith("$"):
                    self.variables[name] = raw
                else:
                    try:
                        self.variables[name] = float(raw) if "." in raw else int(raw)
                    except ValueError:
                        try:
                            self.variables[name] = float(raw)
                        except ValueError:
                            self.variables[name] = 0.0

    def _exec_if(self, stmt: IfStmt):
        cond = self._eval(stmt.condition)
        if self._truthy(cond):
            self._exec_stmts(stmt.then_part)
        else:
            if stmt.else_part:
                self._exec_stmts(stmt.else_part)

    def _truthy(self, val) -> bool:
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return val != 0
        if isinstance(val, str):
            return len(val) > 0
        return bool(val)

    def _exec_for(self, stmt: ForStmt):
        start = self._to_number(self._eval(stmt.start))
        stop = self._to_number(self._eval(stmt.stop))
        step = self._to_number(self._eval(stmt.step)) if stmt.step else 1.0
        if step == 0:
            raise BasicRuntimeError("FOR step cannot be zero")

        var_name = stmt.var.name
        self.variables[var_name] = start

        # Check if there's already a FOR with this variable on the stack
        for entry in self.for_stack:
            if entry["var"] == var_name:
                # Re-entering the same FOR — pop old one
                self.for_stack.remove(entry)
                break

        self.for_stack.append({
            "var": var_name,
            "stop": stop,
            "step": step,
            "pc": self.pc,   # line index where FOR is
        })

    def _exec_next(self, stmt: NextStmt):
        # Find the matching FOR
        if stmt.var:
            var_name = stmt.var.name
            for_idx = None
            for i in range(len(self.for_stack) - 1, -1, -1):
                if self.for_stack[i]["var"] == var_name:
                    for_idx = i
                    break
            if for_idx is None:
                raise BasicRuntimeError(f"NEXT without FOR: {var_name}")
        else:
            if not self.for_stack:
                raise BasicRuntimeError("NEXT without FOR")
            for_idx = len(self.for_stack) - 1

        entry = self.for_stack[for_idx]
        var_name = entry["var"]

        current = self._to_number(self.variables.get(var_name, 0))
        step = entry["step"]
        stop = entry["stop"]

        current += step
        self.variables[var_name] = current

        # Check loop condition
        done = False
        if step > 0:
            done = current > stop
        else:
            done = current < stop

        if done:
            # Pop the FOR entry and continue after NEXT (normal flow)
            self.for_stack.pop(for_idx)
        else:
            # Loop back: set pc to the line AFTER the FOR statement.
            # The FOR line index is entry["pc"]. The next line to execute
            # is entry["pc"] + 1. We use pc = target - 1 convention since
            # run() will add +1 when it detects a jump.
            self.pc = entry["pc"]  # FOR line index
            # run() detects pc changed from current_pc, so it will add +1,
            # making us land at entry["pc"] + 1 (the line after FOR).

    def _exec_while(self, stmt: WhileStmt):
        cond = self._truthy(self._eval(stmt.condition))
        if not cond:
            # Skip to after WEND
            wend_info = self._find_wend(self.pc)
            if wend_info:
                self.pc = wend_info[0]  # wend line index
            else:
                raise BasicRuntimeError("WHILE without matching WEND")

    def _exec_wend(self, stmt: WendStmt):
        # Jump back to WHILE line
        while_info = self._find_while(self.pc)
        if while_info:
            self.pc = while_info[0]  # while line index
            # Decrement so that after run() increments, we're at the WHILE line
            self.pc -= 1  # will be incremented back in run()
        else:
            raise BasicRuntimeError("WEND without matching WHILE")

    def _exec_goto(self, stmt: GotoStmt):
        if stmt.line not in self.lines:
            raise BasicRuntimeError(f"GOTO: line {stmt.line} not found")
        idx = self.sorted_lines.index(stmt.line)
        self.pc = idx - 1  # -1 because run() will increment

    def _exec_gosub(self, stmt: GosubStmt):
        if stmt.line not in self.lines:
            raise BasicRuntimeError(f"GOSUB: line {stmt.line} not found")
        self.call_stack.append(self.pc)
        idx = self.sorted_lines.index(stmt.line)
        self.pc = idx - 1

    def _exec_return(self, stmt: ReturnStmt):
        if not self.call_stack:
            raise BasicRuntimeError("RETURN without GOSUB")
        self.pc = self.call_stack.pop()

    def _exec_dim(self, stmt: DimStmt):
        for name, dims in stmt.declarations:
            if name in self.arrays:
                raise BasicRuntimeError(f"Array {name} already dimensioned")
            if len(dims) == 1:
                self.arrays[name] = [0.0] * (dims[0] + 1)
            elif len(dims) == 2:
                self.arrays[name] = [[0.0] * (dims[1] + 1) for _ in range(dims[0] + 1)]
            else:
                raise BasicRuntimeError("DIM supports 1D and 2D arrays only")

    def _exec_read(self, stmt: ReadStmt):
        for var in stmt.vars:
            if self.data_pointer >= len(self.data_values):
                raise BasicRuntimeError("Out of DATA")
            raw = self.data_values[self.data_pointer]
            self.data_pointer += 1
            if isinstance(var, VarRef):
                name = var.name
                if name.endswith("$"):
                    self.variables[name] = str(raw)
                else:
                    try:
                        self.variables[name] = float(raw) if isinstance(raw, str) and "." in raw else (float(raw) if isinstance(raw, str) else raw)
                    except (ValueError, TypeError):
                        self.variables[name] = 0.0
            elif isinstance(var, ArrayRef):
                # Set array element
                indices = [int(self._eval(idx)) for idx in var.indices]
                self._set_array(var.name, indices, raw)

    def _exec_def_fn(self, stmt: DefFnStmt):
        fn_name = "FN" + stmt.name
        self.user_fns[fn_name] = stmt

    def _exec_on_goto(self, stmt: OnGotoStmt):
        val = int(self._to_number(self._eval(stmt.expr)))
        if 1 <= val <= len(stmt.targets):
            target = stmt.targets[val - 1]
            if target not in self.lines:
                raise BasicRuntimeError(f"ON GOTO: line {target} not found")
            idx = self.sorted_lines.index(target)
            self.pc = idx - 1
        else:
            pass  # Out of range: do nothing

    def _exec_on_gosub(self, stmt: OnGosubStmt):
        val = int(self._to_number(self._eval(stmt.expr)))
        if 1 <= val <= len(stmt.targets):
            target = stmt.targets[val - 1]
            if target not in self.lines:
                raise BasicRuntimeError(f"ON GOSUB: line {target} not found")
            self.call_stack.append(self.pc)
            idx = self.sorted_lines.index(target)
            self.pc = idx - 1
        else:
            pass

    def _exec_swap(self, stmt: SwapStmt):
        v1_name = self._get_lvalue_name(stmt.var1)
        v2_name = self._get_lvalue_name(stmt.var2)
        if v1_name in self.variables and v2_name in self.variables:
            self.variables[v1_name], self.variables[v2_name] = self.variables[v2_name], self.variables[v1_name]
        else:
            raise BasicRuntimeError("SWAP requires defined variables")

    def _get_lvalue_name(self, lv):
        if isinstance(lv, VarRef):
            return lv.name
        raise BasicRuntimeError("SWAP only supports simple variables")

    def _exec_color(self, stmt: ColorStmt):
        # ANSI color codes (simplified)
        fg = int(self._to_number(self._eval(stmt.fg))) if stmt.fg else 7
        ansi_fg = 30 + fg if fg < 8 else (90 + fg - 8) if fg < 16 else 37
        code = f"\033[{ansi_fg}m"
        if stmt.bg is not None:
            bg = int(self._to_number(self._eval(stmt.bg)))
            ansi_bg = 40 + bg if bg < 8 else (100 + bg - 8) if bg < 16 else 40
            code += f"\033[{ansi_bg}m"
        self.stdout.write(code)
        self.stdout.flush()

    def _exec_locate(self, stmt: LocateStmt):
        row = int(self._to_number(self._eval(stmt.row))) if stmt.row else 1
        col = int(self._to_number(self._eval(stmt.col))) if stmt.col else 1
        self.stdout.write(f"\033[{row};{col}H")
        self.stdout.flush()

    def _set_array(self, name, indices, value):
        if name not in self.arrays:
            if len(indices) == 1:
                self.arrays[name] = [0.0] * (max(indices[0], 10) + 1)
            elif len(indices) == 2:
                self.arrays[name] = [[0.0] * (max(indices[1], 10) + 1) for _ in range(max(indices[0], 10) + 1)]
        arr = self.arrays[name]
        if len(indices) == 1:
            if indices[0] >= len(arr):
                arr.extend([0.0] * (indices[0] - len(arr) + 1))
            arr[indices[0]] = value
        elif len(indices) == 2:
            if indices[0] >= len(arr):
                while len(arr) <= indices[0]:
                    arr.append([0.0] * (len(arr[0]) if arr else 11))
            if indices[1] >= len(arr[indices[0]]):
                arr[indices[0]].extend([0.0] * (indices[1] - len(arr[indices[0]]) + 1))
            arr[indices[0]][indices[1]] = value

    # ── Expression evaluation ──

    def _eval(self, expr) -> Any:
        if isinstance(expr, NumberLit):
            return expr.value
        if isinstance(expr, StringLit):
            return expr.value
        if isinstance(expr, VarRef):
            name = expr.name
            if name in self.variables:
                return self.variables[name]
            # Undeclared numeric variable defaults to 0
            if not name.endswith("$"):
                return 0.0
            return ""
        if isinstance(expr, ArrayRef):
            name = expr.name
            indices = [int(self._to_number(self._eval(idx))) for idx in expr.indices]
            if name not in self.arrays:
                if not name.endswith("$"):
                    return 0.0
                return ""
            arr = self.arrays[name]
            if len(indices) == 1:
                if indices[0] < len(arr):
                    return arr[indices[0]]
                return 0.0 if not name.endswith("$") else ""
            elif len(indices) == 2:
                if indices[0] < len(arr) and indices[1] < len(arr[0]):
                    return arr[indices[0]][indices[1]]
                return 0.0 if not name.endswith("$") else ""
        if isinstance(expr, FnCall):
            return self._eval_fn(expr)
        if isinstance(expr, UnaryOp):
            val = self._eval(expr.operand)
            if expr.op == "-":
                return -self._to_number(val)
            if expr.op == "NOT":
                return -1 if not self._truthy(val) else 0  # BASIC NOT: -1 for true, 0 for false
            raise BasicRuntimeError(f"Unknown unary op: {expr.op}")
        if isinstance(expr, BinOp):
            return self._eval_binop(expr)

        raise BasicRuntimeError(f"Cannot evaluate: {type(expr).__name__}")

    def _eval_fn(self, expr: FnCall) -> Any:
        name = expr.name

        # User-defined functions
        if name in self.user_fns:
            fn_def = self.user_fns[name]
            arg_vals = [self._eval(a) for a in expr.args]
            if len(arg_vals) != len(fn_def.params):
                raise BasicRuntimeError(f"FN {name}: expected {len(fn_def.params)} args, got {len(arg_vals)}")
            # Save current param values, set new ones
            saved = {}
            for param, val in zip(fn_def.params, arg_vals):
                saved[param] = self.variables.get(param)
                self.variables[param] = val
            try:
                result = self._eval(fn_def.body)
            finally:
                for param, old_val in saved.items():
                    if old_val is None:
                        self.variables.pop(param, None)
                    else:
                        self.variables[param] = old_val
            return result

        # Built-in functions
        args = [self._eval(a) for a in expr.args]

        if name == "ABS":
            return abs(self._to_number(args[0]))
        if name == "INT":
            return float(math.floor(self._to_number(args[0])))
        if name == "RND":
            if args:
                x = self._to_number(args[0])
                if x < 0:
                    random.seed(int(x))
                elif x == 0:
                    return random.random()
            return random.random()
        if name == "SQR":
            return math.sqrt(self._to_number(args[0]))
        if name == "SIN":
            return math.sin(self._to_number(args[0]))
        if name == "COS":
            return math.cos(self._to_number(args[0]))
        if name == "TAN":
            return math.tan(self._to_number(args[0]))
        if name == "ATN":
            return math.atan(self._to_number(args[0]))
        if name == "LOG":
            return math.log(self._to_number(args[0]))
        if name == "EXP":
            return math.exp(self._to_number(args[0]))
        if name == "LEN":
            return float(len(str(args[0])))
        if name == "LEFT$":
            s = str(args[0])
            n = int(self._to_number(args[1]))
            return s[:n]
        if name == "RIGHT$":
            s = str(args[0])
            n = int(self._to_number(args[1]))
            return s[-n:] if n > 0 else ""
        if name == "MID$":
            s = str(args[0])
            start = int(self._to_number(args[1])) - 1  # BASIC is 1-indexed
            if len(args) > 2:
                length = int(self._to_number(args[2]))
                return s[start:start + length]
            return s[start:]
        if name == "CHR$":
            return chr(int(self._to_number(args[0])))
        if name == "ASC":
            s = str(args[0])
            if not s:
                raise BasicRuntimeError("ASC of empty string")
            return float(ord(s[0]))
        if name == "STR$":
            val = args[0]
            if isinstance(val, float) and val == int(val):
                return " " + str(int(val))
            return str(val)
        if name == "VAL":
            s = str(args[0]).strip()
            try:
                if "." in s:
                    return float(s)
                return float(int(s))
            except ValueError:
                return 0.0
        if name == "TAB":
            n = int(self._to_number(args[0]))
            self.stdout.write(" " * max(0, n))
            return ""
        if name == "SPC":
            n = int(self._to_number(args[0]))
            self.stdout.write(" " * max(0, n))
            return ""
        if name == "STRING$":
            n = int(self._to_number(args[0]))
            if isinstance(args[1], (int, float)):
                return chr(int(args[1])) * n
            return str(args[1])[0] * n if str(args[1]) else ""
        if name == "INSTR":
            if len(args) == 2:
                haystack = str(args[0])
                needle = str(args[1])
                idx = haystack.find(needle)
                return float(idx + 1) if idx >= 0 else 0.0
            elif len(args) == 3:
                start = int(self._to_number(args[0])) - 1  # 1-indexed
                haystack = str(args[1])
                needle = str(args[2])
                idx = haystack.find(needle, start)
                return float(idx + 1) if idx >= 0 else 0.0
        if name == "TIMER":
            return time.time() % 86400
        if name == "PEEK":
            return 0.0  # stub

        raise BasicRuntimeError(f"Unknown function: {name}")

    def _eval_binop(self, expr: BinOp) -> Any:
        # Short-circuit for logical operators
        if expr.op == "AND":
            left = self._truthy(self._eval(expr.left))
            if not left:
                return 0
            right = self._truthy(self._eval(expr.right))
            return -1 if right else 0
        if expr.op == "OR":
            left = self._truthy(self._eval(expr.left))
            if left:
                return -1
            right = self._truthy(self._eval(expr.right))
            return -1 if right else 0

        left = self._eval(expr.left)
        right = self._eval(expr.right)

        # String concatenation
        if expr.op == "+" and (isinstance(left, str) or isinstance(right, str)):
            return str(left) + str(right)

        # String comparison
        if expr.op in ("=", "<>", "<", ">", "<=", ">=") and isinstance(left, str) and isinstance(right, str):
            if expr.op == "=":
                return -1 if left == right else 0
            if expr.op == "<>":
                return -1 if left != right else 0
            if expr.op == "<":
                return -1 if left < right else 0
            if expr.op == ">":
                return -1 if left > right else 0
            if expr.op == "<=":
                return -1 if left <= right else 0
            if expr.op == ">=":
                return -1 if left >= right else 0

        ln = self._to_number(left)
        rn = self._to_number(right)

        if expr.op == "+":
            return ln + rn
        if expr.op == "-":
            return ln - rn
        if expr.op == "*":
            return ln * rn
        if expr.op == "/":
            if rn == 0:
                raise BasicRuntimeError("Division by zero")
            return ln / rn
        if expr.op == "\\":
            if rn == 0:
                raise BasicRuntimeError("Division by zero")
            return float(int(ln) // int(rn))
        if expr.op == "MOD":
            if rn == 0:
                raise BasicRuntimeError("Division by zero")
            return float(int(ln) % int(rn))
        if expr.op == "^":
            return ln ** rn
        if expr.op == "=":
            return -1 if ln == rn else 0
        if expr.op == "<>":
            return -1 if ln != rn else 0
        if expr.op == "<":
            return -1 if ln < rn else 0
        if expr.op == ">":
            return -1 if ln > rn else 0
        if expr.op == "<=":
            return -1 if ln <= rn else 0
        if expr.op == ">=":
            return -1 if ln >= rn else 0

        raise BasicRuntimeError(f"Unknown operator: {expr.op}")

    def _to_number(self, val) -> float:
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            try:
                return float(val)
            except ValueError:
                return 0.0
        if isinstance(val, bool):
            return -1.0 if val else 0.0
        return 0.0

    # ── Reworked run() with proper PC management ──

    def run(self):
        """Run the loaded program with proper line advancement."""
        if not self.sorted_lines:
            return
        self.running = True
        self.pc = 0
        self._iteration_count = 0

        while self.running and 0 <= self.pc < len(self.sorted_lines):
            self._iteration_count += 1
            if self._iteration_count > self.max_iterations:
                raise BasicRuntimeError("Maximum iteration count exceeded")

            current_pc = self.pc
            line_num = self.sorted_lines[self.pc]

            if self.trace:
                self.stdout.write(f"[{line_num}] ")

            stmts = self.lines[line_num]
            self._exec_stmts(stmts)

            if not self.running:
                break

            # If pc was changed by a GOTO/GOSUB/WHILE/WEND etc., respect it
            if self.pc != current_pc:
                # pc was modified by a jump; since we use "pc = target - 1" convention,
                # we need to increment it now
                self.pc += 1
            else:
                # Normal advancement
                self.pc += 1


# ── REPL ────────────────────────────────────────────────────────────────────

def repl():
    """Interactive BASIC REPL."""
    interp = Interpreter()
    interp.stdout.write("BASIC Interpreter — type RUN to execute, LIST to view, QUIT to exit\n")
    interp.stdout.write("> ")
    interp.stdout.flush()

    program_lines: Dict[int, str] = {}

    try:
        while True:
            try:
                line = input()
            except EOFError:
                break

            line = line.strip()
            if not line:
                interp.stdout.write("> ")
                interp.stdout.flush()
                continue

            upper = line.upper()

            if upper == "QUIT" or upper == "EXIT" or upper == "SYSTEM":
                break

            if upper == "LIST":
                for ln in sorted(program_lines.keys()):
                    interp.stdout.write(f"{ln} {program_lines[ln]}\n")
                interp.stdout.write("> ")
                interp.stdout.flush()
                continue

            if upper == "RUN":
                source = "\n".join(f"{ln} {program_lines[ln]}" for ln in sorted(program_lines.keys()))
                try:
                    interp.load(source)
                    interp.run()
                except BasicError as e:
                    interp.stdout.write(f"Error: {e}\n")
                except BasicStopException:
                    interp.stdout.write("Break\n")
                interp.stdout.write("> ")
                interp.stdout.flush()
                continue

            if upper == "NEW":
                program_lines.clear()
                interp = Interpreter()
                interp.stdout.write("OK\n> ")
                interp.stdout.flush()
                continue

            # Check if it starts with a line number
            match = re.match(r'^(\d+)\s+(.*)', line)
            if match:
                line_num = int(match.group(1))
                code = match.group(2)
                program_lines[line_num] = code
                interp.stdout.write("> ")
                interp.stdout.flush()
                continue

            # Just a line number = delete
            if re.match(r'^\d+$', line):
                line_num = int(line)
                program_lines.pop(line_num, None)
                interp.stdout.write("> ")
                interp.stdout.flush()
                continue

            # Immediate execution
            try:
                interp.load(line)
            except BasicError as e:
                interp.stdout.write(f"Error: {e}\n")
            interp.stdout.write("> ")
            interp.stdout.flush()
    except KeyboardInterrupt:
        interp.stdout.write("\n")

    interp.stdout.write("Goodbye!\n")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="BASIC Language Interpreter")
    parser.add_argument("file", nargs="?", help="BASIC source file to run")
    parser.add_argument("-e", "--eval", help="Evaluate a one-liner")
    parser.add_argument("--trace", action="store_true", help="Trace line execution")
    parser.add_argument("--max-iter", type=int, default=10_000_000, help="Max iterations")
    args = parser.parse_args()

    interp = Interpreter()
    interp.trace = args.trace
    interp.max_iterations = args.max_iter

    if args.eval:
        try:
            interp.load(args.eval)
        except BasicError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if args.file:
        try:
            with open(args.file, "r") as f:
                source = f.read()
        except FileNotFoundError:
            print(f"File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        try:
            interp.load(source)
            interp.run()
        except BasicError as e:
            print(f"Error at line {interp.sorted_lines[interp.pc] if interp.pc < len(interp.sorted_lines) else '?'}: {e}", file=sys.stderr)
            sys.exit(1)
        except BasicStopException:
            print("Break")
        return

    repl()


if __name__ == "__main__":
    main()