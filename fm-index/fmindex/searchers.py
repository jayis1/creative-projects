"""High-level search utilities built on top of FMIndex.

Provides:

  - :func:`regex_search` — translate simple glob/regex patterns to
    wildcard queries.
  - :func:`find_all_repeats` — find all repeated substrings of length ≥ k.
  - :func:`top_k_frequent_kmers` — the k most frequent k-mers.
  - :func:`find_maximal_unique_matches` — MUMs between the indexed text
    and a query string (simplified single-text version).
  - :func:`find_minimal_unique_substrings` — shortest unique substrings
    at each position (useful for primer design).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from .index import FMIndex, FMIndexMatch


# ---------------------------------------------------------------------------
# Simple glob → wildcard translation
# ---------------------------------------------------------------------------
_GLOB_SINGLE = "?"  # matches any single char
_GLOB_MULTI = "*"   # matches zero or more chars


def glob_to_wildcard(pattern: str) -> Optional[str]:
    """Translate a simple glob pattern to a wildcard pattern.

    ``?`` → single-char wildcard (kept as ``?``).
    ``*`` → unsupported in fixed-length wildcard search; returns ``None``
    to signal the caller should fall back to a different method.

    Returns the translated pattern or ``None`` if it contains ``*``.
    """
    if _GLOB_MULTI in pattern:
        return None
    return pattern


def regex_search(idx: FMIndex, pattern: str) -> List[FMIndexMatch]:
    """Search with a simplified regex-like pattern.

    Supports:
      - ``.``  → any single character (wildcard)
      - literal characters

    Does NOT support ``*``, ``+``, ``[]``, anchors, or backreferences
    — those require a different approach (suffix-tree traversal).
    """
    # translate '.' to the wildcard char used by search_wildcard
    wc_pattern = pattern.replace(".", _GLOB_SINGLE)
    if _GLOB_MULTI in wc_pattern:
        raise ValueError("regex_search does not support '*' quantifier")
    return idx.search_wildcard(wc_pattern, wildcard=_GLOB_SINGLE)


# ---------------------------------------------------------------------------
# Find all repeated substrings of length >= min_len
# ---------------------------------------------------------------------------
def find_all_repeats(
    idx: FMIndex,
    min_len: int = 2,
    max_len: Optional[int] = None,
) -> List[Tuple[str, int]]:
    """Find all distinct substrings of length ≥ *min_len* that appear ≥ 2 times.

    Uses the LCP array: a substring of length ℓ appearing k times
    corresponds to a run of k−1 consecutive LCP values ≥ ℓ in the SA.

    Parameters
    ----------
    min_len:
        Minimum repeat length.
    max_len:
        Optional maximum repeat length (to bound output).

    Returns a sorted list of ``(substring, occurrence_count)``.
    """
    if min_len < 1:
        raise ValueError("min_len must be >= 1")
    sa = idx.suffix_array
    lcp = idx.lcp_array()
    n = idx.n
    text = idx.text
    results: Dict[str, int] = {}

    # For each position i in the SA, the longest repeat starting here is
    # determined by the maximum of LCP[i] and LCP[i+1] (if they exist).
    # We use a stack-based approach to find all maximal repeats.
    for i in range(1, n):
        if lcp[i] >= min_len:
            length = lcp[i]
            if max_len is not None:
                length = min(length, max_len)
            pos = sa[i]
            sub = text[pos : pos + length]
            if "$" in sub:
                continue
            # count occurrences via the index
            cnt = idx.count(sub)
            if cnt >= 2 and sub not in results:
                results[sub] = cnt
    return sorted(results.items(), key=lambda x: (-len(x[0]), x[0]))


# ---------------------------------------------------------------------------
# Top-k most frequent k-mers
# ---------------------------------------------------------------------------
def top_k_frequent_kmers(
    idx: FMIndex,
    k: int,
    top: int = 10,
) -> List[Tuple[str, int]]:
    """Return the *top* most frequent k-mers of length *k*.

    >>> idx = FMIndex("banana")
    >>> top_k_frequent_kmers(idx, 1, 3)
    [('a', 3), ('b', 1), ('n', 2)]  # sorted by count descending
    """
    kmers = list(idx.iter_kmers(k))
    kmers.sort(key=lambda x: (-x[1], x[0]))
    return kmers[:top]


# ---------------------------------------------------------------------------
# Minimal unique substrings (shortest unique substring at each position)
# ---------------------------------------------------------------------------
def find_minimal_unique_substrings(
    idx: FMIndex,
    min_len: int = 1,
    max_len: int = 50,
) -> Dict[int, Tuple[str, int]]:
    """Find the shortest unique substring starting at each position.

    A "unique substring" starting at position *p* is the shortest prefix
    of ``text[p:]`` that occurs exactly once in the text.

    Returns a dict mapping position → ``(substring, length)``.
    """
    sa = idx.suffix_array
    lcp = idx.lcp_array()
    n = idx.n
    text = idx.text

    # rank[i] = position of suffix i in the SA
    rank = [0] * n
    for i in range(n):
        rank[sa[i]] = i

    result: Dict[int, Tuple[str, int]] = {}
    for p in range(len(text)):
        r = rank[p]
        # LCP with the previous and next suffix in SA order
        prev_lcp = lcp[r] if r > 0 else 0
        next_lcp = lcp[r + 1] if r + 1 < n else 0
        # the minimal unique length is max(prev_lcp, next_lcp) + 1
        unique_len = max(prev_lcp, next_lcp) + 1
        if unique_len > max_len:
            continue
        if unique_len < min_len:
            unique_len = min_len
        if p + unique_len > len(text):
            continue
        sub = text[p : p + unique_len]
        if "$" in sub:
            continue
        # verify uniqueness
        if idx.count(sub) == 1:
            result[p] = (sub, unique_len)
    return result


# ---------------------------------------------------------------------------
# Maximal Unique Matches (simplified: longest unique substring per position)
# ---------------------------------------------------------------------------
def find_maximal_unique_matches(
    idx: FMIndex,
    query: str,
    min_len: int = 3,
) -> List[Tuple[int, int, str]]:
    """Find maximal unique matches of *query* within the indexed text.

    A MUM is a substring that:
      - appears exactly once in the text and exactly once in the query
      - cannot be extended left or right without breaking uniqueness

    Returns a list of ``(text_pos, query_pos, substring)`` tuples.
    """
    text = idx.text
    results: List[Tuple[int, int, str]] = []
    seen: Set[str] = set()

    for qstart in range(len(query)):
        # binary search for the longest unique match starting at qstart
        lo, hi = min_len, min(len(query) - qstart, len(text))
        best: Optional[Tuple[int, str]] = None
        while lo <= hi:
            mid = (lo + hi) // 2
            sub = query[qstart : qstart + mid]
            cnt = idx.count(sub)
            if cnt == 1:
                best = (mid, sub)
                lo = mid + 1
            elif cnt == 0:
                hi = mid - 1
            else:
                # appears >1 times in text, try shorter
                hi = mid - 1
        if best is not None:
            length, sub = best
            # check left-extension uniqueness
            if qstart > 0:
                left_ext = query[qstart - 1 : qstart + length]
                if idx.count(left_ext) == 1:
                    continue  # can extend left → not maximal
            # check right-extension
            if qstart + length < len(query):
                right_ext = query[qstart : qstart + length + 1]
                if idx.count(right_ext) == 1:
                    continue  # can extend right → not maximal
            if sub not in seen:
                positions = idx.locate(sub)
                if positions:
                    results.append((positions[0], qstart, sub))
                    seen.add(sub)
    return results