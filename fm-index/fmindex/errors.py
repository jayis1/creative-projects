"""Custom exception hierarchy for the FM-Index package.

All exceptions raised by the package derive from :class:`FMIndexError` so
callers can catch every package-specific error with a single ``except``
clause.
"""

from __future__ import annotations


class FMIndexError(Exception):
    """Base class for all FM-Index errors."""


class ConstructionError(FMIndexError):
    """Raised when index construction fails (bad input, sentinel issues, …)."""


class SerializationError(FMIndexError):
    """Raised when loading/saving an index fails (bad magic, version, …)."""


class QueryError(FMIndexError):
    """Raised for invalid query parameters (bad pattern, out-of-range, …)."""


class ConfigError(FMIndexError):
    """Raised when a configuration file is malformed or invalid."""