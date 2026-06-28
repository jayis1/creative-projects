"""Exception hierarchy for the SMT solver."""


class SMTError(Exception):
    """Base exception for all SMT solver errors."""


class ParseError(SMTError):
    """Raised when SMT-LIB input cannot be parsed."""


class TheoryError(SMTError):
    """Raised when a theory solver encounters an inconsistency."""


class TypeCheckError(SMTError):
    """Raised when a term has a type error."""