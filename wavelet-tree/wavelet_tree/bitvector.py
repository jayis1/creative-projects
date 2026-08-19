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

    Uses a two-level block structure:
    - Super-blocks of size L2 = log²(n) bits with cumulative rank
    - Blocks of size L1 = log(n)/2 bits with rank relative to super-block

    This gives O(1) rank queries. Select uses binary search over super-blocks
    then linear scan within the identified super-block.
    """

    def __init__(self, bits: list[int] | None = None):
        super().__init__(bits)
        self._build_index()

    def _build_index(self) -> None:
        """Precompute block-level rank indices."""
        import math

        n = self._n
        if n == 0:
            self._super_blocks: list[int] = []
            self._blocks: list[int] = []
            self._super_size: int = 1
            self._block_size: int = 1
            return

        # Choose block sizes based on n
        log_n = max(1, int(math.log2(n))) if n > 1 else 1
        self._block_size = max(1, log_n // 2)
        self._super_size = max(1, log_n * log_n)

        # Build block-level rank (relative to super-block start)
        self._blocks = []
        self._super_blocks = []
        cumulative = 0
        for i in range(0, n, self._super_size):
            self._super_blocks.append(cumulative)
            super_end = min(i + self._super_size, n)
            for j in range(i, super_end, self._block_size):
                block_end = min(j + self._block_size, n)
                block_count = sum(self._bits[j:block_end])
                self._blocks.append(block_count)
            cumulative += sum(self._bits[i:super_end])

    def rank1(self, i: int) -> int:
        """O(1) rank1 using precomputed blocks."""
        if i < 0:
            raise ValueError(f"rank1 index must be >= 0, got {i}")
        if i > self._n:
            i = self._n
        if i == 0:
            return 0

        super_idx = (i - 1) // self._super_size
        super_start = super_idx * self._super_size
        result = self._super_blocks[super_idx]

        # Add blocks within the super-block
        block_idx = super_start // self._block_size
        pos = super_start
        while pos + self._block_size <= i:
            result += self._blocks[block_idx]
            block_idx += 1
            pos += self._block_size

        # Add remaining bits within the last partial block
        for j in range(pos, i):
            if self._bits[j]:
                result += 1

        return result

    def select1(self, k: int) -> int:
        """O(log n) select1 using binary search over super-blocks."""
        if k < 0:
            raise ValueError(f"select1 k must be >= 0, got {k}")
        if k >= self.count1():
            return -1

        # Binary search over super-blocks to find the one containing the k-th 1
        import bisect

        # Find the super-block where cumulative rank exceeds k
        lo, hi = 0, len(self._super_blocks)
        while lo < hi:
            mid = (lo + hi) // 2
            if self._super_blocks[mid] <= k:
                lo = mid + 1
            else:
                hi = mid

        super_idx = lo - 1
        remaining = k - self._super_blocks[super_idx]
        super_start = super_idx * self._super_size
        super_end = min(super_start + self._super_size, self._n)

        # Linear scan within super-block
        count = 0
        for j in range(super_start, super_end):
            if self._bits[j]:
                if count == remaining:
                    return j
                count += 1

        return -1

    def __repr__(self) -> str:
        return f"BlockedBitVector(len={self._n}, ones={self.count1()})"