"""AST node definitions for the BASIC interpreter.

This module defines the abstract syntax tree nodes used by the parser
and interpreter. Each node represents a specific BASIC statement or
expression construct.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional


# ── Expression nodes ──

@dataclass
class NumberLit:
    """A numeric literal value."""
    value: float


@dataclass
class StringLit:
    """A string literal value."""
    value: str


@dataclass
class VarRef:
    """A reference to a variable (e.g., X, NAME$, COUNT%)."""
    name: str


@dataclass
class ArrayRef:
    """A reference to an array element (e.g., A(5), M$(I, J))."""
    name: str
    indices: list


@dataclass
class FnCall:
    """A function call (built-in or user-defined)."""
    name: str
    args: list


@dataclass
class UnaryOp:
    """A unary operation (e.g., -X, NOT Y)."""
    op: str
    operand: Any


@dataclass
class BinOp:
    """A binary operation (e.g., X + Y, A AND B)."""
    op: str
    left: Any
    right: Any


# ── Statement nodes ──

@dataclass
class LetStmt:
    """Assignment: LET target = value (or implicit LET)."""
    target: Any
    value: Any


@dataclass
class PrintStmt:
    """PRINT statement with optional USING format."""
    items: list
    using: Any = None


@dataclass
class InputStmt:
    """INPUT statement for user input with optional prompt."""
    prompt: Any
    vars: list


@dataclass
class LineInputStmt:
    """LINE INPUT statement for reading entire lines."""
    prompt: Any
    var: Any
    file_num: Any = None


@dataclass
class IfStmt:
    """IF...THEN...ELSE statement."""
    condition: Any
    then_part: list
    else_part: list


@dataclass
class ForStmt:
    """FOR...NEXT loop initialization."""
    var: VarRef
    start: Any
    stop: Any
    step: Any


@dataclass
class NextStmt:
    """NEXT statement to close a FOR loop."""
    var: Optional[VarRef]


@dataclass
class WhileStmt:
    """WHILE statement to start a WHILE...WEND loop."""
    condition: Any
    body: list


@dataclass
class WendStmt:
    """WEND statement to close a WHILE loop."""
    pass


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
    """GOTO line_number — unconditional jump."""
    line: int


@dataclass
class GosubStmt:
    """GOSUB line_number — subroutine call."""
    line: int


@dataclass
class ReturnStmt:
    """RETURN — return from subroutine."""
    pass


@dataclass
class DimStmt:
    """DIM statement to declare arrays."""
    declarations: list


@dataclass
class EraseStmt:
    """ERASE statement to deallocate arrays."""
    names: list


@dataclass
class ReadStmt:
    """READ statement to read from DATA blocks."""
    vars: list


@dataclass
class DataStmt:
    """DATA statement providing static data values."""
    values: list


@dataclass
class RestoreStmt:
    """RESTORE [line] — reset DATA pointer."""
    line_num: Optional[int] = None


@dataclass
class DefFnStmt:
    """DEF FN — define a user function."""
    name: str
    params: list
    body: Any


@dataclass
class EndStmt:
    """END statement — terminate program."""
    pass


@dataclass
class StopStmt:
    """STOP statement — breakpoint."""
    pass


@dataclass
class RemStmt:
    """REM — comment."""
    text: str


@dataclass
class OnGotoStmt:
    """ON expr GOTO line1, line2, ... — computed branching."""
    expr: Any
    targets: list


@dataclass
class OnGosubStmt:
    """ON expr GOSUB line1, line2, ... — computed subroutine call."""
    expr: Any
    targets: list


@dataclass
class SwapStmt:
    """SWAP var1, var2 — exchange variable values."""
    var1: Any
    var2: Any


@dataclass
class ClsStmt:
    """CLS — clear screen."""
    pass


@dataclass
class ColorStmt:
    """COLOR fg[, bg] — set text colors."""
    fg: Any
    bg: Any = None


@dataclass
class LocateStmt:
    """LOCATE row, col — position cursor."""
    row: Any
    col: Any


@dataclass
class BeepStmt:
    """BEEP — produce an audible alert."""
    pass


@dataclass
class SelectCaseStmt:
    """SELECT CASE expr — start of a SELECT block."""
    test_expr: Any


@dataclass
class CaseStmt:
    """CASE conditions — a case branch within SELECT."""
    conditions: list


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
    """A single CASE condition: value, IS op value, or value TO value."""
    low: Any = None
    high: Any = None
    is_op: Optional[str] = None
    is_val: Any = None


@dataclass
class OpenStmt:
    """OPEN filename FOR mode AS #n — open a file."""
    filename: Any
    mode: str
    file_num: Any


@dataclass
class CloseStmt:
    """CLOSE [#n] — close a file."""
    file_num: Any = None


@dataclass
class PrintFileStmt:
    """PRINT# file_num, items — write to file."""
    file_num: Any
    items: list


@dataclass
class InputFileStmt:
    """INPUT# file_num, vars — read from file."""
    file_num: Any
    vars: list


@dataclass
class OnErrorStmt:
    """ON ERROR GOTO line — set error handler."""
    line: int


@dataclass
class ResumeStmt:
    """RESUME [line|NEXT] — resume after error handling."""
    line: Optional[int] = None


@dataclass
class ExitDoStmt:
    """EXIT DO — exit a DO loop."""
    pass