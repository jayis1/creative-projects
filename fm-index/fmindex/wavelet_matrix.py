"""
Wavelet matrix — a level-ordered alternative to the wavelet tree.

A wavelet matrix stores the same information as a wavelet tree but flattens
it into a sequence of bit vectors indexed by *level* rather than by tree
node.  This has two practical advantages:

  1. **Memory locality** — each level is a contiguous bit array, so rank
     queries touch fewer cache lines.
  2. **Simpler rank/select** — there is no recursion; every query descends
     log(σ) levels with a single array lookup per level.

The wavelet matrix is used as an optional backend for the FM-Index.  It
supports the same interface (access / rank / select) and gives identical
results; the choice is purely about performance characteristics.

Construction: for each level ℓ we partition the current symbol stream into
those whose ℓ-th bit (of the alphabet index) is 0 (keep in order) and those
whose ℓ-th bit is 1 (keep in order).  The level's bit vector records the
partition bit for each position.  We track the starting position of the
"1-partition" for the next level (the ``_level_starts`` array).
"""

from __future__ import annotations

from typing import Dict, List

from .wavelet import BitArray


class WaveletMatrix:
    """A wavelet matrix over an integer alphabet.

    Like :class:`~fmindex.wavelet.WaveletTree`, symbols may be any integers;
    they are mapped to a contiguous 0..σ-1 range internally.
    """

    __slots__ = (
        "_codes",
        "_code_to_idx",
        "_idx_to_code",
        "sigma",
        "n",
        "height",
        "_levels",
        "_level_starts",
        "_leaf_starts_arr",
    )

    def __init__(self, data: List[int]):
        if not data:
            raise ValueError("cannot build a wavelet matrix from empty data")
        codes = sorted(set(data))
        self._codes = codes
        self._code_to_idx: Dict[int, int] = {c: i for i, c in enumerate(codes)}
        self._idx_to_code = codes
        self.sigma = len(codes)
        self.n = len(data)

        if self.sigma == 1:
            self.height = 0
            self._levels: List[BitArray] = []
            self._level_starts = [0]
            self._leaf_starts_arr = [0]
            return

        # height = ceil(log2(sigma))
        height = 0
        s = self.sigma - 1
        while s > 0:
            s >>= 1
            height += 1
        self.height = height

        # map data to alphabet indices
        idx_data = [self._code_to_idx[c] for c in data]

        self._levels = []
        # _z[level] = number of 0-bits at `level`; used when descending with
        # bit=1: new_pos = _z[level] + rank1(pos).
        self._level_starts = [0] * self.height

        current = idx_data
        for level in range(self.height):
            shift = self.height - 1 - level
            bits = [(x >> shift) & 1 for x in current]
            ba = BitArray(bits)
            self._levels.append(ba)
            # number of 0-bits at this level = start of 1-bits at this level
            self._level_starts[level] = ba.count_zeros()
            # stable partition: zeros first, ones after, preserving order
            left = [x for x, b in zip(current, bits) if b == 0]
            right = [x for x, b in zip(current, bits) if b == 1]
            current = left + right

        # Precompute the leaf-level start position of each alphabet index.
        # At the leaf level the symbols are sorted by their bit-prefix
        # representation (which may differ from numeric index order when
        # sigma is not a power of two).  We compute starts by simulating the
        # full partition and recording the first position of each index.
        self._leaf_starts_arr = [-1] * self.sigma
        cur = list(idx_data)
        for level in range(self.height):
            shift = self.height - 1 - level
            bits = [(x >> shift) & 1 for x in cur]
            left = [x for x, b in zip(cur, bits) if b == 0]
            right = [x for x, b in zip(cur, bits) if b == 1]
            cur = left + right
        # cur is now the leaf-level stream, sorted by bit-prefix
        for pos, x in enumerate(cur):
            if self._leaf_starts_arr[x] == -1:
                self._leaf_starts_arr[x] = pos
        # symbols that don't appear get a default of n (so rank returns 0)
        for j in range(self.sigma):
            if self._leaf_starts_arr[j] == -1:
                self._leaf_starts_arr[j] = self.n

    # ------------------------------------------------------------------
    def access(self, i: int) -> int:
        if not 0 <= i < self.n:
            raise IndexError(f"access index {i} out of range [0, {self.n})")
        if self.sigma == 1:
            return self._idx_to_code[0]
        idx = 0
        pos = i
        for level in range(self.height):
            ba = self._levels[level]
            bit = ba[pos]
            idx = (idx << 1) | bit
            if bit == 0:
                pos = ba.rank0(pos)
            else:
                pos = self._level_starts[level] + ba.rank1(pos)
        return self._idx_to_code[idx]

    def __getitem__(self, i: int) -> int:
        return self.access(i)

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
        idx = self._code_to_idx[c]
        pos = i
        for level in range(self.height):
            ba = self._levels[level]
            shift = self.height - 1 - level
            bit = (idx >> shift) & 1
            if bit == 0:
                pos = ba.rank0(pos)
            else:
                pos = self._level_starts[level] + ba.rank1(pos)
        # At the leaf level, pos is the absolute position within the sorted
        # stream.  The rank of c in [0, i) is pos minus the starting position
        # of symbol c at the leaf level (i.e. the number of symbols whose
        # alphabet index < idx).
        return pos - self._leaf_start(idx)

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
        idx = self._code_to_idx[c]
        # descend to the leaf: find the starting position of symbol c
        # Actually for select we go bottom-up: at the leaf level the k-th
        # occurrence of c is at position (count of symbols < c) + (k-1)
        # because the leaf level is sorted.  Then we map back up.
        pos = self._leaf_start(idx) + (k - 1)
        for level in range(self.height - 1, -1, -1):
            ba = self._levels[level]
            shift = self.height - 1 - level
            bit = (idx >> shift) & 1
            if bit == 0:
                pos = ba.select0(pos + 1)
            else:
                # we have the rank-1-index within the 1-half at this level;
                # convert to the select1 query (1-indexed).
                pos = ba.select1(pos - self._level_starts[level] + 1)
        return pos

    def _leaf_start(self, idx: int) -> int:
        """Position of the first occurrence of alphabet-index ``idx`` at the
        leaf (sorted) level.

        Precomputed at construction time in ``_leaf_starts_arr`` for O(1)
        lookup.
        """
        if self.sigma == 1:
            return 0
        return self._leaf_starts_arr[idx]

    def alphabet(self) -> List[int]:
        return list(self._codes)