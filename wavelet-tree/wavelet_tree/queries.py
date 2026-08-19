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


def range_min(
    wt: WaveletTree | WaveletMatrix, l: int, r: int
) -> Any:
    """Find the minimum (smallest) symbol in S[l..r).

    Equivalent to range_quantile(l, r, 0).
    """
    if l >= r:
        raise ValueError(f"Empty range: l={l} >= r={r}")
    return range_quantile(wt, l, r, 0)


def range_max(
    wt: WaveletTree | WaveletMatrix, l: int, r: int
) -> Any:
    """Find the maximum (largest) symbol in S[l..r).

    Equivalent to range_quantile(l, r, (r-l)-1).
    """
    if l >= r:
        raise ValueError(f"Empty range: l={l} >= r={r}")
    return range_quantile(wt, l, r, (r - l) - 1)


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


def range_prev_value(
    wt: WaveletTree | WaveletMatrix, l: int, r: int, threshold: Any
) -> Any | None:
    """Find the largest symbol <= threshold in S[l..r).

    Returns None if no such symbol exists.
    """
    if l < 0 or r < 0:
        raise ValueError("Range bounds must be non-negative")
    if l > r:
        raise ValueError(f"Invalid range: l={l} > r={r}")

    alphabet = wt.alphabet
    # Find the last symbol <= threshold that exists in the range
    for sym in reversed(alphabet):
        if sym <= threshold:
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


def range_intersection(
    wt: WaveletTree | WaveletMatrix,
    l1: int,
    r1: int,
    l2: int,
    r2: int,
) -> dict[Any, tuple[int, int]]:
    """Find symbols that appear in both S[l1..r1) and S[l2..r2).

    Returns a dict {symbol: (count_in_range1, count_in_range2)}.
    """
    if l1 < 0 or r1 < 0 or l2 < 0 or r2 < 0:
        raise ValueError("Range bounds must be non-negative")
    if l1 > r1 or l2 > r2:
        raise ValueError("Invalid range: l > r")

    result: dict[Any, tuple[int, int]] = {}
    for sym in wt.alphabet:
        c1 = range_count(wt, sym, l1, r1)
        c2 = range_count(wt, sym, l2, r2)
        if c1 > 0 and c2 > 0:
            result[sym] = (c1, c2)
    return result


def prefix_search(
    wt: WaveletTree | WaveletMatrix, prefix: list | str
) -> list[int]:
    """Find all positions where the sequence starts with the given prefix.

    Works by computing rank/select for each symbol in the prefix.

    Args:
        wt: A wavelet tree/matrix.
        prefix: A list of symbols (or a string for char-based sequences).

    Returns:
        A sorted list of starting positions.
    """
    if isinstance(prefix, str):
        prefix = list(prefix)
    if len(prefix) == 0:
        return list(range(len(wt)))

    # For each position, check if the prefix matches
    # This is O(n * |prefix|) but correct for all structure types
    positions: list[int] = []
    n = len(wt)
    for i in range(n - len(prefix) + 1):
        match = True
        for j, sym in enumerate(prefix):
            if wt.access(i + j) != sym:
                match = False
                break
        if match:
            positions.append(i)
    return positions


def count_distinct(
    wt: WaveletTree | WaveletMatrix, l: int, r: int
) -> int:
    """Count the number of distinct symbols in S[l..r)."""
    if l < 0 or r < 0:
        raise ValueError("Range bounds must be non-negative")
    if l > r:
        raise ValueError(f"Invalid range: l={l} > r={r}")
    return len(interval_symbols(wt, l, r))


def range_report(
    wt: WaveletTree | WaveletMatrix, l: int, r: int
) -> list[tuple[Any, int]]:
    """Report all distinct symbols in S[l..r) with their counts.

    Similar to interval_symbols but returns a sorted list of (symbol, count)
    pairs instead of a dict.

    Args:
        wt: A wavelet tree/matrix.
        l: Start of range (inclusive).
        r: End of range (exclusive).

    Returns:
        A list of (symbol, count) tuples sorted by symbol.
    """
    if l < 0 or r < 0:
        raise ValueError("Range bounds must be non-negative")
    if l > r:
        raise ValueError(f"Invalid range: l={l} > r={r}")
    result = interval_symbols(wt, l, r)
    return sorted(result.items())


def range_report_all(
    wt: WaveletTree | WaveletMatrix, l: int, r: int
) -> list[Any]:
    """Report all symbols in S[l..r) in sorted order.

    This is equivalent to sorting S[l..r) and returning the sorted list.
    Uses range_quantile to extract symbols one by one.

    Args:
        wt: A wavelet tree/matrix.
        l: Start of range (inclusive).
        r: End of range (exclusive).

    Returns:
        A sorted list of all symbols in the range.
    """
    if l < 0 or r < 0:
        raise ValueError("Range bounds must be non-negative")
    if l > r:
        raise ValueError(f"Invalid range: l={l} > r={r}")
    if l == r:
        return []

    result: list[Any] = []
    for k in range(r - l):
        result.append(range_quantile(wt, l, r, k))
    return result


def range_top_k(
    wt: WaveletTree | WaveletMatrix, l: int, r: int, k: int
) -> list[tuple[Any, int]]:
    """Find the k most frequent symbols in S[l..r).

    Args:
        wt: A wavelet tree/matrix.
        l: Start of range (inclusive).
        r: End of range (exclusive).
        k: Number of top symbols to return.

    Returns:
        A list of (symbol, count) tuples sorted by count (descending),
        then by symbol (ascending) for ties. At most k entries.
    """
    if l < 0 or r < 0:
        raise ValueError("Range bounds must be non-negative")
    if l > r:
        raise ValueError(f"Invalid range: l={l} > r={r}")
    if k <= 0:
        return []

    syms = interval_symbols(wt, l, r)
    # Sort by count descending, then symbol ascending
    sorted_items = sorted(syms.items(), key=lambda x: (-x[1], x[0]))
    return sorted_items[:k]


def range_bottom_k(
    wt: WaveletTree | WaveletMatrix, l: int, r: int, k: int
) -> list[tuple[Any, int]]:
    """Find the k least frequent symbols in S[l..r).

    Args:
        wt: A wavelet tree/matrix.
        l: Start of range (inclusive).
        r: End of range (exclusive).
        k: Number of bottom symbols to return.

    Returns:
        A list of (symbol, count) tuples sorted by count (ascending),
        then by symbol (ascending) for ties. At most k entries.
    """
    if l < 0 or r < 0:
        raise ValueError("Range bounds must be non-negative")
    if l > r:
        raise ValueError(f"Invalid range: l={l} > r={r}")
    if k <= 0:
        return []

    syms = interval_symbols(wt, l, r)
    # Sort by count ascending, then symbol ascending
    sorted_items = sorted(syms.items(), key=lambda x: (x[1], x[0]))
    return sorted_items[:k]