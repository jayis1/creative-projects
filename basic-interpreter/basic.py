#!/usr/bin/env python3
"""
A full-featured interpreter for a classic BASIC dialect.

Supports:
  - Line-numbered programs with GOTO / GOSUB / RETURN
  - IF...THEN...ELSE / FOR...NEXT / WHILE...WEND / DO...LOOP
  - SELECT CASE multi-way branching
  - LET, PRINT, PRINT USING, INPUT, LINE INPUT, READ, DATA, RESTORE
  - DIM for arrays (1D and 2D), ERASE to deallocate
  - DEF FN for user-defined functions
  - String and numeric operations
  - Built-in functions: ABS, INT, RND, SQR, SIN, COS, TAN, ATN, LOG, EXP,
    LEN, LEFT$, RIGHT$, MID$, CHR$, ASC, STR$, VAL, TAB, SPC, STRING$,
    INSTR, TIMER, PEEK, DATE$, TIME$, INKEY$, FRE, ENVIRON$,
    LCASE$, UCASE$, LTRIM$, RTRIM$, FIX, SGN, CINT
  - Logical operators: AND, OR, NOT, XOR, EQV, IMP
  - Comparison operators: =, <>, <, >, <=, >=
  - REM for comments, END, STOP, BEEP statements
  - ON...GOTO / ON...GOSUB, ON ERROR GOTO / RESUME
  - SWAP statement
  - File I/O: OPEN, CLOSE, PRINT#, INPUT#, LINE INPUT#
  - COLOR, CLS, LOCATE (terminal control)
  - SELECT CASE with CASE IS, CASE expr TO expr, CASE ELSE

Usage:
    python3 basic.py program.bas           # run a program
    python3 basic.py -e "PRINT 42"        # one-liner
    python3 basic.py                       # interactive REPL
"""

from __future__ import annotations

import datetime
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
    DO = auto()
    LOOP = auto()
    UNTIL = auto()
    GOTO = auto()
    GOSUB = auto()
    RETURN = auto()
    DIM = auto()
    ERASE = auto()
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
    SELECT = auto()
    CASE = auto()
    IS = auto()
    OPEN = auto()
    CLOSE = auto()
    BEEP = auto()
    LINE = auto()
    USING = auto()
    ERROR = auto()
    RESUME = auto()
    XOR = auto()
    EQV = auto()
    IMP = auto()
    # Operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    CARET = auto()
    BACKSLASH = auto()
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
    HASH = auto()
    # Line number (only at start of line)
    LINENUM = auto()
    # EOF
    EOF = auto()


KEYWORDS = {
    "LET": TokenType.LET, "PRINT": TokenType.PRINT, "INPUT": TokenType.INPUT,
    "IF": TokenType.IF, "THEN": TokenType.THEN, "ELSE": TokenType.ELSE,
    "FOR": TokenType.FOR, "TO": TokenType.TO, "STEP": TokenType.STEP,
    "NEXT": TokenType.NEXT, "WHILE": TokenType.WHILE, "WEND": TokenType.WEND,
    "DO": TokenType.DO, "LOOP": TokenType.LOOP, "UNTIL": TokenType.UNTIL,
    "GOTO": TokenType.GOTO, "GOSUB": TokenType.GOSUB, "RETURN": TokenType.RETURN,
    "DIM": TokenType.DIM, "ERASE": TokenType.ERASE, "READ": TokenType.READ,
    "DATA": TokenType.DATA, "RESTORE": TokenType.RESTORE, "DEF": TokenType.DEF,
    "FN": TokenType.FN, "REM": TokenType.REM, "END": TokenType.END,
    "STOP": TokenType.STOP, "ON": TokenType.ON, "SWAP": TokenType.SWAP,
    "CLS": TokenType.CLS, "COLOR": TokenType.COLOR, "LOCATE": TokenType.LOCATE,
    "SELECT": TokenType.SELECT, "CASE": TokenType.CASE, "IS": TokenType.IS,
    "OPEN": TokenType.OPEN, "CLOSE": TokenType.CLOSE, "BEEP": TokenType.BEEP,
    "LINE": TokenType.LINE, "USING": TokenType.USING,
    "ERROR": TokenType.ERROR, "RESUME": TokenType.RESUME,
    "AND": TokenType.AND, "OR": TokenType.OR, "NOT": TokenType.NOT,
    "MOD": TokenType.MOD, "XOR": TokenType.XOR, "EQV": TokenType.EQV,
    "IMP": TokenType.IMP,
}


@dataclass
class Token:
    type: TokenType
    value: Any
    line: int = 0
    col: int = 0


# ── Lexer ────────────────────────────────────────────────────────────────────

class Lexer:
    """Tokenize a BASIC source line."""

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
                self._advance()
                if self.pos < len(self.text) and self.text[self.pos] == '"':
                    result.append('"')
                    self._advance()
                    continue
                return "".join(result)
            result.append(ch)
            self._advance()
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
            self._skip_spaces()
            self.tokens.append(Token(TokenType.LINENUM, int(num_str), self.line_num, start))

        while self.pos < len(self.text):
            self._skip_spaces()
            if self.pos >= len(self.text):
                break

            ch = self.text[self.pos]
            col = self.pos

            if ch == '"':
                s = self._read_string()
                self.tokens.append(Token(TokenType.STRING, s, self.line_num, col))
                continue

            if ch.isdigit() or (ch == "." and self.pos + 1 < len(self.text) and self.text[self.pos + 1].isdigit()):
                n = self._read_number()
                self.tokens.append(Token(TokenType.NUMBER, n, self.line_num, col))
                continue

            if ch.isalpha() or ch == "_":
                ident = self._read_ident()
                upper = ident.upper()
                if upper in KEYWORDS:
                    tok_type = KEYWORDS[upper]
                    if tok_type == TokenType.REM:
                        self.tokens.append(Token(TokenType.REM, self.text[self.pos:], self.line_num, col))
                        break
                    self.tokens.append(Token(tok_type, upper, self.line_num, col))
                else:
                    self.tokens.append(Token(TokenType.IDENT, ident, self.line_num, col))
                continue

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

            simple = {
                "+": TokenType.PLUS, "-": TokenType.MINUS,
                "*": TokenType.STAR, "/": TokenType.SLASH,
                "^": TokenType.CARET, "\\": TokenType.BACKSLASH,
                "(": TokenType.LPAREN, ")": TokenType.RPAREN,
                ",": TokenType.COMMA, ";": TokenType.SEMI,
                ":": TokenType.COLON, "=": TokenType.EQ,
                "#": TokenType.HASH,
            }
            if ch in simple:
                self._advance()
                self.tokens.append(Token(simple[ch], ch, self.line_num, col))
                continue

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
    indices: list

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
    target: Any
    value: Any

@dataclass
class PrintStmt:
    items: list
    using: Any = None

@dataclass
class InputStmt:
    prompt: Any
    vars: list

@dataclass
class LineInputStmt:
    prompt: Any
    var: Any
    file_num: Any = None

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
    step: Any

@dataclass
class NextStmt:
    var: Optional[VarRef]

@dataclass
class WhileStmt:
    condition: Any
    body: list  # not used for line-based; kept for API compat

@dataclass
class WendStmt:
    pass

# DO...LOOP: line-based markers
@dataclass
class DoStmt:
    """DO [WHILE|UNTIL condition] — start of a DO block."""
    pre_condition: Any = None
    pre_until: bool = False

@dataclass
class LoopStmt:
    """LOOP [WHILE|UNTIL condition] — end of a DO block."""
    post_condition: Any = None
    post_until: bool = False

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
    declarations: list

@dataclass
class EraseStmt:
    names: list

@dataclass
class ReadStmt:
    vars: list

@dataclass
class DataStmt:
    values: list

@dataclass
class RestoreStmt:
    line_num: Optional[int] = None

@dataclass
class DefFnStmt:
    name: str
    params: list
    body: Any

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

@dataclass
class BeepStmt:
    pass

