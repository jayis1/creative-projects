"""Tests for ROT13 cipher."""

import pytest
from cryptanalysis_toolkit.ciphers.rot13 import ROT13Cipher


class TestROT13Cipher:
    def test_encrypt_basic(self):
        cipher = ROT13Cipher()
        assert cipher.encrypt("HELLO") == "URYYB"

    def test_decrypt_basic(self):
        cipher = ROT13Cipher()
        assert cipher.decrypt("URYYB") == "HELLO"

    def test_reciprocal(self):
        """ROT13 is its own inverse: encrypt(encrypt(x)) == x."""
        cipher = ROT13Cipher()
        text = "Hello World 123!"
        assert cipher.encrypt(cipher.encrypt(text)) == text

    def test_encrypt_decrypt_roundtrip(self):
        cipher = ROT13Cipher()
        text = "The Quick Brown Fox"
        assert cipher.decrypt(cipher.encrypt(text)) == text

    def test_preserves_nonalpha(self):
        cipher = ROT13Cipher()
        assert cipher.encrypt("Hello, World! 123") == "Uryyb, Jbeyq! 123"

    def test_preserves_case(self):
        cipher = ROT13Cipher()
        result = cipher.encrypt("HeLLo")
        assert result[0].isupper()  # H→U
        assert result[1].islower()  # e→r
        assert result[2].isupper()  # L→Y
        assert result[3].isupper()  # L→Y
        assert result[4].islower()  # o→b

    def test_empty_string(self):
        cipher = ROT13Cipher()
        assert cipher.encrypt("") == ""
        assert cipher.decrypt("") == ""

    def test_known_rot13(self):
        cipher = ROT13Cipher()
        assert cipher.encrypt("ABCDEFGHIJKLMNOPQRSTUVWXYZ") == "NOPQRSTUVWXYZABCDEFGHIJKLM"

    def test_repr(self):
        cipher = ROT13Cipher()
        assert repr(cipher) == "ROT13Cipher()"