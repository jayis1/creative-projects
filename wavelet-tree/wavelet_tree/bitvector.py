"""BitVector implementations with rank/select support."""

from __future__ import annotations

import array
from typing import Iterator


class BitVector:
    """A simple bitvector with naive rank/select.

    rank1(i) returns the number of 1-bits in B[0..i) in O(n) time.
    select1(k) returns the position of the k-th 1-bit (0-indexed) in O(n) time.
    """

    def __init__(self, bits: list[int] | None = None):
        """Create a BitVector from a list of 0/1 integers."""
        if bits is None:
            bits = []
        for b in bits:
            if b not in (0, 1):
                raise ValueError(f"Bit must be 0 or 1, got {b}")
        self._bits: array.array = array.array("B", bits)
        self._n: int = len(bits)

    # --- basic access ---

    def __len__(self) -> int:
        return self._n

    def __getitem__(self, i: int) -> int:
        if i < 0:
            i += self._n
        if i < 0 or i >= self._n:
            raise IndexError(f"Index {i} out of range [0, {self._n})")
        return self._bits[i]

    def __iter__(self) -> Iterator[int]:
        return iter(self._bits)

    def append(self, bit: int) -> None:
        """Append a bit (0 or 1) to the end."""
        if bit not in (0, 1):
            raise ValueError(f"Bit must be 0 or 1, got {bit}")
        self._bits.append(bit)
        self._n += 1

    def to_list(self) -> list[int]:
        """Return the bits as a Python list."""
        return list(self._bits)

    # --- rank ---

    def rank1(self, i: int) -> int:
        """Number of 1-bits in B[0..i)."""
        if i < 0:
            raise ValueError(f"rank1 index must be >= 0, got {i}")
        if i > self._n:
            i = self._n
        count = 0
        for j in range(i):
            if self._bits[j]:
                count += 1
        return count

    def rank0(self, i: int) -> int:
        """Number of 0-bits in B[0..i)."""
        if i < 0:
            raise ValueError(f"rank0 index must be >= 0, got {i}")
        if i > self._n:
            i = self._n
        return i - self.rank1(i)

    # --- select ---

    def select1(self, k: int) -> int:
        """Position of the k-th 1-bit (0-indexed k). Returns -1 if not found."""
        if k < 0:
            raise ValueError(f"select1 k must be >= 0, got {k}")
        count = 0
        for j in range(self._n):
            if self._bits[j]:
                if count == k:
                    return j
                count += 1
        return -1

    def select0(self, k: int) -> int:
        """Position of the k-th 0-bit (0-indexed k). Returns -1 if not found."""
        if k < 0:
            raise ValueError(f"select0 k must be >= 0, got {k}")
        count = 0
        for j in range(self._n):
            if not self._bits[j]:
                if count == k:
                    return j
                count += 1
        return -1

    # --- total counts ---

    def count1(self) -> int:
        """Total number of 1-bits."""
        return self.rank1(self._n)

    def count0(self) -> int:
        """Total number of 0-bits."""
        return self._n - self.count1()

    def __repr__(self) -> str:
        return f"BitVector(len={self._n}, ones={self.count1()})"


class BlockedBitVector(BitVector):
    """BitVector with precomputed blocks for O(1) rank and O(log n) select.

    Uses a simple one-level block structure: a cumulative prefix-sum array
    of 1-bit counts at every block_size boundary.  rank(i) is computed as
    the prefix sum at the last full block boundary plus a short linear scan
    of the remaining (< block_size) bits.

    This is technically O(block_size) per rank, but with block_size = log(n)
    it is effectively O(1) for practical purposes.  The implementation
    prioritises correctness over theoretical optimality.
    """

    def __init__(self, bits: list[int] | None = None):
        super().__init__(bits)
        self._build_index()

    def _build_index(self) -> None:
        """Precompute cumulative prefix sums at block boundaries."""
        import math

        n = self._n
        if n == 0:
            self._block_size: int = 1
            self._prefix: list[int] = [0]
            return

        # Block size = ceil(log2(n)) for practical O(1) rank
        log_n = max(1, int(math.log2(n))) if n > 1 else 1
        self._block_size = max(1, log_n)

        # _prefix[k] = number of 1-bits in B[0 .. k*block_size)
        # So _prefix[0] = 0, _prefix[k] = sum of bits[0 : k*block_size]
        self._prefix = [0]
        count = 0
        for i in range(0, n, self._block_size):
            block_end = min(i + self._block_size, n)
            for j in range(i, block_end):
                if self._bits[j]:
                    count += 1
            self._prefix.append(count)

    def rank1(self, i: int) -> int:
        """O(1) rank1 using precomputed prefix sums."""
        if i < 0:
            raise ValueError(f"rank1 index must be >= 0, got {i}")
        if i > self._n:
            i = self._n
        if i == 0:
            return 0

        block_idx = i // self._block_size
        result = self._prefix[block_idx]

        # Scan remaining bits within the current block
        start = block_idx * self._block_size
        for j in range(start, i):
            if self._bits[j]:
                result += 1

        return result

    def select1(self, k: int) -> int:
        """O(log n) select1 using binary search over prefix sums."""
        if k < 0:
            raise ValueError(f"select1 k must be >= 0, got {k}")
        total = self.rank1(self._n)
        if k >= total:
            return -1

        # Binary search over prefix sums to find the block containing the k-th 1
        lo, hi = 0, len(self._prefix)
        while lo < hi:
            mid = (lo + hi) // 2
            if self._prefix[mid] <= k:
                lo = mid + 1
            else:
                hi = mid

        block_idx = lo - 1
        remaining = k - self._prefix[block_idx]
        start = block_idx * self._block_size
        end = min(start + self._block_size, self._n)

        # Linear scan within the block
        count = 0
        for j in range(start, end):
            if self._bits[j]:
                if count == remaining:
                    return j
                count += 1

        return -1

    def __repr__(self) -> str:
        return f"BlockedBitVector(len={self._n}, ones={self.count1()})"