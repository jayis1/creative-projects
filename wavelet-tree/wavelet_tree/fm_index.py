"""Pattern matching using backward search on wavelet trees.

This module implements backward search — the core algorithm behind FM-indexes —
using a wavelet tree/matrix over the BWT (Burrows-Wheeler Transform) of a text.

The backward search finds all occurrences of a pattern P in a text T in
O(|P| · log |Σ|) time using only rank queries on the wavelet tree.

The full FM-index pipeline:
    1. Compute the BWT of the text (using the suffix array)
    2. Build a wavelet tree over the BWT
    3. Compute the C array (count of symbols lexicographically < c in the text)
    4. Backward search: iteratively narrow the range [l, r) in the BWT
       that corresponds to the suffixes starting with the current suffix of P

This module provides:
    - compute_bwt(text): Compute the BWT of a text via the suffix array
    - build_fm_index(text): Build a complete FM-index from a text
    - backward_search(wt_bwt, C, pattern): Find the BWT range for a pattern
    - locate(wt_bwt, C, sa, range): Map BWT positions to text positions

For simplicity, we compute the suffix array naively (O(n² log n)), which is
sufficient for educational purposes and moderate text sizes. For production
use, replace with a linear-time suffix array construction algorithm.
"""

from __future__ import annotations

from typing import Any
from .base import WaveletBase


def _compute_suffix_array(text: list) -> list[int]:
    """Compute the suffix array of a text.

    Args:
        text: A list of symbols (must be comparable/sortable).

    Returns:
        A list of starting positions, sorted by the suffix at each position.
    """
    n = len(text)
    # Create (suffix, index) pairs and sort
    suffixes = []
    for i in range(n):
        suffixes.append((text[i:], i))
    suffixes.sort(key=lambda x: x[0])
    return [idx for _, idx in suffixes]


def compute_bwt(text: list) -> list:
    """Compute the Burrows-Wheeler Transform of a text.

    The BWT is formed by taking the last column of the sorted rotations matrix.
    Equivalently, BWT[i] = text[(SA[i] - 1) % n] where SA is the suffix array.

    Args:
        text: A list of symbols.

    Returns:
        The BWT as a list of symbols.
    """
    n = len(text)
    if n == 0:
        return []
    sa = _compute_suffix_array(text)
    bwt = []
    for i in range(n):
        # BWT[i] = character preceding the suffix at SA[i]
        bwt.append(text[(sa[i] - 1) % n])
    return bwt


def compute_c_array(text: list) -> dict[Any, int]:
    """Compute the C array for FM-index backward search.

    C[c] = number of symbols in the text that are lexicographically less than c.
    Equivalently, C[c] = starting position of c in the sorted BWT column.

    Args:
        text: The original text as a list of symbols.

    Returns:
        A dict mapping each symbol to its C value.
    """
    from collections import Counter
    counts = Counter(text)
    sorted_symbols = sorted(counts.keys())
    c_array: dict[Any, int] = {}
    cumulative = 0
    for sym in sorted_symbols:
        c_array[sym] = cumulative
        cumulative += counts[sym]
    return c_array


def backward_search(
    wt_bwt: WaveletBase,
    c_array: dict[Any, int],
    pattern: list,
) -> tuple[int, int]:
    """Find the BWT range [l, r) corresponding to all occurrences of pattern.

    Uses the backward search algorithm:
        Start with [l, r) = [0, n)
        For each character c in reversed(pattern):
            l = C[c] + rank(c, l)
            r = C[c] + rank(c, r)
            if l >= r: return (l, r)  # pattern not found

    Args:
        wt_bwt: A wavelet tree/matrix built over the BWT of the text.
        c_array: The C array for the text.
        pattern: The pattern to search for (as a list of symbols).

    Returns:
        A tuple (l, r) where [l, r) is the range in the BWT. If the pattern
        is not found, l >= r.
    """
    n = len(wt_bwt)
    l, r = 0, n

    for c in reversed(pattern):
        if c not in c_array:
            return (0, 0)  # symbol not in text at all

        rank_l = wt_bwt.rank(c, l)
        rank_r = wt_bwt.rank(c, r)
        l = c_array[c] + rank_l
        r = c_array[c] + rank_r

        if l >= r:
            return (l, r)  # pattern not found

    return (l, r)


def _compute_inverse_sa(
    wt_bwt: WaveletBase,
    c_array: dict[Any, int],
    sa: list[int],
) -> list[int]:
    """Compute the inverse suffix array (ISA) from SA.

    ISA[SA[i]] = i, i.e., ISA maps a text position to its rank in the SA.
    """
    n = len(sa)
    isa = [0] * n
    for i in range(n):
        isa[sa[i]] = i
    return isa


def locate_positions(
    l: int,
    r: int,
    sa: list[int],
) -> list[int]:
    """Map a BWT range [l, r) to text positions using the suffix array.

    Each position i in [l, r) corresponds to suffix SA[i], so the pattern
    starts at text position SA[i].

    Args:
        l, r: The BWT range from backward_search.
        sa: The suffix array of the text.

    Returns:
        A sorted list of text positions where the pattern occurs.
    """
    return sorted(sa[i] for i in range(l, r))


