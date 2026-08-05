"""
Exception hierarchy for the TDA toolkit.

All TDA-specific exceptions derive from :class:`TDAError`, making it
easy for callers to catch toolkit errors without masking unrelated
exceptions (``except TDAError``).
"""


class TDAError(Exception):
    """Base class for all TDA toolkit errors."""


class EmptyInputError(TDAError):
    """Raised when a required input (point cloud, grid, etc.) is empty."""


class DimensionMismatchError(TDAError):
    """Raised when two diagrams or structures have incompatible dimensions."""


class InvalidParameterError(TDAError):
    """Raised when a parameter value is out of range or otherwise invalid."""


class ComputationError(TDAError):
    """Raised when a computation cannot be completed (e.g. degenerate input)."""


class FileFormatError(TDAError):
    """Raised when a file cannot be parsed or is in an unexpected format."""