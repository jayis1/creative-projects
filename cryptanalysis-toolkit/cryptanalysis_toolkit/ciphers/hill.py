"""Hill cipher — matrix-based polygraphic substitution cipher."""

from __future__ import annotations
import math
import string
from typing import List, Optional


def _matrix_multiply(a: List[List[int]], b: List[List[int]], mod: int) -> List[List[int]]:
    """Multiply two matrices modulo mod.

    Args:
        a: First matrix (m x n).
        b: Second matrix (n x p).
        mod: Modulus for all operations.

    Returns:
        Product matrix (m x p) with all entries mod mod.
    """
    rows_a, cols_a = len(a), len(a[0])
    cols_b = len(b[0])
    result = [[0] * cols_b for _ in range(rows_a)]
    for i in range(rows_a):
        for j in range(cols_b):
            total = 0
            for k in range(cols_a):
                total += a[i][k] * b[k][j]
            result[i][j] = total % mod
    return result


def _matrix_determinant(matrix: List[List[int]], mod: int) -> int:
    """Compute determinant of an n×n matrix modulo mod.

    Args:
        matrix: Square matrix.
        mod: Modulus.

    Returns:
        Determinant modulo mod.
    """
    n = len(matrix)
    if n == 1:
        return matrix[0][0] % mod
    if n == 2:
        return (matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]) % mod

    det = 0
    for j in range(n):
        # Build minor matrix by removing row 0 and column j
        minor = []
        for i in range(1, n):
            row = []
            for k in range(n):
                if k != j:
                    row.append(matrix[i][k])
            minor.append(row)
        cofactor = matrix[0][j] * _matrix_determinant(minor, mod)
        if j % 2 == 0:
            det += cofactor
        else:
            det -= cofactor
    return det % mod


def _matrix_adjugate(matrix: List[List[int]], mod: int) -> List[List[int]]:
    """Compute the adjugate (classical adjoint) of a matrix modulo mod.

    Args:
        matrix: Square matrix.
        mod: Modulus.

    Returns:
        Adjugate matrix with entries modulo mod.
    """
    n = len(matrix)
    if n == 1:
        return [[1]]

    adjugate = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            # Build minor by removing row i and column j
            minor = []
            for r in range(n):
                if r != i:
                    row = []
                    for c in range(n):
                        if c != j:
                            row.append(matrix[r][c])
                    minor.append(row)
            cofactor = _matrix_determinant(minor, mod)
            sign = 1 if (i + j) % 2 == 0 else -1
            adjugate[j][i] = (sign * cofactor) % mod  # Note: transposed

    return adjugate


