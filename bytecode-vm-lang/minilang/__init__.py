"""MiniLang — a small statically-typed language with a bytecode VM.

Public API::

    from minilang import Source, compile_program, VM

    src = Source("let x: int = 40 + 2; print(x)")
    program = compile_program(src.code)
    result = VM(program).run()
"""

from .lexer import Lexer, Token, TokenKind
from .parser import Parser
from .types import TypeChecker, TypeError as MLTypeError
from .optimizer import optimize
from .bytecode import Instruction, OpCode, Disassembler
from .compiler import Compiler, compile_program
from .vm import VM
from .value import Value, Object
from .errors import MiniLangError, LexError, ParseError

__version__ = "2.0.0"

__all__ = [
    "Lexer", "Token", "TokenKind",
    "Parser",
    "TypeChecker", "MLTypeError",
    "optimize",
    "Instruction", "OpCode", "Disassembler",
    "Compiler", "compile_program",
    "VM",
    "Value", "Object",
    "MiniLangError", "LexError", "ParseError",
    "Source",
]


class Source:
    """Convenience wrapper for a source-code string.

    Carries a ``name`` for error messages and exposes ``code``.
    """

    __slots__ = ("code", "name")

    def __init__(self, code: str, name: str = "<string>"):
        self.code = code
        self.name = name

    def __repr__(self) -> str:
        return f"Source(name={self.name!r}, len={len(self.code)})"