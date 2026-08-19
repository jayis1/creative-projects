"""Huffman shaped Wavelet Tree and Matrix.

Uses Huffman coding to shape the tree, giving O(H₀(S)) average query time
instead of O(log |Σ|).
"""

from __future__ import annotations

import heapq
from typing import Any

from .bitvector import BitVector, BlockedBitVector
from .base import WaveletBase


def build_huffman_code(freqs: dict[Any, int]) -> dict[Any, str]:
    """Build Huffman codes from a frequency map.

    Args:
        freqs: A dict mapping symbols to their frequencies.

    Returns:
        A dict mapping symbols to binary code strings (e.g. "010").
    """
    if not freqs:
        return {}

    if len(freqs) == 1:
        sym = next(iter(freqs))
        return {sym: "0"}

    # Build Huffman tree using a heap.
    # Each heap entry: (weight, counter, node) where node is either a leaf
    # symbol or a tuple of (left_node, right_node).
    counter = 0
    heap: list = []
    for sym, freq in freqs.items():
        heapq.heappush(heap, (freq, counter, sym))
        counter += 1

    while len(heap) > 1:
        w1, _, n1 = heapq.heappop(heap)
        w2, _, n2 = heapq.heappop(heap)
        heapq.heappush(heap, (w1 + w2, counter, (n1, n2)))
        counter += 1

    _, _, root = heap[0]

    # Traverse to build codes
    codes: dict[Any, str] = {}

    def _traverse(node, prefix: str):
        if isinstance(node, tuple):
            _traverse(node[0], prefix + "0")
            _traverse(node[1], prefix + "1")
        else:
            codes[node] = prefix

    _traverse(root, "")
    return codes


class _HuffmanNode:
    """A node in the Huffman-shaped wavelet tree."""

    __slots__ = ("bits", "left", "right", "symbol")

    def __init__(self):
        self.bits: BitVector | None = None
        self.left: "_HuffmanNode | None" = None
        self.right: "_HuffmanNode | None" = None
        self.symbol: Any = None  # Only set for leaf nodes


class HuffmanWaveletTree(WaveletBase):
    """Huffman-shaped Wavelet Tree.

    The tree shape follows the Huffman code of the sequence, so frequent
    symbols are near the root.  Average query time is O(H₀(S)).
    """

    def __init__(self, sequence: list | str, use_blocked: bool = True):
        if isinstance(sequence, str):
            sequence = list(sequence)

        self._n = len(sequence)
        self._alphabet = sorted(set(sequence)) if sequence else []
        self._bv_class = BlockedBitVector if use_blocked else BitVector
        self._original_sequence = list(sequence)

        if self._n == 0:
            self._codes: dict = {}
            self._root: _HuffmanNode | None = None
            return

        # Build Huffman codes from frequencies
        freqs: dict = {}
        for s in sequence:
            freqs[s] = freqs.get(s, 0) + 1
        self._codes = build_huffman_code(freqs)

        # Build the tree structure (skeleton)
        self._root = _HuffmanNode()
        for sym, code in self._codes.items():
            self._insert_symbol(self._root, sym, code)

        # Build bitvectors recursively, partitioning positions
        self._fill_bitvectors(self._root, list(range(self._n)), 0)

    def _insert_symbol(self, root: _HuffmanNode, symbol: Any, code: str) -> None:
        """Insert a symbol into the Huffman tree skeleton."""
        node = root
        for bit_char in code:
            if bit_char == "0":
                if node.left is None:
                    node.left = _HuffmanNode()
                node = node.left
            else:
                if node.right is None:
                    node.right = _HuffmanNode()
                node = node.right
        node.symbol = symbol

    def _fill_bitvectors(
        self, node: _HuffmanNode, positions: list[int], depth: int
    ) -> None:
        """Recursively fill bitvectors. positions = indices into original seq."""
        if node.left is None and node.right is None:
            return  # Leaf

        bits = []
        left_positions = []
        right_positions = []
        for pos in positions:
            sym = self._original_sequence[pos]
            code = self._codes[sym]
            bit = int(code[depth])
            bits.append(bit)
            if bit == 0:
                left_positions.append(pos)
            else:
                right_positions.append(pos)

        node.bits = self._bv_class(bits)

        if node.left is not None and left_positions:
            self._fill_bitvectors(node.left, left_positions, depth + 1)
        if node.right is not None and right_positions:
            self._fill_bitvectors(node.right, right_positions, depth + 1)

    def access(self, i: int) -> Any:
        """Return the symbol at position i. O(H₀(S)) average."""
        if i < 0 or i >= self._n:
            raise IndexError(f"Index {i} out of range [0, {self._n})")

        node = self._root
        if node is None:
            raise IndexError("Empty wavelet tree")

        pos = i
        while node.bits is not None:
            bit = node.bits[pos]
            if bit == 0:
                pos = node.bits.rank0(pos)
                node = node.left
            else:
                pos = node.bits.rank1(pos)
                node = node.right
            if node is None:
                raise RuntimeError("Invalid tree structure")

        return node.symbol

    def rank(self, c: Any, i: int) -> int:
        """Count occurrences of symbol c in S[0..i). O(H₀(S)) average."""
        if i < 0:
            raise ValueError(f"rank index must be >= 0, got {i}")
        if i > self._n:
            i = self._n
        if c not in self._codes:
            return 0

        code = self._codes[c]
        node = self._root
        if node is None:
            return 0

        pos = i
        for bit_char in code:
            if node is None or node.bits is None:
                return 0
            bit = int(bit_char)
            if bit == 0:
                pos = node.bits.rank0(pos)
                node = node.left
            else:
                pos = node.bits.rank1(pos)
                node = node.right

        return pos

    def select(self, c: Any, k: int) -> int:
        """Return the position of the k-th occurrence of c. O(H₀(S)) average."""
        if k < 0:
            raise ValueError(f"select k must be >= 0, got {k}")
        if c not in self._codes:
            return -1

        # Check if k is within the valid range for this symbol
        total = self.rank(c, self._n)
        if k >= total:
            return -1

        code = self._codes[c]
        node = self._root
        if node is None:
            return -1

        # Descend to leaf, recording path
        path = []
        for bit_char in code:
            if node is None or node.bits is None:
                return -1
            bit = int(bit_char)
            path.append((node, bit))
            if bit == 0:
                node = node.left
            else:
                node = node.right

        # Climb back up
        pos = k
        for node, bit in reversed(path):
            if bit == 0:
                pos = node.bits.select0(pos)
            else:
                pos = node.bits.select1(pos)
            if pos == -1:
                return -1

        return pos

    def __len__(self) -> int:
        return self._n

    @property
    def alphabet(self) -> list:
        return list(self._alphabet)

    @property
    def codes(self) -> dict:
        return dict(self._codes)

    def __repr__(self) -> str:
        return f"HuffmanWaveletTree(len={self._n}, sigma={len(self._alphabet)})"


