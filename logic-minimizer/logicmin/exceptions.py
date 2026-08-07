"""
Custom exception hierarchy for logicmin.
"""


class LogicMinError(Exception):
    """Base exception for all logicmin errors."""


class ParseError(LogicMinError):
    """Raised when input parsing fails."""


class MinimizationError(LogicMinError):
    """Raised when minimization fails (e.g. internal inconsistency)."""


class InvalidFunctionError(LogicMinError):
    """Raised when a boolean function specification is invalid."""


class PetrickExpansionError(LogicMinError):
    """Raised when Petrick's method expansion exceeds the product limit."""