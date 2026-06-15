"""Atbash cipher — a classic reciprocal substitution cipher."""

from __future__ import annotations
import string


class AtbashCipher:
    """Atbash cipher implementation.

    A monoalphabetic substitution cipher that maps the alphabet to its
    reverse: A↔Z, B↔Y, C↔X, etc. It is reciprocal, meaning encryption
    and decryption are identical operations. Originally used with the
    Hebrew alphabet.

    No key is needed — the mapping is always A→Z, B→Y, ..., Z→A.
    """

    # Build the Atbash mapping: A→Z, B→Y, ..., Z→A
    _MAP: dict[str, str] = {}
    for _ch in string.ascii_uppercase:
        _MAP[_ch] = chr(ord('Z') - (ord(_ch) - ord('A')))

    def __init__(self) -> None:
        pass

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext using Atbash cipher.

        Args:
            plaintext: The text to encrypt. Non-alpha characters pass through unchanged.

        Returns:
            Encrypted ciphertext string.
        """
        return self._apply_atbash(plaintext)

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext using Atbash cipher.

        Since Atbash is reciprocal, decryption is identical to encryption.

        Args:
            ciphertext: The text to decrypt. Non-alpha characters pass through unchanged.

        Returns:
            Decrypted plaintext string.
        """
        return self._apply_atbash(ciphertext)

    def _apply_atbash(self, text: str) -> str:
        """Apply Atbash transformation to text."""
        result = []
        for ch in text:
            if ch.isalpha():
                mapped = self._MAP[ch.upper()]
                result.append(mapped if ch.isupper() else mapped.lower())
            else:
                result.append(ch)
        return "".join(result)

    def __repr__(self) -> str:
        return "AtbashCipher()"