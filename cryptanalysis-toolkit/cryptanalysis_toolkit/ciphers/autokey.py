"""Autokey cipher — Vigenère variant using plaintext as part of the key."""

from __future__ import annotations


class AutokeyCipher:
    """Autokey cipher implementation.

    Similar to Vigenère but appends the plaintext to the keyword,
    preventing periodic repetition that Vigenère suffers from.

    Args:
        keyword: The initial keyword. Must contain only letters.
    """

    def __init__(self, keyword: str) -> None:
        keyword = keyword.upper()
        if not keyword.isalpha():
            raise ValueError(f"Keyword must contain only letters, got {keyword!r}")
        if len(keyword) == 0:
            raise ValueError("Keyword cannot be empty")
        self.keyword = keyword

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext using autokey cipher.

        The key is the keyword followed by the plaintext itself.

        Args:
            plaintext: The text to encrypt. Non-alpha characters pass through.

        Returns:
            Encrypted ciphertext string.
        """
        result = []
        alpha_chars = [ch for ch in plaintext if ch.isalpha()]
        # Build full key: keyword + plaintext
        full_key = self.keyword + "".join(alpha_chars).upper()

        key_idx = 0
        for ch in plaintext:
            if ch.isalpha():
                base = ord('A') if ch.isupper() else ord('a')
                shift = ord(full_key[key_idx]) - ord('A')
                shifted = (ord(ch) - base + shift) % 26
                result.append(chr(shifted + base))
                key_idx += 1
            else:
                result.append(ch)
        return "".join(result)

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext using autokey cipher.

        The key is the keyword followed by the recovered plaintext.

        Args:
            ciphertext: The text to decrypt. Non-alpha characters pass through.

        Returns:
            Decrypted plaintext string.
        """
        result = []
        recovered_alpha = []  # Recovered plaintext letters feed back into key
        full_key = list(self.keyword)

        key_idx = 0
        for ch in ciphertext:
            if ch.isalpha():
                base = ord('A') if ch.isupper() else ord('a')
                # Get key character: from keyword or from recovered plaintext
                if key_idx < len(self.keyword):
                    key_char = self.keyword[key_idx]
                else:
                    key_char = recovered_alpha[key_idx - len(self.keyword)]

                shift = ord(key_char) - ord('A')
                decrypted = (ord(ch) - base - shift) % 26
                result_char = chr(decrypted + base)
                result.append(result_char)
                recovered_alpha.append(result_char.upper())
                key_idx += 1
            else:
                result.append(ch)
        return "".join(result)

    def __repr__(self) -> str:
        return f"AutokeyCipher(keyword={self.keyword!r})"