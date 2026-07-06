"""
Wavelet tree implementation for the FM-index.

A wavelet tree stores a string over an alphabet Σ and supports:
  - access(i):        the i-th symbol (0-indexed)
  - rank(c, i):       number of occurrences of symbol c in s[0:i] (i exclusive)
  - select(c, k):     position of the k-th (1-indexed) occurrence of c

The tree partitions the alphabet recursively.  Each internal node stores a
bit array indicating whether a symbol belongs to the left or right child.
We use a precomputed-popcount rank structure for O(1) bit-level rank/select,
giving overall alphabet-size O(|Σ|·n) space and O(log |Σ|) query time.

For simplicity we build a balanced binary tree over the *sorted* alphabet
(actually balanced on the alphabet codes, not on frequency).  This is more
than enough for the FM-index's needs where alphabets are small.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple


class BitArray:
    """A bit array with rank/select and rank-of-one support.

    Uses one Python int as a bit buffer per chunk of 64 bits for
    memory efficiency; rank is accelerated by precomputed block
    popcount sums (superblock + block level).

    Memory: n bits + n/64 integers of overhead -- negligible.
    """

    __slots__ = ("n", "_words", "_word_size", "_ranks", "_select_ones")

    def __init__(self, bits: Optional[List[int]] = None):
        self._word_size: int = 64
        self.n: int = 0
        self._words: List[int] = []
        # _ranks[i] = number of 1-bits before the i-th word (inclusive)
        self._ranks: List[int] = []
        # one-indexed positions of 1-bits (for select)
        self._select_ones: List[int] = []
        if bits is not None:
            self._build(bits)

    # ------------------------------------------------------------------
    # building
    # ------------------------------------------------------------------
    def _build(self, bits: List[int]) -> None:
        self.n = len(bits)
        n_words = (self.n + self._word_size - 1) // self._word_size
        self._words = [0] * n_words
        ones: List[int] = []
        for i, b in enumerate(bits):
            if b:
                self._words[i >> 6] |= 1 << (i & 63)
                ones.append(i)
        self._select_ones = ones
        self._ranks = [0] * (n_words + 1)
        for w in range(n_words):
            self._ranks[w + 1] = self._ranks[w] + bin(self._words[w]).count("1")

    # ------------------------------------------------------------------
    # access
    # ------------------------------------------------------------------
    def __getitem__(self, i: int) -> int:
        """Return the i-th bit (0-indexed)."""
        if not 0 <= i < self.n:
            raise IndexError(f"bit index {i} out of range [0, {self.n})")
        return (self._words[i >> 6] >> (i & 63)) & 1

    def __len__(self) -> int:
        return self.n

    # ------------------------------------------------------------------
    # rank1(i): number of 1-bits in positions [0, i)
    # ------------------------------------------------------------------
    def rank1(self, i: int) -> int:
        if i <= 0:
            return 0
        if i > self.n:
            i = self.n
        word = i >> 6
        offset = i & 63
        if offset == 0:
            return self._ranks[word]
        mask = (1 << offset) - 1
        return self._ranks[word] + bin(self._words[word] & mask).count("1")

    # ------------------------------------------------------------------
    # rank0(i): number of 0-bits in positions [0, i)
    # ------------------------------------------------------------------
    def rank0(self, i: int) -> int:
        return i - self.rank1(i)

    # ------------------------------------------------------------------
    # select1(k): position of the k-th 1-bit (1-indexed)
    # ------------------------------------------------------------------
    def select1(self, k: int) -> int:
        if k < 1 or k > len(self._select_ones):
            raise IndexError(f"select1({k}) out of range (have {len(self._select_ones)} ones)")
        return self._select_ones[k - 1]

    # ------------------------------------------------------------------
    # select0(k): position of the k-th 0-bit (1-indexed)
    # ------------------------------------------------------------------
    def select0(self, k: int) -> int:
        """Position of the k-th 0-bit (1-indexed)."""
        if k < 1:
            raise IndexError(f"select0({k}) out of range")
        # binary search for the smallest i where rank0(i+1) == k
        lo, hi = 0, self.n
        while lo < hi:
            mid = (lo + hi) // 2
            if self.rank0(mid + 1) >= k:
                hi = mid
            else:
                lo = mid + 1
        if self.rank0(lo + 1) != k:
            raise IndexError(f"select0({k}): not enough 0-bits")
        return lo

    def count_ones(self) -> int:
        return self._ranks[-1] if self._ranks else 0

    def count_zeros(self) -> int:
        return self.n - self.count_ones()


class WaveletNode:
    """Internal node of a wavelet tree.

    Each node handles a contiguous range [alpha_lo, alpha_hi] of alphabet
    codes (inclusive).  If the range has more than one code, the node stores
    a BitArray over the symbols it received (0 = left child, 1 = right child)
    and recurses on each half.

    We also keep the length of the subsequence at each node so we can
    descend into children for rank/access without re-reading the BitArray.
    """

    __slots__ = ("alpha_lo", "alpha_hi", "mid", "bits", "left", "right")

    def __init__(self, alpha_lo: int, alpha_hi: int):
        self.alpha_lo = alpha_lo
        self.alpha_hi = alpha_hi
        self.mid = (alpha_lo + alpha_hi) // 2
        self.bits: Optional[BitArray] = None
        self.left: Optional["WaveletNode"] = None
        self.right: Optional["WaveletNode"] = None

    def is_leaf(self) -> bool:
        return self.alpha_lo == self.alpha_hi


class WaveletTree:
    """A balanced wavelet tree over an integer alphabet.

    The alphabet is determined automatically from the data.  Symbols can be
    any integers (typically character ordinals).  We translate them into a
    contiguous 0..sigma-1 range internally, keeping a mapping back to the
    original codes.
    """

    __slots__ = (
        "root",
        "_alpha_codes",
        "_code_to_idx",
        "_idx_to_code",
        "sigma",
        "n",
    )

    def __init__(self, data: List[int]):
        if not data:
            raise ValueError("cannot build a wavelet tree from empty data")
        codes = sorted(set(data))
        self._alpha_codes = codes
        self._code_to_idx: Dict[int, int] = {c: i for i, c in enumerate(codes)}
        self._idx_to_code = codes
        self.sigma = len(codes)
        self.n = len(data)

        if self.sigma == 1:
            # single-symbol alphabet: trivial tree, no bits needed
            self.root = WaveletNode(0, 0)
            return

        # build recursively
        self.root = self._build(0, self.sigma - 1, data)

    def _build(
        self, alpha_lo: int, alpha_hi: int, symbols: List[int]
    ) -> WaveletNode:
        node = WaveletNode(alpha_lo, alpha_hi)
        if alpha_lo == alpha_hi:
            return node
        mid = node.mid
        bit_values: List[int] = []
        left_syms: List[int] = []
        right_syms: List[int] = []
        for s in symbols:
            idx = self._code_to_idx[s]
            if idx <= mid:
                bit_values.append(0)
                left_syms.append(s)
            else:
                bit_values.append(1)
                right_syms.append(s)
        node.bits = BitArray(bit_values)
        node.left = self._build(alpha_lo, mid, left_syms)
        node.right = self._build(mid + 1, alpha_hi, right_syms)
        return node

    # ------------------------------------------------------------------
    # access(i): return the i-th symbol (0-indexed)
    # ------------------------------------------------------------------
    def access(self, i: int) -> int:
        if not 0 <= i < self.n:
            raise IndexError(f"access index {i} out of range [0, {self.n})")
        if self.sigma == 1:
            return self._idx_to_code[0]
        node = self.root
        lo = node.alpha_lo
        hi = node.alpha_hi
        pos = i
        while not node.is_leaf():
            assert node.bits is not None
            bit = node.bits[pos]
            if bit == 0:
                pos = node.bits.rank0(pos)
                hi = node.mid
                node = node.left
            else:
                pos = node.bits.rank1(pos)
                lo = node.mid + 1
                node = node.right
        assert lo == hi
        return self._idx_to_code[lo]

    def __getitem__(self, i: int) -> int:
        return self.access(i)

    # ------------------------------------------------------------------
    # rank(c, i): number of occurrences of symbol c in positions [0, i)
    # ------------------------------------------------------------------
    def rank(self, c: int, i: int) -> int:
        if c not in self._code_to_idx:
            return 0
        if i < 0:
            return 0
        if i > self.n:
            i = self.n
        if self.sigma == 1:
            return i if c == self._idx_to_code[0] else 0
        node = self.root
        idx = self._code_to_idx[c]
        pos = i
        while not node.is_leaf():
            assert node.bits is not None
            if idx <= node.mid:
                pos = node.bits.rank0(pos)
                node = node.left
            else:
                pos = node.bits.rank1(pos)
                node = node.right
        return pos

    # ------------------------------------------------------------------
    # select(c, k): position of the k-th (1-indexed) occurrence of c
    # ------------------------------------------------------------------
    def select(self, c: int, k: int) -> int:
        if c not in self._code_to_idx:
            raise IndexError(f"symbol {c} not in alphabet")
        if k < 1:
            raise IndexError(f"select k must be >= 1")
        if self.sigma == 1:
            if k > self.n:
                raise IndexError("not enough occurrences")
            return k - 1
        # find the leaf first, then climb back up
        idx = self._code_to_idx[c]
        # descend to leaf, recording path
        path: List[Tuple[WaveletNode, int]] = []
        node = self.root
        while not node.is_leaf():
            if idx <= node.mid:
                path.append((node, 0))
                node = node.left
            else:
                path.append((node, 1))
                node = node.right
        # now climb back, translating the count k into a position
        pos = k - 1  # 0-indexed offset within the leaf
        for node, bit in reversed(path):
            assert node.bits is not None
            if bit == 0:
                pos = node.bits.select0(pos + 1)
            else:
                pos = node.bits.select1(pos + 1)
        return pos

    def alphabet(self) -> List[int]:
        """Return the sorted alphabet (original codes)."""
        return list(self._alpha_codes)