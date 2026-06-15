"""Beaufort cipher — reciprocal polyalphabetic cipher."""

from __future__ import annotations


class BeaufortCipher:
    """Beaufort cipher implementation.

    A reciprocal polyalphabetic cipher: E(x) = (K - P) mod 26.
    Encryption and decryption are identical operations.

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
        """Encrypt plaintext using Beaufort cipher.

        Args:
            plaintext: The text to encrypt. Non-alpha characters pass through.

        Returns:
            Encrypted ciphertext string.
        """
        return self._process(plaintext)

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext using Beaufort cipher.

        Since Beaufort is reciprocal, decryption is the same as encryption.

        Args:
            ciphertext: The text to decrypt. Non-alpha characters pass through.

        Returns:
            Decrypted plaintext string.
        """
        return self._process(ciphertext)

    def _process(self, text: str) -> str:
        """Apply Beaufort transformation (same for encrypt and decrypt)."""
        result = []
        key_idx = 0
        for ch in text:
            if ch.isalpha():
                base = ord('A') if ch.isupper() else ord('a')
                p = ord(ch) - base
                k = ord(self.keyword[key_idx % len(self.keyword)]) - ord('A')
                transformed = (k - p) % 26
                result.append(chr(transformed + base))
                key_idx += 1
            else:
                result.append(ch)
        return "".join(result)

    def __repr__(self) -> str:
        return f"BeaufortCipher(keyword={self.keyword!r})"