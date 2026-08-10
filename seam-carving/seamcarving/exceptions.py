"""
seamcarving/exceptions.py — Exception hierarchy for seam carving.

Centralises all custom exception types so that callers can catch
specific error conditions without relying on ``core`` module imports.
"""

from __future__ import annotations


class SeamCarvingError(Exception):
    """Base exception for all seam-carving errors."""


class InvalidImageError(SeamCarvingError):
    """Raised when an image is malformed, unsupported, or has the wrong shape."""

    def __init__(self, message: str, path: str | None = None) -> None:
        self.path = path
        if path:
            super().__init__(f"{message} ({path})")
        else:
            super().__init__(message)


class InvalidConfigError(SeamCarvingError):
    """Raised when a configuration file is malformed or has invalid values."""


class InvalidMaskError(SeamCarvingError):
    """Raised when a mask file or array has invalid dimensions or content."""


class EnergyComputationError(SeamCarvingError):
    """Raised when energy computation fails (e.g. unknown energy type)."""


class SeamOperationError(SeamCarvingError):
    """Raised when a seam carving operation fails (e.g. dimensions exceeded)."""