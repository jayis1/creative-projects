"""
Cell data model and error types for the spreadsheet engine.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class CellType(Enum):
    """The kind of value stored in a cell."""

    EMPTY = "empty"
    NUMBER = "number"
    STRING = "string"
    BOOLEAN = "boolean"
    ERROR = "error"
    FORMULA = "formula"  # cell holds a parsed formula AST


class ErrorType(Enum):
    """Spreadsheet error categories (Excel-compatible names)."""

    DIV_ZERO = "#DIV/0!"
    VALUE = "#VALUE!"
    REF = "#REF!"
    NAME = "#NAME?"
    NUM = "#NUM!"
    NA = "#N/A"
    CYCLE = "#CYCLE!"
    PARSE = "#PARSE!"


# ---------------------------------------------------------------------------
# Cell reference helpers
# ---------------------------------------------------------------------------

_COL_RE = re.compile(r"[A-Z]+")


def col_to_index(col: str) -> int:
    """Convert column letters (A, B, ..., Z, AA, AB, ...) to 0-based index."""
    col = col.upper()
    if not col.isalpha():
        raise ValueError(f"Invalid column label: {col!r}")
    idx = 0
    for ch in col:
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx - 1


def index_to_col(idx: int) -> str:
    """Convert 0-based column index back to letters."""
    if idx < 0:
        raise ValueError(f"Negative column index: {idx}")
    result = ""
    idx += 1  # 1-based internally
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        result = chr(ord("A") + rem) + result
    return result


def parse_a1(ref: str) -> tuple[int, int]:
    """Parse 'A1' into (row=0, col=0).  Raises ValueError on bad format."""
    m = re.fullmatch(r"([A-Za-z]+)(\d+)", ref)
    if not m:
        raise ValueError(f"Invalid A1 reference: {ref!r}")
    col = col_to_index(m.group(1))
    row = int(m.group(2)) - 1  # 0-based
    if row < 0:
        raise ValueError(f"Row must be >= 1: {ref!r}")
    return row, col


def format_a1(row: int, col: int) -> str:
    """Convert (row=0, col=0) to 'A1'."""
    return f"{index_to_col(col)}{row + 1}"


# ---------------------------------------------------------------------------
# Cell
# ---------------------------------------------------------------------------

@dataclass
class CellError:
    """An error value that a cell can hold."""

    type: ErrorType
    message: str = ""

    def __str__(self) -> str:
        return self.type.value

    def __repr__(self) -> str:
        return f"CellError({self.type.name}, {self.message!r})"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, CellError):
            return self.type == other.type
        return False

    def __hash__(self) -> int:
        return hash(self.type)


@dataclass
class Cell:
    """
    A single spreadsheet cell.

    Attributes
    ----------
    row, col : 0-based coordinates
    raw      : the user-typed text (number, string, or formula starting with '=')
    value    : the computed/evaluated value (number, str, bool, CellError, or None)
    formula  : parsed AST root if raw starts with '=', else None
    type     : CellType classification
    deps     : set of (sheet_name, row, col) tuples this cell depends on
    """

    row: int
    col: int
    raw: str = ""
    value: Any = None
    formula: Optional[Any] = None  # AST node
    type: CellType = CellType.EMPTY
    deps: set = field(default_factory=set)

    @property
    def ref(self) -> str:
        return format_a1(self.row, self.col)

    def clear(self) -> None:
        self.raw = ""
        self.value = None
        self.formula = None
        self.type = CellType.EMPTY
        self.deps.clear()

    def is_empty(self) -> bool:
        return self.type == CellType.EMPTY or (
            self.type == CellType.STRING and self.raw == ""
        )