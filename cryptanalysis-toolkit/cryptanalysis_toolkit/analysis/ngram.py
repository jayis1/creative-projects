"""N-gram scoring for cipher breaking and language identification."""

from __future__ import annotations
import math
from collections import Counter
from typing import Dict, Optional


# English monogram log probabilities (base 10)
_ENGLISH_MONOGRAMS = {
    'A': -2.086, 'B': -3.127, 'C': -2.556, 'D': -2.371, 'E': -1.896,
    'F': -2.652, 'G': -2.696, 'H': -2.215, 'I': -2.158, 'J': -3.815,
    'K': -3.113, 'L': -2.395, 'M': -2.619, 'N': -2.171, 'O': -2.125,
    'P': -2.714, 'Q': -4.022, 'R': -2.223, 'S': -2.199, 'T': -2.044,
    'U': -2.560, 'V': -3.010, 'W': -2.627, 'X': -3.823, 'Y': -2.705,
    'Z': -4.134,
}

# English bigram log probabilities (top 100+)
_ENGLISH_BIGRAMS = {
    'TH': -2.550, 'HE': -2.513, 'IN': -2.614, 'ER': -2.688, 'AN': -2.701,
    'RE': -2.732, 'ON': -2.754, 'AT': -2.827, 'EN': -2.838, 'ND': -2.870,
    'TI': -2.871, 'ES': -2.872, 'OR': -2.892, 'TE': -2.896, 'OF': -2.932,
    'ED': -2.932, 'IS': -2.948, 'IT': -2.951, 'AL': -2.963, 'AR': -2.970,
    'ST': -2.978, 'TO': -2.978, 'NT': -2.983, 'NG': -3.022, 'SE': -3.032,
    'HA': -3.032, 'AS': -3.061, 'OU': -3.061, 'IO': -3.081, 'LE': -3.081,
    'VE': -3.086, 'CO': -3.090, 'ME': -3.094, 'DE': -3.098, 'HI': -3.103,
    'RI': -3.105, 'RO': -3.109, 'IC': -3.120, 'NE': -3.129, 'EA': -3.129,
    'RA': -3.136, 'CE': -3.150, 'LI': -3.162, 'CH': -3.165, 'LL': -3.168,
    'BE': -3.170, 'MA': -3.173, 'SI': -3.177, 'OM': -3.180, 'UR': -3.189,
}


class NgramScorer:
    """N-gram based text scoring for cipher breaking.

    Scores text by how "English-like" it is using monogram, bigram,
    and trigram log-probability statistics. Higher scores = more English-like.

    Can be used for hill-climbing attacks on substitution ciphers.
    """

    def __init__(self) -> None:
        self._monograms = _ENGLISH_MONOGRAMS
        self._bigrams = _ENGLISH_BIGRAMS
        self._trigrams: Dict[str, float] = {}
        self._loaded_trigrams = False

    def score_monograms(self, text: str) -> float:
        """Score text using monogram (single letter) frequencies.

        Args:
            text: Text to score.

        Returns:
            Log-probability score. Higher = more English-like.
        """
        text = text.upper()
        text = "".join(ch for ch in text if ch.isalpha())
        if not text:
            return float('-inf')

        total = 0.0
        for ch in text:
            total += self._monograms.get(ch, -5.0)
        return total / len(text)

    def score_bigrams(self, text: str) -> float:
        """Score text using bigram frequencies.

        Args:
            text: Text to score.

        Returns:
            Log-probability score. Higher = more English-like.
        """
        text = text.upper()
        text = "".join(ch for ch in text if ch.isalpha())
        if len(text) < 2:
            return float('-inf')

        total = 0.0
        count = 0
        for i in range(len(text) - 1):
            bg = text[i:i + 2]
            total += self._bigrams.get(bg, -4.0)
            count += 1
        return total / max(count, 1)

    def score_combined(self, text: str, mono_weight: float = 0.2, bi_weight: float = 0.8) -> float:
        """Score text using weighted combination of monogram and bigram scores.

        Args:
            text: Text to score.
            mono_weight: Weight for monogram score (default 0.2).
            bi_weight: Weight for bigram score (default 0.8).

        Returns:
            Combined weighted score. Higher = more English-like.
        """
        mono = self.score_monograms(text)
        bi = self.score_bigrams(text)
        if mono == float('-inf') or bi == float('-inf'):
            return float('-inf')
        return mono_weight * mono + bi_weight * bi

    def score(self, text: str) -> float:
        """Score text using the best available method.

        Uses combined monogram + bigram scoring by default.

        Args:
            text: Text to score.

        Returns:
            Score. Higher = more English-like.
        """
        return self.score_combined(text)