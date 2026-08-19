"""Balanced Wavelet Tree implementation."""

from __future__ import annotations

from typing import Any

from .bitvector import BitVector, BlockedBitVector


class WaveletTreeNode:
    """A single node in the wavelet tree."""

    def __init__(self):
        self.bits: BitVector | None = None
        self.left: "WaveletTreeNode | None" = None
        self.right: "WaveletTreeNode | None" = None
        self.alpha_min: int = 0  # min symbol in this node's alphabet (inclusive)
        self.alpha_max: int = 0  # max symbol in this node's alphabet (inclusive)


class WaveletTree:
    """Balanced binary Wavelet Tree over a sequence of symbols.

    Supports access(i), rank(c, i), select(c, k) in O(log |Σ|) time.
    Space: n·H₀(S) + o(n·log σ) bits.

    Symbols can be any hashable objects that are mapped to integers via a
    sorted alphabet.  For strings, each character is a symbol.
    """

    def __init__(self, sequence: list | str, use_blocked: bool = True):
        """Build a wavelet tree from a sequence.

        Args:
            sequence: A list of symbols or a string (treated as list of chars).
            use_blocked: If True, use BlockedBitVector for O(1) rank.
        """
        if isinstance(sequence, str):
            sequence = list(sequence)
        if len(sequence) == 0:
            self._sequence = []
            self._alphabet: list = []
            self._symbol_to_code: dict = {}
            self._root: WaveletTreeNode | None = None
            return

        # Build alphabet (sorted, unique symbols)
        self._alphabet = sorted(set(sequence))
        self._symbol_to_code: dict = {}
        for i, sym in enumerate(self._alphabet):
            self._symbol_to_code[sym] = i

        # Map sequence to integer codes
        codes = [self._symbol_to_code[s] for s in sequence]
        self._sequence = list(sequence)  # keep original for reference

        self._bv_class = BlockedBitVector if use_blocked else BitVector
        self._root = self._build(codes, 0, len(self._alphabet) - 1)

    def _build(
        self, codes: list[int], alpha_min: int, alpha_max: int
    ) -> WaveletTreeNode | None:
        """Recursively build the wavelet tree."""
        node = WaveletTreeNode()
        node.alpha_min = alpha_min
        node.alpha_max = alpha_max

        if alpha_min == alpha_max:
            # Leaf node — no bitvector needed
            node.bits = None
            return node

        mid = (alpha_min + alpha_max) // 2

        # Build bitvector: 0 if code <= mid (goes left), 1 if code > mid (goes right)
        bits = [0 if c <= mid else 1 for c in codes]
        node.bits = self._bv_class(bits)

        # Partition codes for children
        left_codes = [c for c in codes if c <= mid]
        right_codes = [c for c in codes if c > mid]

        if left_codes:
            node.left = self._build(left_codes, alpha_min, mid)
        if right_codes:
            node.right = self._build(right_codes, mid + 1, alpha_max)

        return node

    # --- queries ---

    def access(self, i: int) -> Any:
        """Return the symbol at position i. O(log |Σ|)."""
        if i < 0 or i >= len(self._sequence):
            raise IndexError(f"Index {i} out of range [0, {len(self._sequence)})")

        node = self._root
        if node is None:
            raise IndexError("Empty wavelet tree")

        pos = i
        while node.bits is not None:
            bit = node.bits[pos]
            mid = (node.alpha_min + node.alpha_max) // 2
            if bit == 0:
                # Go left; new position = rank0(pos)
                pos = node.bits.rank0(pos)
                node = node.left
            else:
                # Go right; new position = rank1(pos)
                pos = node.bits.rank1(pos)
                node = node.right

        return self._alphabet[node.alpha_min]

    def rank(self, c: Any, i: int) -> int:
        """Count occurrences of symbol c in S[0..i). O(log |Σ|)."""
        if i < 0:
            raise ValueError(f"rank index must be >= 0, got {i}")
        if i > len(self._sequence):
            i = len(self._sequence)
        if c not in self._symbol_to_code:
            return 0

        code = self._symbol_to_code[c]
        node = self._root
        if node is None:
            return 0

        pos = i
        while node.bits is not None:
            mid = (node.alpha_min + node.alpha_max) // 2
            if code <= mid:
                pos = node.bits.rank0(pos)
                node = node.left
            else:
                pos = node.bits.rank1(pos)
                node = node.right

            if node is None:
                return 0

        return pos

    def select(self, c: Any, k: int) -> int:
        """Return the position of the k-th (0-indexed) occurrence of c.
        Returns -1 if not found. O(log |Σ|)."""
        if k < 0:
            raise ValueError(f"select k must be >= 0, got {k}")
        if c not in self._symbol_to_code:
            return -1

        # Check if k is within the valid range for this symbol
        total = self.rank(c, len(self._sequence))
        if k >= total:
            return -1

        code = self._symbol_to_code[c]
        node = self._root
        if node is None:
            return -1

        # Descend to the leaf for c, recording the path
        path = []
        while node.bits is not None:
            mid = (node.alpha_min + node.alpha_max) // 2
            if code <= mid:
                path.append((node, 0))
                node = node.left
            else:
                path.append((node, 1))
                node = node.right
            if node is None:
                return -1

        # Now climb back up, computing the position at each level
        pos = k  # at the leaf, the k-th occurrence is just k
        for node, bit in reversed(path):
            if bit == 0:
                pos = node.bits.select0(pos)
            else:
                pos = node.bits.select1(pos)
            if pos == -1:
                return -1

        return pos

    def __len__(self) -> int:
        return len(self._sequence)

    @property
    def alphabet(self) -> list:
        """Return the sorted alphabet."""
        return list(self._alphabet)

    def __repr__(self) -> str:
        return f"WaveletTree(len={len(self._sequence)}, sigma={len(self._alphabet)})"