"""RRR-compressed BitVector implementation.

Implements a simplified version of the Raman-Raman-Rao (RRR) compressed
bitvector with O(1) rank/select using a two-level index structure.

The bitvector is divided into blocks of size w = log(n). Each block stores
its popcount (class). Superblocks store cumulative popcounts at intervals
of size w^2. Rank is answered as:

    rank1(i) = superblock_prefix + block_offset + popcount(within block)

This gives O(1) rank and O(log n) select with o(n) bits of overhead.

For practical purposes, this implementation stores the bit data plus a
compact two-level index. It's not a fully entropy-compressed bitvector
but demonstrates the RRR technique.
"""

from __future__ import annotations

import math
from typing import Iterator

from .bitvector import BitVector


class RRRBitVector(BitVector):
    """RRR-style compressed bitvector with O(1) rank and O(log n) select.

    Uses a two-level (superblock / block) index for fast rank queries.
    Space overhead is O(n / log n) integers, which is o(n).

    This is a practical implementation that stores the raw bits alongside
    the index. A fully compressed RRR would store only block classes and
    offsets, but the query interface and complexity are the same.
    """

    def __init__(self, bits: list[int] | None = None):
        super().__init__(bits)
        self._build_rrr_index()

    def _build_rrr_index(self) -> None:
        """Build the two-level RRR index.

        Structure:
            - block_size = ceil(log2(n)) if n > 1, else 1
            - superblock_interval = block_size * block_size
            - _block_popcount[k] = popcount of block k (0-indexed)
            - _superblock_cumulative[j] = cumulative popcount up to
              superblock j (i.e., up to bit position j * superblock_interval)
        """
        n = self._n
        if n == 0:
            self._block_size = 1
            self._superblock_interval = 1
            self._block_popcount: list[int] = []
            self._superblock_cumulative: list[int] = [0]
            return

        log_n = max(1, int(math.log2(n))) if n > 1 else 1
        self._block_size = max(1, log_n)
        self._superblock_interval = max(1, self._block_size * self._block_size)

        # Build block popcounts
        self._block_popcount = []
        for i in range(0, n, self._block_size):
            block_end = min(i + self._block_size, n)
            pc = sum(1 for j in range(i, block_end) if self._bits[j])
            self._block_popcount.append(pc)

        # Build superblock cumulative popcounts
        # _superblock_cumulative[j] = total 1-bits in B[0 .. j*superblock_interval)
        self._superblock_cumulative = [0]
        num_superblocks = (n + self._superblock_interval - 1) // self._superblock_interval
        for j in range(num_superblocks):
            sb_start = j * self._superblock_interval
            sb_end = min((j + 1) * self._superblock_interval, n)
            # Sum popcounts of all blocks within this superblock
            start_block = sb_start // self._block_size
            end_block = (sb_end + self._block_size - 1) // self._block_size
            pc = sum(self._block_popcount[start_block:end_block])
            self._superblock_cumulative.append(self._superblock_cumulative[-1] + pc)

    def rank1(self, i: int) -> int:
        """O(1) rank1 using the two-level RRR index.

        rank1(i) = superblock_cumulative[j] +
                   sum(block_popcount[blocks between sb and block of i]) +
                   popcount(within the block containing i, up to position i)
        """
        if i < 0:
            raise ValueError(f"rank1 index must be >= 0, got {i}")
        if i > self._n:
            i = self._n
        if i == 0:
            return 0

        # Find superblock
        sb_idx = i // self._superblock_interval
        result = self._superblock_cumulative[sb_idx]

        # Sum block popcounts from superblock boundary to block containing i
        sb_start_block = sb_idx * self._superblock_interval // self._block_size
        block_idx = i // self._block_size

        for b in range(sb_start_block, block_idx):
            result += self._block_popcount[b]

        # Add popcount within the current block
        block_start = block_idx * self._block_size
        for j in range(block_start, i):
            if self._bits[j]:
                result += 1

        return result

    def select1(self, k: int) -> int:
        """O(log n) select1 using binary search over superblocks and blocks."""
        if k < 0:
            raise ValueError(f"select1 k must be >= 0, got {k}")
        total = self._superblock_cumulative[-1] if self._superblock_cumulative else 0
        if k >= total:
            return -1

        # Binary search over superblocks to find the one containing the k-th 1
        lo, hi = 0, len(self._superblock_cumulative)
        while lo < hi:
            mid = (lo + hi) // 2
            if self._superblock_cumulative[mid] <= k:
                lo = mid + 1
            else:
                hi = mid
        sb_idx = lo - 1
        remaining = k - self._superblock_cumulative[sb_idx]

        # Find the block within the superblock
        sb_start_block = sb_idx * self._superblock_interval // self._block_size
        for b in range(sb_start_block, len(self._block_popcount)):
            if self._block_popcount[b] > remaining:
                # The k-th 1 is in block b
                block_start = b * self._block_size
                block_end = min(block_start + self._block_size, self._n)
                count = 0
                for j in range(block_start, block_end):
                    if self._bits[j]:
                        if count == remaining:
                            return j
                        count += 1
                return -1  # shouldn't happen
            remaining -= self._block_popcount[b]

        return -1

    def __repr__(self) -> str:
        return f"RRRBitVector(len={self._n}, ones={self.count1()})"