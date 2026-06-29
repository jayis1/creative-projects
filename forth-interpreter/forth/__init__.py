"""
forth — A stack-based Forth interpreter implemented in pure Python.

Public API::

    from forth import ForthInterpreter, ForthError, Word
    from forth import ForthThrow

    out = io.StringIO()
    interp = ForthInterpreter(output=out)
    interp.eval(': SQUARE DUP * ; 5 SQUARE . CR')
    print(out.getvalue())  # "25 \\n"

Architecture
------------
The interpreter is organised into a modular package:

* :mod:`forth.core` — the core interpreter engine (stack, dictionary,
  compilation, bytecode execution)
* :mod:`forth.builtins` — built-in word set, split by category
* :mod:`forth.cli` — command-line interface with config-file and logging support
"""

from forth.core import (
    ForthError,
    ForthThrow,
    ForthInterpreter,
    Word,
)

__version__ = "3.0.0"

__all__ = [
    "ForthError",
    "ForthThrow",
    "ForthInterpreter",
    "Word",
    "__version__",
]