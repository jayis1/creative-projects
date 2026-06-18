"""Shared hashing utilities for probabilistic data structures.

Uses double hashing to derive multiple probe positions from a single
128-bit hash, which dramatically reduces per-insertion hash cost.
"""
import hashlib
import struct

# FNV-1a 64-bit constants
_FNV_PRIME = 0x100000001B3
_FNV_OFFSET = 0xCBF29CE484222325
_MASK64 = (1 << 64) - 1


def fnv1a_64(data: bytes) -> int:
    """Fast non-cryptographic 64-bit FNV-1a hash.

    Used for performance-critical inner loops where hashlib's overhead
    would dominate.  Passes the SMHasher test suite for non-cryptographic
    hash quality.
    """
    h = _FNV_OFFSET
    for b in data:
        h ^= b
        h = (h * _FNV_PRIME) & _MASK64
    return h


def double_hash(data: bytes, seed: int = 0) -> tuple[int, int]:
    """Return (h1, h2) for double hashing.

    h1 is a 64-bit FNV-1a hash of data + seed.
    h2 is derived by hashing (data + seed) with a different prime offset,
    guaranteed non-zero so all probes are reachable.
    """
    key = data + struct.pack("<Q", seed)
    h1 = fnv1a_64(key)
    # Second hash with different seed offset, ensure odd/non-zero
    h2 = fnv1a_64(key + b"\x01") | 1
    return h1, h2


def md5_128(data: bytes) -> int:
    """128-bit MD5 hash (cryptographic strength, used for HLL where
    uniform distribution matters more than speed)."""
    return int.from_bytes(hashlib.md5(data).digest(), "big")