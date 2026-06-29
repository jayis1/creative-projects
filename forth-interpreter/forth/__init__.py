"""A stack-based Forth interpreter implemented in pure Python."""

from .interpreter import ForthInterpreter, ForthError, Word

__version__ = "2.0.0"

__all__ = ["ForthInterpreter", "ForthError", "Word"]