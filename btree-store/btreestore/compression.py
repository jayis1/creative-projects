"""
Optional page-level compression for btreestore.

Compresses page content using zlib before writing to disk, and
decompresses on read. This can significantly reduce file size for
data with repetition (e.g., JSON, text, similar values).

Compression is transparent: the store's page_size still determines
the in-memory page size, but compressed content may be shorter on disk.
When compression is enabled, pages are stored as:
  [type(1)] [compressed_flag(1)] [compressed_data...] [padding] [CRC32(4)]

When compressed_flag=0, the page is stored uncompressed (for pages
where compression doesn't help, e.g., already-random data).

Usage:
    from btreestore import Store
    from btreestore.compression import CompressionConfig

    with Store("mydb.btree", compression=CompressionConfig(level=6)) as store:
        store.put("key", "value" * 1000)  # compressed on disk
"""

from __future__ import annotations

import zlib
from dataclasses import dataclass
from typing import Optional


@dataclass
class CompressionConfig:
    """Configuration for page-level compression.

    Attributes:
        level: zlib compression level (0=none, 1=fast, 6=default, 9=best).
            Level 0 disables compression entirely.
        min_size: Minimum page content size to attempt compression.
            Pages smaller than this are stored uncompressed.
        max_ratio: If the compressed data is larger than max_ratio * original,
            the uncompressed data is stored instead. E.g., 0.9 means
            compression must save at least 10%.
    """
    level: int = 6
    min_size: int = 64
    max_ratio: float = 0.9

    def __post_init__(self):
        if not 0 <= self.level <= 9:
            raise ValueError(f"compression level must be 0-9, got {self.level}")
        if self.min_size < 0:
            raise ValueError("min_size must be >= 0")
        if not 0 < self.max_ratio <= 1.0:
            raise ValueError("max_ratio must be in (0, 1.0]")


def compress_page(data: bytes, config: CompressionConfig) -> bytes:
    """Compress page content.

    If the data is too small or compression doesn't help, returns
    the original data with a flag byte prepended.

    Args:
        data: Raw page content (without CRC).
        config: Compression configuration.

    Returns:
        Compressed data with a 1-byte flag prefix:
          0x00 = uncompressed, followed by original data
          0x01 = compressed, followed by zlib-compressed data
    """
    if config.level == 0 or len(data) < config.min_size:
        return b"\x00" + data

    compressed = zlib.compress(data, config.level)
    if len(compressed) < len(data) * config.max_ratio:
        return b"\x01" + compressed
    return b"\x00" + data


def decompress_page(data: bytes) -> bytes:
    """Decompress page content.

    Args:
        data: Compressed data with 1-byte flag prefix.

    Returns:
        Original page content (without CRC).
    """
    if not data:
        return data
    flag = data[0]
    if flag == 0x01:
        return zlib.decompress(data[1:])
    elif flag == 0x00:
        return data[1:]
    else:
        # Unknown flag — assume uncompressed (no flag byte)
        # This handles pages written without compression support
        return data


def compression_ratio(original_size: int, compressed_size: int) -> float:
    """Calculate the compression ratio (0.0 = perfect, 1.0 = no change)."""
    if original_size == 0:
        return 1.0
    return compressed_size / original_size