def _mod_inverse_det(det: int, mod: int) -> int:
    """Compute the modular inverse of determinant using extended Euclidean algorithm.

    Args:
        det: Determinant value (already mod mod).
        mod: Modulus.

    Returns:
        Modular inverse of det mod mod.

    Raises:
        ValueError: If inverse does not exist (det and mod not coprime).
    """
    def extended_gcd(a: int, b: int) -> tuple:
        if a == 0:
            return b, 0, 1
        gcd, x1, y1 = extended_gcd(b % a, a)
        return gcd, y1 - (b // a) * x1, x1

    gcd, x, _ = extended_gcd(det % mod, mod)
    if gcd != 1:
        raise ValueError(
            f"Key matrix is not invertible modulo {mod} "
            f"(determinant={det}, gcd with {mod} is {gcd}). "
            "Choose a key matrix with a determinant coprime to 26."
        )
    return x % mod


def _matrix_inverse(matrix: List[List[int]], mod: int) -> List[List[int]]:
    """Compute the modular inverse of a matrix.

    Args:
        matrix: Square invertible matrix.
        mod: Modulus.

    Returns:
        Inverse matrix modulo mod.

    Raises:
        ValueError: If matrix is not invertible modulo mod.
    """
    det = _matrix_determinant(matrix, mod)
    if det % mod == 0:
        raise ValueError(
            f"Key matrix determinant is 0 modulo {mod}. "
            "Matrix is not invertible."
        )

    det_inv = _mod_inverse_det(det, mod)
    adjugate = _matrix_adjugate(matrix, mod)

    n = len(matrix)
    inverse = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            inverse[i][j] = (det_inv * adjugate[i][j]) % mod

    return inverse


def _validate_key_matrix(matrix: List[List[int]], mod: int = 26) -> None:
    """Validate that a key matrix is suitable for the Hill cipher.

    Args:
        matrix: Key matrix to validate.
        mod: Modulus (default 26 for English alphabet).

    Raises:
        ValueError: If the matrix is not square, not invertible, or has
                   invalid entries.
    """
    n = len(matrix)
    if n == 0:
        raise ValueError("Key matrix cannot be empty")
    for row in matrix:
        if len(row) != n:
            raise ValueError(f"Key matrix must be square, got {n}×{len(row)}")
        for val in row:
            if val < 0 or val >= mod:
                raise ValueError(
                    f"Matrix entries must be 0-{mod-1}, got {val}"
                )

    det = _matrix_determinant(matrix, mod)
    try:
        _mod_inverse_det(det, mod)
    except ValueError as e:
        raise ValueError(str(e))


class HillCipher:
    """Hill cipher implementation.

    A polygraphic substitution cipher that uses linear algebra (matrix
    multiplication) to perform substitution. Invented by Lester S. Hill
    in 1929, it was the first polygraphic cipher to operate on more than
    three symbols at once.

    The key is an n×n invertible matrix over Z_26. Text is divided into
    n-letter blocks; each block is multiplied by the key matrix to
    produce the ciphertext block.

    Args:
        key_matrix: A list of lists representing the n×n key matrix.
            Each entry must be 0-25, and the matrix must be invertible
            modulo 26 (determinant coprime with 26).

    Raises:
        ValueError: If key_matrix is not square, not invertible mod 26,
                   or contains invalid entries.

    Example:
        >>> cipher = HillCipher(key_matrix=[[6, 24, 1], [13, 16, 10], [20, 17, 15]])
        >>> cipher.encrypt("ACT")
        'POH'
    """

    MOD = 26

    def __init__(self, key_matrix: List[List[int]]) -> None:
        _validate_key_matrix(key_matrix, self.MOD)
        self.key_matrix = key_matrix
        self.n = len(key_matrix)
        self._inverse_matrix = _matrix_inverse(key_matrix, self.MOD)

    def _text_to_vectors(self, text: str) -> List[List[int]]:
        """Convert text to column vectors of length n.

        Pads with 'X' if necessary.
        """
        text = "".join(ch for ch in text.upper() if ch.isalpha())
        # Pad with X to make length divisible by n
        while len(text) % self.n != 0:
            text += "X"

        vectors = []
        for i in range(0, len(text), self.n):
            block = text[i:i + self.n]
            vectors.append([ord(ch) - ord('A') for ch in block])
        return vectors

    def _vectors_to_text(self, vectors: List[List[int]]) -> str:
        """Convert column vectors back to text."""
        chars = []
        for vec in vectors:
            for val in vec:
                chars.append(chr(val + ord('A')))
        return "".join(chars)

    def _encrypt_block(self, vector: List[int]) -> List[int]:
        """Encrypt a single block vector using the key matrix."""
        # Multiply key_matrix × vector mod 26
        result = []
        for i in range(self.n):
            total = sum(self.key_matrix[i][j] * vector[j] for j in range(self.n))
            result.append(total % self.MOD)
        return result

    def _decrypt_block(self, vector: List[int]) -> List[int]:
        """Decrypt a single block vector using the inverse key matrix."""
        result = []
        for i in range(self.n):
            total = sum(self._inverse_matrix[i][j] * vector[j] for j in range(self.n))
            result.append(total % self.MOD)
        return result

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext using Hill cipher.

        Args:
            plaintext: The text to encrypt. Only letters are processed.
                Text is padded with 'X' if length is not a multiple of
                the matrix size.

        Returns:
            Encrypted ciphertext string (uppercase).
        """
        alpha_chars = [ch for ch in plaintext if ch.isalpha()]
        if not alpha_chars:
            return ""

        vectors = self._text_to_vectors(plaintext)
        encrypted_vectors = [self._encrypt_block(v) for v in vectors]
        return self._vectors_to_text(encrypted_vectors)

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext using Hill cipher.

        Args:
            ciphertext: The text to decrypt. Only letters are processed.

        Returns:
            Decrypted plaintext string (uppercase, may contain padding Xs).
        """
        alpha_chars = [ch for ch in ciphertext if ch.isalpha()]
        if not alpha_chars:
            return ""

        vectors = self._text_to_vectors(ciphertext)
        decrypted_vectors = [self._decrypt_block(v) for v in vectors]
        return self._vectors_to_text(decrypted_vectors)

    def __repr__(self) -> str:
        return f"HillCipher(n={self.n})"