class FMIndex:
    """A complete FM-index built on top of a wavelet tree.

    Combines the BWT, wavelet tree, C array, and suffix array to provide
    efficient pattern matching with count and locate operations.

    Attributes:
        text: The original text.
        bwt: The Burrows-Wheeler Transform.
        sa: The suffix array.
        c_array: The C array for backward search.
        wt_bwt: The wavelet tree over the BWT.
    """

    def __init__(
        self,
        text: list | str,
        structure: str = "matrix",
        use_blocked: bool = True,
    ):
        """Build an FM-index from a text.

        Args:
            text: The text to index (string or list of symbols).
            structure: Which wavelet structure to use over the BWT.
                One of "tree", "matrix", "huffman-tree", "huffman-matrix".
            use_blocked: Whether to use BlockedBitVector.
        """
        if isinstance(text, str):
            text = list(text)

        # We append a unique sentinel character that is lexicographically
        # smaller than all other symbols. This ensures the suffix array is
        # well-defined and the backward search correctly handles patterns
        # longer than some suffixes. We use '\x00' (null character) as the
        # sentinel, which is lexicographically smaller than any printable char.
        SENTINEL = "\x00"
        text_with_sentinel = list(text) + [SENTINEL]

        self.text: list = list(text)  # original text without sentinel
        self._n = len(text)  # length of original text
        self._sentinel = SENTINEL
        self._n_with_sentinel = len(text_with_sentinel)

        if self._n == 0:
            self.bwt: list = [SENTINEL]
            self.sa: list[int] = [0]
            self.c_array: dict = {SENTINEL: 0}
            from .wavelet_tree import WaveletTree
            from .wavelet_matrix import WaveletMatrix
            from .huffman import HuffmanWaveletTree, HuffmanWaveletMatrix

            struct_map = {
                "tree": WaveletTree,
                "matrix": WaveletMatrix,
                "huffman-tree": HuffmanWaveletTree,
                "huffman-matrix": HuffmanWaveletMatrix,
            }
            if structure not in struct_map:
                raise ValueError(
                    f"Unknown structure '{structure}'. "
                    f"Must be one of {list(struct_map.keys())}"
                )
            self.wt_bwt = struct_map[structure](self.bwt, use_blocked=use_blocked)
            return

        # Compute suffix array and BWT over text + sentinel
        self.sa = _compute_suffix_array(text_with_sentinel)
        self.bwt = []
        for i in range(self._n_with_sentinel):
            self.bwt.append(text_with_sentinel[(self.sa[i] - 1) % self._n_with_sentinel])

        # Compute C array over text + sentinel
        self.c_array = compute_c_array(text_with_sentinel)

        # Build wavelet tree over BWT
        from .wavelet_tree import WaveletTree
        from .wavelet_matrix import WaveletMatrix
        from .huffman import HuffmanWaveletTree, HuffmanWaveletMatrix

        struct_map = {
            "tree": WaveletTree,
            "matrix": WaveletMatrix,
            "huffman-tree": HuffmanWaveletTree,
            "huffman-matrix": HuffmanWaveletMatrix,
        }
        if structure not in struct_map:
            raise ValueError(
                f"Unknown structure '{structure}'. "
                f"Must be one of {list(struct_map.keys())}"
            )
        self.wt_bwt = struct_map[structure](self.bwt, use_blocked=use_blocked)

    def count(self, pattern: list | str) -> int:
        """Count the number of occurrences of pattern in the text.

        O(|pattern| · log |Σ|) time.

        Args:
            pattern: The pattern to count (string or list of symbols).

        Returns:
            The number of occurrences.
        """
        if isinstance(pattern, str):
            pattern = list(pattern)
        if not pattern or self._n == 0 or self.wt_bwt is None:
            return 0
        l, r = backward_search(self.wt_bwt, self.c_array, pattern)
        # The range [l, r) includes the sentinel suffix if the pattern is empty,
        # but since we check for non-empty pattern, the sentinel suffix (which
        # starts with '\x00') won't match any printable pattern.
        return r - l

    def locate(self, pattern: list | str) -> list[int]:
        """Find all positions where pattern occurs in the text.

        O(|pattern| · log |Σ| + occ) time, where occ is the number of matches.

        Args:
            pattern: The pattern to find.

        Returns:
            A sorted list of starting positions.
        """
        if isinstance(pattern, str):
            pattern = list(pattern)
        if not pattern or self._n == 0 or self.wt_bwt is None:
            return []
        l, r = backward_search(self.wt_bwt, self.c_array, pattern)
        if l >= r:
            return []
        # SA positions map to text positions. Filter out the sentinel position
        # (which is self._n, the position of the sentinel in the augmented text).
        positions = locate_positions(l, r, self.sa)
        return [p for p in positions if p < self._n]

    def __len__(self) -> int:
        return self._n

    def __repr__(self) -> str:
        return f"FMIndex(len={self._n}, sigma={len(self.c_array)})"