"""MiniLang error hierarchy.

All errors raised by the compiler pipeline carry:
  - a human-readable ``message``
  - an optional ``line`` / ``col`` for source-level diagnostics
  - an optional ``name`` (the source-file name) for error formatting
"""


class MiniLangError(Exception):
    """Base class for every MiniLang error."""

    def __init__(self, message: str, line: int | None = None,
                 col: int | None = None, name: str = "<string>"):
        super().__init__(message)
        self.message = message
        self.line = line
        self.col = col
        self.name = name

    def format(self) -> str:
        """Return a nicely formatted diagnostic string."""
        loc = ""
        if self.line is not None:
            loc = f"{self.name}:{self.line}"
            if self.col is not None:
                loc += f":{self.col}"
            loc += " "
        return f"error: {loc}{self.message}"


class LexError(MiniLangError):
    """Raised by the lexer for an invalid character."""


class ParseError(MiniLangError):
    """Raised by the parser for a grammar violation."""


class CompileError(MiniLangError):
    """Raised by the compiler for a code-generation problem."""


class VMError(MiniLangError):
    """Raised by the VM for a runtime failure (e.g. stack underflow)."""