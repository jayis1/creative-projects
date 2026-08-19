"""High-level range queries built on top of wavelet trees/matrices."""

from __future__ import annotations

from typing import Any

from .wavelet_tree import WaveletTree
from .wavelet_matrix import WaveletMatrix


def range_count(wt: WaveletTree | WaveletMatrix, c: Any, l: int, r: int) -> int:
    """Count occurrences of symbol c in S[l..r).

    Uses rank: rank(c, r) - rank(c, l).
    """
    if l < 0 or r < 0:
        raise ValueError("Range bounds must be non-negative")
    if l > r:
        raise ValueError(f"Invalid range: l={l} > r={r}")
    return wt.rank(c, r) - wt.rank(c, l)


def range_quantile(
    wt: WaveletTree | WaveletMatrix, l: int, r: int, k: int
) -> Any:
    """Find the k-th smallest (0-indexed) symbol in S[l..r).

    Uses the wavelet tree structure to descend levels, counting how many
    symbols go left (smaller) vs right (larger) at each level.

    Works with WaveletTree (balanced) and WaveletMatrix.
    """
    if l < 0 or r < 0:
        raise ValueError("Range bounds must be non-negative")
    if l > r:
        raise ValueError(f"Invalid range: l={l} > r={r}")
    if k < 0 or k >= (r - l):
        raise ValueError(f"k={k} out of range [0, {r - l})")

    if isinstance(wt, WaveletMatrix):
        return _range_quantile_matrix(wt, l, r, k)
    return _range_quantile_tree(wt, l, r, k)


def _range_quantile_tree(wt: WaveletTree, l: int, r: int, k: int) -> Any:
    """Range quantile for balanced WaveletTree."""
    node = wt._root
    if node is None:
        raise ValueError("Empty wavelet tree")

    while node.bits is not None:
        # Count zeros in [l, r)
        zeros_in_range = node.bits.rank0(r) - node.bits.rank0(l)
        if k < zeros_in_range:
            # Go left
            l = node.bits.rank0(l)
            r = node.bits.rank0(r)
            node = node.left
        else:
            # Go right
            k -= zeros_in_range
            l = node.bits.rank1(l)
            r = node.bits.rank1(r)
            node = node.right
        if node is None:
            raise ValueError("Invalid tree structure")

    return wt._alphabet[node.alpha_min]


def _range_quantile_matrix(wt: WaveletMatrix, l: int, r: int, k: int) -> Any:
    """Range quantile for WaveletMatrix."""
    code = 0
    for level in range(wt._num_levels):
        bv = wt._level_bits[level]
        zeros_l = bv.rank0(l)
        zeros_r = bv.rank0(r)
        zeros_in_range = zeros_r - zeros_l
        if k < zeros_in_range:
            # Go left (bit 0)
            code = (code << 1) | 0
            l = zeros_l
            r = zeros_r
        else:
            # Go right (bit 1)
            code = (code << 1) | 1
            k -= zeros_in_range
            total_zeros = bv.count0()
            l = total_zeros + (l - zeros_l)
            r = total_zeros + (r - zeros_r)

    return wt._alphabet[code]


def range_next_value(
    wt: WaveletTree | WaveletMatrix, l: int, r: int, threshold: Any
) -> Any | None:
    """Find the smallest symbol >= threshold in S[l..r).

    Returns None if no such symbol exists.
    """
    if l < 0 or r < 0:
        raise ValueError("Range bounds must be non-negative")
    if l > r:
        raise ValueError(f"Invalid range: l={l} > r={r}")

    alphabet = wt.alphabet
    # Find the first symbol >= threshold that exists in the range
    for sym in alphabet:
        if sym >= threshold:
            count = range_count(wt, sym, l, r)
            if count > 0:
                return sym
    return None


def interval_symbols(
    wt: WaveletTree | WaveletMatrix, l: int, r: int
) -> dict[Any, int]:
    """Enumerate all distinct symbols in S[l..r) with their counts.

    Returns a dict {symbol: count}.
    """
    if l < 0 or r < 0:
        raise ValueError("Range bounds must be non-negative")
    if l > r:
        raise ValueError(f"Invalid range: l={l} > r={r}")

    result: dict[Any, int] = {}
    for sym in wt.alphabet:
        count = range_count(wt, sym, l, r)
        if count > 0:
            result[sym] = count
    return result