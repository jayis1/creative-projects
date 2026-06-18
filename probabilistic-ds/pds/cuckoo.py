"""Cuckoo filter: approximate set membership with deletion support.

Cuckoo filters store fingerprints in a table of buckets and use cuckoo
hashing to resolve collisions.  They support deletion (unlike standard
Bloom filters) and achieve better space efficiency than Bloom filters
for low FPR targets.

Reference: Fan, Andersen, Kaminsky, Mitzenmacher (2014).
"""
import math
import random
from .hashing import fnv1a_64

_MAX_KICKS = 500
_MAX_BUCKET_SIZE = 4


class CuckooFilter:
    """Cuckoo filter with configurable bucket size and fingerprint size.

    Parameters
    ----------
    capacity : int
        Expected number of distinct elements.  The table is sized to
        ``capacity / bucket_size * (1/fpr_factor)`` rounded to a power of two.
    bucket_size : int
        Number of slots per bucket (default 4, optimal per the paper).
    fingerprint_bits : int
        Bit width of fingerprints (default 12).  Larger → lower FPR, more space.
    max_kicks : int
        Max displacement attempts before declaring "full".
    """

    def __init__(self, capacity: int, bucket_size: int = 4,
                 fingerprint_bits: int = 12, max_kicks: int = _MAX_KICKS):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if bucket_size <= 0:
            raise ValueError("bucket_size must be positive")
        if fingerprint_bits < 4 or fingerprint_bits > 32:
            raise ValueError("fingerprint_bits must be in [4, 32]")

        self.bucket_size = bucket_size
        self.fingerprint_bits = fingerprint_bits
        self.fingerprint_mask = (1 << fingerprint_bits) - 1
        self.max_kicks = max_kicks
        # Table size = next power of 2 >= capacity/bucket_size
        raw = max(1, int(math.ceil(capacity / bucket_size)))
        self.num_buckets = 1
        while self.num_buckets < raw:
            self.num_buckets <<= 1
        self._table: list[list[int]] = [[] for _ in range(self.num_buckets)]
        self.count = 0

    def _fingerprint(self, data: bytes) -> int:
        # Derive fingerprint from upper bits of a 64-bit hash, independent
        # from the index hash (lower bits) to avoid correlation.
        # Cache the hash to avoid recomputing it in _hash().
        h = fnv1a_64(data + b"\x01")
        fp = (h >> (64 - self.fingerprint_bits)) & self.fingerprint_mask
        # Ensure fingerprint is never zero (zero is used as empty slot sentinel)
        return fp if fp != 0 else 1

    def _hash(self, data: bytes) -> int:
        # Use the lower 32 bits of the same hash for the primary index,
        # independent from the fingerprint (upper bits).
        return fnv1a_64(data + b"\x01") & 0xFFFFFFFF

    def _alt_index(self, index: int, fp: int) -> int:
        # partial-key cuckoo hashing: h2 = h1 ^ hash(fp)
        fp_hash = fnv1a_64(struct_fp(fp))
        return (index ^ fp_hash) & (self.num_buckets - 1)

    def _compute_fp_and_index(self, data: bytes) -> tuple[int, int, int]:
        """Compute fingerprint, primary index, and alternate index in one pass.

        Returns (fp, i1, i2).  Computes the 64-bit hash only once instead
        of twice (previously _fingerprint and _hash each called fnv1a_64).
        """
        h = fnv1a_64(data + b"\x01")
        fp = (h >> (64 - self.fingerprint_bits)) & self.fingerprint_mask
        if fp == 0:
            fp = 1  # zero is the empty-slot sentinel
        i1 = (h & 0xFFFFFFFF) & (self.num_buckets - 1)
        i2 = self._alt_index(i1, fp)
        return fp, i1, i2

    def add(self, item) -> None:
        """Add an item. Raises if the filter is full."""
        data = self._serialize(item)
        fp, i1, i2 = self._compute_fp_and_index(data)

        if len(self._table[i1]) < self.bucket_size:
            self._table[i1].append(fp)
            self.count += 1
            return
        if len(self._table[i2]) < self.bucket_size:
            self._table[i2].append(fp)
            self.count += 1
            return

        # Cuckoo eviction
        i = random.choice([i1, i2])
        for _ in range(self.max_kicks):
            if len(self._table[i]) < self.bucket_size:
                self._table[i].append(fp)
                self.count += 1
                return
            # Evict a random slot
            slot = random.randrange(len(self._table[i]))
            fp, self._table[i][slot] = self._table[i][slot], fp
            i = self._alt_index(i, fp)

        raise RuntimeError("CuckooFilter is full — try increasing capacity")

    def __contains__(self, item) -> bool:
        data = self._serialize(item)
        fp, i1, i2 = self._compute_fp_and_index(data)
        return fp in self._table[i1] or fp in self._table[i2]

    def remove(self, item) -> bool:
        """Remove an item. Returns True if found and removed."""
        data = self._serialize(item)
        fp, i1, i2 = self._compute_fp_and_index(data)

        if fp in self._table[i1]:
            self._table[i1].remove(fp)
            self.count -= 1
            return True
        if fp in self._table[i2]:
            self._table[i2].remove(fp)
            self.count -= 1
            return True
        return False

    @staticmethod
    def _serialize(item) -> bytes:
        if isinstance(item, bytes):
            return item
        if isinstance(item, str):
            return item.encode("utf-8")
        return repr(item).encode("utf-8")

    def __len__(self) -> int:
        return self.count

    @property
    def load_factor(self) -> float:
        return self.count / (self.num_buckets * self.bucket_size)


def struct_fp(fp: int) -> bytes:
    """Encode a fingerprint as bytes for hashing."""
    return bytes([fp & 0xFF, (fp >> 8) & 0xFF, (fp >> 16) & 0xFF, (fp >> 24) & 0xFF])