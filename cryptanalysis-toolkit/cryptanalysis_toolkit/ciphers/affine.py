"""Affine cipher — E(x) = (ax + b) mod 26."""

from __future__ import annotations
import math
from typing import List, Tuple


def _extended_gcd(a: int, b: int) -> Tuple[int, int, int]:
    """Extended Euclidean algorithm.

    Returns (gcd, x, y) such that a*x + b*y = gcd(a, b).
    """
    if a == 0:
        return b, 0, 1
    gcd, x1, y1 = _extended_gcd(b % a, a)
    return gcd, y1 - (b // a) * x1, x1


def _mod_inverse(a: int, m: int) -> int:
    """Compute modular multiplicative inverse of a mod m.

    Args:
        a: The number to find the inverse of.
        m: The modulus.

    Returns:
        The modular inverse of a mod m.

    Raises:
        ValueError: If the inverse does not exist (gcd(a, m) != 1).
    """
    gcd, x, _ = _extended_gcd(a % m, m)
    if gcd != 1:
        raise ValueError(f"No modular inverse for a={a} mod {m}")
    return x % m


class AffineCipher:
    """Affine cipher implementation.

    Encrypts using E(x) = (a*x + b) mod 26.
    Decrypts using D(y) = a_inv * (y - b) mod 26.

    'a' must be coprime with 26 for the cipher to be valid.

    Args:
        a: The multiplicative key. Must be coprime with 26.
        b: The additive key (shift). Must be 0-25.

    Raises:
        ValueError: If a is not coprime with 26 or b is out of range.
    """

    VALID_A_VALUES = [1, 3, 5, 7, 9, 11, 15, 17, 19, 21, 23, 25]

    def __init__(self, a: int, b: int) -> None:
        if a not in self.VALID_A_VALUES:
            raise ValueError(
                f"a must be coprime with 26. Valid values: {self.VALID_A_VALUES}. Got {a}"
            )
        if not 0 <= b <= 25:
            raise ValueError(f"b must be 0-25, got {b}")
        self.a = a
        self.b = b
        self.a_inv = _mod_inverse(a, 26)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext using affine cipher.

        Args:
            plaintext: The text to encrypt. Non-alpha characters pass through unchanged.

        Returns:
            Encrypted ciphertext string.
        """
        result = []
        for ch in plaintext:
            if ch.isalpha():
                base = ord('A') if ch.isupper() else ord('a')
                x = ord(ch) - base
                encrypted = (self.a * x + self.b) % 26
                result.append(chr(encrypted + base))
            else:
                result.append(ch)
        return "".join(result)

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext using affine cipher.

        Args:
            ciphertext: The text to decrypt. Non-alpha characters pass through unchanged.

        Returns:
            Decrypted plaintext string.
        """
        result = []
        for ch in ciphertext:
            if ch.isalpha():
                base = ord('A') if ch.isupper() else ord('a')
                y = ord(ch) - base
                decrypted = (self.a_inv * (y - self.b)) % 26
                result.append(chr(decrypted + base))
            else:
                result.append(ch)
        return "".join(result)

    @staticmethod
    def brute_force(ciphertext: str) -> List[Tuple[int, int, str]]:
        """Return all possible decryptions for all valid (a, b) combinations.

        Args:
            ciphertext: Text encrypted with an unknown affine key.

        Returns:
            List of (a, b, plaintext) tuples for all 312 valid key combinations.
        """
        results = []
        for a in AffineCipher.VALID_A_VALUES:
            for b in range(26):
                try:
                    cipher = AffineCipher(a=a, b=b)
                    results.append((a, b, cipher.decrypt(ciphertext)))
                except ValueError:
                    continue
        return results

    def __repr__(self) -> str:
        return f"AffineCipher(a={self.a}, b={self.b})"