"""
Spreadsheet Engine — a from-scratch formula evaluation engine.

Core package providing a Cell, Sheet, and Engine with:
  - Formula parsing (recursive-descent expression parser)
  - Cell references (A1 notation), ranges (A1:B2), cross-sheet refs (Sheet!A1)
  - 90+ built-in functions (math, stats, logic, text, lookup)
  - Dependency graph + topological-sort recalculation
  - Cycle detection with circular-reference errors
  - Value types: numbers, strings, booleans, error cells
  - Named ranges for reusable references
  - Formula auditing (precedents/dependents tracing)
  - Incremental recalculation
  - CSV import/export, JSON serialization
  - Multi-sheet workbooks
"""

from .engine import Engine, EngineError
from .sheet import Sheet
from .cell import Cell, CellType, CellError, ErrorType
from .named_ranges import NamedRange, NamedRangeManager

__version__ = "2.0.0"
__all__ = [
    "Engine",
    "EngineError",
    "Sheet",
    "Cell",
    "CellType",
    "CellError",
    "ErrorType",
    "NamedRange",
    "NamedRangeManager",
]