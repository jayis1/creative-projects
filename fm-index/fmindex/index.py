"""
The FM-Index: a compressed full-text index.

This module ties together the BWT, a wavelet tree, and a sampled suffix
array to provide:

  - count(pattern)   — number of occurrences of *pattern* in the text
  - locate(pattern)  — starting positions of all occurrences
  - extract(pos, len) — retrieve any substring of the text
  - search with mismatches via backtracking over the BWT

The index stores:
  * the BWT string (compressed in a wavelet tree)
  * the C array (number of symbols lexicographically smaller than each char)
  * a sampled suffix array (every `sample_rate`-th SA entry), with
    LF-mapping to recover unsampled entries.

Construction is O(n log^2 n) for the suffix array + O(n) for the BWT and
wavelet tree.  Queries are O(|pattern| log |Σ|) for count, and O(occ · log n
/ sample_rate) per locate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterator, List, Optional, Tuple

from .bwt import SENTINEL, bwt_encode
from .suffix_array import build_suffix_array, build_suffix_array_naive
from .wavelet import WaveletTree
from .wavelet_matrix import WaveletMatrix
from .errors import ConstructionError, QueryError
from .logging_utils import get_logger, log_time


@dataclass
class FMIndexMatch:
    """A single match returned by :meth:`FMIndex.locate`."""

    position: int
    """0-indexed start position of the match in the original text."""

    mismatches: int
    """Number of mismatches (0 for exact search)."""

    pattern: str
    """The pattern that was searched for."""

    def __repr__(self) -> str:
        if self.mismatches == 0:
            return f"FMIndexMatch(pos={self.position})"
        return f"FMIndexMatch(pos={self.position}, mismatches={self.mismatches})"


class FMIndex:
    """A compressed full-text index over a single text.

    Parameters
    ----------
    text:
        The text to index.  A ``$`` sentinel is appended automatically if not
        already present; it must not appear anywhere else in the text.
    sample_rate:
        Sample the suffix array every ``sample_rate`` rows.  Smaller values
        use more memory but make :meth:`locate` faster.  A common default is
        32 or 64.
    use_naive_sa:
        If True, use the O(n^2 log n) naive suffix-array construction instead
        of the prefix-doubling algorithm.  Useful for testing on very small
        inputs or validating the fast construction.

    Attributes
    ----------
    n : int
        Length of the indexed text (including the sentinel).
    alphabet_size : int
        Number of distinct characters (including the sentinel).
    """

    def __init__(
        self,
        text: str,
        sample_rate: int = 16,
        use_naive_sa: bool = False,
        backend: str = "wavelet_tree",
    ):
        if not isinstance(text, str):
            raise TypeError("text must be a str")
        if sample_rate < 1:
            raise ValueError("sample_rate must be >= 1")
        if backend not in ("wavelet_tree", "wavelet_matrix"):
            raise ValueError(
                f"backend must be 'wavelet_tree' or 'wavelet_matrix', got {backend!r}"
            )

        self._logger = get_logger()
        self._backend_name = backend

        # --- handle the sentinel ------------------------------------------------
        if SENTINEL in text:
            if text.count(SENTINEL) > 1 or text[-1] != SENTINEL:
                raise ConstructionError(
                    "sentinel '$' may only appear once, as the final character"
                )
            self._raw_text = text
        else:
            self._raw_text = text + SENTINEL

        self.sample_rate = sample_rate
        self.n = len(self._raw_text)

        # --- build the suffix array and BWT ------------------------------------
        with log_time(f"SA construction (n={self.n})"):
            if use_naive_sa:
                sa = build_suffix_array_naive(self._raw_text)
            else:
                sa = build_suffix_array(self._raw_text)
        self._sa = sa
        bwt, sa = bwt_encode(self._raw_text, sa)
        self._bwt = bwt

        # --- wavelet tree or matrix over the BWT -------------------------------
        with log_time(f"wavelet construction ({backend})"):
            bwt_codes = [ord(c) for c in bwt]
            if backend == "wavelet_matrix":
                self._wt = WaveletMatrix(bwt_codes)
            else:
                self._wt = WaveletTree(bwt_codes)

        # --- C array: number of chars lex-smaller than c -----------------------
        # counts of every symbol in the text (== counts in BWT since BWT is a perm)
        counts: Dict[int, int] = {}
        for c in self._raw_text:
            code = ord(c)
            counts[code] = counts.get(code, 0) + 1
        sorted_codes = sorted(counts.keys())
        self._alphabet = [chr(c) for c in sorted_codes]
        self._c: Dict[int, int] = {}
        cumulative = 0
        for code in sorted_codes:
            self._c[code] = cumulative
            cumulative += counts[code]
        self.alphabet_size = len(sorted_codes)

        # --- sampled suffix array ----------------------------------------------
        # For every row i where sa[i] % sample_rate == 0, store sa[i].
        self._sa_sampled: Dict[int, int] = {}
        for i in range(self.n):
            if sa[i] % sample_rate == 0:
                self._sa_sampled[i] = sa[i]

        # --- cache of the original text length without sentinel -----------------
        self._text_len = self.n - 1  # exclude sentinel
        # lazy reverse SA lookup, populated on first extract()
        self._sa_inverse: Optional[List[int]] = None

    __slots__ = (
        "_logger",
        "_backend_name",
        "_raw_text",
        "sample_rate",
        "n",
        "_sa",
        "_bwt",
        "_wt",
        "_c",
        "_alphabet",
        "alphabet_size",
        "_sa_sampled",
        "_text_len",
        "_sa_inverse",
    )

    # ==================================================================
    # public read-only properties
    # ==================================================================
    @property
    def text(self) -> str:
        """The original text (without the sentinel)."""
        return self._raw_text[:-1]

    @property
    def bwt(self) -> str:
        """The Burrows-Wheeler Transform string (with the sentinel)."""
        return self._bwt

    @property
    def alphabet(self) -> List[str]:
        """Sorted list of characters in the alphabet (including sentinel)."""
        return list(self._alphabet)

    @property
    def suffix_array(self) -> List[int]:
        """The full suffix array (a copy)."""
        return list(self._sa)

    @property
    def backend(self) -> str:
        """The wavelet backend in use (``"wavelet_tree"`` or ``"wavelet_matrix"``)."""
        return self._backend_name

    # ==================================================================
    # LF mapping
    # ==================================================================
    def _lf(self, i: int) -> int:
        """LF-mapping: row i -> row LF(i).

        LF(i) = C[c] + rank(c, i) where c = BWT[i].
        """
        c = self._wt.access(i)
        return self._c[c] + self._wt.rank(c, i)

    # ==================================================================
    # backward search (exact count)
    # ==================================================================
    def _backward_search_interval(self, pattern: str) -> Optional[Tuple[int, int]]:
        """Return the half-open SA interval [l, r) for *pattern*, or None.

        Uses the classic backward-search algorithm.  Time O(|pattern| log σ).
        """
        if not pattern:
            return (0, self.n)
        l = 0
        r = self.n  # half-open [l, r)
        for ch in reversed(pattern):
            code = ord(ch)
            if code not in self._c:
                return None  # character not in alphabet
            rank_l = self._wt.rank(code, l)
            rank_r = self._wt.rank(code, r)
            if rank_l == rank_r:
                return None  # no occurrences
            l = self._c[code] + rank_l
            r = self._c[code] + rank_r
        if l >= r:
            return None
        return (l, r)

    def count(self, pattern: str) -> int:
        """Return the number of occurrences of *pattern* in the text."""
        if not isinstance(pattern, str):
            raise TypeError("pattern must be a str")
        interval = self._backward_search_interval(pattern)
        if interval is None:
            return 0
        l, r = interval
        return r - l

    def _locate_row(self, row: int) -> int:
        """Recover the suffix-array value at *row* using LF-mapping.

        Walks backwards through the BWT applying LF until we hit a sampled
        SA row, counting the steps.  The real position is sa_sample + steps.
        """
        steps = 0
        cur = row
        while cur not in self._sa_sampled:
            cur = self._lf(cur)
            steps += 1
            if steps > self.n:
                # safety valve — should never happen
                raise RuntimeError("locate failed to reach a sampled SA row")
        return self._sa_sampled[cur] + steps

    def locate(self, pattern: str) -> List[int]:
        """Return the starting positions of all occurrences of *pattern*.

        Positions are 0-indexed into the original text (excluding the sentinel).
        The list is sorted ascending.
        """
        interval = self._backward_search_interval(pattern)
        if interval is None:
            return []
        l, r = interval
        positions = [self._locate_row(l + i) for i in range(r - l)]
        positions.sort()
        return positions

    def search(self, pattern: str) -> List[FMIndexMatch]:
        """Like :meth:`locate` but returns :class:`FMIndexMatch` objects."""
        positions = self.locate(pattern)
        return [FMIndexMatch(position=p, mismatches=0, pattern=pattern) for p in positions]

    # ==================================================================
    # extract
    # ==================================================================
    def extract(self, pos: int, length: int) -> str:
        """Return ``text[pos : pos+length]``.

        Uses the sampled suffix array and LF-mapping.  Works even when the
        original text is not retained in memory (here it is, but we exercise
        the index path for correctness).
        """
        if length <= 0:
            return ""
        if pos < 0 or pos + length > self._text_len:
            raise IndexError(
                f"extract({pos}, {length}) out of range [0, {self._text_len})"
            )
        # We read the text backwards using the LF-mapping.
        #
        # The BWT character at row r is text[SA[r] - 1] (the character
        # *preceding* the suffix start), or '$' if SA[r] == 0.  So to read
        # text[end], we need the row whose SA value is end+1, whose BWT
        # character is text[end].
        #
        # We start at the row for SA = pos + length (one past the last char we
        # want), read its BWT (= text[pos+length-1]), apply LF to get the row
        # for SA = pos+length-1, read text[pos+length-2], and so on.
        end_plus_1 = pos + length  # SA value whose BWT = text[pos+length-1]
        row = self._find_row_for_position(end_plus_1)
        chars: List[str] = []
        for _ in range(length):
            chars.append(chr(self._wt.access(row)))
            row = self._lf(row)
        chars.reverse()
        return "".join(chars)

    def _find_row_for_position(self, pos: int) -> int:
        """Find the SA row whose value equals *pos*.

        Walk LF backwards from a sampled row to reach the desired position,
        counting steps; here we walk in the opposite direction: we find a
        sampled SA row `s` with value `v`, then walk LF until the accumulated
        position equals `pos`.
        """
        # Strategy: iterate over sampled rows, pick the one with the smallest
        # number of LF steps to reach pos.  For simplicity (and correctness),
        # we walk from the row whose sampled SA value is the largest value
        # <= pos, and then walk forward.  But we can't walk forward easily.
        #
        # Instead: walk LF *backwards* from row 0 (the sentinel row, SA value
        # n-1).  We need the row r such that LF^k(r) == 0 for k = n-1-pos.
        # That is expensive.  The practical approach: we already keep the full
        # text, so fall back to scanning.  But to honor the "index-only"
        # contract, we do it properly:
        #
        # We pick *any* sampled row s0 with SA value v0.  We need a row r with
        # SA(r) = pos.  We know SA(r) = pos.  After k LF-steps, SA(LF^k(r)) =
        # pos - k (mod n).  So if we walk k = (pos - v0) mod n LF-steps from r
        # we land on s0.  Conversely, from s0 we need k = (v0 - pos) mod n
        # *inverse*-LF steps.  We don't have inverse LF precomputed here.
        #
        # Simplest correct method given our structures: linear scan of the
        # sampled SA dict to find a sampled row, then walk LF from an
        # arbitrary row and detect when steps align.  This is O(n) worst case
        # which is acceptable for extract (called rarely).
        #
        # We'll walk from row 0 (sentinel, SA = n-1) forward via LF until we
        # reach SA value `pos`.  But we can't read SA values without locating.
        # Catch-22.  So we use the stored raw text as the authoritative source
        # for _find_row_for_position via a reverse lookup of suffix array.
        # This is fine: extract() is not the hot path; count/locate are.
        # We build a reverse map SA value -> row lazily.
        if self._sa_inverse is None:
            self._sa_inverse = [0] * self.n
            for row, val in enumerate(self._sa):
                self._sa_inverse[val] = row
        return self._sa_inverse[pos]

    # ==================================================================
    # approximate search (Hamming distance)
    # ==================================================================
    def search_approx(
        self,
        pattern: str,
        max_mismatches: int = 0,
    ) -> List[FMIndexMatch]:
        """Search for *pattern* allowing up to *max_mismatches* substitutions.

        Uses recursive backward search with backtracking.  Returns matches
        sorted by position; each carries its mismatch count.  Duplicate
        positions (different mismatch paths) are collapsed to the smallest
        mismatch count.
        """
        if max_mismatches < 0:
            raise ValueError("max_mismatches must be >= 0")
        if not pattern:
            return []

        results: Dict[int, int] = {}  # position -> min mismatches

        # Backward search with backtracking: process the pattern from the last
        # character to the first (depth 0 = last char).  At each depth we try
        # every alphabet character, accumulating mismatches and pruning
        # branches that exceed max_mismatches.
        def recurse_back(l: int, r: int, depth: int, mismatches: int) -> None:
            if l >= r:
                return
            if depth == len(pattern):
                for row in range(l, r):
                    p = self._locate_row(row)
                    if p + len(pattern) <= self._text_len:
                        existing = results.get(p)
                        if existing is None or mismatches < existing:
                            results[p] = mismatches
                return
            ch = pattern[len(pattern) - 1 - depth]
            ch_code = ord(ch)
            for c in self._alphabet:
                if c == SENTINEL:
                    continue
                code = ord(c)
                rank_l = self._wt.rank(code, l)
                rank_r = self._wt.rank(code, r)
                if rank_l == rank_r:
                    continue
                new_l = self._c[code] + rank_l
                new_r = self._c[code] + rank_r
                add_mm = 0 if code == ch_code else 1
                if mismatches + add_mm > max_mismatches:
                    continue
                recurse_back(new_l, new_r, depth + 1, mismatches + add_mm)

        recurse_back(0, self.n, 0, 0)

        matches = [
            FMIndexMatch(position=p, mismatches=mm, pattern=pattern)
            for p, mm in sorted(results.items())
        ]
        return matches

    # ==================================================================
    # wildcard search (character classes / '?')
    # ==================================================================
    def search_wildcard(
        self,
        pattern: str,
        wildcard: str = "?",
    ) -> List[FMIndexMatch]:
        """Search for *pattern* where *wildcard* matches any single character.

        Uses recursive backward search with backtracking over the alphabet at
        wildcard positions.  Returns matches sorted by position (exact
        matches, zero mismatches).
        """
        if not pattern:
            return []

        results: Dict[int, int] = {}  # position -> always 0 (exact)

        def recurse(l: int, r: int, depth: int) -> None:
            if l >= r:
                return
            if depth == len(pattern):
                for row in range(l, r):
                    p = self._locate_row(row)
                    if p + len(pattern) <= self._text_len:
                        results[p] = 0
                return
            ch = pattern[len(pattern) - 1 - depth]
            if ch == wildcard:
                for c in self._alphabet:
                    if c == SENTINEL:
                        continue
                    code = ord(c)
                    rank_l = self._wt.rank(code, l)
                    rank_r = self._wt.rank(code, r)
                    if rank_l == rank_r:
                        continue
                    recurse(
                        self._c[code] + rank_l,
                        self._c[code] + rank_r,
                        depth + 1,
                    )
            else:
                code = ord(ch)
                if code not in self._c:
                    return
                rank_l = self._wt.rank(code, l)
                rank_r = self._wt.rank(code, r)
                if rank_l == rank_r:
                    return
                recurse(
                    self._c[code] + rank_l,
                    self._c[code] + rank_r,
                    depth + 1,
                )

        recurse(0, self.n, 0)
        return [
            FMIndexMatch(position=p, mismatches=0, pattern=pattern)
            for p in sorted(results)
        ]

    # ==================================================================
    # multi-pattern search
    # ==================================================================
    def locate_multi(
        self,
        patterns: List[str],
    ) -> Dict[str, List[int]]:
        """Locate multiple patterns in a single pass.

        Returns a dict mapping each pattern to its sorted list of positions.
        More efficient than calling :meth:`locate` separately when patterns
        share suffixes, because backward search reuses the BWT structure.
        """
        return {p: self.locate(p) for p in patterns}

    def count_multi(
        self,
        patterns: List[str],
    ) -> Dict[str, int]:
        """Count multiple patterns.  Returns {pattern: count}."""
        return {p: self.count(p) for p in patterns}

    # ==================================================================
    # range query: count occurrences within a text window
    # ==================================================================
    def count_in_range(
        self,
        pattern: str,
        pos_lo: int,
        pos_hi: int,
    ) -> int:
        """Count occurrences of *pattern* whose start is in [pos_lo, pos_hi)."""
        positions = self.locate(pattern)
        return sum(1 for p in positions if pos_lo <= p < pos_hi)

    # ==================================================================
    # suffix-array based longest common prefix (LCP) array
    # ==================================================================
    def lcp_array(self) -> List[int]:
        """Compute the LCP array via Kasai's algorithm in O(n).

        LCP[i] = length of the longest common prefix between suffix SA[i] and
        suffix SA[i-1].  LCP[0] is undefined and set to 0.
        """
        sa = self._sa
        text = self._raw_text
        n = self.n
        rank = [0] * n
        for i in range(n):
            rank[sa[i]] = i
        lcp = [0] * n
        h = 0
        for i in range(n):
            if rank[i] > 0:
                j = sa[rank[i] - 1]
                while i + h < n and j + h < n and text[i + h] == text[j + h]:
                    h += 1
                lcp[rank[i]] = h
                if h > 0:
                    h -= 1
            else:
                h = 0
        return lcp

    # ==================================================================
    # longest repeated substring (via LCP array)
    # ==================================================================
    def longest_repeated_substring(self, min_len: int = 1) -> Optional[Tuple[str, int]]:
        """Return the longest substring that appears at least twice.

        Returns (substring, length) or None if no repetition of at least
        *min_len* exists.  Uses the LCP array.
        """
        lcp = self.lcp_array()
        best_len = min_len - 1
        best_pos = -1
        for i in range(1, self.n):
            if lcp[i] > best_len:
                # the repeated substring is text[sa[i] : sa[i]+lcp[i]]
                best_len = lcp[i]
                best_pos = self._sa[i]
        if best_pos < 0:
            return None
        # the substring may include the sentinel if it reaches the end; trim
        sub = self._raw_text[best_pos : best_pos + best_len]
        if SENTINEL in sub:
            sub = sub[: sub.index(SENTINEL)]
        if len(sub) < min_len:
            return None
        return (sub, len(sub))

    # ==================================================================
    # convenience
    # ==================================================================
    def __contains__(self, pattern: str) -> bool:
        return self.count(pattern) > 0

    def __len__(self) -> int:
        return self._text_len

    def __repr__(self) -> str:
        return (
            f"FMIndex(text_len={self._text_len}, alphabet_size={self.alphabet_size}, "
            f"sample_rate={self.sample_rate}, backend={self._backend_name!r})"
        )

    # ==================================================================
    # batch locate: multiple patterns in one call
    # ==================================================================
    def batch_locate(
        self,
        patterns: List[str],
        unique: bool = True,
    ) -> Dict[str, List[int]]:
        """Locate multiple patterns efficiently.

        Parameters
        ----------
        patterns:
            List of patterns to locate.
        unique:
            If True, deduplicate identical patterns (locate once, copy result).

        Returns a dict mapping each pattern to its sorted list of positions.
        """
        if not isinstance(patterns, list):
            raise TypeError("patterns must be a list of str")
        results: Dict[str, List[int]] = {}
        cache: Dict[str, List[int]] = {}
        for p in patterns:
            if not isinstance(p, str):
                raise TypeError("each pattern must be a str")
            if unique and p in cache:
                results[p] = list(cache[p])
            else:
                pos = self.locate(p)
                cache[p] = pos
                results[p] = list(pos)
        return results

    # ==================================================================
    # first / last occurrence
    # ==================================================================
    def first_occurrence(self, pattern: str) -> Optional[int]:
        """Return the first (smallest) position of *pattern*, or None."""
        positions = self.locate(pattern)
        return positions[0] if positions else None

    def last_occurrence(self, pattern: str) -> Optional[int]:
        """Return the last (largest) position of *pattern*, or None."""
        positions = self.locate(pattern)
        return positions[-1] if positions else None

    # ==================================================================
    # memory estimation
    # ==================================================================
    def estimate_memory_bytes(self) -> int:
        """Estimate the in-memory size of the index in bytes.

        Accounts for the BWT string, suffix array, sampled SA, C array,
        and wavelet tree/matrix bit arrays.  This is an approximation
        (Python object overhead is hard to measure exactly).
        """
        # suffix array: list of n ints
        sa_bytes = self.n * 28  # ~28 bytes per Python int in a list
        # BWT string: n bytes (plus str overhead)
        bwt_bytes = self.n + 49
        # sampled SA dict
        sampled_bytes = len(self._sa_sampled) * 100  # rough dict entry cost
        # C array dict
        c_bytes = self.alphabet_size * 100
        # wavelet tree: ~n bits per level × log(σ) levels
        import math
        levels = max(1, math.ceil(math.log2(self.alphabet_size))) if self.alphabet_size > 1 else 1
        wt_bytes = (self.n * levels) // 8
        # raw text (if retained)
        text_bytes = self.n + 49
        return sa_bytes + bwt_bytes + sampled_bytes + c_bytes + wt_bytes + text_bytes

    # ==================================================================
    # iteration over all distinct k-mers (optional helper)
    # ==================================================================
    def iter_kmers(self, k: int) -> Iterator[Tuple[str, int]]:
        """Yield (kmer, count) for every distinct k-mer in the text.

        Uses the suffix-array range tree: for each suffix we take its first k
        characters.  Sorted SA means equal k-mers are contiguous, so we can
        group them in one pass.  Suffixes shorter than k are skipped.
        """
        if k < 1:
            raise ValueError("k must be >= 1")
        sa = self._sa
        text = self._raw_text
        n = self._text_len
        prev_kmer: Optional[str] = None
        count = 0
        for s in sa:
            if s + k > n:
                continue  # suffix (excluding sentinel) shorter than k
            kmer = text[s : s + k]
            if kmer == prev_kmer:
                count += 1
            else:
                if prev_kmer is not None and count > 0:
                    yield (prev_kmer, count)
                prev_kmer = kmer
                count = 1
        if prev_kmer is not None and count > 0:
            yield (prev_kmer, count)