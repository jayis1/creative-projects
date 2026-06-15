"""ROT13 cipher — a special case of Caesar cipher with shift 13."""

from __future__ import annotations


class ROT13Cipher:
    """ROT13 cipher implementation.

    A special case of the Caesar cipher where the shift is always 13.
    Since 13 is exactly half of 26, encryption and decryption are
    identical operations. ROT13 is commonly used to obscure text
    (e.g., spoiler warnings) rather than for actual security.

    No parameters are needed — ROT13 always uses shift 13.
    """

    def __init__(self) -> None:
        self._shift = 13

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext using ROT13.

        Args:
            plaintext: The text to encrypt. Non-alpha characters pass through unchanged.

        Returns:
            Encrypted ciphertext string.
        """
        return self._apply_rot13(plaintext)

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext using ROT13.

        Since ROT13 is its own inverse, decryption is identical to encryption.

        Args:
            ciphertext: The text to decrypt. Non-alpha characters pass through unchanged.

        Returns:
            Decrypted plaintext string.
        """
        return self._apply_rot13(ciphertext)

    def _apply_rot13(self, text: str) -> str:
        """Apply ROT13 transformation to text."""
        result = []
        for ch in text:
            if ch.isalpha():
                base = ord('A') if ch.isupper() else ord('a')
                shifted = (ord(ch) - base + self._shift) % 26
                result.append(chr(shifted + base))
            else:
                result.append(ch)
        return "".join(result)

    def __repr__(self) -> str:
        return "ROT13Cipher()"