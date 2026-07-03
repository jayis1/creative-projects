"""PostScript interpreter package."""
from .interpreter import Interpreter
from .graphics import GraphicsState
from .errors import PSError, PSStackUnderflow, PSTypeError, PSUndefined

__all__ = [
    "Interpreter",
    "GraphicsState",
    "PSError",
    "PSStackUnderflow",
    "PSTypeError",
    "PSUndefined",
]

__version__ = "1.0.0"