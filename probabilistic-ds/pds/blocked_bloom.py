"""Blocked Bloom Filter: cache-friendly Bloom filter variant.

A Blocked Bloom Filter divides the bit array into blocks (each fitting in a
cache line, e.g. 512 bits = 64 bytes).  Each element is hashed to determine
which *block* it belongs to, then all k hash functions operate within that
single block.  This dramatically improves cache locality — every access
touches at most one cache line instead of k scattered lines.

Reference: Putze, Sanders, Singler (2007).

The trade-off: slightly higher false-positive rate than a standard Bloom
filter (because all k bits land in the same block), but much faster due to
cache efficiency.  For the FPR to stay close to the target, we use k
independently-seeded FNV-1a hashes within each block (rather than double
hashing, which creates correlated probe sequences within small blocks).
"""
from __future__ import annotations

import math
import struct

from .hashing import fnv1a_64
from .bloom import BloomFilter


class BlockedBloomFilter:
    """Cache-friendly Bloom filter with block-level hashing.

    Parameters
    ----------
    capacity : int
        Expected number of distinct elements.
    error_rate : float
        Target false-positive probability.
    block_bits : int
        Bits per block (default 512 = one 64-byte cache line).
    """

    BLOCK_BITS = 512  # 64 bytes, typical cache line size

    def __init__(self, capacity: int, error_rate: float = 0.01,
                 block_bits: int = 512):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if not (0 < error_rate < 1):
            raise ValueError("error_rate must be in (0, 1)")
        if block_bits <= 0 or (block_bits & (block_bits - 1)) != 0:
            raise ValueError("block_bits must be a positive power of 2")

        self.capacity = capacity
        self.error_rate = error_rate
        self.block_bits = block_bits

        # Total bits: standard Bloom sizing
        total_bits = max(block_bits,
                         BloomFilter._optimal_m(capacity, error_rate))
        # Round up to a multiple of block_bits
        self.num_bits = ((total_bits + block_bits - 1) // block_bits) * block_bits
        self.num_blocks = self.num_bits // block_bits

        # Number of hash functions (standard optimal k)
        self.num_hashes = BloomFilter._optimal_k(self.num_bits, capacity)

        # Pre-compute seeds for k independent within-block hash functions.
        # Each seed produces a different FNV-1a hash, giving us k truly
        # independent probe positions within the block.
        self._seeds = [(i * 0x9E3779B9 + 0x85EBCA77) & 0xFFFFFFFF
                       for i in range(self.num_hashes)]

        # Storage
        self._bits = bytearray(self.num_bits // 8)
        self.count = 0

    @staticmethod
    def _serialize(item) -> bytes:
        if isinstance(item, bytes):
            return item
        if isinstance(item, str):
            return item.encode("utf-8")
        return repr(item).encode("utf-8")

    def _block_and_positions(self, data: bytes) -> tuple[int, list[int]]:
        """Compute block index and k within-block positions for serialized data.

        Uses MD5 for both block selection and within-block positions to
        ensure high-quality, independent hashing.  MD5 is used here (not
        FNV-1a) because FNV-1a has poor avalanche properties for short
        inputs, which causes severely inflated false-positive rates when
        all k probes land in the same small block.

        For applications where speed is more important than exact FPR, use
        the standard ``BloomFilter`` instead.
        """
        from .hashing import md5_128
        # Block selection from first 8 bytes of MD5
        block_idx = md5_128(b"B" + data) % self.num_blocks
        base = block_idx * self.block_bits
        # Within-block positions: k independent hashes derived from MD5
        # with different seed prefixes
        positions = []
        for i in range(self.num_hashes):
            h = md5_128(i.to_bytes(2, "little") + data)
            positions.append(h % self.block_bits + base)
        return block_idx, positions

    def add(self, item) -> None:
        """Add an item to the filter."""
        data = self._serialize(item)
        _, positions = self._block_and_positions(data)
        for pos in positions:
            self._bits[pos >> 3] |= (1 << (pos & 7))
        self.count += 1

    def __contains__(self, item) -> bool:
        """Check membership — may return false positives, never false negatives."""
        data = self._serialize(item)
        _, positions = self._block_and_positions(data)
        for pos in positions:
            if not (self._bits[pos >> 3] & (1 << (pos & 7))):
                return False
        return True

    def __len__(self) -> int:
        return self.count

    @property
    def estimated_false_positive_rate(self) -> float:
        """Current estimated FPR.

        Slightly higher than a standard Bloom filter because all k hashes
        land in the same block.  We use a correction factor.
        """
        n = self.count
        # Standard formula
        base_fpr = (1 - math.exp(-self.num_hashes * n / self.num_bits)) ** \
                   self.num_hashes
        # Block correction: within-block collisions increase FPR slightly.
        # Approximation: FPR_blocked ≈ FPR * (1 + k*(k-1)/(2*block_bits))
        correction = 1 + self.num_hashes * (self.num_hashes - 1) / \
                     (2 * self.block_bits)
        return min(1.0, base_fpr * correction)

    def to_bytes(self) -> bytes:
        """Serialize to bytes."""
        header = struct.pack(
            "<QdQIQIQ",
            self.capacity, self.error_rate, self.num_bits,
            self.num_blocks, self.block_bits, self.num_hashes, self.count,
        )
        return header + bytes(self._bits)

    @classmethod
    def from_bytes(cls, data: bytes) -> "BlockedBloomFilter":
        """Deserialize from bytes."""
        header_size = struct.calcsize("<QdQIQIQ")
        capacity, error_rate, num_bits, num_blocks, block_bits, \
            num_hashes, count = struct.unpack("<QdQIQIQ", data[:header_size])
        bf = cls(capacity, error_rate, block_bits)
        bf.num_bits = num_bits
        bf.num_blocks = num_blocks
        bf.num_hashes = num_hashes
        bf.count = count
        bf._bits = bytearray(data[header_size:])
        return bf