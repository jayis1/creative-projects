"""Playfair cipher — digraph substitution using a 5x5 key square."""

from __future__ import annotations
import string


class PlayfairCipher:
    """Playfair cipher implementation.

    Encrypts/decrypts pairs of letters (digraphs) using a 5x5 key square.
    J is merged with I (standard convention).

    Args:
        keyword: The keyword to build the key square from.

    Raises:
        ValueError: If keyword contains no letters.
    """

    def __init__(self, keyword: str) -> None:
        keyword = keyword.upper().replace("J", "I")
        if not any(ch.isalpha() for ch in keyword):
            raise ValueError("Keyword must contain at least one letter")

        # Build 5x5 key square
        seen: set = set()
        key_chars: list = []
        for ch in keyword:
            if ch.isalpha() and ch not in seen:
                key_chars.append(ch)
                seen.add(ch)

        # Fill remaining letters (J excluded)
        for ch in string.ascii_uppercase:
            if ch != "J" and ch not in seen:
                key_chars.append(ch)
                seen.add(ch)

        self.square: list = [key_chars[i:i + 5] for i in range(0, 25, 5)]
        # Build position lookup
        self._pos: dict = {}
        for row_idx, row in enumerate(self.square):
            for col_idx, ch in enumerate(row):
                self._pos[ch] = (row_idx, col_idx)

    def _prepare_text(self, text: str) -> list:
        """Prepare text into digraphs, inserting X between repeated letters
        and padding with X if needed."""
        text = text.upper().replace("J", "I")
        text = "".join(ch for ch in text if ch.isalpha())

        digraphs = []
        i = 0
        while i < len(text):
            a = text[i]
            if i + 1 < len(text):
                b = text[i + 1]
                if a == b:
                    digraphs.append((a, "X"))
                    i += 1
                else:
                    digraphs.append((a, b))
                    i += 2
            else:
                digraphs.append((a, "X"))
                i += 1
        return digraphs

    def _process_digraph(self, a: str, b: str, encrypt: bool) -> tuple:
        """Process a single digraph according to Playfair rules."""
        r1, c1 = self._pos[a]
        r2, c2 = self._pos[b]

        if r1 == r2:
            # Same row: shift right (encrypt) or left (decrypt)
            shift = 1 if encrypt else -1
            return (
                self.square[r1][(c1 + shift) % 5],
                self.square[r2][(c2 + shift) % 5],
            )
        elif c1 == c2:
            # Same column: shift down (encrypt) or up (decrypt)
            shift = 1 if encrypt else -1
            return (
                self.square[(r1 + shift) % 5][c1],
                self.square[(r2 + shift) % 5][c2],
            )
        else:
            # Rectangle: swap columns
            return (
                self.square[r1][c2],
                self.square[r2][c1],
            )

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext using Playfair cipher.

        Args:
            plaintext: The text to encrypt. Only letters are processed; J→I.

        Returns:
            Encrypted ciphertext string (uppercase, no spaces).
        """
        digraphs = self._prepare_text(plaintext)
        result = []
        for a, b in digraphs:
            ca, cb = self._process_digraph(a, b, encrypt=True)
            result.append(ca)
            result.append(cb)
        return "".join(result)

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext using Playfair cipher.

        Args:
            ciphertext: The text to decrypt. Only letters are processed; J→I.

        Returns:
            Decrypted plaintext string (uppercase, may contain padding Xs).
        """
        text = ciphertext.upper().replace("J", "I")
        text = "".join(ch for ch in text if ch.isalpha())

        if len(text) % 2 != 0:
            raise ValueError("Ciphertext length must be even for Playfair decryption")

        digraphs = []
        for i in range(0, len(text), 2):
            digraphs.append((text[i], text[i + 1]))

        result = []
        for a, b in digraphs:
            da, db = self._process_digraph(a, b, encrypt=False)
            result.append(da)
            result.append(db)
        return "".join(result)

    def __repr__(self) -> str:
        return f"PlayfairCipher(keyword={self.square[0][0]}...)"