"""Cipher breaking tools — automatic cryptanalysis."""

from __future__ import annotations
import random
import string
from typing import Dict, List, Optional, Tuple

from .ciphers.caesar import CaesarCipher
from .ciphers.substitution import SubstitutionCipher
from .ciphers.vigenere import VigenereCipher
from .ciphers.affine import AffineCipher
from .analysis.frequency import FrequencyAnalyzer
from .analysis.ic import IndexOfCoincidence
from .analysis.kasiski import KasiskiExaminer
from .analysis.ngram import NgramScorer


class CipherBreaker:
    """Automatic cipher breaking tools.

    Provides methods for breaking classical ciphers using statistical
    and heuristic techniques including:
    - Brute force (Caesar, Affine)
    - Frequency analysis
    - Kasiski examination + IC for Vigenère
    - Hill climbing for substitution ciphers
    """

    def __init__(self) -> None:
        self.freq = FrequencyAnalyzer()
        self.ic = IndexOfCoincidence()
        self.kasiski = KasiskiExaminer()
        self.scorer = NgramScorer()

    def break_caesar(self, ciphertext: str, top_n: int = 5) -> List[Dict]:
        """Break a Caesar cipher by scoring all 26 shifts.

        Args:
            ciphertext: Text encrypted with an unknown Caesar shift.
            top_n: Number of top candidates to return.

        Returns:
            List of dicts with keys: 'shift', 'plaintext', 'score', 'correlation'.
            Sorted by best score (highest correlation with English).
        """
        results = []
        for shift in range(26):
            candidate = CaesarCipher(shift=shift).decrypt(ciphertext)
            correlation = self.freq.frequency_correlation(candidate)
            results.append({
                "shift": shift,
                "plaintext": candidate,
                "correlation": correlation,
            })

        results.sort(key=lambda x: x["correlation"], reverse=True)
        return results[:top_n]

    def break_affine(self, ciphertext: str, top_n: int = 5) -> List[Dict]:
        """Break an affine cipher by scoring all valid (a, b) combinations.

        Args:
            ciphertext: Text encrypted with an unknown affine key.
            top_n: Number of top candidates to return.

        Returns:
            List of dicts with keys: 'a', 'b', 'plaintext', 'correlation'.
        """
        results = []
        for a in AffineCipher.VALID_A_VALUES:
            for b in range(26):
                try:
                    cipher = AffineCipher(a=a, b=b)
                    candidate = cipher.decrypt(ciphertext)
                    correlation = self.freq.frequency_correlation(candidate)
                    results.append({
                        "a": a,
                        "b": b,
                        "plaintext": candidate,
                        "correlation": correlation,
                    })
                except ValueError:
                    continue

        results.sort(key=lambda x: x["correlation"], reverse=True)
        return results[:top_n]

    def break_vigenere(self, ciphertext: str, max_key_length: int = 20,
                       top_n: int = 5) -> List[Dict]:
        """Break a Vigenère cipher using Kasiski + IC analysis.

        Args:
            ciphertext: Text encrypted with an unknown Vigenère key.
            max_key_length: Maximum key length to try.
            top_n: Number of top candidates to return.

        Returns:
            List of dicts with keys: 'key', 'plaintext', 'score'.
        """
        # Get key length candidates from both methods
        kasiski_results = self.kasiski.analyze(ciphertext, max_key_length)
        ic_results = self.ic.estimated_key_length(ciphertext, max_key_length)

        # Combine candidate key lengths
        candidate_lengths = set()
        for kl, _ in kasiski_results[:5]:
            candidate_lengths.add(kl)
        for kl, _ in ic_results[:5]:
            candidate_lengths.add(kl)

        # Also try small key lengths as fallback
        for kl in range(1, min(6, max_key_length + 1)):
            candidate_lengths.add(kl)

        alpha = "".join(ch for ch in ciphertext.upper() if ch.isalpha())

        results = []
        for key_len in candidate_lengths:
            if key_len < 1 or key_len > max_key_length:
                continue
            if key_len > len(alpha) // 2:
                continue

            key = self._find_vigenere_key(ciphertext, key_len)
            if key:
                candidate = VigenereCipher(keyword=key).decrypt(ciphertext)
                score = self.scorer.score(candidate)
                results.append({
                    "key": key,
                    "key_length": key_len,
                    "plaintext": candidate,
                    "score": score,
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_n]

    def _find_vigenere_key(self, ciphertext: str, key_length: int) -> Optional[str]:
        """Find the Vigenère key of a given length using frequency analysis.

        Splits ciphertext into groups by position mod key_length and
        finds the most likely shift for each group.

        Args:
            ciphertext: Encrypted text.
            key_length: Assumed key length.

        Returns:
            Best-guess keyword string, or None if text is too short.
        """
        alpha = "".join(ch for ch in ciphertext.upper() if ch.isalpha())
        if len(alpha) < key_length:
            return None

        key_chars = []
        for i in range(key_length):
            group = "".join(alpha[j] for j in range(i, len(alpha), key_length))
            best_shift, _ = self.freq.most_likely_shift(group)
            key_chars.append(chr(best_shift + ord('A')))

        return "".join(key_chars)

    def break_substitution(self, ciphertext: str, iterations: int = 5000,
                           restarts: int = 5, seed: Optional[int] = None) -> Dict:
        """Break a simple substitution cipher using hill climbing.

        Uses a simulated annealing / hill climbing approach with random
        perturbations of the substitution key.

        Args:
            ciphertext: Text encrypted with an unknown monoalphabetic substitution.
            iterations: Number of iterations per restart.
            restarts: Number of random restarts.
            seed: Random seed for reproducibility.

        Returns:
            Dict with keys: 'key', 'plaintext', 'score'.
        """
        if seed is not None:
            random.seed(seed)

        best_result = {"key": string.ascii_uppercase, "plaintext": ciphertext, "score": float('-inf')}

        for restart in range(restarts):
            # Start with frequency-based initial key
            if restart == 0:
                key = self._freq_based_initial_key(ciphertext)
            else:
                key = list(string.ascii_uppercase)
                random.shuffle(key)
                key = "".join(key)

            cipher = SubstitutionCipher(key=key)
            plaintext = cipher.decrypt(ciphertext)
            score = self.scorer.score(plaintext)

            temperature = 20.0
            for iteration in range(iterations):
                # Swap two random positions in the key
                key_list = list(key)
                i, j = random.sample(range(26), 2)
                key_list[i], key_list[j] = key_list[j], key_list[i]
                new_key = "".join(key_list)

                new_cipher = SubstitutionCipher(key=new_key)
                new_plaintext = new_cipher.decrypt(ciphertext)
                new_score = self.scorer.score(new_plaintext)

                # Accept if better, or with probability based on temperature
                delta = new_score - score
                if delta > 0 or (temperature > 0.01 and random.random() < math.exp(delta / max(temperature, 0.01))):
                    key = new_key
                    plaintext = new_plaintext
                    score = new_score

                # Cool down
                temperature *= 0.995

            if score > best_result["score"]:
                best_result = {
                    "key": key,
                    "plaintext": plaintext,
                    "score": score,
                }

        return best_result

    def _freq_based_initial_key(self, ciphertext: str) -> str:
        """Generate an initial substitution key based on frequency matching.

        Maps the most common ciphertext letters to the most common English letters.

        Args:
            ciphertext: The ciphertext to analyze.

        Returns:
            A 26-character substitution key string.
        """
        freqs = self.freq.letter_frequencies(ciphertext)
        # Sort cipher letters by frequency (descending)
        cipher_order = sorted(string.ascii_uppercase, key=lambda c: freqs.get(c, 0), reverse=True)
        # English letters by frequency (descending)
        english_order = sorted(string.ascii_uppercase, key=lambda c: self.freq.english_freq.get(c, 0), reverse=True)

        # Build key: key[english_pos] = cipher_letter
        key = [''] * 26
        for i, cipher_letter in enumerate(cipher_order):
            english_letter = english_order[i]
            key[ord(english_letter) - ord('A')] = cipher_letter

        return "".join(key)

    def identify_cipher_type(self, ciphertext: str) -> Dict:
        """Attempt to identify the type of cipher used.

        Uses IC, frequency analysis, and pattern analysis to classify
        the cipher type.

        Args:
            ciphertext: Encrypted text to classify.

        Returns:
            Dict with keys: 'ic', 'likely_type', 'details'.
        """
        ic_value = self.ic.calculate(ciphertext)
        chi_sq = self.freq.chi_squared(ciphertext)
        correlation = self.freq.frequency_correlation(ciphertext)

        if ic_value > 0.060:
            # IC close to English — likely monoalphabetic
            likely_type = "monoalphabetic (Caesar, substitution, or affine)"
            if abs(correlation) > 0.8:
                likely_type = "Caesar or simple substitution"
        elif ic_value > 0.045:
            likely_type = "polyalphabetic with short key (Vigenère, Beaufort)"
        elif ic_value > 0.038:
            likely_type = "polyalphabetic with long key or one-time pad"
        else:
            likely_type = "possibly transposition or very long polyalphabetic key"

        return {
            "ic": ic_value,
            "chi_squared": chi_sq,
            "correlation": correlation,
            "likely_type": likely_type,
        }


import math