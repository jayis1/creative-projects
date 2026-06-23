"""Scheme Interpreter — a from-scratch Scheme implementation in pure Python.

This package implements a substantial subset of R5RS Scheme with:
- Tail-call optimization (trampoline-based)
- First-class continuations (call/cc via escape continuations)
- Hygienic syntax-rules macros
- 100+ primitive procedures
- Standard library (auto-loaded)
- Interactive REPL and CLI

Key exports:
    Interpreter: The main interpreter class.
    run: Convenience function to evaluate a Scheme source string.
    repl: Start the interactive REPL.

Version: 2.0.0
"""

from __future__ import annotations

__version__ = "2.0.0"

from .interpreter import Interpreter, SchemeError, SchemeExit
from .types import (
    Symbol, Pair, Nil, Bool, Char, Vector, Unspecified, EOF,
    Procedure, Lambda, Continuation, Macro,
    TRUE, FALSE,
    scheme_repr, scheme_display,
    list_to_pairs, pairs_to_list, is_list,
)


def run(source: str, load_stdlib: bool = True) -> object:
    """Convenience function: evaluate a Scheme source string and return the result.

    Args:
        source: Scheme source code to evaluate.
        load_stdlib: If True, auto-load the standard library first.

    Returns:
        The value of the last evaluated expression.

    Examples::

        >>> from scheme_interpreter import run
        >>> run('(+ 1 2 3)')
        6
        >>> run('(map square (list 1 2 3 4))')
        (1 4 9 16)
    """
    from .primitives import set_global_interpreter
    interp = Interpreter(load_stdlib=load_stdlib)
    set_global_interpreter(interp)
    return interp.run(source)


def repl():
    """Start the interactive REPL.

    Returns:
        Exit code (0 for success).
    """
    from .repl import run_repl
    return run_repl()