"""Frequency analysis for cryptanalysis."""

from __future__ import annotations
from collections import Counter
from typing import Dict, List, Tuple


# English letter frequencies (percentage)
ENGLISH_FREQUENCIES: Dict[str, float] = {
    'A': 8.167, 'B': 1.492, 'C': 2.782, 'D': 4.253, 'E': 12.702,
    'F': 2.228, 'G': 2.015, 'H': 6.094, 'I': 6.966, 'J': 0.153,
    'K': 0.772, 'L': 4.025, 'M': 2.406, 'N': 6.749, 'O': 7.507,
    'P': 1.929, 'Q': 0.095, 'R': 5.987, 'S': 6.327, 'T': 9.056,
    'U': 2.758, 'V': 0.978, 'W': 2.360, 'X': 0.150, 'Y': 1.974,
    'Z': 0.074,
}

# English bigram frequencies (top 20, percentage approximation)
ENGLISH_BIGRAMS: Dict[str, float] = {
    'TH': 3.56, 'HE': 3.07, 'IN': 2.43, 'ER': 2.05, 'AN': 1.99,
    'RE': 1.85, 'ON': 1.76, 'AT': 1.49, 'EN': 1.45, 'ND': 1.35,
    'TI': 1.34, 'ES': 1.34, 'OR': 1.28, 'TE': 1.27, 'OF': 1.17,
    'ED': 1.17, 'IS': 1.13, 'IT': 1.12, 'AL': 1.09, 'AR': 1.07,
    'ST': 1.05, 'TO': 1.05, 'NT': 1.04, 'NG': 0.95, 'SE': 0.93,
    'HA': 0.93, 'AS': 0.87, 'OU': 0.87, 'IO': 0.83, 'LE': 0.83,
}


