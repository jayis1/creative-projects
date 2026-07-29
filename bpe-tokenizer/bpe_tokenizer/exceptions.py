"""Custom exception hierarchy for the BPE tokenizer.

All exceptions raised by the library derive from :class:`BPETokenizerError`,
making it easy for users to catch library-specific errors without
interfering with stdlib exceptions.
"""

from __future__ import annotations

__all__ = [
    "BPETokenizerError",
    "TrainingError",
    "EncodingError",
    "DecodingError",
    "SerializationError",
    "ConfigError",
    "VocabError",
]


class BPETokenizerError(Exception):
    """Base exception for all BPE tokenizer errors."""


class TrainingError(BPETokenizerError):
    """Raised when training fails (invalid config, empty corpus, etc.)."""


class EncodingError(BPETokenizerError):
    """Raised when encoding fails (untrained tokenizer, invalid input)."""


class DecodingError(BPETokenizerError):
    """Raised when decoding fails (invalid ids, corrupted state)."""


class SerializationError(BPETokenizerError):
    """Raised when serialization/deserialization fails."""


class ConfigError(BPETokenizerError):
    """Raised when configuration is invalid or cannot be loaded."""


class VocabError(BPETokenizerError):
    """Raised for vocabulary-related errors (duplicates, missing tokens)."""