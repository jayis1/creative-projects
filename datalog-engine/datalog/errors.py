"""Exception hierarchy for the Datalog engine."""

from __future__ import annotations


class DatalogError(Exception):
    """Base class for all Datalog engine errors."""


class StratificationError(DatalogError):
    """Raised when a program cannot be stratified (negative cycle)."""


class SafetyError(DatalogError):
    """Raised when a rule violates the Datalog safety condition."""


class ConfigurationError(DatalogError):
    """Raised when a configuration file is invalid."""


class QueryError(DatalogError):
    """Raised when a query cannot be evaluated."""