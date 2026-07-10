"""
Spreadsheet Engine — a from-scratch formula evaluation engine.

Core package providing a Cell, Sheet, and Engine with:
  - Formula parsing (recursive-descent expression parser)
  - Cell references (A1 notation), ranges (A1:B2), cross-sheet refs (Sheet!A1)
  - 90+ built-in functions (math, stats, logic, text, lookup, date, financial, info)
  - Dependency graph + topological-sort recalculation
  - Cycle detection with circular-reference errors
  - Value types: numbers, strings, booleans, error cells
  - Named ranges for reusable references
  - Formula auditing (precedents/dependents tracing)
  - Incremental recalculation
  - CSV import/export, JSON serialization
  - Multi-sheet workbooks
  - YAML/JSON configuration file support
  - Logging with configurable verbosity
  - LRU-cached evaluation for performance
"""

from .engine import Engine, EngineError
from .sheet import Sheet
from .cell import Cell, CellType, CellError, ErrorType
from .named_ranges import NamedRange, NamedRangeManager
from .extended_functions import register_extended_functions
from .config import load_config, save_config, ConfigError
from .optimizer import CachedEngine, LRUCache, batch_set, load_matrix
from .logging_utils import configure as configure_logging, get_logger

# Ensure extended functions are registered
register_extended_functions()

__version__ = "3.0.0"
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
    "CachedEngine",
    "LRUCache",
    "batch_set",
    "load_matrix",
    "load_config",
    "save_config",
    "ConfigError",
    "configure_logging",
    "get_logger",
]