"""Vigenère cipher — polyalphabetic substitution using a keyword."""

from __future__ import annotations
from typing import List


class VigenereCipher:
    """Vigenère cipher implementation.

    A polyalphabetic cipher that uses a keyword to determine different
    shift values for each letter position.

    Args:
        keyword: The encryption/decryption keyword. Must contain only letters.
    """

    def __init__(self, keyword: str) -> None:
        keyword = keyword.upper()
        if not keyword.isalpha():
            raise ValueError(f"Keyword must contain only letters, got {keyword!r}")
        if len(keyword) == 0:
            raise ValueError("Keyword cannot be empty")
        self.keyword = keyword

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext using Vigenère cipher.

        Args:
            plaintext: The text to encrypt. Non-alpha characters pass through unchanged.

        Returns:
            Encrypted ciphertext string.
        """
        result = []
        key_idx = 0
        for ch in plaintext:
            if ch.isalpha():
                base = ord('A') if ch.isupper() else ord('a')
                shift = ord(self.keyword[key_idx % len(self.keyword)]) - ord('A')
                shifted = (ord(ch) - base + shift) % 26
                result.append(chr(shifted + base))
                key_idx += 1
            else:
                result.append(ch)
        return "".join(result)

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext using Vigenère cipher.

        Args:
            ciphertext: The text to decrypt. Non-alpha characters pass through unchanged.

        Returns:
            Decrypted plaintext string.
        """
        result = []
        key_idx = 0
        for ch in ciphertext:
            if ch.isalpha():
                base = ord('A') if ch.isupper() else ord('a')
                shift = ord(self.keyword[key_idx % len(self.keyword)]) - ord('A')
                shifted = (ord(ch) - base - shift) % 26
                result.append(chr(shifted + base))
                key_idx += 1
            else:
                result.append(ch)
        return "".join(result)

    @staticmethod
    def keyword_to_shifts(keyword: str) -> List[int]:
        """Convert a keyword to a list of shift values.

        Args:
            keyword: The keyword to convert.

        Returns:
            List of integer shift values (A=0, B=1, ..., Z=25).
        """
        return [ord(ch.upper()) - ord('A') for ch in keyword if ch.isalpha()]

    def __repr__(self) -> str:
        return f"VigenereCipher(keyword={self.keyword!r})"