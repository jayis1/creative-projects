"""Index of Coincidence calculation for cryptanalysis."""

from __future__ import annotations
from collections import Counter
from typing import Dict, List, Tuple


# Language IC reference values
LANGUAGE_IC = {
    "english": 0.0667,
    "french": 0.0778,
    "german": 0.0762,
    "spanish": 0.0770,
    "italian": 0.0738,
    "russian": 0.0529,
    "random": 0.0385,  # 1/26
}


class IndexOfCoincidence:
    """Index of Coincidence (IC) analysis tools.

    The IC measures the probability that two randomly selected letters
    from a text are the same. For English text, IC ≈ 0.0667.
    For random text, IC ≈ 0.0385 (1/26).

    This is useful for:
    - Distinguishing monoalphabetic from polyalphabetic ciphers
    - Estimating the key length of Vigenère-type ciphers
    - Identifying the language of plaintext
    """

    @staticmethod
    def calculate(text: str) -> float:
        """Calculate the Index of Coincidence for text.

        Args:
            text: Input text (only alphabetic characters are used).

        Returns:
            IC value between 0 and 1. English ≈ 0.0667, random ≈ 0.0385.
        """
        text = text.upper()
        counts = Counter(ch for ch in text if ch.isalpha())
        n = sum(counts.values())

        if n <= 1:
            return 0.0

        ic = sum(c * (c - 1) for c in counts.values()) / (n * (n - 1))
        return ic

    @staticmethod
    def estimated_key_length(ciphertext: str, max_length: int = 20) -> List[Tuple[int, float]]:
        """Estimate Vigenère key length using IC method.

        Splits ciphertext into groups by position modulo each candidate length,
        computes average IC across groups, and returns results sorted by
        how close the average IC is to English IC.

        Args:
            ciphertext: Encrypted text to analyze.
            max_length: Maximum key length to try.

        Returns:
            List of (key_length, average_ic) tuples sorted by distance
            from English IC (best first).
        """
        ciphertext = ciphertext.upper()
        alpha = "".join(ch for ch in ciphertext if ch.isalpha())
        results = []

        for kl in range(1, min(max_length + 1, len(alpha) // 2 + 1)):
            groups = [[] for _ in range(kl)]
            for i, ch in enumerate(alpha):
                groups[i % kl].append(ch)

            ics = []
            for group in groups:
                if len(group) >= 2:
                    group_text = "".join(group)
                    ic = IndexOfCoincidence.calculate(group_text)
                    ics.append(ic)

            if ics:
                avg_ic = sum(ics) / len(ics)
                results.append((kl, avg_ic))

        # Sort by distance from English IC
        english_ic = LANGUAGE_IC["english"]
        results.sort(key=lambda x: abs(x[1] - english_ic))
        return results

    @staticmethod
    def friedman_test(ciphertext: str) -> float:
        """Estimate key length using the Friedman test.

        Uses the formula: k ≈ 0.0266 * n / ((IC * (n-1)) - 0.0279 * n + 0.0385)
        where n is the text length and IC is the observed index of coincidence.

        Args:
            ciphertext: Encrypted text to analyze.

        Returns:
            Estimated key length as a float. Round to nearest integer for practical use.
        """
        text = "".join(ch for ch in ciphertext.upper() if ch.isalpha())
        n = len(text)
        if n < 2:
            return 0.0
        ic = IndexOfCoincidence.calculate(text)
        # Friedman formula for English
        numerator = 0.0266 * n
        denominator = ic * (n - 1) - 0.0279 * n + 0.0385
        if abs(denominator) < 1e-10:
            return 0.0
        return numerator / denominator

    @staticmethod
    def identify_language(text: str) -> List[Tuple[str, float, float]]:
        """Attempt to identify the language of text by comparing IC to known values.

        Args:
            text: Plaintext to identify.

        Returns:
            List of (language, expected_ic, observed_ic) tuples sorted by
            closeness of match (best first).
        """
        observed_ic = IndexOfCoincidence.calculate(text)
        results = []
        for lang, expected_ic in LANGUAGE_IC.items():
            if lang != "random":
                results.append((lang, expected_ic, observed_ic))
        results.sort(key=lambda x: abs(x[2] - x[1]))
        return results