"""
Suffix array construction.

Provides two implementations:

  - build_suffix_array_naive(text): O(n^2 log n) sort of suffixes.  Used for
    validation and small inputs.
  - build_suffix_array(text): O(n log^2 n) prefix-doubling (Manber-Myers)
    which is fast enough for typical FM-index use (texts up to ~10^6 chars).

The suffix array is a permutation of [0, n) listing suffix start positions
sorted lexicographically.
"""

from __future__ import annotations

from typing import List


def build_suffix_array_naive(text: str) -> List[int]:
    """O(n^2 log n) naive suffix array -- sorted list of suffix start indices."""
    n = len(text)
    suffixes = list(range(n))
    # key by the suffix string itself; Python sort is timsort, stable.
    suffixes.sort(key=lambda i: text[i:])
    return suffixes


def build_suffix_array(text: str) -> List[int]:
    """O(n log^2 n) prefix-doubling suffix array construction (Manber-Myers).

    We iteratively sort suffixes by their first 2^k characters using rank
    pairs.  After ceil(log2(n)) rounds every suffix has a unique rank pair
    and the array is complete.
    """
    n = len(text)
    if n == 0:
        return []
    if n == 1:
        return [0]

    # initial ranks: character ordinals (must handle the implicit '$' terminator
    # — but the FM-index appends a unique sentinel, so we operate on the raw text
    # whose last suffix is naturally the smallest because of the sentinel).
    ranks = [ord(c) for c in text]
    sa = list(range(n))
    k = 1
    while True:
        # sort by (rank[i], rank[i+k] or -1)
        def key(i: int):
            second = ranks[i + k] if (i + k) < n else -1
            return (ranks[i], second)

        sa.sort(key=key)

        # recompute ranks
        new_ranks = [0] * n
        new_ranks[sa[0]] = 0
        for j in range(1, n):
            prev = sa[j - 1]
            cur = sa[j]
            prev_key = (ranks[prev], ranks[prev + k] if (prev + k) < n else -1)
            cur_key = (ranks[cur], ranks[cur + k] if (cur + k) < n else -1)
            new_ranks[cur] = new_ranks[prev] + (1 if cur_key != prev_key else 0)
        ranks = new_ranks

        if ranks[sa[-1]] == n - 1:
            # all suffixes have unique ranks — done
            break
        k *= 2
        if k >= n:
            break

    return sa