"""Monoalphabetic substitution cipher."""

from __future__ import annotations
import string
from typing import Dict, Optional


class SubstitutionCipher:
    """Monoalphabetic substitution cipher.

    Maps each letter to another letter according to a permutation of the alphabet.
    The key is a 26-character string representing the substitution for A-Z.

    Args:
        key: A 26-character string mapping A->key[0], B->key[1], etc.
             If None, identity mapping is used.

    Raises:
        ValueError: If key is not a valid 26-letter permutation of A-Z.
    """

    ALPHABET = string.ascii_uppercase

    def __init__(self, key: Optional[str] = None) -> None:
        if key is None:
            self.key = self.ALPHABET
        else:
            key = key.upper()
            if len(key) != 26:
                raise ValueError(f"Key must be exactly 26 characters, got {len(key)}")
            if set(key) != set(self.ALPHABET):
                raise ValueError("Key must be a permutation of A-Z (all 26 letters, no repeats)")
            self.key = key

        self._encrypt_map: Dict[str, str] = {
            self.ALPHABET[i]: self.key[i] for i in range(26)
        }
        self._decrypt_map: Dict[str, str] = {
            v: k for k, v in self._encrypt_map.items()
        }

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext using substitution cipher.

        Args:
            plaintext: Text to encrypt. Non-alpha characters pass through unchanged.

        Returns:
            Encrypted ciphertext string.
        """
        result = []
        for ch in plaintext:
            if ch.isalpha():
                sub = self._encrypt_map[ch.upper()]
                result.append(sub if ch.isupper() else sub.lower())
            else:
                result.append(ch)
        return "".join(result)

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext using substitution cipher.

        Args:
            ciphertext: Text to decrypt. Non-alpha characters pass through unchanged.

        Returns:
            Decrypted plaintext string.
        """
        result = []
        for ch in ciphertext:
            if ch.isalpha():
                sub = self._decrypt_map[ch.upper()]
                result.append(sub if ch.isupper() else sub.lower())
            else:
                result.append(ch)
        return "".join(result)

    @classmethod
    def from_keyword(cls, keyword: str) -> "SubstitutionCipher":
        """Create a substitution cipher from a keyword.

        The keyword (without repeated letters) is placed at the start
        of the alphabet, followed by remaining letters in order.

        Args:
            keyword: A word or phrase to derive the key from.

        Returns:
            A SubstitutionCipher instance with the derived key.

        Example:
            >>> cipher = SubstitutionCipher.from_keyword("ZEBRA")
            >>> cipher.key
            'ZEBRACDFGHIJKLMNOPQSTUVWXY'
        """
        keyword = keyword.upper()
        seen: set = set()
        key_chars: list = []
        for ch in keyword:
            if ch.isalpha() and ch not in seen:
                key_chars.append(ch)
                seen.add(ch)

        for ch in cls.ALPHABET:
            if ch not in seen:
                key_chars.append(ch)
                seen.add(ch)

        return cls(key="".join(key_chars))

    def __repr__(self) -> str:
        return f"SubstitutionCipher(key={self.key!r})"