"""Rail fence cipher — transposition using zigzag rails."""

from __future__ import annotations


class RailFenceCipher:
    """Rail fence cipher implementation.

    Writes text in a zigzag pattern across N rails, then reads off row by row.

    Args:
        rails: Number of rails (must be >= 2).

    Raises:
        ValueError: If rails < 2.
    """

    def __init__(self, rails: int = 3) -> None:
        if rails < 2:
            raise ValueError(f"Number of rails must be >= 2, got {rails}")
        self.rails = rails

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext using rail fence cipher.

        Args:
            plaintext: The text to encrypt.

        Returns:
            Encrypted ciphertext string.
        """
        if not plaintext:
            return ""

        fence = [[] for _ in range(self.rails)]
        rail = 0
        direction = 1

        for ch in plaintext:
            fence[rail].append(ch)
            if rail == 0:
                direction = 1
            elif rail == self.rails - 1:
                direction = -1
            rail += direction

        return "".join("".join(row) for row in fence)

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext using rail fence cipher.

        Args:
            ciphertext: The text to decrypt.

        Returns:
            Decrypted plaintext string.
        """
        if not ciphertext:
            return ""

        n = len(ciphertext)
        # Calculate the length of each rail
        pattern = self._rail_pattern(n)
        rail_lengths = [0] * self.rails
        for r in pattern:
            rail_lengths[r] += 1

        # Fill rails with ciphertext characters
        fence = []
        idx = 0
        for rail_idx in range(self.rails):
            length = rail_lengths[rail_idx]
            fence.append(list(ciphertext[idx:idx + length]))
            idx += length

        # Read off in zigzag order
        result = []
        rail_indices = [0] * self.rails
        for r in pattern:
            result.append(fence[r][rail_indices[r]])
            rail_indices[r] += 1

        return "".join(result)

    def _rail_pattern(self, length: int) -> list:
        """Generate the rail assignment pattern for each character position."""
        pattern = []
        rail = 0
        direction = 1
        for _ in range(length):
            pattern.append(rail)
            if rail == 0:
                direction = 1
            elif rail == self.rails - 1:
                direction = -1
            rail += direction
        return pattern

    def __repr__(self) -> str:
        return f"RailFenceCipher(rails={self.rails})"