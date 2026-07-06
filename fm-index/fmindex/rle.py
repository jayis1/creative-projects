"""Run-length encoding (RLE) for BWT compression.

The Burrows-Wheeler Transform tends to produce long runs of identical
characters — that is precisely why it is useful for compression.  An
RL-FM-Index stores the BWT in run-length-encoded form to reduce memory
while still supporting rank queries.

This module provides:

  - :func:`rle_encode` / :func:`rle_decode` — generic RLE of a string.
  - :class:`RLEString` — a run-length-encoded string supporting
    ``access(i)`` and ``rank(c, i)`` in O(log r) time where *r* is the
    number of runs (typically r ≪ n for BWT output).

The rank implementation uses a prefix-sum over per-run character counts
plus a binary search over run start positions, giving O(log r) per query.
"""

from __future__ import annotations

from bisect import bisect_right
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# Generic RLE functions
# ---------------------------------------------------------------------------
def rle_encode(s: str) -> List[Tuple[str, int]]:
    """Encode *s* as a list of ``(char, count)`` runs.

    >>> rle_encode("aaabbc")
    [('a', 3), ('b', 2), ('c', 1)]
    """
    if not s:
        return []
    runs: List[Tuple[str, int]] = []
    prev = s[0]
    count = 1
    for ch in s[1:]:
        if ch == prev:
            count += 1
        else:
            runs.append((prev, count))
            prev = ch
            count = 1
    runs.append((prev, count))
    return runs


def rle_decode(runs: List[Tuple[str, int]]) -> str:
    """Decode a list of ``(char, count)`` runs back into a string.

    >>> rle_decode([('a', 3), ('b', 2), ('c', 1)])
    'aaabbc'
    """
    return "".join(ch * count for ch, count in runs)


# ---------------------------------------------------------------------------
# RLEString: rank/access over a run-length-encoded string
# ---------------------------------------------------------------------------
class RLEString:
    """A run-length-encoded string with O(log r) rank and access.

    Parameters
    ----------
    data:
        The string to encode (or a pre-encoded list of runs if
        *from_runs* is True).
    from_runs:
        If True, *data* is interpreted as a list of ``(char, count)`` runs.
    """

    __slots__ = (
        "_runs",
        "_run_starts",
        "_char_counts",
        "_prefix_counts",
        "_n",
    )

    def __init__(self, data, from_runs: bool = False):
        if from_runs:
            self._runs: List[Tuple[str, int]] = list(data)
        else:
            self._runs = rle_encode(data)
        self._n = sum(c for _, c in self._runs)
        # _run_starts[i] = cumulative start position of run i
        self._run_starts: List[int] = []
        cum = 0
        for _, count in self._runs:
            self._run_starts.append(cum)
            cum += count
        # per-character cumulative counts for rank acceleration
        # _prefix_counts[char] = list of cumulative counts at run boundaries
        self._char_counts: Dict[str, List[Tuple[int, int]]] = {}
        self._prefix_counts: Dict[str, List[int]] = {}
        run_cum: Dict[str, int] = {}
        for i, (ch, count) in enumerate(self._runs):
            run_cum[ch] = run_cum.get(ch, 0) + count
            self._char_counts.setdefault(ch, []).append((i, run_cum[ch]))
        for ch, entries in self._char_counts.items():
            self._prefix_counts[ch] = [c for _, c in entries]

    @property
    def n(self) -> int:
        """Length of the decoded string."""
        return self._n

    @property
    def num_runs(self) -> int:
        """Number of RLE runs (≤ n, often much smaller for BWT)."""
        return len(self._runs)

    def compression_ratio(self) -> float:
        """Return n / num_runs — higher means better compression."""
        if self._runs:
            return self._n / len(self._runs)
        return 0.0

    def access(self, i: int) -> str:
        """Return the character at position *i* (0-indexed)."""
        if not 0 <= i < self._n:
            raise IndexError(f"RLE access {i} out of range [0, {self._n})")
        # binary search for the run containing position i
        run_idx = bisect_right(self._run_starts, i) - 1
        return self._runs[run_idx][0]

    def __getitem__(self, i: int) -> str:
        return self.access(i)

    def rank(self, c: str, i: int) -> int:
        """Number of occurrences of *c* in positions ``[0, i)``."""
        if i <= 0:
            return 0
        if i > self._n:
            i = self._n
        if c not in self._prefix_counts:
            return 0
        # find which run contains position i-1
        run_idx = bisect_right(self._run_starts, i - 1) - 1
        # count of c in runs [0 .. run_idx-1]
        # plus partial count within run_idx
        prefix = self._char_counts[c]
        # binary search in prefix for entries with run index < run_idx
        lo, hi = 0, len(prefix)
        while lo < hi:
            mid = (lo + hi) // 2
            if prefix[mid][0] < run_idx:
                lo = mid + 1
            else:
                hi = mid
        count_before = prefix[lo - 1][1] if lo > 0 else 0
        # partial: how many c's in run_idx up to position i
        ch, run_count = self._runs[run_idx]
        if ch == c:
            run_start = self._run_starts[run_idx]
            count_before += i - run_start
        return count_before

    def decode(self) -> str:
        """Decode back to the full string."""
        return rle_decode(self._runs)

    def __len__(self) -> int:
        return self._n

    def __repr__(self) -> str:
        return f"RLEString(n={self._n}, runs={len(self._runs)}, ratio={self.compression_ratio():.1f})"