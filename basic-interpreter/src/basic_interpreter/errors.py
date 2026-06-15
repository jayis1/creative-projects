"""Custom exceptions for the BASIC interpreter."""


class BasicError(Exception):
    """Base exception for all BASIC interpreter errors."""
    pass


class BasicSyntaxError(BasicError):
    """Raised when the parser encounters invalid syntax."""
    pass


class BasicRuntimeError(BasicError):
    """Raised when the interpreter encounters a runtime error."""
    pass


class BasicStopException(Exception):
    """Raised when a STOP statement is encountered (not an error, but a break)."""
    pass