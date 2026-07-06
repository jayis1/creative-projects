"""Text statistics utilities for FM-Index.

Computes information-theoretic and descriptive statistics about the
indexed text:

  - Shannon entropy (order-0)
  - Character frequency distribution
  - Gini coefficient of character distribution
  - Text length, alphabet size, average run length of the BWT
  - Most/least frequent characters
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .index import FMIndex


@dataclass
class TextStatistics:
    """Container for computed text statistics."""

    text_length: int = 0
    alphabet_size: int = 0
    alphabet: List[str] = field(default_factory=list)
    char_frequencies: Dict[str, int] = field(default_factory=dict)
    shannon_entropy: float = 0.0
    max_entropy: float = 0.0
    redundancy: float = 0.0  # 1 - H/Hmax
    gini_coefficient: float = 0.0
    most_frequent: List[Tuple[str, int]] = field(default_factory=list)
    least_frequent: List[Tuple[str, int]] = field(default_factory=list)
    bwt_length: int = 0
    bwt_num_runs: int = 0
    bwt_average_run_length: float = 0.0

    def summary(self) -> str:
        """Return a human-readable multi-line summary."""
        lines = [
            f"Text length        : {self.text_length:,}",
            f"Alphabet size      : {self.alphabet_size}",
            f"Shannon entropy    : {self.shannon_entropy:.4f} bits/char",
            f"Max entropy        : {self.max_entropy:.4f} bits/char",
            f"Redundancy         : {self.redundancy:.2%}",
            f"Gini coefficient   : {self.gini_coefficient:.4f}",
            f"BWT length         : {self.bwt_length:,}",
            f"BWT runs           : {self.bwt_num_runs:,}",
            f"BWT avg run length : {self.bwt_average_run_length:.2f}",
        ]
        if self.most_frequent:
            top = ", ".join(f"{c!r}:{n}" for c, n in self.most_frequent[:5])
            lines.append(f"Most frequent      : {top}")
        if self.least_frequent:
            bot = ", ".join(f"{c!r}:{n}" for c, n in self.least_frequent[:5])
            lines.append(f"Least frequent     : {bot}")
        return "\n".join(lines)


def compute_statistics(idx: FMIndex) -> TextStatistics:
    """Compute comprehensive statistics about the indexed text.

    Parameters
    ----------
    idx:
        A built :class:`FMIndex`.

    Returns
    -------
    TextStatistics
    """
    stats = TextStatistics()
    text = idx.text
    stats.text_length = len(text)
    stats.alphabet_size = idx.alphabet_size
    stats.alphabet = idx.alphabet
    stats.bwt_length = idx.n

    # character frequencies
    freq: Dict[str, int] = {}
    for ch in text:
        freq[ch] = freq.get(ch, 0) + 1
    stats.char_frequencies = freq

    # Shannon entropy: H = -sum(p_i * log2(p_i))
    n = len(text)
    if n > 0:
        entropy = 0.0
        for count in freq.values():
            p = count / n
            if p > 0:
                entropy -= p * math.log2(p)
        stats.shannon_entropy = entropy
        stats.max_entropy = math.log2(len(freq)) if len(freq) > 1 else 0.0
        if stats.max_entropy > 0:
            stats.redundancy = 1.0 - entropy / stats.max_entropy

    # Gini coefficient of the frequency distribution
    if freq:
        sorted_counts = sorted(freq.values())
        m = len(sorted_counts)
        cum = 0.0
        for i, c in enumerate(sorted_counts):
            cum += (i + 1) * c
        total = sum(sorted_counts)
        if total > 0 and m > 1:
            stats.gini_coefficient = (2 * cum) / (m * total) - (m + 1) / m
        else:
            stats.gini_coefficient = 0.0

    # most / least frequent
    sorted_freq = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
    stats.most_frequent = sorted_freq[:10]
    stats.least_frequent = sorted(sorted_freq[-10:], key=lambda x: (x[1], x[0]))

    # BWT run statistics
    from .rle import rle_encode

    runs = rle_encode(idx.bwt)
    stats.bwt_num_runs = len(runs)
    if runs:
        stats.bwt_average_run_length = idx.n / len(runs)

    return stats