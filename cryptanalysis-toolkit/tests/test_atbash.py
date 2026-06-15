"""Tests for Atbash cipher."""

import pytest
from cryptanalysis_toolkit.ciphers.atbash import AtbashCipher


class TestAtbashCipher:
    def test_encrypt_basic(self):
        cipher = AtbashCipher()
        assert cipher.encrypt("HELLO") == "SVOOL"

    def test_decrypt_basic(self):
        cipher = AtbashCipher()
        assert cipher.decrypt("SVOOL") == "HELLO"

    def test_reciprocal(self):
        """Atbash is its own inverse: encrypt(encrypt(x)) == x."""
        cipher = AtbashCipher()
        text = "Test Message"
        assert cipher.encrypt(cipher.encrypt(text)) == text

    def test_roundtrip(self):
        cipher = AtbashCipher()
        text = "The Quick Brown Fox"
        assert cipher.decrypt(cipher.encrypt(text)) == text

    def test_a_to_z(self):
        cipher = AtbashCipher()
        assert cipher.encrypt("A") == "Z"
        assert cipher.encrypt("Z") == "A"
        assert cipher.encrypt("M") == "N"
        assert cipher.encrypt("N") == "M"

    def test_full_alphabet(self):
        cipher = AtbashCipher()
        result = cipher.encrypt("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        assert result == "ZYXWVUTSRQPONMLKJIHGFEDCBA"

    def test_preserves_nonalpha(self):
        cipher = AtbashCipher()
        assert cipher.encrypt("Hello, World! 123") == "Svool, Dliow! 123"

    def test_preserves_case(self):
        cipher = AtbashCipher()
        result = cipher.encrypt("HeLLo")
        assert result[0].isupper()
        assert result[1].islower()

    def test_empty_string(self):
        cipher = AtbashCipher()
        assert cipher.encrypt("") == ""
        assert cipher.decrypt("") == ""

    def test_repr(self):
        cipher = AtbashCipher()
        assert repr(cipher) == "AtbashCipher()"