# SELECT CASE: line-based markers
@dataclass
class SelectCaseStmt:
    """SELECT CASE expr — start of a SELECT block."""
    test_expr: Any

@dataclass
class CaseStmt:
    """CASE conditions — a case branch within SELECT."""
    conditions: list  # list of CaseCondition

@dataclass
class CaseElseStmt:
    """CASE ELSE — default case branch."""
    pass

@dataclass
class EndSelectStmt:
    """END SELECT — end of a SELECT block."""
    pass

@dataclass
class CaseCondition:
    """A single CASE condition: value, IS op value, value TO value."""
    low: Any = None
    high: Any = None
    is_op: str = None
    is_val: Any = None

@dataclass
class OpenStmt:
    filename: Any
    mode: str
    file_num: Any

@dataclass
class CloseStmt:
    file_num: Any = None

@dataclass
class PrintFileStmt:
    file_num: Any
    items: list

@dataclass
class InputFileStmt:
    file_num: Any
    vars: list

@dataclass
class OnErrorStmt:
    line: int

@dataclass
class ResumeStmt:
    line: Optional[int] = None


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
        if tok.type == TokenType.LINE:
            return self._parse_line_input()
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
        if tok.type == TokenType.DO:
            return self._parse_do()
        if tok.type == TokenType.LOOP:
            return self._parse_loop()
        if tok.type == TokenType.GOTO:
            return self._parse_goto()
        if tok.type == TokenType.GOSUB:
            return self._parse_gosub()
        if tok.type == TokenType.RETURN:
            self._advance()
            return ReturnStmt()
        if tok.type == TokenType.DIM:
            return self._parse_dim()
        if tok.type == TokenType.ERASE:
            return self._parse_erase()
        if tok.type == TokenType.READ:
            return self._parse_read()
        if tok.type == TokenType.DATA:
            return self._parse_data()
        if tok.type == TokenType.RESTORE:
            return self._parse_restore()
        if tok.type == TokenType.DEF:
            return self._parse_def_fn()
        if tok.type == TokenType.END:
            # Could be END or END SELECT or END IF
            self._advance()
            if self._peek().type == TokenType.SELECT:
                self._advance()
                return EndSelectStmt()
            if self._peek().type == TokenType.IF:
                self._advance()
                # END IF is a no-op in single-line IF
                return RemStmt("END IF")
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
        if tok.type == TokenType.BEEP:
            self._advance()
            return BeepStmt()
        if tok.type == TokenType.REM:
            self._advance()
            return RemStmt(tok.value or "")
        if tok.type == TokenType.SELECT:
            return self._parse_select_case()
        if tok.type == TokenType.CASE:
            return self._parse_case()
        if tok.type == TokenType.OPEN:
            return self._parse_open()
        if tok.type == TokenType.CLOSE:
            return self._parse_close()
        if tok.type == TokenType.ERROR:
            return self._parse_error_stmt()
        if tok.type == TokenType.RESUME:
            return self._parse_resume()

        # Implicit LET
        if tok.type == TokenType.IDENT:
            next_pos = self.pos + 1
            while next_pos < len(self.tokens) and self.tokens[next_pos].type in (TokenType.LPAREN,):
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

        # Hash followed by number = file reference
        if tok.type == TokenType.HASH:
            return self._parse_file_print()

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

    def _parse_print(self):
        self._expect(TokenType.PRINT)
        using = None
        if self._peek().type == TokenType.USING:
            self._advance()
            using = self._parse_expr()
            if self._match(TokenType.SEMI):
                pass
        if self._peek().type == TokenType.HASH:
            self._advance()
            file_num = self._parse_expr()
            if self._match(TokenType.COMMA):
                pass
            items = self._parse_print_items()
            return PrintFileStmt(file_num, items)
        items = self._parse_print_items()
        return PrintStmt(items, using)

    def _parse_print_items(self) -> list:
        items = []
        if self._peek().type in (TokenType.EOF, TokenType.COLON):
            return [(None, None)]

        while True:
            if self._peek().type in (TokenType.SEMI, TokenType.COMMA):
                sep = self._advance()
                items.append((None, sep.value))
                if self._peek().type in (TokenType.EOF, TokenType.COLON):
                    break
                continue

            expr = self._parse_expr()
            sep_tok = self._match(TokenType.SEMI, TokenType.COMMA)
            if sep_tok:
                items.append((expr, sep_tok.value))
                if self._peek().type in (TokenType.EOF, TokenType.COLON):
                    break
            else:
                items.append((expr, None))
                break
        return items

    def _parse_input(self):
        self._expect(TokenType.INPUT)
        if self._peek().type == TokenType.HASH:
            self._advance()
            file_num = self._parse_expr()
            self._match(TokenType.COMMA)
            vars_ = [self._parse_lvalue()]
            while self._match(TokenType.COMMA):
                vars_.append(self._parse_lvalue())
            return InputFileStmt(file_num, vars_)

        prompt = None
        if self._peek().type == TokenType.STRING:
            prompt = StringLit(self._advance().value)
            if self._match(TokenType.SEMI):
                pass
            elif self._match(TokenType.COMMA):
                pass
        vars_ = []
        vars_.append(self._parse_lvalue())
        while self._match(TokenType.COMMA):
            vars_.append(self._parse_lvalue())
        return InputStmt(prompt, vars_)

    def _parse_line_input(self):
        self._expect(TokenType.LINE)
        self._expect(TokenType.INPUT)
        file_num = None
        if self._peek().type == TokenType.HASH:
            self._advance()
            file_num = self._parse_expr()
            self._match(TokenType.COMMA)
        prompt = None
        if self._peek().type == TokenType.STRING:
            prompt = StringLit(self._advance().value)
            self._match(TokenType.SEMI)
        var = self._parse_lvalue()
        return LineInputStmt(prompt, var, file_num)

    def _parse_if(self):
        self._expect(TokenType.IF)
        condition = self._parse_expr()
        self._expect(TokenType.THEN)
        if self._peek().type == TokenType.NUMBER:
            line_num = int(self._advance().value)
            then_part = [GotoStmt(line_num)]
        else:
            then_part = self._parse_stmts()
        else_part = []
        if self._peek().type == TokenType.ELSE:
            self._advance()
            if self._peek().type == TokenType.NUMBER:
                line_num = int(self._advance().value)
                else_part = [GotoStmt(line_num)]
            else:
                else_part = self._parse_stmts()
        return IfStmt(condition, then_part, else_part)

    def _parse_for(self):
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

    def _parse_next(self):
        self._expect(TokenType.NEXT)
        var = None
        if self._peek().type == TokenType.IDENT:
            var = VarRef(self._normalize_var(self._advance().value))
        return NextStmt(var)

    def _parse_while(self):
        self._expect(TokenType.WHILE)
        condition = self._parse_expr()
        return WhileStmt(condition, [])

    def _parse_do(self):
        self._expect(TokenType.DO)
        pre_condition = None
        pre_until = False
        if self._match(TokenType.WHILE):
            pre_condition = self._parse_expr()
        elif self._match(TokenType.UNTIL):
            pre_condition = self._parse_expr()
            pre_until = True
        return DoStmt(pre_condition, pre_until)

    def _parse_loop(self):
        self._expect(TokenType.LOOP)
        post_condition = None
        post_until = False
        if self._match(TokenType.WHILE):
            post_condition = self._parse_expr()
        elif self._match(TokenType.UNTIL):
            post_condition = self._parse_expr()
            post_until = True
        return LoopStmt(post_condition, post_until)

    def _parse_goto(self):
        self._expect(TokenType.GOTO)
        line = int(self._expect(TokenType.NUMBER).value)
        return GotoStmt(line)

    def _parse_gosub(self):
        self._expect(TokenType.GOSUB)
        line = int(self._expect(TokenType.NUMBER).value)
        return GosubStmt(line)

    def _parse_dim(self):
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

    def _parse_erase(self):
        self._expect(TokenType.ERASE)
        names = [self._normalize_var(self._expect(TokenType.IDENT).value)]
        while self._match(TokenType.COMMA):
            names.append(self._normalize_var(self._expect(TokenType.IDENT).value))
        return EraseStmt(names)

    def _parse_read(self):
        self._expect(TokenType.READ)
        vars_ = [self._parse_lvalue()]
        while self._match(TokenType.COMMA):
            vars_.append(self._parse_lvalue())
        return ReadStmt(vars_)

    def _parse_data(self):
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
        if tok.type == TokenType.IDENT:
            self._advance()
            return tok.value
        raise BasicSyntaxError(f"Unexpected token in DATA: {tok}")

    def _parse_restore(self):
        self._expect(TokenType.RESTORE)
        line_num = None
        if self._peek().type == TokenType.NUMBER:
            line_num = int(self._advance().value)
        return RestoreStmt(line_num)

    def _parse_def_fn(self):
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
        if self._peek().type == TokenType.ERROR:
            self._advance()
            self._expect(TokenType.GOTO)
            if self._peek().type == TokenType.NUMBER:
                line = int(self._advance().value)
                return OnErrorStmt(line)
            raise BasicSyntaxError("Expected line number after ON ERROR GOTO")
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

    def _parse_swap(self):
        self._expect(TokenType.SWAP)
        v1 = self._parse_lvalue()
        self._expect(TokenType.COMMA)
        v2 = self._parse_lvalue()
        return SwapStmt(v1, v2)

    def _parse_color(self):
        self._expect(TokenType.COLOR)
        fg = self._parse_expr()
        bg = None
        if self._match(TokenType.COMMA):
            bg = self._parse_expr()
        return ColorStmt(fg, bg)

    def _parse_locate(self):
        self._expect(TokenType.LOCATE)
        row = self._parse_expr()
        col = None
        if self._match(TokenType.COMMA):
            col = self._parse_expr()
        return LocateStmt(row, col)

    def _parse_select_case(self):
        self._expect(TokenType.SELECT)
        self._expect(TokenType.CASE)
        test_expr = self._parse_expr()
        return SelectCaseStmt(test_expr)

    def _parse_case(self):
        self._expect(TokenType.CASE)
        # CASE ELSE
        if self._peek().type == TokenType.ELSE:
            self._advance()
            return CaseElseStmt()
        # Parse case conditions
        conditions = [self._parse_case_condition()]
        while self._match(TokenType.COMMA):
            conditions.append(self._parse_case_condition())
        return CaseStmt(conditions)

    def _parse_case_condition(self) -> CaseCondition:
        if self._peek().type == TokenType.IS:
            self._advance()
            comp_types = {TokenType.EQ: "=", TokenType.NE: "<>",
                          TokenType.LT: "<", TokenType.GT: ">",
                          TokenType.LE: "<=", TokenType.GE: ">="}
            if self._peek().type in comp_types:
                op = comp_types[self._peek().type]
                self._advance()
                val = self._parse_expr()
                return CaseCondition(is_op=op, is_val=val)
            raise BasicSyntaxError("Expected comparison after IS")

        expr1 = self._parse_expr()
        if self._match(TokenType.TO):
            expr2 = self._parse_expr()
            return CaseCondition(low=expr1, high=expr2)
        return CaseCondition(low=expr1)

    def _parse_open(self):
        self._expect(TokenType.OPEN)
        filename = self._parse_expr()
        # OPEN file$ FOR mode AS #n  or  OPEN mode, #n, file$
        # Try FOR syntax
        if self._peek().type == TokenType.FOR:
            self._advance()
            # Mode is an identifier (INPUT, OUTPUT, APPEND) — but these are keywords
            # Accept either keyword or identifier
            mode_tok = self._peek()
            if mode_tok.type == TokenType.IDENT:
                mode = self._advance().value.upper()
            elif mode_tok.type == TokenType.INPUT:
                mode = "INPUT"
                self._advance()
            else:
                # OUTPUT, APPEND are not keywords; treat as IDENT
                # But the lexer won't recognize them since they're not in KEYWORDS
                # So they should arrive as IDENT tokens
                raise BasicSyntaxError(f"Expected file mode after FOR, got {mode_tok}")
            if mode not in ("INPUT", "OUTPUT", "APPEND", "I", "O", "A"):
                raise BasicSyntaxError(f"Invalid file mode: {mode}")
            mode_map = {"INPUT": "I", "OUTPUT": "O", "APPEND": "A"}
            mode = mode_map.get(mode, mode)
            # Optional AS
            if self._peek().type == TokenType.IDENT and self._peek().value.upper() == "AS":
                self._advance()
            self._expect(TokenType.HASH)
            file_num = self._parse_expr()
            return OpenStmt(filename, mode, file_num)
        else:
            # Old syntax: OPEN "I", #1, "file"
            mode_expr = self._parse_expr()
            mode = str(self._eval_const(mode_expr)).upper() if isinstance(mode_expr, StringLit) else "I"
            self._expect(TokenType.COMMA)
            self._expect(TokenType.HASH)
            file_num = self._parse_expr()
            return OpenStmt(filename, mode, file_num)

    def _eval_const(self, expr):
        """Evaluate a constant expression at parse time."""
        if isinstance(expr, StringLit):
            return expr.value
        if isinstance(expr, NumberLit):
            return expr.value
        return None

    def _parse_close(self):
        self._expect(TokenType.CLOSE)
        file_num = None
        if self._peek().type == TokenType.HASH:
            self._advance()
            file_num = self._parse_expr()
        elif self._peek().type == TokenType.NUMBER:
            file_num = self._parse_expr()
        return CloseStmt(file_num)

    def _parse_file_print(self):
        self._expect(TokenType.HASH)
        file_num = self._parse_expr()
        if self._match(TokenType.COMMA):
            pass
        items = self._parse_print_items()
        return PrintFileStmt(file_num, items)

    def _parse_error_stmt(self):
        """Parse ERROR statement (standalone, not ON ERROR)."""
        self._expect(TokenType.ERROR)
        expr = self._parse_expr()
        return expr  # Just evaluate the expression for now

    def _parse_resume(self):
        self._expect(TokenType.RESUME)
        line = None
        if self._peek().type == TokenType.NUMBER:
            line = int(self._advance().value)
        elif self._peek().type == TokenType.NEXT:
            self._advance()
            line = -1  # RESUME NEXT
        return ResumeStmt(line)

    # ── Expression parsing ──

    def _parse_expr(self) -> Any:
        return self._parse_imp()

    def _parse_imp(self) -> Any:
        left = self._parse_eqv()
        while self._peek().type == TokenType.IMP:
            self._advance()
            right = self._parse_eqv()
            left = BinOp("IMP", left, right)
        return left

    def _parse_eqv(self) -> Any:
        left = self._parse_xor()
        while self._peek().type == TokenType.EQV:
            self._advance()
            right = self._parse_xor()
            left = BinOp("EQV", left, right)
        return left

    def _parse_xor(self) -> Any:
        left = self._parse_or()
        while self._peek().type == TokenType.XOR:
            self._advance()
            right = self._parse_or()
            left = BinOp("XOR", left, right)
        return left

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
            exp = self._parse_power()
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

        if tok.type == TokenType.NUMBER:
            self._advance()
            return NumberLit(tok.value)

        if tok.type == TokenType.STRING:
            self._advance()
            return StringLit(tok.value)

        if tok.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_expr()
            self._expect(TokenType.RPAREN)
            return expr

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

        if tok.type == TokenType.IDENT:
            name = tok.value
            upper = name.upper()
            builtin_funcs = {
                "ABS", "INT", "RND", "SQR", "SIN", "COS", "TAN", "ATN",
                "LOG", "EXP", "LEN", "LEFT$", "RIGHT$", "MID$",
                "CHR$", "ASC", "STR$", "VAL", "TAB", "SPC",
                "STRING$", "INSTR", "TIMER", "PEEK",
                "DATE$", "TIME$", "INKEY$", "FRE", "ENVIRON$",
                "LCASE$", "UCASE$", "LTRIM$", "RTRIM$",
                "FIX", "SGN", "CSNG", "CDBL", "CINT",
            }
            if upper in builtin_funcs and self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].type == TokenType.LPAREN:
                self._advance()
                self._expect(TokenType.LPAREN)
                args = []
                if self._peek().type != TokenType.RPAREN:
                    args.append(self._parse_expr())
                    while self._match(TokenType.COMMA):
                        args.append(self._parse_expr())
                self._expect(TokenType.RPAREN)
                return FnCall(upper, args)

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
        return name.upper()


