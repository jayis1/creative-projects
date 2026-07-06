"""
Burrows-Wheeler Transform (BWT) construction and inversion.

The BWT is the last column of the sorted rotations matrix of a text that
ends with a unique sentinel character (smaller than every other char).

  - bwt_encode(text): given text (must end with a unique sentinel '$'),
    return the BWT string and the suffix array.
  - bwt_decode(bwt): given the BWT string, reconstruct the original text
    using the LF-mapping.

We construct the BWT from the suffix array: bwt[i] = text[sa[i] - 1] for
sa[i] > 0, and bwt[i] = '$' (the sentinel) when sa[i] == 0.
"""

from __future__ import annotations

from typing import List, Tuple

from .suffix_array import build_suffix_array


SENTINEL = "$"


def bwt_encode(text: str, sa: List[int] | None = None) -> Tuple[str, List[int]]:
    """Construct the BWT of *text*.

    The text **must** end with a unique sentinel ``$`` that is lexicographically
    smaller than every other character in the text.

    Returns (bwt_string, suffix_array).
    """
    if not text:
        raise ValueError("text must be non-empty (include the sentinel)")
    if text[-1] != SENTINEL:
        raise ValueError(
            f"text must end with the sentinel {SENTINEL!r}; got {text[-1]!r}"
        )
    if SENTINEL in text[:-1]:
        raise ValueError("sentinel '$' may only appear as the final character")

    if sa is None:
        sa = build_suffix_array(text)

    n = len(text)
    bwt_chars = []
    for i in range(n):
        if sa[i] == 0:
            bwt_chars.append(text[-1])  # the sentinel itself
        else:
            bwt_chars.append(text[sa[i] - 1])
    return "".join(bwt_chars), sa


def bwt_decode(bwt: str) -> str:
    """Invert the BWT using the LF-mapping.

    Given the BWT string (which contains exactly one sentinel ``$``),
    reconstruct the original text.  This is O(n) time and O(n) space.
    """
    if not bwt:
        raise ValueError("bwt must be non-empty")
    if SENTINEL not in bwt:
        raise ValueError("bwt must contain the sentinel '$'")
    if bwt.count(SENTINEL) > 1:
        raise ValueError("bwt must contain exactly one sentinel '$'")

    n = len(bwt)

    # Build the first column F by sorting the BWT.
    # The LF-mapping: LF[i] = position in F of the same character as BWT[i].
    # Concretely: for character c, the j-th occurrence of c in BWT maps to
    # the j-th occurrence of c in F (because F is sorted).
    char_counts: dict[str, int] = {}
    for ch in bwt:
        char_counts[ch] = char_counts.get(ch, 0) + 1

    # Starting position of each character's run in F
    sorted_chars = sorted(char_counts.keys())
    starts: dict[str, int] = {}
    cumulative = 0
    for ch in sorted_chars:
        starts[ch] = cumulative
        cumulative += char_counts[ch]

    # next_index[i] = LF[i] = starts[bwt[i]] + rank of bwt[i] up to position i
    rank_counts: dict[str, int] = {}
    lf = [0] * n
    sentinel_row = -1
    for i in range(n):
        ch = bwt[i]
        rank_counts[ch] = rank_counts.get(ch, 0) + 1
        lf[i] = starts[ch] + rank_counts[ch] - 1
        if ch == SENTINEL:
            sentinel_row = i  # row where sa == 0

    # Reconstruct text by walking from the sentinel row (sa == 0).
    # L[sentinel_row] = text[n-1] = '$'.  LF maps to the row with sa = n-1,
    # whose L value is text[n-2], and so on.  We read characters in reverse
    # order, then reverse at the end.
    result = []
    i = sentinel_row
    for _ in range(n):
        result.append(bwt[i])
        i = lf[i]
    # result is text[n-1], text[n-2], ..., text[0]  =>  reverse to recover
    text = "".join(reversed(result))
    return text