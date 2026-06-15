"""Tests for Affine cipher."""

import pytest
from cryptanalysis_toolkit.ciphers.affine import AffineCipher


class TestAffineCipher:
    def test_encrypt_basic(self):
        # a=5, b=8: E(x) = (5x + 8) mod 26
        cipher = AffineCipher(a=5, b=8)
        # H=7: (5*7+8)%26 = 43%26 = 17 → R
        # E=4: (5*4+8)%26 = 28%26 = 2 → C
        # L=11: (5*11+8)%26 = 63%26 = 11 → L
        # L=11: L
        # O=14: (5*14+8)%26 = 78%26 = 0 → A
        assert cipher.encrypt("HELLO") == "RCLLA"

    def test_decrypt_basic(self):
        cipher = AffineCipher(a=5, b=8)
        assert cipher.decrypt("RCLLA") == "HELLO"

    def test_roundtrip(self):
        cipher = AffineCipher(a=7, b=3)
        text = "HELLO WORLD"
        assert cipher.decrypt(cipher.encrypt(text)) == text

    def test_all_valid_a_values(self):
        for a in AffineCipher.VALID_A_VALUES:
            cipher = AffineCipher(a=a, b=0)
            text = "TEST"
            assert cipher.decrypt(cipher.encrypt(text)) == text

    def test_invalid_a(self):
        with pytest.raises(ValueError):
            AffineCipher(a=2, b=3)  # 2 not coprime with 26

    def test_invalid_b(self):
        with pytest.raises(ValueError):
            AffineCipher(a=5, b=26)

    def test_brute_force(self):
        cipher = AffineCipher(a=5, b=8)
        plaintext = "HELLO"
        ciphertext = cipher.encrypt(plaintext)
        results = AffineCipher.brute_force(ciphertext)
        found = False
        for a, b, pt in results:
            if pt == plaintext and a == 5 and b == 8:
                found = True
        assert found

    def test_a_equals_1_is_caesar(self):
        # When a=1, affine is just a shift (Caesar) cipher
        cipher = AffineCipher(a=1, b=5)
        assert cipher.encrypt("HELLO") == "MJQQT"