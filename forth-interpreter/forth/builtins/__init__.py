"""
Built-in word set for the Forth interpreter.

This package is organised by category.  Each module exposes a single
``register_*`` function that takes a :class:`~forth.core.ForthInterpreter`
and registers the relevant words on it.
"""

from forth.builtins.stack_ops import register_stack_ops
from forth.builtins.arithmetic import register_arithmetic
from forth.builtins.float_ops import register_float_ops
from forth.builtins.comparison import register_comparison
from forth.builtins.bitwise import register_bitwise
from forth.builtins.io_ops import register_io_ops
from forth.builtins.memory import register_memory_ops
from forth.builtins.defining import register_defining_words
from forth.builtins.control_flow import register_control_flow
from forth.builtins.case_ops import register_case_ops
from forth.builtins.arrays import register_array_ops
from forth.builtins.strings import register_string_ops
from forth.builtins.utility import register_utility_words
from forth.builtins.exceptions import register_exception_words
from forth.builtins.file_ops import register_file_ops

__all__ = ["register_all"]


def register_all(interp) -> None:
    """Register every built-in word on *interp*."""
    register_stack_ops(interp)
    register_arithmetic(interp)
    register_float_ops(interp)
    register_comparison(interp)
    register_bitwise(interp)
    register_io_ops(interp)
    register_memory_ops(interp)
    register_defining_words(interp)
    register_control_flow(interp)
    register_case_ops(interp)
    register_array_ops(interp)
    register_string_ops(interp)
    register_utility_words(interp)
    register_exception_words(interp)
    register_file_ops(interp)