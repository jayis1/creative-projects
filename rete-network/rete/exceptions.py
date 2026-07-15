"""Custom exceptions for the Rete engine."""


class ReteError(Exception):
    """Base exception for all Rete-related errors."""


class RuleError(ReteError):
    """Raised when a rule definition is invalid."""


class FactError(ReteError):
    """Raised when a fact is invalid."""


class MatchError(ReteError):
    """Raised when pattern matching fails unexpectedly."""


class InfiniteLoopError(ReteError):
    """Raised when the engine detects a non-terminating rule set."""