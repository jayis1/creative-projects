"""
Performance optimization utilities for the spreadsheet engine.

Provides a cell-value cache to avoid redundant recomputation, a memoized
dependency resolver, and batch-set helpers for bulk data loading.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Dict, List, Tuple

from .cell import CellType, parse_a1, format_a1
from .engine import Engine


class LRUCache:
    """Simple LRU cache for cell evaluation results."""

    def __init__(self, capacity: int = 4096):
        self.capacity = capacity
        self._cache: OrderedDict[Tuple[str, int, int], Any] = OrderedDict()

    def get(self, key: Tuple[str, int, int]) -> Any:
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return _MISS

    def put(self, key: Tuple[str, int, int], value: Any) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self.capacity:
                self._cache.popitem(last=False)
        self._cache[key] = value

    def invalidate(self, key: Tuple[str, int, int]) -> None:
        self._cache.pop(key, None)

    def clear(self) -> None:
        self._cache.clear()

    def __len__(self) -> int:
        return len(self._cache)

    def __contains__(self, key: Tuple[str, int, int]) -> bool:
        return key in self._cache


_MISS = object()


class CachedEngine(Engine):
    """Engine subclass that caches cell evaluation results during recalc.

    For workbooks where many cells share sub-expressions or reference the
    same precedent cells, this can significantly speed up recalculation by
    avoiding redundant recursive evaluation.
    """

    def __init__(self, cache_capacity: int = 4096):
        super().__init__()
        self._value_cache = LRUCache(cache_capacity)

    def evaluate_cell(self, sheet_name: str, row: int, col: int) -> Any:
        key = (sheet_name, row, col)
        cached = self._value_cache.get(key)
        if cached is not _MISS:
            return cached
        result = super().evaluate_cell(sheet_name, row, col)
        self._value_cache.put(key, result)
        return result

    def recalculate(self) -> Dict[str, int]:
        self._value_cache.clear()
        return super().recalculate()

    def set(self, sheet: str, ref: str, raw: str) -> None:
        super().set(sheet, ref, raw)
        # Invalidate the cache for this cell
        row, col = parse_a1(ref)
        self._value_cache.invalidate((sheet, row, col))

    def set_value(self, sheet: str, ref: str, value: Any) -> None:
        super().set_value(sheet, ref, value)
        row, col = parse_a1(ref)
        self._value_cache.invalidate((sheet, row, col))


def batch_set(engine: Engine, sheet: str, data: List[List[str]]) -> None:
    """Set a 2D grid of values efficiently.

    Args:
        engine: the engine to modify
        sheet: sheet name (created if it doesn't exist)
        data: list of rows, each a list of cell value strings

    Example:
        batch_set(engine, "S", [["1", "2"], ["3", "=A1+A2"]])
    """
    if sheet not in engine.sheets:
        engine.add_sheet(sheet)
    for r, row_vals in enumerate(data):
        for c, val in enumerate(row_vals):
            if val:
                ref = format_a1(r, c)
                engine.set(sheet, ref, str(val))


def load_matrix(engine: Engine, sheet: str, matrix: List[List[Any]]) -> None:
    """Load a matrix of Python values (numbers, strings) into a sheet."""
    if sheet not in engine.sheets:
        engine.add_sheet(sheet)
    for r, row_vals in enumerate(matrix):
        for c, val in enumerate(row_vals):
            if val is not None:
                ref = format_a1(r, c)
                if isinstance(val, (int, float)):
                    engine.set(sheet, ref, str(val))
                else:
                    engine.set(sheet, ref, str(val))