# ── Exceptions ───────────────────────────────────────────────────────────────

class BasicError(Exception):
    pass

class BasicSyntaxError(BasicError):
    pass

class BasicRuntimeError(BasicError):
    pass

class BasicStopException(Exception):
    pass


# ── Interpreter ─────────────────────────────────────────────────────────────

class Interpreter:
    """Execute BASIC programs."""

    def __init__(self, stdin=None, stdout=None):
        self.lines: Dict[int, list] = {}
        self.sorted_lines: List[int] = []
        self._line_to_idx: Dict[int, int] = {}  # line_number -> index in sorted_lines, for O(1) lookup
        self.variables: Dict[str, Any] = {}
        self.arrays: Dict[str, Any] = {}
        self.data_values: List[Any] = []
        self.data_pointer: int = 0
        self.call_stack: List[int] = []
        self.for_stack: List[dict] = []
        self.while_stack: List[Tuple[int, int, int, int]] = []
        # DO...LOOP cross-reference: (do_line_idx, loop_line_idx) pairs
        self.do_loop_pairs: List[Tuple[int, int]] = []
        # SELECT CASE cross-reference: maps select_line_idx -> (case_indices, case_else_idx, end_select_idx)
        self.select_info: Dict[int, dict] = {}
        self.user_fns: Dict[str, DefFnStmt] = {}
        self.pc: int = 0
        self.running: bool = False
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout
        self.trace: bool = False
        self.max_iterations: int = 10_000_000
        self._iteration_count: int = 0
        self._print_col: int = 0
        self._files: Dict[int, Any] = {}
        self._on_error_line: Optional[int] = None
        self._error_occurred: bool = False
        self._error_resume_line: Optional[int] = None
        # SELECT CASE runtime tracking
        # _active_select_end: the END SELECT line index (None if not in a SELECT block)
        # _active_select_matched: the line index of the matched CASE (None until matched)
        self._active_select_end: Optional[int] = None
        self._active_select_matched: Optional[int] = None

    def __del__(self):
        """Clean up open file handles on interpreter destruction."""
        for f in self._files.values():
            try:
                f.close()
            except OSError:
                pass

    # ── Program loading ──

    def load(self, source: str):
        # Close any previously open files before loading new program
        for f in self._files.values():
            try:
                f.close()
            except OSError:
                pass
        self._files.clear()
        
        self.lines.clear()
        self.data_values.clear()
        self.data_pointer = 0
        self.variables.clear()
        self.arrays.clear()
        self.call_stack.clear()
        self.for_stack.clear()
        self.while_stack.clear()
        self.do_loop_pairs.clear()
        self.select_info.clear()
        self.user_fns.clear()
        self._on_error_line = None
        self._error_occurred = False
        self._active_select_end = None
        self._active_select_matched = None

        immediate_stmts = []
        for raw_line in source.splitlines():
            raw_line = raw_line.rstrip()
            if not raw_line.strip():
                continue
            try:
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
            except BasicSyntaxError:
                raise

        self._rebuild()
        self._collect_data()
        self._resolve_while_wend()
        self._resolve_do_loop()
        self._resolve_select_case()

        if immediate_stmts:
            self.running = True
            self._exec_stmts(immediate_stmts)

    def _rebuild(self):
        self.sorted_lines = sorted(self.lines.keys())
        self._line_to_idx = {ln: i for i, ln in enumerate(self.sorted_lines)}

    def _collect_data(self):
        self.data_values = []
        self.data_pointer = 0
        for ln in self.sorted_lines:
            for stmt in self.lines[ln]:
                if isinstance(stmt, DataStmt):
                    self.data_values.extend(stmt.values)

    def _resolve_while_wend(self):
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

    def _resolve_do_loop(self):
        """Match DO and LOOP statements across lines."""
        self.do_loop_pairs = []
        stack = []
        for i, ln in enumerate(self.sorted_lines):
            stmts = self.lines[ln]
            for j, stmt in enumerate(stmts):
                if isinstance(stmt, DoStmt):
                    stack.append(i)
                elif isinstance(stmt, LoopStmt):
                    if not stack:
                        raise BasicSyntaxError("LOOP without matching DO")
                    do_idx = stack.pop()
                    self.do_loop_pairs.append((do_idx, i))
        if stack:
            raise BasicSyntaxError("DO without matching LOOP")

    def _find_loop_for_do(self, do_line_idx: int) -> Optional[int]:
        for do_idx, loop_idx in self.do_loop_pairs:
            if do_idx == do_line_idx:
                return loop_idx
        return None

    def _find_do_for_loop(self, loop_line_idx: int) -> Optional[int]:
        for do_idx, loop_idx in self.do_loop_pairs:
            if loop_idx == loop_line_idx:
                return do_idx
        return None

    def _resolve_select_case(self):
        """Match SELECT CASE, CASE, CASE ELSE, END SELECT across lines."""
        self.select_info = {}
        select_stack = []
        for i, ln in enumerate(self.sorted_lines):
            stmts = self.lines[ln]
            for j, stmt in enumerate(stmts):
                if isinstance(stmt, SelectCaseStmt):
                    select_stack.append({"select_idx": i, "case_indices": [], "case_else_idx": None})
                elif isinstance(stmt, CaseStmt):
                    if select_stack:
                        select_stack[-1]["case_indices"].append(i)
                elif isinstance(stmt, CaseElseStmt):
                    if select_stack:
                        select_stack[-1]["case_else_idx"] = i
                elif isinstance(stmt, EndSelectStmt):
                    if select_stack:
                        info = select_stack.pop()
                        info["end_select_idx"] = i
                        self.select_info[info["select_idx"]] = info
        if select_stack:
            raise BasicSyntaxError("SELECT CASE without END SELECT")

    # ── Execution ──

    def run(self):
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
            try:
                self._exec_stmts(stmts)
            except BasicRuntimeError as e:
                if self._on_error_line is not None and self._on_error_line != 0:
                    self._error_occurred = True
                    self._error_resume_line = current_pc
                    if self._on_error_line in self._line_to_idx:
                        idx = self._line_to_idx[self._on_error_line]
                        self.pc = idx - 1
                    else:
                        raise
                else:
                    raise

            if not self.running:
                break

            if self.pc != current_pc:
                self.pc += 1
            else:
                self.pc += 1

    def _exec_stmts(self, stmts: list):
        for stmt in stmts:
            if not self.running:
                return
            self._exec_stmt(stmt)

    def _exec_stmt(self, stmt: Any):
        if isinstance(stmt, (NumberLit, StringLit, BinOp, UnaryOp)):
            self._eval(stmt)
            return

        if isinstance(stmt, LetStmt):
            self._exec_let(stmt)
        elif isinstance(stmt, PrintStmt):
            self._exec_print(stmt)
        elif isinstance(stmt, InputStmt):
            self._exec_input(stmt)
        elif isinstance(stmt, LineInputStmt):
            self._exec_line_input(stmt)
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
        elif isinstance(stmt, DoStmt):
            self._exec_do(stmt)
        elif isinstance(stmt, LoopStmt):
            self._exec_loop(stmt)
        elif isinstance(stmt, GotoStmt):
            self._exec_goto(stmt)
        elif isinstance(stmt, GosubStmt):
            self._exec_gosub(stmt)
        elif isinstance(stmt, ReturnStmt):
            self._exec_return(stmt)
        elif isinstance(stmt, DimStmt):
            self._exec_dim(stmt)
        elif isinstance(stmt, EraseStmt):
            self._exec_erase(stmt)
        elif isinstance(stmt, ReadStmt):
            self._exec_read(stmt)
        elif isinstance(stmt, DataStmt):
            pass  # collected at load time
        elif isinstance(stmt, RestoreStmt):
            self._exec_restore(stmt)
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
            self._exec_cls(stmt)
        elif isinstance(stmt, ColorStmt):
            self._exec_color(stmt)
        elif isinstance(stmt, LocateStmt):
            self._exec_locate(stmt)
        elif isinstance(stmt, BeepStmt):
            self._exec_beep(stmt)
        elif isinstance(stmt, SelectCaseStmt):
            self._exec_select_case(stmt)
        elif isinstance(stmt, CaseStmt):
            # CASE encountered during line-by-line execution.
            # If we're inside a SELECT block and this CASE is NOT the one we matched,
            # skip to END SELECT to prevent fall-through into the next case body.
            if self._active_select_end is not None and self._active_select_matched is not None:
                if self.pc != self._active_select_matched:
                    self.pc = self._active_select_end
                    self._active_select_end = None
                    self._active_select_matched = None
        elif isinstance(stmt, CaseElseStmt):
            # Same as CaseStmt — skip to END SELECT if this is not our matched case
            if self._active_select_end is not None and self._active_select_matched is not None:
                if self.pc != self._active_select_matched:
                    self.pc = self._active_select_end
                    self._active_select_end = None
                    self._active_select_matched = None
        elif isinstance(stmt, EndSelectStmt):
            # END SELECT clears the active select tracking
            self._active_select_end = None
            self._active_select_matched = None
        elif isinstance(stmt, OpenStmt):
            self._exec_open(stmt)
        elif isinstance(stmt, CloseStmt):
            self._exec_close(stmt)
        elif isinstance(stmt, PrintFileStmt):
            self._exec_print_file(stmt)
        elif isinstance(stmt, InputFileStmt):
            self._exec_input_file(stmt)
        elif isinstance(stmt, OnErrorStmt):
            self._exec_on_error(stmt)
        elif isinstance(stmt, ResumeStmt):
            self._exec_resume(stmt)
        elif isinstance(stmt, FnCall):
            self._eval(stmt)
        else:
            raise BasicRuntimeError(f"Unknown statement: {type(stmt).__name__}")

    def _exec_let(self, stmt: LetStmt):
        value = self._eval(stmt.value)
        if isinstance(stmt.target, VarRef):
            self.variables[stmt.target.name] = value
        elif isinstance(stmt.target, ArrayRef):
            self._set_array_ref(stmt.target, value)
        else:
            raise BasicRuntimeError(f"Invalid LET target: {stmt.target}")

    def _set_array_ref(self, ref: ArrayRef, value: Any):
        name = ref.name
        indices = [int(self._eval(idx)) for idx in ref.indices]
        if name not in self.arrays:
            dim_count = len(indices)
            if dim_count == 1:
                self.arrays[name] = [0.0] * (max(indices[0], 10) + 1)
            elif dim_count == 2:
                self.arrays[name] = [[0.0] * (max(indices[1], 10) + 1) for _ in range(max(indices[0], 10) + 1)]
        arr = self.arrays[name]
        if len(indices) == 1:
            if indices[0] < 0:
                raise BasicRuntimeError("Negative array index")
            if indices[0] >= len(arr):
                arr.extend([0.0] * (indices[0] - len(arr) + 1))
            arr[indices[0]] = value
        elif len(indices) == 2:
            if indices[0] < 0 or indices[1] < 0:
                raise BasicRuntimeError("Negative array index")
            if indices[0] >= len(arr):
                while len(arr) <= indices[0]:
                    arr.append([0.0] * (len(arr[0]) if arr else [0.0] * 11))
            if indices[1] >= len(arr[indices[0]]):
                arr[indices[0]].extend([0.0] * (indices[1] - len(arr[indices[0]]) + 1))
            arr[indices[0]][indices[1]] = value

    def _exec_print(self, stmt: PrintStmt):
        if stmt.using:
            self._exec_print_using(stmt)
            return
        end_newline = True
        zone_width = 14
        for expr, sep in stmt.items:
            if expr is not None:
                val = self._eval(expr)
                text = self._format_value(val)
                self.stdout.write(text)
                self._print_col += len(text)
            if sep == ";":
                end_newline = False
            elif sep == ",":
                spaces = zone_width - (self._print_col % zone_width)
                self.stdout.write(" " * spaces)
                self._print_col += spaces
                end_newline = False
            else:
                end_newline = True
        if end_newline:
            self.stdout.write("\n")
            self._print_col = 0
        self.stdout.flush()

    def _format_value(self, val) -> str:
        if isinstance(val, (int, float)):
            # BASIC prints numbers with a leading space (sign position) and trailing space
            if isinstance(val, float) and val == int(val) and abs(val) < 1e15:
                return " " + str(int(val)) + " "
            if isinstance(val, int):
                return " " + str(val) + " "
            return " " + str(val) + " "
        return str(val)

    def _exec_print_using(self, stmt: PrintStmt):
        fmt = str(self._eval(stmt.using))
        items = [(self._eval(expr), sep) for expr, sep in stmt.items if expr is not None]
        result = self._apply_print_using(fmt, items)
        self.stdout.write(result)
        if not stmt.items or stmt.items[-1][1] is None:
            self.stdout.write("\n")
        self.stdout.flush()

    def _apply_print_using(self, fmt: str, items: list) -> str:
        result = []
        fi = 0
        ii = 0
        while fi < len(fmt):
            ch = fmt[fi]
            if ch == "#":
                width = 0
                decimal = 0
                has_decimal = False
                while fi < len(fmt) and fmt[fi] in ("#", ".", ","):
                    if fmt[fi] == "#":
                        width += 1
                        if has_decimal:
                            decimal += 1
                    elif fmt[fi] == ".":
                        has_decimal = True
                    fi += 1
                if ii < len(items):
                    val = self._to_number(items[ii][0])
                    ii += 1
                    if has_decimal:
                        s = f"{val:{width + 1}.{decimal}f}"
                    else:
                        s = f"{int(val):>{width}d}"
                    result.append(s)
                continue
            elif ch == "&":
                fi += 1
                if ii < len(items):
                    val = str(items[ii][0])
                    ii += 1
                    result.append(val)
                continue
            elif ch == "\\" and fi + 1 < len(fmt) and fmt[fi + 1] == " ":
                fi += 1
                width = 2
                while fi < len(fmt) and fmt[fi] == " ":
                    width += 1
                    fi += 1
                if fi < len(fmt) and fmt[fi] == "\\":
                    width += 1
                    fi += 1
                if ii < len(items):
                    val = str(items[ii][0])
                    ii += 1
                    result.append(val[:width].ljust(width))
                continue
            elif ch == "!":
                fi += 1
                if ii < len(items):
                    val = str(items[ii][0])
                    ii += 1
                    result.append(val[0] if val else " ")
                continue
            else:
                result.append(ch)
                fi += 1
        return "".join(result)

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

        values = [v.strip() for v in line.split(",")]
        for i, var in enumerate(stmt.vars):
            raw = values[i] if i < len(values) else ""
            if isinstance(var, VarRef):
                self._assign_input_var(var.name, raw)

    def _exec_line_input(self, stmt: LineInputStmt):
        if stmt.file_num is not None:
            fnum = int(self._to_number(self._eval(stmt.file_num)))
            if fnum not in self._files:
                raise BasicRuntimeError(f"File #{fnum} not open")
            line = self._files[fnum].readline()
            if not line:
                raise BasicRuntimeError(f"End of file #{fnum}")
            line = line.rstrip("\n\r")
            if isinstance(stmt.var, VarRef):
                self.variables[stmt.var.name] = line
            return

        prompt = ""
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

        if isinstance(stmt.var, VarRef):
            self.variables[stmt.var.name] = line

    def _assign_input_var(self, name: str, raw: str):
        if name.endswith("$"):
            self.variables[name] = raw
        else:
            try:
                self.variables[name] = float(raw) if "." in raw else float(int(raw))
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

        for entry in self.for_stack:
            if entry["var"] == var_name:
                self.for_stack.remove(entry)
                break

        self.for_stack.append({
            "var": var_name,
            "stop": stop,
            "step": step,
            "pc": self.pc,
        })

    def _exec_next(self, stmt: NextStmt):
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

        done = (step > 0 and current > stop) or (step < 0 and current < stop)

        if done:
            self.for_stack.pop(for_idx)
        else:
            self.pc = entry["pc"]

    def _exec_while(self, stmt: WhileStmt):
        cond = self._truthy(self._eval(stmt.condition))
        if not cond:
            wend_info = self._find_wend(self.pc)
            if wend_info:
                self.pc = wend_info[0]
            else:
                raise BasicRuntimeError("WHILE without matching WEND")

    def _exec_wend(self, stmt: WendStmt):
        while_info = self._find_while(self.pc)
        if while_info:
            self.pc = while_info[0]
            self.pc -= 1  # will be incremented back in run()
        else:
            raise BasicRuntimeError("WEND without matching WHILE")

    def _exec_do(self, stmt: DoStmt):
        """DO statement: check pre-condition, skip to LOOP if false."""
        if stmt.pre_condition is not None:
            cond = self._truthy(self._eval(stmt.pre_condition))
            if stmt.pre_until:
                cond = not cond
            if not cond:
                # Skip to LOOP line
                loop_idx = self._find_loop_for_do(self.pc)
                if loop_idx is not None:
                    self.pc = loop_idx  # will be incremented past LOOP
                else:
                    raise BasicRuntimeError("DO without matching LOOP")
        # If condition passes (or no pre-condition), continue into body.

    def _exec_loop(self, stmt: LoopStmt):
        """LOOP statement: check post-condition, jump back to DO or fall through."""
        do_idx = self._find_do_for_loop(self.pc)
        if do_idx is None:
            raise BasicRuntimeError("LOOP without matching DO")

        if stmt.post_condition is not None:
            cond_val = self._truthy(self._eval(stmt.post_condition))
            if stmt.post_until:
                # LOOP UNTIL cond: exit if TRUE, continue if FALSE
                if cond_val:
                    return  # Exit loop
                else:
                    self.pc = do_idx - 1  # Jump back to DO line
            else:
                # LOOP WHILE cond: continue if TRUE, exit if FALSE
                if cond_val:
                    self.pc = do_idx - 1  # Jump back to DO line
                else:
                    return  # Exit loop
        else:
            # No post-condition on LOOP. Check if the DO had a pre-condition.
            do_line = self.sorted_lines[do_idx]
            for s in self.lines[do_line]:
                if isinstance(s, DoStmt):
                    if s.pre_condition is not None:
                        self.pc = do_idx - 1  # Jump back to DO line
                        return
            # DO...LOOP without any condition: infinite loop
            raise BasicRuntimeError("DO...LOOP without condition: infinite loop")

    def _exec_goto(self, stmt: GotoStmt):
        if stmt.line not in self._line_to_idx:
            raise BasicRuntimeError(f"GOTO: line {stmt.line} not found")
        idx = self._line_to_idx[stmt.line]
        self.pc = idx - 1

    def _exec_gosub(self, stmt: GosubStmt):
        if stmt.line not in self._line_to_idx:
            raise BasicRuntimeError(f"GOSUB: line {stmt.line} not found")
        self.call_stack.append(self.pc)
        idx = self._line_to_idx[stmt.line]
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

    def _exec_erase(self, stmt: EraseStmt):
        for name in stmt.names:
            self.arrays.pop(name, None)

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
                indices = [int(self._eval(idx)) for idx in var.indices]
                self._set_array(var.name, indices, raw)

    def _exec_restore(self, stmt: RestoreStmt):
        if stmt.line_num is not None:
            target = stmt.line_num
            ptr = 0
            for ln in self.sorted_lines:
                for s in self.lines[ln]:
                    if isinstance(s, DataStmt):
                        if ln == target:
                            self.data_pointer = ptr
                            return
                        ptr += len(s.values)
            raise BasicRuntimeError(f"RESTORE: line {target} not found or has no DATA")
        else:
            self.data_pointer = 0

    def _exec_def_fn(self, stmt: DefFnStmt):
        fn_name = "FN" + stmt.name
        self.user_fns[fn_name] = stmt

    def _exec_on_goto(self, stmt: OnGotoStmt):
        val = int(self._to_number(self._eval(stmt.expr)))
        if 1 <= val <= len(stmt.targets):
            target = stmt.targets[val - 1]
            if target not in self._line_to_idx:
                raise BasicRuntimeError(f"ON GOTO: line {target} not found")
            idx = self._line_to_idx[target]
            self.pc = idx - 1

    def _exec_on_gosub(self, stmt: OnGosubStmt):
        val = int(self._to_number(self._eval(stmt.expr)))
        if 1 <= val <= len(stmt.targets):
            target = stmt.targets[val - 1]
            if target not in self._line_to_idx:
                raise BasicRuntimeError(f"ON GOSUB: line {target} not found")
            self.call_stack.append(self.pc)
            idx = self._line_to_idx[target]
            self.pc = idx - 1

    def _exec_swap(self, stmt: SwapStmt):
        v1_name = self._get_lvalue_name(stmt.var1)
        v2_name = self._get_lvalue_name(stmt.var2)
        v1 = self.variables.get(v1_name, 0.0 if not v1_name.endswith("$") else "")
        v2 = self.variables.get(v2_name, 0.0 if not v2_name.endswith("$") else "")
        self.variables[v1_name] = v2
        self.variables[v2_name] = v1

    def _get_lvalue_name(self, lv):
        if isinstance(lv, VarRef):
            return lv.name
        raise BasicRuntimeError("SWAP only supports simple variables")

    def _exec_cls(self, stmt: ClsStmt):
        self.stdout.write("\033[2J\033[H")
        self.stdout.flush()
        self._print_col = 0

    def _exec_color(self, stmt: ColorStmt):
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
        self._print_col = col - 1

    def _exec_beep(self, stmt: BeepStmt):
        self.stdout.write("\a")
        self.stdout.flush()

    def _exec_select_case(self, stmt: SelectCaseStmt):
        """SELECT CASE: evaluate test expr, then jump to matching CASE line.
        
        Sets _active_select_end so that when execution reaches a subsequent
        CASE/CASE ELSE/END SELECT line (after the matched CASE body has run),
        we can skip to END SELECT to prevent fall-through.
        """
        test_val = self._eval(stmt.test_expr)
        info = self.select_info.get(self.pc)
        if info is None:
            return  # No CASE blocks found

        # Determine which CASE matches
        case_indices = info["case_indices"]
        case_else_idx = info.get("case_else_idx")
        end_select_idx = info.get("end_select_idx", len(self.sorted_lines) - 1)

        matched_case_idx = None
        for case_idx in case_indices:
            case_stmts = self.lines[self.sorted_lines[case_idx]]
            for s in case_stmts:
                if isinstance(s, CaseStmt):
                    if self._match_case(test_val, s.conditions):
                        matched_case_idx = case_idx
                        break
            if matched_case_idx is not None:
                break

        # Track the END SELECT index so CASE/END SELECT lines can skip to it
        self._active_select_end = end_select_idx

        if matched_case_idx is not None:
            # Jump to the matching CASE line
            self._active_select_matched = matched_case_idx
            self.pc = matched_case_idx - 1  # -1 because run() will add 1
        elif case_else_idx is not None:
            self._active_select_matched = case_else_idx
            self.pc = case_else_idx - 1
        else:
            # No match, no CASE ELSE: skip to END SELECT
            self.pc = end_select_idx
            self._active_select_end = None
            self._active_select_matched = None

    def _match_case(self, test_val, conditions: list) -> bool:
        for cond in conditions:
            if cond.is_op is not None:
                cmp_val = self._eval(cond.is_val)
                if self._compare(test_val, cond.is_op, cmp_val):
                    return True
            elif cond.high is not None:
                low = self._eval(cond.low)
                high = self._eval(cond.high)
                if isinstance(test_val, str):
                    if low <= test_val <= high:
                        return True
                else:
                    if self._to_number(low) <= self._to_number(test_val) <= self._to_number(high):
                        return True
            else:
                val = self._eval(cond.low)
                if isinstance(test_val, str) and isinstance(val, str):
                    if test_val == val:
                        return True
                elif not isinstance(test_val, str) and not isinstance(val, str):
                    if self._to_number(test_val) == self._to_number(val):
                        return True
                elif isinstance(val, str):
                    if str(test_val) == val:
                        return True
                else:
                    if self._to_number(test_val) == self._to_number(val):
                        return True
        return False

    def _compare(self, left, op: str, right) -> bool:
        if isinstance(left, str) and isinstance(right, str):
            ops = {"=": lambda a, b: a == b, "<>": lambda a, b: a != b,
                   "<": lambda a, b: a < b, ">": lambda a, b: a > b,
                   "<=": lambda a, b: a <= b, ">=": lambda a, b: a >= b}
            return ops.get(op, lambda a, b: False)(left, right)
        ln = self._to_number(left)
        rn = self._to_number(right)
        if op == "=": return ln == rn
        if op == "<>": return ln != rn
        if op == "<": return ln < rn
        if op == ">": return ln > rn
        if op == "<=": return ln <= rn
        if op == ">=": return ln >= rn
        return False

    def _exec_open(self, stmt: OpenStmt):
        filename = str(self._eval(stmt.filename))
        fnum = int(self._to_number(self._eval(stmt.file_num)))
        mode = stmt.mode.upper()
        try:
            if mode == "I":
                f = open(filename, "r")
            elif mode == "O":
                f = open(filename, "w")
            elif mode == "A":
                f = open(filename, "a")
            else:
                raise BasicRuntimeError(f"Invalid file mode: {mode}")
            self._files[fnum] = f
        except OSError as e:
            raise BasicRuntimeError(f"Cannot open file '{filename}': {e}")

    def _exec_close(self, stmt: CloseStmt):
        if stmt.file_num is not None:
            fnum = int(self._to_number(self._eval(stmt.file_num)))
            if fnum in self._files:
                self._files[fnum].close()
                del self._files[fnum]
        else:
            for f in self._files.values():
                f.close()
            self._files.clear()

    def _exec_print_file(self, stmt: PrintFileStmt):
        fnum = int(self._to_number(self._eval(stmt.file_num)))
        if fnum not in self._files:
            raise BasicRuntimeError(f"File #{fnum} not open")
        f = self._files[fnum]
        end_newline = True
        for expr, sep in stmt.items:
            if expr is not None:
                val = self._eval(expr)
                f.write(self._format_value(val))
            if sep == ";":
                end_newline = False
            elif sep == ",":
                f.write("\t")
                end_newline = False
            else:
                end_newline = True
        if end_newline:
            f.write("\n")
        f.flush()

    def _exec_input_file(self, stmt: InputFileStmt):
        fnum = int(self._to_number(self._eval(stmt.file_num)))
        if fnum not in self._files:
            raise BasicRuntimeError(f"File #{fnum} not open")
        f = self._files[fnum]
        line = f.readline()
        if not line:
            raise BasicRuntimeError(f"End of file #{fnum}")
        line = line.rstrip("\n\r")
        values = [v.strip() for v in line.split(",")]
        for i, var in enumerate(stmt.vars):
            raw = values[i] if i < len(values) else ""
            if isinstance(var, VarRef):
                self._assign_input_var(var.name, raw)

    def _exec_on_error(self, stmt: OnErrorStmt):
        if stmt.line == 0:
            self._on_error_line = None
        else:
            self._on_error_line = stmt.line

    def _exec_resume(self, stmt: ResumeStmt):
        if not self._error_occurred:
            raise BasicRuntimeError("RESUME without error")
        if stmt.line is not None and stmt.line > 0:
            if stmt.line not in self._line_to_idx:
                raise BasicRuntimeError(f"RESUME: line {stmt.line} not found")
            idx = self._line_to_idx[stmt.line]
            self.pc = idx - 1
        elif stmt.line == -1:
            # RESUME NEXT: skip the line that caused the error
            if self._error_resume_line is not None:
                self.pc = self._error_resume_line
        else:
            # RESUME: go back to the line that caused the error
            if self._error_resume_line is not None:
                self.pc = self._error_resume_line - 1  # re-execute the line
        self._error_occurred = False

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
            # Check if this is a system variable that's also a zero-arg function
            system_vars = {"DATE$", "TIME$", "INKEY$", "TIMER"}
            if name in system_vars and name not in self.variables:
                return self._eval_fn(FnCall(name, []))
            if name in self.variables:
                return self.variables[name]
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
                if 0 <= indices[0] < len(arr):
                    return arr[indices[0]]
                return 0.0 if not name.endswith("$") else ""
            elif len(indices) == 2:
                if 0 <= indices[0] < len(arr) and 0 <= indices[1] < len(arr[0]):
                    return arr[indices[0]][indices[1]]
                return 0.0 if not name.endswith("$") else ""
        if isinstance(expr, FnCall):
            return self._eval_fn(expr)
        if isinstance(expr, UnaryOp):
            val = self._eval(expr.operand)
            if expr.op == "-":
                return -self._to_number(val)
            if expr.op == "NOT":
                return -1 if not self._truthy(val) else 0
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
        if name == "FIX":
            return float(math.trunc(self._to_number(args[0])))
        if name == "SGN":
            n = self._to_number(args[0])
            if n > 0: return 1.0
            if n < 0: return -1.0
            return 0.0
        if name == "RND":
            if args:
                x = self._to_number(args[0])
                if x < 0:
                    random.seed(int(x))
                elif x == 0:
                    return random.random()
            return random.random()
        if name == "SQR":
            n = self._to_number(args[0])
            if n < 0:
                raise BasicRuntimeError("SQR of negative number")
            return math.sqrt(n)
        if name == "SIN":
            return math.sin(self._to_number(args[0]))
        if name == "COS":
            return math.cos(self._to_number(args[0]))
        if name == "TAN":
            return math.tan(self._to_number(args[0]))
        if name == "ATN":
            return math.atan(self._to_number(args[0]))
        if name == "LOG":
            n = self._to_number(args[0])
            if n <= 0:
                raise BasicRuntimeError("LOG of non-positive number")
            return math.log(n)
        if name == "EXP":
            return math.exp(self._to_number(args[0]))
        if name == "CINT":
            return float(round(self._to_number(args[0])))
        if name == "CSNG":
            return float(self._to_number(args[0]))
        if name == "CDBL":
            return float(self._to_number(args[0]))

        # String functions
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
            start = int(self._to_number(args[1])) - 1
            if start < 0:
                start = 0
            if len(args) > 2:
                length = int(self._to_number(args[2]))
                return s[start:start + length]
            return s[start:]
        if name == "CHR$":
            code = int(self._to_number(args[0]))
            try:
                return chr(code)
            except ValueError:
                return "?"
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
        if name == "LCASE$":
            return str(args[0]).lower()
        if name == "UCASE$":
            return str(args[0]).upper()
        if name == "LTRIM$":
            return str(args[0]).lstrip()
        if name == "RTRIM$":
            return str(args[0]).rstrip()
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
                start = int(self._to_number(args[0])) - 1
                haystack = str(args[1])
                needle = str(args[2])
                idx = haystack.find(needle, max(0, start))
                return float(idx + 1) if idx >= 0 else 0.0

        # I/O and system functions
        if name == "TAB":
            n = int(self._to_number(args[0]))
            spaces = max(0, n - self._print_col)
            self.stdout.write(" " * spaces)
            self._print_col = n
            return ""
        if name == "SPC":
            n = int(self._to_number(args[0]))
            self.stdout.write(" " * max(0, n))
            self._print_col += n
            return ""
        if name == "TIMER":
            return time.time() % 86400
        if name == "PEEK":
            return 0.0
        if name == "FRE":
            return float(655360)
        if name == "DATE$":
            return datetime.date.today().strftime("%m-%d-%Y")
        if name == "TIME$":
            return datetime.datetime.now().strftime("%H:%M:%S")
        if name == "INKEY$":
            return ""
        if name == "ENVIRON$":
            if args:
                return os.environ.get(str(args[0]), "")
            return ""

        raise BasicRuntimeError(f"Unknown function: {name}")

    def _eval_binop(self, expr: BinOp) -> Any:
        # Logical operators
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
        if expr.op == "XOR":
            left = self._truthy(self._eval(expr.left))
            right = self._truthy(self._eval(expr.right))
            return -1 if left != right else 0
        if expr.op == "EQV":
            left = self._truthy(self._eval(expr.left))
            right = self._truthy(self._eval(expr.right))
            return -1 if left == right else 0
        if expr.op == "IMP":
            left = self._truthy(self._eval(expr.left))
            right = self._truthy(self._eval(expr.right))
            return -1 if (not left) or right else 0

        left = self._eval(expr.left)
        right = self._eval(expr.right)

        if expr.op == "+" and (isinstance(left, str) or isinstance(right, str)):
            return str(left) + str(right)

        if expr.op in ("=", "<>", "<", ">", "<=", ">=") and isinstance(left, str) and isinstance(right, str):
            ops = {"=": lambda a, b: a == b, "<>": lambda a, b: a != b,
                   "<": lambda a, b: a < b, ">": lambda a, b: a > b,
                   "<=": lambda a, b: a <= b, ">=": lambda a, b: a >= b}
            return -1 if ops[expr.op](left, right) else 0

        ln = self._to_number(left)
        rn = self._to_number(right)

        if expr.op == "+": return ln + rn
        if expr.op == "-": return ln - rn
        if expr.op == "*": return ln * rn
        if expr.op == "/":
            if rn == 0: raise BasicRuntimeError("Division by zero")
            return ln / rn
        if expr.op == "\\":
            if rn == 0: raise BasicRuntimeError("Division by zero")
            # BASIC integer division truncates toward zero, not floor division
            return float(int(int(ln) / int(rn)))
        if expr.op == "MOD":
            if rn == 0: raise BasicRuntimeError("Division by zero")
            # BASIC MOD: result has same sign as dividend
            return float(int(ln) - int(int(ln) / int(rn)) * int(rn))
        if expr.op == "^": return ln ** rn
        if expr.op == "=": return -1 if ln == rn else 0
        if expr.op == "<>": return -1 if ln != rn else 0
        if expr.op == "<": return -1 if ln < rn else 0
        if expr.op == ">": return -1 if ln > rn else 0
        if expr.op == "<=": return -1 if ln <= rn else 0
        if expr.op == ">=": return -1 if ln >= rn else 0

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


