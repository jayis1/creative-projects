"""Abstract base class for all compression codecs.

Provides a consistent interface contract and shared utilities
for integrity checking and error handling.
"""

from __future__ import annotations

import abc
import zlib
from typing import Optional


class CompressionError(Exception):
    """Base exception for compression/decompression failures."""


class IntegrityError(CompressionError):
    """Raised when CRC32 checksum verification fails."""

    def __init__(self, expected: int, actual: int, context: str = "") -> None:
        self.expected = expected
        self.actual = actual
        msg = f"CRC32 mismatch: expected {expected:#010x}, got {actual:#010x}"
        if context:
            msg += f" ({context})"
        super().__init__(msg)


class FormatError(CompressionError):
    """Raised when compressed data format is invalid or corrupted."""


def verify_crc32(data: bytes, expected: int, context: str = "") -> None:
    """Verify CRC32 checksum of data, raising IntegrityError on mismatch.

    Args:
        data: The decompressed data to verify.
        expected: The expected CRC32 checksum.
        context: Optional context string for error messages.

    Raises:
        IntegrityError: If checksum doesn't match.
    """
    actual = zlib.crc32(data) & 0xFFFFFFFF
    if actual != expected:
        raise IntegrityError(expected, actual, context)


def compute_crc32(data: bytes) -> int:
    """Compute CRC32 checksum of data.

    Args:
        data: Input byte sequence.

    Returns:
        CRC32 checksum as unsigned 32-bit integer.
    """
    return zlib.crc32(data) & 0xFFFFFFFF


class Codec(abc.ABC):
    """Abstract base class for compression codecs.

    All codecs must implement compress() and decompress() methods.
    Subclasses should also set a `name` class attribute for identification.
    """

    name: str = "unknown"

    @abc.abstractmethod
    def compress(self, data: bytes) -> bytes:
        """Compress the input data.

        Args:
            data: Raw input bytes to compress.

        Returns:
            Compressed bytes including any header/metadata.

        Raises:
            CompressionError: If compression fails.
        """

    @abc.abstractmethod
    def decompress(self, data: bytes) -> bytes:
        """Decompress the input data.

        Args:
            data: Compressed bytes (as returned by compress).

        Returns:
            Original uncompressed bytes.

        Raises:
            FormatError: If the compressed data format is invalid.
            IntegrityError: If CRC32 verification fails.
        """

    def roundtrip(self, data: bytes) -> bool:
        """Test whether compress then decompress reproduces original data.

        Args:
            data: Input bytes to test.

        Returns:
            True if roundtrip succeeds, False otherwise.
        """
        try:
            return self.decompress(self.compress(data)) == data
        except Exception:
            return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"