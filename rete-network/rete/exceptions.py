"""Custom exceptions for the Rete engine.

Exception hierarchy
-------------------
    ReteError
    ├── RuleError
    ├── FactError
    ├── MatchError
    ├── InfiniteLoopError
    └── SerializationError
"""

from __future__ import annotations


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


class SerializationError(ReteError):
    """Raised when serialization or deserialization fails."""