"""Columnar transposition cipher."""

from __future__ import annotations
import math


class ColumnarTranspositionCipher:
    """Columnar transposition cipher implementation.

    Writes plaintext into rows under a keyword, then reads off columns
    in alphabetical order of the keyword letters.

    Args:
        key: The keyword determining column order. Must be non-empty with unique
             letter ordering (duplicates get sequential positions).

    Raises:
        ValueError: If key is empty or contains no letters.
    """

    def __init__(self, key: str) -> None:
        key = key.upper()
        key = "".join(ch for ch in key if ch.isalpha())
        if not key:
            raise ValueError("Key must contain at least one letter")
        self.key = key
        self._key_order = self._compute_key_order(key)

    @staticmethod
    def _compute_key_order(key: str) -> list:
        """Compute the column read order from the keyword.

        Columns are ordered by the alphabetical position of each keyword letter.
        Tied letters get sequential positions (left to right).
        """
        order = [0] * len(key)
        sorted_indices = sorted(range(len(key)), key=lambda i: (key[i], i))
        for rank, idx in enumerate(sorted_indices):
            order[idx] = rank
        return order

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext using columnar transposition.

        Args:
            plaintext: The text to encrypt. Only letters are processed.

        Returns:
            Encrypted ciphertext string (uppercase).
        """
        text = "".join(ch for ch in plaintext.upper() if ch.isalpha())
        if not text:
            return ""

        ncols = len(self.key)
        nrows = math.ceil(len(text) / ncols)
        # Pad with X to fill the grid
        padded = text.ljust(nrows * ncols, 'X')

        # Write into grid row by row
        grid = []
        for r in range(nrows):
            row = list(padded[r * ncols:(r + 1) * ncols])
            grid.append(row)

        # Read columns in key order
        result = []
        for col in range(ncols):
            key_col = self._key_order.index(col)
            for r in range(nrows):
                result.append(grid[r][key_col])

        return "".join(result)

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext using columnar transposition.

        Args:
            ciphertext: The text to decrypt (letters only).

        Returns:
            Decrypted plaintext string (may contain padding Xs at the end).
        """
        text = "".join(ch for ch in ciphertext.upper() if ch.isalpha())
        if not text:
            return ""

        ncols = len(self.key)
        nrows = math.ceil(len(text) / ncols)
        # How many characters in the last (possibly short) row
        full_cols = len(text) % ncols
        if full_cols == 0:
            full_cols = ncols

        # Build column lengths: columns read first have nrows chars,
        # columns read last may have nrows-1 chars
        col_lengths = []
        for col in range(ncols):
            key_col = self._key_order.index(col)
            if key_col < full_cols:
                col_lengths.append(nrows)
            else:
                col_lengths.append(nrows - 1)

        # Fill columns from ciphertext
        idx = 0
        grid = [[''] * ncols for _ in range(nrows)]
        for col in range(ncols):
            key_col = self._key_order.index(col)
            length = col_lengths[col]
            col_chars = text[idx:idx + length]
            for r, ch in enumerate(col_chars):
                grid[r][key_col] = ch
            idx += length

        # Read row by row
        result = []
        for r in range(nrows):
            for c in range(ncols):
                if grid[r][c]:
                    result.append(grid[r][c])

        return "".join(result)

    def __repr__(self) -> str:
        return f"ColumnarTranspositionCipher(key={self.key!r})"