"""Exception hierarchy for the mini-Prolog engine.

Provides a clean, structured set of exceptions for different error
conditions, making it easier to catch specific failures.
"""

from __future__ import annotations

from typing import Optional


class PrologError(Exception):
    """Base exception for all Prolog engine errors."""

    def __init__(self, message: str, *, detail: Optional[str] = None):
        super().__init__(message)
        self.detail = detail

    def __str__(self) -> str:
        if self.detail:
            return f"{super().__str__()} ({self.detail})"
        return super().__str__()


class LexerError(PrologError):
    """Raised when the lexer encounters an invalid character or token.

    Attributes:
        line: Source line where the error occurred.
        col: Source column where the error occurred.
    """

    def __init__(self, message: str, line: int = 0, col: int = 0):
        super().__init__(f"{message} at line {line}, column {col}")
        self.line = line
        self.col = col


class ParseError(PrologError):
    """Raised when the parser encounters unexpected tokens.

    Attributes:
        token: The token where parsing failed (if available).
    """

    def __init__(self, message: str, token=None):
        super().__init__(message)
        self.token = token


class UnificationError(PrologError):
    """Raised when two terms cannot be unified."""


class EngineError(PrologError):
    """Raised when the engine encounters a runtime error.

    This includes depth limit exceeded, maximum solutions exceeded,
    division by zero, and other execution-time errors.
    """


class EvaluationError(PrologError):
    """Raised when an arithmetic expression cannot be evaluated.

    In standard Prolog, this is an evaluation error (e.g., unknown function,
    non-numeric argument). In our implementation, these are caught by builtins
    and converted to failure (no solutions), since that's more user-friendly.
    """


class InstantiationError(PrologError):
    """Raised when an argument that should be instantiated is a variable.

    For example, trying to evaluate `X is Y + 1` when Y is uninstantiated.
    """

    def __init__(self, message: str = "Instantiation error", *, argument=None):
        super().__init__(message)
        self.argument = argument


class TypeError(PrologError):
    """Raised when an argument has the wrong type.

    For example, passing a string where a number is expected.
    """

    def __init__(self, message: str = "Type error", *, expected: str = "", got: str = ""):
        detail = f"expected {expected}, got {got}" if expected or got else None
        super().__init__(message, detail=detail)
        self.expected = expected
        self.got = got


class ExistenceError(PrologError):
    """Raised when a referenced procedure or file does not exist.

    For example, calling an undefined predicate.
    """

    def __init__(self, message: str = "Existence error", *, procedure: str = ""):
        detail = f"procedure {procedure}" if procedure else None
        super().__init__(message, detail=detail)
        self.procedure = procedure


class PermissionError(PrologError):
    """Raised when an operation is not permitted.

    For example, modifying a static predicate.
    """

    def __init__(self, message: str = "Permission error", *, operation: str = ""):
        detail = f"operation {operation}" if operation else None
        super().__init__(message, detail=detail)
        self.operation = operation