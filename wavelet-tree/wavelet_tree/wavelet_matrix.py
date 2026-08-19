"""Wavelet Matrix implementation (level-ordered wavelet tree variant)."""

from __future__ import annotations

from typing import Any

from .bitvector import BitVector, BlockedBitVector


class WaveletMatrix:
    """Wavelet Matrix: a level-ordered wavelet tree.

    Instead of a tree structure, the wavelet matrix stores one bitvector per
    level.  At each level the sequence is stably partitioned: elements with
    bit 0 go to the front, elements with bit 1 go to the back.  After all
    levels, elements are sorted by their **bit-reversed** code.

    Supports access(i), rank(c, i), select(c, k) in O(log |Σ|) time.
    """

    def __init__(self, sequence: list | str, use_blocked: bool = True):
        """Build a wavelet matrix from a sequence.

        Args:
            sequence: A list of symbols or a string.
            use_blocked: If True, use BlockedBitVector for O(1) rank.
        """
        if isinstance(sequence, str):
            sequence = list(sequence)
        if len(sequence) == 0:
            self._n: int = 0
            self._alphabet: list = []
            self._symbol_to_code: dict = {}
            self._level_bits: list = []
            self._sigma: int = 0
            self._symbol_offsets: dict = {}
            self._original_sequence: list = []
            return

        self._n = len(sequence)
        self._alphabet = sorted(set(sequence))
        self._symbol_to_code = {s: i for i, s in enumerate(self._alphabet)}
        self._sigma = len(self._alphabet)
        self._original_sequence = list(sequence)

        codes = [self._symbol_to_code[s] for s in sequence]
        self._bv_class = BlockedBitVector if use_blocked else BitVector

        self._level_bits: list[BitVector] = []
        self._num_levels = 0
        if self._sigma > 1:
            self._num_levels = (self._sigma - 1).bit_length()

        # Build level by level, tracking the final partitioned order
        current = list(codes)
        for level in range(self._num_levels):
            bit_pos = self._num_levels - 1 - level
            bits = [(c >> bit_pos) & 1 for c in current]
            self._level_bits.append(self._bv_class(bits))

            # Stable partition: 0s first, then 1s
            zeros = [c for c, b in zip(current, bits) if b == 0]
            ones = [c for c, b in zip(current, bits) if b == 1]
            current = zeros + ones

        # Compute symbol offsets from the actual final partitioned order.
        # After all levels, `current` is sorted by bit-reversed code, NOT by
        # the natural code order, so we must read offsets from `current`.
        self._symbol_offsets: dict[int, int] = {}
        if self._num_levels > 0:
            for i, c in enumerate(current):
                if c not in self._symbol_offsets:
                    self._symbol_offsets[c] = i
        else:
            # Single-symbol alphabet: everything is at offset 0
            self._symbol_offsets = {0: 0} if codes else {}

    def access(self, i: int) -> Any:
        """Return the symbol at position i. O(log |Σ|)."""
        if i < 0 or i >= self._n:
            raise IndexError(f"Index {i} out of range [0, {self._n})")

        pos = i
        code = 0
        for level in range(self._num_levels):
            bv = self._level_bits[level]
            bit = bv[pos]
            code = (code << 1) | bit
            if bit == 0:
                pos = bv.rank0(pos)
            else:
                z = bv.count0()
                pos = z + bv.rank1(pos)

        return self._alphabet[code]

    def rank(self, c: Any, i: int) -> int:
        """Count occurrences of symbol c in S[0..i). O(log |Σ|)."""
        if i < 0:
            raise ValueError(f"rank index must be >= 0, got {i}")
        if i > self._n:
            i = self._n
        if c not in self._symbol_to_code:
            return 0

        code = self._symbol_to_code[c]
        pos = i
        for level in range(self._num_levels):
            bv = self._level_bits[level]
            bit_pos = self._num_levels - 1 - level
            bit = (code >> bit_pos) & 1
            if bit == 0:
                pos = bv.rank0(pos)
            else:
                z = bv.count0()
                pos = z + bv.rank1(pos)

        return pos - self._symbol_offsets.get(code, 0)

    def select(self, c: Any, k: int) -> int:
        """Return the position of the k-th (0-indexed) occurrence of c.
        Returns -1 if not found. O(log |Σ|)."""
        if k < 0:
            raise ValueError(f"select k must be >= 0, got {k}")
        if c not in self._symbol_to_code:
            return -1

        code = self._symbol_to_code[c]
        if self._num_levels == 0:
            # Single symbol alphabet
            if k < self._n:
                return k
            return -1

        # Start from the offset of this symbol in the final partitioned order
        pos = self._symbol_offsets[code] + k

        # Climb back up the levels, inverting the rank mapping.
        # Forward: if bit==0, pos_new = rank0(pos_old)  →  pos_old = select0(pos_new)
        # Forward: if bit==1, pos_new = z + rank1(pos_old)  →  pos_old = select1(pos_new - z)
        for level in range(self._num_levels - 1, -1, -1):
            bv = self._level_bits[level]
            bit_pos = self._num_levels - 1 - level
            bit = (code >> bit_pos) & 1
            if bit == 0:
                pos = bv.select0(pos)
            else:
                z = bv.count0()
                pos = bv.select1(pos - z)
            if pos == -1:
                return -1

        return pos

    def __len__(self) -> int:
        return self._n

    @property
    def alphabet(self) -> list:
        return list(self._alphabet)

    def __repr__(self) -> str:
        return f"WaveletMatrix(len={self._n}, sigma={self._sigma})"