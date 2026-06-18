"""MinHash: approximate set similarity (Jaccard) estimation.

MinHash estimates the Jaccard similarity |A ∩ B| / |A ∪ B| between two sets
using a fixed number of independent hash functions.  Each "signature" is a
fixed-length array of minimum hash values; similarity ≈ fraction of
matching signature positions.

Based on Broder (1997).

Memory: O(k) 64-bit integers regardless of set size.  This is dramatically
smaller than storing full sets, and enables near-duplicate detection at scale
(e.g. web page dedup, document clustering).
"""
from __future__ import annotations

import io
import json
import base64
from typing import Iterable, Iterator

from .hashing import fnv1a_64, double_hash


class MinHash:
    """MinHash signature for approximate Jaccard similarity.

    Parameters
    ----------
    num_perm : int
        Number of permutations (hash functions).  Higher → lower error.
        Standard error ≈ 1/√num_perm.  Default 128 (~8.8% error).
    seed : int
        Base seed for the hash functions (so two MinHashes must share the
        same ``num_perm`` *and* ``seed`` to be comparable).

    Examples
    --------
    >>> m1 = MinHash(num_perm=64)
    >>> m2 = MinHash(num_perm=64)
    >>> for w in "the quick brown fox".split(): m1.add(w)
    >>> for w in "the quick red fox".split(): m2.add(w)
    >>> 0.4 < m1.jaccard(m2) < 0.8
    True
    """

    MAX_HASH = (1 << 64) - 1
    _MERSENNE = (1 << 61) - 1  # large prime for modular hashing

    def __init__(self, num_perm: int = 128, seed: int = 0):
        if num_perm <= 0:
            raise ValueError("num_perm must be positive")
        self.num_perm = num_perm
        self.seed = seed
        # Each permutation is (a, b) where h(x) = (a*x + b) mod p
        # We derive these deterministically from the seed.
        self._a: list[int] = []
        self._b: list[int] = []
        rng_state = seed
        for i in range(num_perm):
            # Simple LCG for deterministic parameter generation
            rng_state = (1103515245 * rng_state + 12345) & 0x7FFFFFFF
            a = (rng_state % (self._MERSENNE - 1)) + 1
            rng_state = (1103515245 * rng_state + 12345) & 0x7FFFFFFF
            b = rng_state % self._MERSENNE
            self._a.append(a)
            self._b.append(b)
        # Signature: initialize to max value
        self._signature: list[int] = [self.MAX_HASH] * num_perm

    @staticmethod
    def _serialize(item) -> bytes:
        if isinstance(item, bytes):
            return item
        if isinstance(item, str):
            return item.encode("utf-8")
        return repr(item).encode("utf-8")

    def _hash_item(self, data: bytes) -> int:
        """Base 64-bit hash of the item.

        Uses MD5 for uniform distribution.  FNV-1a has poor avalanche
        properties for short inputs, which biases MinHash signatures.
        """
        from .hashing import md5_128
        return md5_128(data) & ((1 << 64) - 1)

    def add(self, item) -> None:
        """Add an item to the signature."""
        data = self._serialize(item)
        x = self._hash_item(data)
        for i in range(self.num_perm):
            # h_i(x) = (a_i * x + b_i) mod p
            h = (self._a[i] * x + self._b[i]) % self._MERSENNE
            if h < self._signature[i]:
                self._signature[i] = h

    def add_batch(self, items: Iterable) -> None:
        """Add multiple items at once (slightly more efficient)."""
        for item in items:
            self.add(item)

    def jaccard(self, other: "MinHash") -> float:
        """Estimate Jaccard similarity with another MinHash.

        Both MinHashes must have the same ``num_perm`` and ``seed``.
        """
        if self.num_perm != other.num_perm:
            raise ValueError(
                "Cannot compare MinHashes with different num_perm"
            )
        if self.seed != other.seed:
            raise ValueError(
                "Cannot compare MinHashes with different seeds "
                f"(self.seed={self.seed}, other.seed={other.seed})"
            )
        if self.num_perm == 0:
            return 0.0
        matches = sum(1 for a, b in zip(self._signature, other._signature)
                      if a == b)
        return matches / self.num_perm

    def merge(self, other: "MinHash") -> None:
        """Merge another MinHash into this one (set union).

        After merge, ``self`` represents the union of the two original sets.
        The merge is element-wise minimum of signatures.
        """
        if self.num_perm != other.num_perm or self.seed != other.seed:
            raise ValueError("Cannot merge MinHashes with different config")
        for i in range(self.num_perm):
            if other._signature[i] < self._signature[i]:
                self._signature[i] = other._signature[i]

    def is_empty(self) -> bool:
        """True if no items have been added."""
        return all(s == self.MAX_HASH for s in self._signature)

    def __len__(self) -> int:
        """Number of permutations."""
        return self.num_perm

    def estimated_cardinality(self) -> float:
        """Rough cardinality estimate from the mean of signature values.

        Uses the fact that for uniform hashing, E[min hash] ≈ MAX_HASH/(n+1)
        where n is the set cardinality.  This is a noisy estimator.
        """
        if self.is_empty():
            return 0.0
        avg = sum(self._signature) / self.num_perm
        if avg == 0:
            return float("inf")
        # n ≈ MAX_HASH / avg - 1
        return self.MAX_HASH / avg - 1

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "num_perm": self.num_perm,
            "seed": self.seed,
            "signature": self._signature,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MinHash":
        """Deserialize from a dict produced by ``to_dict``."""
        mh = cls(num_perm=d["num_perm"], seed=d["seed"])
        mh._signature = list(d["signature"])
        return mh

    def to_json(self) -> str:
        """Serialize to a JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, data: str) -> "MinHash":
        """Deserialize from a JSON string."""
        return cls.from_dict(json.loads(data))


class LSHIndex:
    """Locality-Sensitive Hashing index for fast near-duplicate detection.

    Bands documents into rows of the MinHash signature; documents that share
    at least one band are candidates for near-duplicate.  This reduces the
    O(n²) pairwise comparison to O(n) per band.

    Parameters
    ----------
    num_perm : int
        Number of permutations (must match MinHash used).
    num_bands : int
        Number of bands; signature is split into ``num_bands`` bands of
        ``num_perm / num_bands`` rows each.  ``num_perm`` must be divisible
        by ``num_bands``.  Higher ``num_bands`` → lower threshold (more
        candidates).
    seed : int
        Base seed, must match the MinHash seed.

    The threshold ≈ (1/num_bands)^(1/rows_per_band).
    """

    def __init__(self, num_perm: int = 128, num_bands: int = 32,
                 seed: int = 0):
        if num_perm <= 0 or num_bands <= 0:
            raise ValueError("num_perm and num_bands must be positive")
        if num_perm % num_bands != 0:
            raise ValueError(
                f"num_perm ({num_perm}) must be divisible by "
                f"num_bands ({num_bands})"
            )
        self.num_perm = num_perm
        self.num_bands = num_bands
        self.rows_per_band = num_perm // num_bands
        self.seed = seed
        # band -> {hash(frozenset of rows): set of doc_ids}
        self._bands: list[dict[int, set]] = [
            {} for _ in range(num_bands)
        ]
        self._docs: dict[str, MinHash] = {}

    @property
    def threshold(self) -> float:
        """Approximate Jaccard similarity threshold above which pairs are
        likely to be returned as candidates."""
        return (1.0 / self.num_bands) ** (1.0 / self.rows_per_band)

    def add(self, doc_id: str, mh: MinHash) -> None:
        """Add a document (with its MinHash signature) to the index."""
        if mh.num_perm != self.num_perm:
            raise ValueError("MinHash num_perm does not match index")
        self._docs[doc_id] = mh
        for band_idx in range(self.num_bands):
            start = band_idx * self.rows_per_band
            end = start + self.rows_per_band
            band = tuple(mh._signature[start:end])
            band_hash = hash(band)
            if band_hash not in self._bands[band_idx]:
                self._bands[band_idx][band_hash] = set()
            self._bands[band_idx][band_hash].add(doc_id)

    def query(self, mh: MinHash, exclude: str | None = None) -> set[str]:
        """Return candidate near-duplicate doc_ids for the given MinHash."""
        if mh.num_perm != self.num_perm:
            raise ValueError("MinHash num_perm does not match index")
        candidates: set[str] = set()
        for band_idx in range(self.num_bands):
            start = band_idx * self.rows_per_band
            end = start + self.rows_per_band
            band = tuple(mh._signature[start:end])
            band_hash = hash(band)
            for doc_id in self._bands[band_idx].get(band_hash, set()):
                if doc_id != exclude:
                    candidates.add(doc_id)
        return candidates

    def __contains__(self, doc_id: str) -> bool:
        return doc_id in self._docs

    def __len__(self) -> int:
        return len(self._docs)

    def get_minhash(self, doc_id: str) -> MinHash | None:
        """Retrieve the MinHash for a document, or None."""
        return self._docs.get(doc_id)