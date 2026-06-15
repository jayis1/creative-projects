"""Porta cipher — digraphic polyalphabetic cipher."""

from __future__ import annotations


# Porta cipher uses 13 paired alphabets
# For key letter index i (A=0...M=12), the substitution pairs are:
# A↔N, B↔O, C↔P, etc., shifted by the key letter position
_PORTA_TABLE = []
for i in range(13):
    row = {}
    for j in range(13):
        # Letters A-M map to N-Z shifted by i
        plain_upper = chr(ord('A') + j)
        cipher_upper = chr(ord('N') + (j + i) % 13)
        row[plain_upper] = cipher_upper
        row[cipher_upper] = plain_upper  # Reciprocal
    _PORTA_TABLE.append(row)


class PortaCipher:
    """Porta cipher implementation.

    A digraphic polyalphabetic cipher that pairs letters A-M with N-Z.
    The key letter determines which pairing/shift to use.
    Encryption and decryption are identical (reciprocal).

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
        """Encrypt plaintext using Porta cipher.

        Args:
            plaintext: The text to encrypt. Non-alpha characters pass through.

        Returns:
            Encrypted ciphertext string.
        """
        return self._process(plaintext)

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext using Porta cipher.

        Since Porta is reciprocal, decryption is identical to encryption.

        Args:
            ciphertext: The text to decrypt. Non-alpha characters pass through.

        Returns:
            Decrypted plaintext string.
        """
        return self._process(ciphertext)

    def _process(self, text: str) -> str:
        """Apply Porta transformation (same for encrypt and decrypt)."""
        result = []
        key_idx = 0
        for ch in text:
            if ch.isalpha():
                upper = ch.upper()
                key_shift = ord(self.keyword[key_idx % len(self.keyword)]) - ord('A')
                # Only first 13 letters (A-M) define unique rows
                row_idx = key_shift % 13
                transformed = _PORTA_TABLE[row_idx].get(upper, upper)
                result.append(transformed if ch.isupper() else transformed.lower())
                key_idx += 1
            else:
                result.append(ch)
        return "".join(result)

    def __repr__(self) -> str:
        return f"PortaCipher(keyword={self.keyword!r})"