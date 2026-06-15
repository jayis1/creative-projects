"""Tests for Caesar cipher."""

import pytest
from cryptanalysis_toolkit.ciphers.caesar import CaesarCipher


class TestCaesarCipher:
    def test_encrypt_basic(self):
        cipher = CaesarCipher(shift=3)
        assert cipher.encrypt("HELLO") == "KHOOR"

    def test_decrypt_basic(self):
        cipher = CaesarCipher(shift=3)
        assert cipher.decrypt("KHOOR") == "HELLO"

    def test_roundtrip(self):
        cipher = CaesarCipher(shift=7)
        plaintext = "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG"
        assert cipher.decrypt(cipher.encrypt(plaintext)) == plaintext

    def test_preserves_case(self):
        cipher = CaesarCipher(shift=5)
        assert cipher.encrypt("Hello World") == "Mjqqt Btwqi"

    def test_preserves_nonalpha(self):
        cipher = CaesarCipher(shift=3)
        assert cipher.encrypt("HELLO, WORLD! 123") == "KHOOR, ZRUOG! 123"

    def test_shift_0(self):
        cipher = CaesarCipher(shift=0)
        assert cipher.encrypt("HELLO") == "HELLO"

    def test_shift_26_is_identity(self):
        # Shift 26 should work same as shift 0
        # But constructor only allows 0-25, so test shift=0
        cipher = CaesarCipher(shift=0)
        assert cipher.encrypt("TEST") == "TEST"

    def test_invalid_shift(self):
        with pytest.raises(ValueError):
            CaesarCipher(shift=26)
        with pytest.raises(ValueError):
            CaesarCipher(shift=-1)

    def test_brute_force(self):
        cipher = CaesarCipher(shift=3)
        ciphertext = cipher.encrypt("HELLO WORLD")
        results = CaesarCipher.brute_force(ciphertext)
        assert len(results) == 26
        # One of the results should be the original plaintext
        assert "HELLO WORLD" in results

    def test_brute_force_finds_correct_shift(self):
        cipher = CaesarCipher(shift=13)
        plaintext = "ATTACK AT DAWN"
        ciphertext = cipher.encrypt(plaintext)
        results = CaesarCipher.brute_force(ciphertext)
        assert plaintext in results

    def test_empty_string(self):
        cipher = CaesarCipher(shift=5)
        assert cipher.encrypt("") == ""
        assert cipher.decrypt("") == ""

    def test_lowercase_roundtrip(self):
        cipher = CaesarCipher(shift=10)
        text = "hello world"
        assert cipher.decrypt(cipher.encrypt(text)) == text