class HuffmanWaveletMatrix(WaveletBase):
    """Huffman-shaped Wavelet Matrix.

    Combines Huffman-optimal shape with the level-ordered matrix layout.
    All codes are padded to the maximum code length with a special sentinel
    bit so the matrix has a uniform number of levels.  After all levels, the
    sequence is sorted by the (padded) Huffman code, so offsets are computed
    from the actual final partitioned order.
    """

    def __init__(self, sequence: list | str, use_blocked: bool = True):
        if isinstance(sequence, str):
            sequence = list(sequence)

        self._n = len(sequence)
        self._alphabet = sorted(set(sequence)) if sequence else []
        self._bv_class = BlockedBitVector if use_blocked else BitVector
        self._original_sequence = list(sequence)

        if self._n == 0:
            self._codes: dict = {}
            self._level_bits: list[BitVector] = []
            self._symbol_offsets: dict = {}
            return

        # Build Huffman codes
        freqs: dict = {}
        for s in sequence:
            freqs[s] = freqs.get(s, 0) + 1
        self._codes = build_huffman_code(freqs)

        max_depth = max(len(c) for c in self._codes.values()) if self._codes else 0

        # Pad codes to max_depth with trailing zeros.  This means all symbols
        # participate at every level.  The padded bits are always 0, so a
        # short-code symbol always goes "left" after its real code ends.
        padded: dict = {}
        for sym, code in self._codes.items():
            padded[sym] = code + "0" * (max_depth - len(code))

        self._level_bits: list[BitVector] = []

        # Build level by level using padded codes
        current = list(sequence)
        for level in range(max_depth):
            bits = []
            zeros = []
            ones = []
            for sym in current:
                code = padded[sym]
                bit = int(code[level])
                bits.append(bit)
                if bit == 0:
                    zeros.append(sym)
                else:
                    ones.append(sym)

            self._level_bits.append(self._bv_class(bits))
            current = zeros + ones

        # Compute symbol offsets from the actual final partitioned order
        self._symbol_offsets: dict = {}
        for i, sym in enumerate(current):
            if sym not in self._symbol_offsets:
                self._symbol_offsets[sym] = i

    def access(self, i: int) -> Any:
        """Return the symbol at position i.

        Note: For Huffman-shaped matrices, access requires the original
        sequence because symbols have variable-length codes.
        """
        if i < 0 or i >= self._n:
            raise IndexError(f"Index {i} out of range [0, {self._n})")
        return self._original_sequence[i]

    def rank(self, c: Any, i: int) -> int:
        """Count occurrences of symbol c in S[0..i)."""
        if i < 0:
            raise ValueError(f"rank index must be >= 0, got {i}")
        if i > self._n:
            i = self._n
        if c not in self._codes:
            return 0

        code = self._codes[c]
        max_depth = len(self._level_bits)
        padded_code = code + "0" * (max_depth - len(code))
        pos = i
        for level in range(max_depth):
            bv = self._level_bits[level]
            bit = int(padded_code[level])
            if bit == 0:
                pos = bv.rank0(pos)
            else:
                z = bv.count0()
                pos = z + bv.rank1(pos)

        return pos - self._symbol_offsets.get(c, 0)

    def select(self, c: Any, k: int) -> int:
        """Return the position of the k-th occurrence of c."""
        if k < 0:
            raise ValueError(f"select k must be >= 0, got {k}")
        if c not in self._codes:
            return -1

        code = self._codes[c]
        max_depth = len(self._level_bits)
        padded_code = code + "0" * (max_depth - len(code))
        pos = self._symbol_offsets.get(c, 0) + k

        for level in range(max_depth - 1, -1, -1):
            bv = self._level_bits[level]
            bit = int(padded_code[level])
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

    @property
    def codes(self) -> dict:
        return dict(self._codes)

    def __repr__(self) -> str:
        return f"HuffmanWaveletMatrix(len={self._n}, sigma={len(self._alphabet)})"