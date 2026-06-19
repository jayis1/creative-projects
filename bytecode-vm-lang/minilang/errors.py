"""MiniLang error hierarchy.

All errors raised by the compiler pipeline carry:
  - a human-readable ``message``
  - an optional ``line`` / ``col`` for source-level diagnostics
  - an optional ``name`` (the source-file name) for error formatting
"""


class MiniLangError(Exception):
    """Base class for every MiniLang error."""

    def __init__(self, message: str, line: int | None = None,
                 col: int | None = None, name: str = "<string>",
                 source: str | None = None):
        super().__init__(message)
        self.message = message
        self.line = line
        self.col = col
        self.name = name
        self.source = source

    def format(self) -> str:
        """Return a nicely formatted diagnostic string with source context."""
        loc = ""
        if self.line is not None:
            loc = f"{self.name}:{self.line}"
            if self.col is not None:
                loc += f":{self.col}"
            loc += " "
        result = f"error: {loc}{self.message}"
        # Add source context if available.
        if self.source is not None and self.line is not None:
            lines = self.source.split("\n")
            if 1 <= self.line <= len(lines):
                src_line = lines[self.line - 1]
                result += f"\n  {self.line:4d} | {src_line}"
                if self.col is not None and 1 <= self.col <= len(src_line) + 1:
                    # Draw a caret pointing at the column.
                    padding = " " * (len(str(self.line)) + 7 + self.col - 1)
                    result += f"\n       {padding}^"
        return result


class LexError(MiniLangError):
    """Raised by the lexer for an invalid character."""


class ParseError(MiniLangError):
    """Raised by the parser for a grammar violation."""


class CompileError(MiniLangError):
    """Raised by the compiler for a code-generation problem."""


class VMError(MiniLangError):
    """Raised by the VM for a runtime failure (e.g. stack underflow)."""