"""Tests for Hill cipher."""

import pytest
from cryptanalysis_toolkit.ciphers.hill import (
    HillCipher,
    _matrix_determinant,
    _matrix_inverse,
    _mod_inverse_det,
    _validate_key_matrix,
)


class TestHillCipher:
    def test_encrypt_basic(self):
        """Classic Hill cipher example: ACT → POH with the standard 3×3 key."""
        cipher = HillCipher(key_matrix=[[6, 24, 1], [13, 16, 10], [20, 17, 15]])
        result = cipher.encrypt("ACT")
        assert result == "POH"

    def test_decrypt_basic(self):
        cipher = HillCipher(key_matrix=[[6, 24, 1], [13, 16, 10], [20, 17, 15]])
        result = cipher.decrypt("POH")
        assert result == "ACT"

    def test_roundtrip(self):
        cipher = HillCipher(key_matrix=[[6, 24, 1], [13, 16, 10], [20, 17, 15]])
        plaintext = "HELLOWORLD"
        decrypted = cipher.decrypt(cipher.encrypt(plaintext))
        # Decryption includes padding Xs (length must be multiple of n=3)
        assert decrypted.startswith(plaintext)

    def test_2x2_matrix(self):
        """Test with a 2×2 key matrix."""
        # Key [[3, 3], [2, 5]], det = 9 mod 26
        cipher = HillCipher(key_matrix=[[3, 3], [2, 5]])
        plaintext = "HELP"
        encrypted = cipher.encrypt(plaintext)
        decrypted = cipher.decrypt(encrypted)
        assert decrypted == plaintext

    def test_padding(self):
        """Text shorter than matrix size should be padded with X."""
        cipher = HillCipher(key_matrix=[[6, 24, 1], [13, 16, 10], [20, 17, 15]])
        result = cipher.encrypt("AB")
        # Should pad to "ABX" and encrypt
        assert len(result) == 3

    def test_empty_string(self):
        cipher = HillCipher(key_matrix=[[6, 24, 1], [13, 16, 10], [20, 17, 15]])
        assert cipher.encrypt("") == ""
        assert cipher.decrypt("") == ""

    def test_non_invertible_matrix_raises(self):
        """Matrix with determinant 0 mod 26 should raise ValueError."""
        with pytest.raises(ValueError, match="not invertible"):
            HillCipher(key_matrix=[[1, 0], [0, 0]])

    def test_non_square_matrix_raises(self):
        with pytest.raises(ValueError, match="square"):
            HillCipher(key_matrix=[[1, 2, 3]])

    def test_invalid_matrix_entries_raises(self):
        with pytest.raises(ValueError, match="0-25"):
            HillCipher(key_matrix=[[26, 0], [0, 1]])

    def test_repr(self):
        cipher = HillCipher(key_matrix=[[6, 24, 1], [13, 16, 10], [20, 17, 15]])
        assert repr(cipher) == "HillCipher(n=3)"


class TestMatrixUtils:
    def test_determinant_2x2(self):
        m = [[3, 3], [2, 5]]
        assert _matrix_determinant(m, 26) == (3 * 5 - 3 * 2) % 26

    def test_determinant_3x3(self):
        m = [[6, 24, 1], [13, 16, 10], [20, 17, 15]]
        det = _matrix_determinant(m, 26)
        # Should be coprime with 26
        assert det != 0

    def test_matrix_inverse_roundtrip(self):
        """A * A_inv should equal identity mod 26."""
        m = [[6, 24, 1], [13, 16, 10], [20, 17, 15]]
        inv = _matrix_inverse(m, 26)
        # Verify A * A_inv ≡ I (mod 26)
        for i in range(3):
            for j in range(3):
                val = sum(m[i][k] * inv[k][j] for k in range(3)) % 26
                if i == j:
                    assert val == 1, f"Diagonal ({i},{j}): expected 1, got {val}"
                else:
                    assert val == 0, f"Off-diagonal ({i},{j}): expected 0, got {val}"

    def test_mod_inverse_det(self):
        assert _mod_inverse_det(1, 26) == 1
        assert (_mod_inverse_det(3, 26) * 3) % 26 == 1

    def test_validate_key_matrix_valid(self):
        _validate_key_matrix([[6, 24, 1], [13, 16, 10], [20, 17, 15]])

    def test_validate_key_matrix_invalid_det(self):
        with pytest.raises(ValueError):
            _validate_key_matrix([[1, 1], [1, 1]])