class FrequencyAnalyzer:
    """Frequency analysis tools for cryptanalysis.

    Provides methods for computing letter, bigram, and trigram frequencies,
    comparing against English language norms, and scoring how closely a
    text matches expected English distributions.
    """

    def __init__(self) -> None:
        self.english_freq = ENGLISH_FREQUENCIES
        self.english_bigrams = ENGLISH_BIGRAMS

    @staticmethod
    def letter_frequencies(text: str) -> Dict[str, float]:
        """Compute letter frequency percentages for text.

        Args:
            text: Input text (only alphabetic characters are counted).

        Returns:
            Dictionary mapping uppercase letters to their frequency percentages.
        """
        text = text.upper()
        counts = Counter(ch for ch in text if ch.isalpha())
        total = sum(counts.values())
        if total == 0:
            return {ch: 0.0 for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"}
        return {ch: (counts.get(ch, 0) / total) * 100 for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"}

    @staticmethod
    def letter_counts(text: str) -> Dict[str, int]:
        """Compute raw letter counts for text.

        Args:
            text: Input text (only alphabetic characters are counted).

        Returns:
            Dictionary mapping uppercase letters to their counts.
        """
        text = text.upper()
        return dict(Counter(ch for ch in text if ch.isalpha()))

    @staticmethod
    def bigram_frequencies(text: str) -> Dict[str, float]:
        """Compute bigram frequency percentages for text.

        Args:
            text: Input text (only consecutive alphabetic pairs are counted).

        Returns:
            Dictionary mapping uppercase bigrams to their frequency percentages.
        """
        text = text.upper()
        alpha_text = "".join(ch for ch in text if ch.isalpha())
        if len(alpha_text) < 2:
            return {}

        bigrams = [alpha_text[i:i + 2] for i in range(len(alpha_text) - 1)]
        counts = Counter(bigrams)
        total = sum(counts.values())
        if total == 0:
            return {}
        return {bg: (count / total) * 100 for bg, count in counts.items()}

    @staticmethod
    def trigram_frequencies(text: str) -> Dict[str, float]:
        """Compute trigram frequency percentages for text.

        Args:
            text: Input text (only consecutive alphabetic triples are counted).

        Returns:
            Dictionary mapping uppercase trigrams to their frequency percentages.
        """
        text = text.upper()
        alpha_text = "".join(ch for ch in text if ch.isalpha())
        if len(alpha_text) < 3:
            return {}

        trigrams = [alpha_text[i:i + 3] for i in range(len(alpha_text) - 2)]
        counts = Counter(trigrams)
        total = sum(counts.values())
        if total == 0:
            return {}
        return {tg: (count / total) * 100 for tg, count in counts.items()}

    def chi_squared(self, text: str) -> float:
        """Compute chi-squared statistic comparing text frequencies to English.

        Args:
            text: Input text to analyze.

        Returns:
            Chi-squared statistic (lower = closer to English).
        """
        freqs = self.letter_frequencies(text)
        text = text.upper()
        total = sum(1 for ch in text if ch.isalpha())
        if total == 0:
            return float('inf')

        chi_sq = 0.0
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            observed = (freqs[letter] / 100) * total
            expected = (self.english_freq[letter] / 100) * total
            if expected > 0:
                chi_sq += (observed - expected) ** 2 / expected
        return chi_sq

    def frequency_correlation(self, text: str) -> float:
        """Compute Pearson correlation between text frequencies and English.

        Args:
            text: Input text to analyze.

        Returns:
            Correlation coefficient (-1 to 1, higher = more like English).
        """
        import math

        freqs = self.letter_frequencies(text)
        letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        x = [self.english_freq[l] for l in letters]
        y = [freqs[l] for l in letters]

        n = len(letters)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi ** 2 for xi in x)
        sum_y2 = sum(yi ** 2 for yi in y)

        denom = math.sqrt((n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2))
        if denom == 0:
            return 0.0
        return (n * sum_xy - sum_x * sum_y) / denom

    def most_likely_shift(self, ciphertext: str) -> Tuple[int, float]:
        """Find the most likely Caesar shift using frequency analysis.

        Args:
            ciphertext: Text encrypted with an unknown Caesar shift.

        Returns:
            Tuple of (best_shift, best_correlation) where best_shift is 0-25.
        """
        from ..ciphers.caesar import CaesarCipher

        best_shift = 0
        best_score = -999.0

        for shift in range(26):
            candidate = CaesarCipher(shift=shift).decrypt(ciphertext)
            score = self.frequency_correlation(candidate)
            if score > best_score:
                best_score = score
                best_shift = shift

        return best_shift, best_score

    def frequency_report(self, text: str, top_n: int = 10) -> str:
        """Generate a human-readable frequency analysis report.

        Args:
            text: Input text to analyze.
            top_n: Number of top items to show.

        Returns:
            Formatted string with frequency analysis results.
        """
        freqs = self.letter_frequencies(text)
        bigrams = self.bigram_frequencies(text)

        # Sort by frequency
        sorted_letters = sorted(freqs.items(), key=lambda x: x[1], reverse=True)
        sorted_bigrams = sorted(bigrams.items(), key=lambda x: x[1], reverse=True)

        lines = ["=== Frequency Analysis Report ===", ""]
        lines.append("Letter frequencies (top):")
        for letter, freq in sorted_letters[:top_n]:
            expected = self.english_freq.get(letter, 0)
            diff = freq - expected
            bar = "█" * int(freq)
            lines.append(f"  {letter}: {freq:6.2f}% (expected {expected:6.2f}%, diff {diff:+.2f}%) {bar}")

        if sorted_bigrams:
            lines.append("")
            lines.append(f"Top {min(top_n, len(sorted_bigrams))} bigrams:")
            for bg, freq in sorted_bigrams[:top_n]:
                lines.append(f"  {bg}: {freq:.2f}%")

        lines.append("")
        lines.append(f"Chi-squared: {self.chi_squared(text):.2f}")
        lines.append(f"Correlation with English: {self.frequency_correlation(text):.4f}")

        return "\n".join(lines)