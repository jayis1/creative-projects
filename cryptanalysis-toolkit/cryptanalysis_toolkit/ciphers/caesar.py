"""Caesar cipher — shift each letter by a fixed amount."""

from __future__ import annotations
from typing import List


class CaesarCipher:
    """Implementation of the Caesar (shift) cipher.

    Each letter in the plaintext is shifted by a fixed number of positions
    in the alphabet. The classic Caesar cipher uses a shift of 3.

    Args:
        shift: Number of positions to shift (0-25). Default is 3 (classic Caesar).
    """

    ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    def __init__(self, shift: int = 3) -> None:
        if not 0 <= shift <= 25:
            raise ValueError(f"Shift must be 0-25, got {shift}")
        self.shift = shift % 26

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext using Caesar cipher.

        Args:
            plaintext: The text to encrypt. Non-alpha characters pass through unchanged.

        Returns:
            Encrypted ciphertext string.
        """
        result = []
        for ch in plaintext:
            if ch.isalpha():
                base = ord('A') if ch.isupper() else ord('a')
                shifted = (ord(ch) - base + self.shift) % 26
                result.append(chr(shifted + base))
            else:
                result.append(ch)
        return "".join(result)

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext using Caesar cipher.

        Args:
            ciphertext: The text to decrypt. Non-alpha characters pass through unchanged.

        Returns:
            Decrypted plaintext string.
        """
        if self.shift == 0:
            return ciphertext
        result = []
        for ch in ciphertext:
            if ch.isalpha():
                base = ord('A') if ch.isupper() else ord('a')
                shifted = (ord(ch) - base - self.shift) % 26
                result.append(chr(shifted + base))
            else:
                result.append(ch)
        return "".join(result)

    @staticmethod
    def brute_force(ciphertext: str) -> List[str]:
        """Return all 26 possible decryptions of a Caesar ciphertext.

        Args:
            ciphertext: Text encrypted with an unknown Caesar shift.

        Returns:
            List of 26 possible plaintexts, one for each shift value.
        """
        return [CaesarCipher(shift=i).decrypt(ciphertext) for i in range(26)]

    def __repr__(self) -> str:
        return f"CaesarCipher(shift={self.shift})"