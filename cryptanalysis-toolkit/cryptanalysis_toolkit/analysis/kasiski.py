"""Kasiski examination for determining Vigenère key length."""

from __future__ import annotations
from collections import Counter
from typing import Dict, List, Tuple
import math


class KasiskiExaminer:
    """Kasiski examination for polyalphabetic cipher key length detection.

    The Kasiski method finds repeated sequences in ciphertext and analyzes
    the distances between them. Common factors of these distances are
    likely key lengths for Vigenère-type ciphers.
    """

    def __init__(self, min_sequence_length: int = 3, max_sequence_length: int = 6) -> None:
        """Initialize Kasiski examiner.

        Args:
            min_sequence_length: Minimum length of repeated sequences to find.
            max_sequence_length: Maximum length of repeated sequences to find.
        """
        self.min_seq = min_sequence_length
        self.max_seq = max_sequence_length

    def find_repeated_sequences(self, text: str) -> Dict[str, List[int]]:
        """Find repeated sequences and their positions in text.

        Args:
            text: Input text to search for repeated sequences.

        Returns:
            Dictionary mapping each repeated sequence to a list of start positions.
        """
        text = text.upper()
        text = "".join(ch for ch in text if ch.isalpha())
        sequences: Dict[str, List[int]] = {}

        for seq_len in range(self.min_seq, self.max_seq + 1):
            for i in range(len(text) - seq_len + 1):
                seq = text[i:i + seq_len]
                if seq not in sequences:
                    # Search for this sequence starting from after this occurrence
                    positions = [i]
                    start = i + 1
                    while True:
                        pos = text.find(seq, start)
                        if pos == -1:
                            break
                        positions.append(pos)
                        start = pos + 1

                    if len(positions) >= 2:
                        sequences[seq] = positions

        return sequences

    def compute_distances(self, sequences: Dict[str, List[int]]) -> List[int]:
        """Compute distances between repeated sequences.

        Args:
            sequences: Dictionary from find_repeated_sequences().

        Returns:
            List of distances between consecutive occurrences of each sequence.
        """
        distances = []
        for seq, positions in sequences.items():
            for i in range(len(positions) - 1):
                for j in range(i + 1, len(positions)):
                    distances.append(positions[j] - positions[i])
        return distances

    def analyze(self, ciphertext: str, max_key_length: int = 20) -> List[Tuple[int, int]]:
        """Perform Kasiski examination to estimate key length.

        Args:
            ciphertext: Encrypted text to analyze.
            max_key_length: Maximum key length to consider.

        Returns:
            List of (key_length, score) tuples sorted by score (highest first).
            Score is the count of distances divisible by that key length.
        """
        sequences = self.find_repeated_sequences(ciphertext)
        distances = self.compute_distances(sequences)

        if not distances:
            return []

        # Count how many distances are divisible by each candidate key length
        factor_counts = Counter()
        for dist in distances:
            for kl in range(2, max_key_length + 1):
                if dist % kl == 0:
                    factor_counts[kl] += 1

        # Score key lengths
        scored = []
        for kl, count in factor_counts.items():
            scored.append((kl, count))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def kasiski_report(self, ciphertext: str, max_key_length: int = 20, top_n: int = 10) -> str:
        """Generate a human-readable Kasiski examination report.

        Args:
            ciphertext: Encrypted text to analyze.
            max_key_length: Maximum key length to consider.
            top_n: Number of top candidates to show.

        Returns:
            Formatted string with Kasiski analysis results.
        """
        sequences = self.find_repeated_sequences(ciphertext)
        distances = self.compute_distances(sequences)
        results = self.analyze(ciphertext, max_key_length)

        lines = ["=== Kasiski Examination Report ===", ""]

        if not sequences:
            lines.append("No repeated sequences found. Text may be too short.")
            return "\n".join(lines)

        lines.append(f"Found {len(sequences)} repeated sequences:")
        for seq, positions in sorted(sequences.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
            dists = [positions[j] - positions[i]
                     for i in range(len(positions))
                     for j in range(i + 1, len(positions))]
            lines.append(f"  '{seq}' at positions {positions} (distances: {dists})")

        lines.append("")
        lines.append(f"Top {min(top_n, len(results))} key length candidates:")
        for kl, score in results[:top_n]:
            lines.append(f"  Key length {kl:2d}: score {score}")

        return "\n".join(lines)