# ── REPL ────────────────────────────────────────────────────────────────────

def repl():
    """Interactive BASIC REPL with enhanced commands."""
    interp = Interpreter()
    interp.stdout.write("BASIC Interpreter v2.0\n")
    interp.stdout.write("Commands: RUN, LIST, NEW, SAVE, LOAD, EDIT, DELETE, QUIT\n")
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

            upper = line.upper().strip()

            if upper in ("QUIT", "EXIT", "SYSTEM"):
                break

            if upper == "LIST":
                for ln in sorted(program_lines.keys()):
                    interp.stdout.write(f"{ln} {program_lines[ln]}\n")
                interp.stdout.write("> ")
                interp.stdout.flush()
                continue

            if upper.startswith("LIST"):
                rest = line[4:].strip()
                try:
                    if "-" in rest:
                        parts = rest.split("-", 1)
                        start = int(parts[0].strip())
                        end = int(parts[1].strip()) if parts[1].strip() else 99999
                    else:
                        start = int(rest.strip())
                        end = start
                    for ln in sorted(program_lines.keys()):
                        if start <= ln <= end:
                            interp.stdout.write(f"{ln} {program_lines[ln]}\n")
                except ValueError:
                    pass
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
                interp.stdout.write("OK\n> ")
                interp.stdout.flush()
                continue

            if upper == "NEW":
                program_lines.clear()
                for f in interp._files.values():
                    f.close()
                interp = Interpreter()
                interp.stdout.write("OK\n> ")
                interp.stdout.flush()
                continue

            if upper.startswith("SAVE"):
                filename = line[4:].strip()
                if not filename:
                    interp.stdout.write("Usage: SAVE filename\n")
                else:
                    try:
                        with open(filename, "w") as f:
                            for ln in sorted(program_lines.keys()):
                                f.write(f"{ln} {program_lines[ln]}\n")
                        interp.stdout.write(f"Saved {len(program_lines)} lines to {filename}\n")
                    except OSError as e:
                        interp.stdout.write(f"Error: {e}\n")
                interp.stdout.write("> ")
                interp.stdout.flush()
                continue

            if upper.startswith("LOAD"):
                filename = line[4:].strip()
                if not filename:
                    interp.stdout.write("Usage: LOAD filename\n")
                else:
                    try:
                        with open(filename, "r") as f:
                            for raw in f:
                                raw = raw.rstrip()
                                match = re.match(r'^(\d+)\s+(.*)', raw)
                                if match:
                                    program_lines[int(match.group(1))] = match.group(2)
                        interp.stdout.write(f"Loaded {len(program_lines)} lines from {filename}\n")
                    except FileNotFoundError:
                        interp.stdout.write(f"File not found: {filename}\n")
                    except OSError as e:
                        interp.stdout.write(f"Error: {e}\n")
                interp.stdout.write("> ")
                interp.stdout.flush()
                continue

            if upper.startswith("DELETE"):
                rest = line[6:].strip()
                try:
                    if "-" in rest:
                        parts = rest.split("-", 1)
                        start = int(parts[0].strip())
                        end = int(parts[1].strip()) if parts[1].strip() else 99999
                        for ln in list(program_lines.keys()):
                            if start <= ln <= end:
                                del program_lines[ln]
                    else:
                        line_num = int(rest)
                        program_lines.pop(line_num, None)
                except ValueError:
                    interp.stdout.write("Usage: DELETE line or DELETE start-end\n")
                interp.stdout.write("> ")
                interp.stdout.flush()
                continue

            if upper.startswith("EDIT"):
                rest = line[4:].strip()
                try:
                    line_num = int(rest)
                    if line_num in program_lines:
                        interp.stdout.write(f"{line_num} {program_lines[line_num]}\n")
                        new_line = input("? ").strip()
                        if new_line:
                            program_lines[line_num] = new_line
                    else:
                        interp.stdout.write(f"Line {line_num} not found\n")
                except ValueError:
                    interp.stdout.write("Usage: EDIT line\n")
                interp.stdout.write("> ")
                interp.stdout.flush()
                continue

            match = re.match(r'^(\d+)\s+(.*)', line)
            if match:
                line_num = int(match.group(1))
                code = match.group(2)
                program_lines[line_num] = code
                interp.stdout.write("> ")
                interp.stdout.flush()
                continue

            if re.match(r'^\d+$', line):
                line_num = int(line)
                program_lines.pop(line_num, None)
                interp.stdout.write("> ")
                interp.stdout.flush()
                continue

            try:
                interp.load(line)
            except BasicError as e:
                interp.stdout.write(f"Error: {e}\n")
            interp.stdout.write("> ")
            interp.stdout.flush()
    except KeyboardInterrupt:
        interp.stdout.write("\n")

    for f in interp._files.values():
        try:
            f.close()
        except Exception:
            pass
    interp.stdout.write("Goodbye!\n")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="BASIC Language Interpreter v2.0")
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
            line_num = interp.sorted_lines[interp.pc] if interp.pc < len(interp.sorted_lines) else "?"
            print(f"Error at line {line_num}: {e}", file=sys.stderr)
            sys.exit(1)
        except BasicStopException:
            print("Break")
        finally:
            for f in interp._files.values():
                try:
                    f.close()
                except Exception:
                    pass
        return

    repl()


if __name__ == "__main__":
    main()