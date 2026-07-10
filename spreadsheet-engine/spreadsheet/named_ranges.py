"""
Named ranges for the spreadsheet engine.

Allows defining named references like 'Revenue' -> 'Sheet1!A1:A10'
that can be used in formulas.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from .cell import parse_a1


class NamedRange:
    """A named reference to a cell or range, possibly cross-sheet."""

    def __init__(self, name: str, sheet: str, start_ref: str, end_ref: Optional[str] = None):
        self.name = name
        self.sheet = sheet
        self.start_row, self.start_col = parse_a1(start_ref)
        if end_ref:
            self.end_row, self.end_col = parse_a1(end_ref)
        else:
            self.end_row, self.end_col = self.start_row, self.start_col

    @property
    def is_range(self) -> bool:
        return (self.start_row, self.start_col) != (self.end_row, self.end_col)

    def cells(self) -> list:
        """Return list of (sheet, row, col) tuples covered by this named range."""
        result = []
        for r in range(self.start_row, self.end_row + 1):
            for c in range(self.start_col, self.end_col + 1):
                result.append((self.sheet, r, c))
        return result

    def __repr__(self) -> str:
        if self.is_range:
            from .cell import format_a1
            return f"NamedRange({self.name}={self.sheet}!{format_a1(self.start_row, self.start_col)}:{format_a1(self.end_row, self.end_col)})"
        from .cell import format_a1
        return f"NamedRange({self.name}={self.sheet}!{format_a1(self.start_row, self.start_col)})"


class NamedRangeManager:
    """Manages named ranges for an engine."""

    def __init__(self):
        self._names: Dict[str, NamedRange] = {}

    def define(self, name: str, sheet: str, ref: str) -> NamedRange:
        """Define a named range.  `ref` can be 'A1' or 'A1:B10'."""
        name = name.strip()
        if not name:
            raise ValueError("Named range name cannot be empty")
        # ref can be "A1" or "A1:B10"
        if ":" in ref:
            start, end = ref.split(":", 1)
            nr = NamedRange(name, sheet, start.strip(), end.strip())
        else:
            nr = NamedRange(name, sheet, ref.strip())
        self._names[name.upper()] = nr
        return nr

    def get(self, name: str) -> Optional[NamedRange]:
        return self._names.get(name.upper())

    def remove(self, name: str) -> bool:
        return self._names.pop(name.upper(), None) is not None

    def list(self) -> Dict[str, NamedRange]:
        return dict(self._names)

    def __contains__(self, name: str) -> bool:
        return name.upper() in self._names

    def __len__(self) -> int:
        return len(self._names)