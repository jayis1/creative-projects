"""
BASIC Language Interpreter — A full-featured interpreter for a classic BASIC dialect.

This package provides a complete interpreter for a classic BASIC programming language,
including a lexer, parser, and tree-walking interpreter with support for:

- Line-numbered programs with GOTO / GOSUB / RETURN
- IF...THEN...ELSE / FOR...NEXT / WHILE...WEND / DO...LOOP
- SELECT CASE multi-way branching
- LET, PRINT, PRINT USING, INPUT, LINE INPUT, READ, DATA, RESTORE
- DIM for arrays (1D and 2D), ERASE to deallocate
- DEF FN for user-defined functions
- String and numeric operations
- Built-in functions (math, string, I/O, system)
- Logical operators (AND, OR, NOT, XOR, EQV, IMP)
- File I/O (OPEN, CLOSE, PRINT#, INPUT#, LINE INPUT#)
- ON ERROR GOTO / RESUME error handling
- Interactive REPL with SAVE, LOAD, LIST, EDIT, DELETE commands
"""

__version__ = "3.0.0"
__author__ = "Creative Projects"

from basic_interpreter.interpreter import Interpreter
from basic_interpreter.errors import BasicError, BasicSyntaxError, BasicRuntimeError, BasicStopException

__all__ = [
    "Interpreter",
    "BasicError",
    "BasicSyntaxError",
    "BasicRuntimeError",
    "BasicStopException",
    "__version__",
]