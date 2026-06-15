"""Tests for substitution cipher."""

import pytest
from cryptanalysis_toolkit.ciphers.substitution import SubstitutionCipher


class TestSubstitutionCipher:
    def test_encrypt_basic(self):
        # A→Z, B→Y, C→X, ... (Atbash-like)
        cipher = SubstitutionCipher(key="ZYXWVUTSRQPONMLKJIHGFEDCBA")
        assert cipher.encrypt("ABC") == "ZYX"

    def test_decrypt_basic(self):
        cipher = SubstitutionCipher(key="ZYXWVUTSRQPONMLKJIHGFEDCBA")
        assert cipher.decrypt("ZYX") == "ABC"

    def test_roundtrip(self):
        cipher = SubstitutionCipher(key="QWERTYUIOPASDFGHJKLZXCVBNM")
        plaintext = "HELLO WORLD"
        assert cipher.decrypt(cipher.encrypt(plaintext)) == plaintext

    def test_preserves_case(self):
        cipher = SubstitutionCipher(key="ZYXWVUTSRQPONMLKJIHGFEDCBA")
        result = cipher.encrypt("Hello")
        assert result[0].isupper()
        assert result[1:].islower()

    def test_preserves_nonalpha(self):
        cipher = SubstitutionCipher(key="ZYXWVUTSRQPONMLKJIHGFEDCBA")
        assert cipher.encrypt("A, B! 1") == "Z, Y! 1"

    def test_from_keyword(self):
        cipher = SubstitutionCipher.from_keyword("ZEBRA")
        assert cipher.key == "ZEBRACDFGHIJKLMNOPQSTUVWXY"
        # Z maps to A, E maps to B in the plaintext → should encrypt correctly
        assert cipher.decrypt(cipher.encrypt("TEST")) == "TEST"

    def test_from_keyword_dedup(self):
        cipher = SubstitutionCipher.from_keyword("HELLO")
        # H, E, L, O → then remaining alphabet
        assert len(cipher.key) == 26
        assert set(cipher.key) == set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    def test_identity_key(self):
        cipher = SubstitutionCipher()
        assert cipher.encrypt("HELLO") == "HELLO"

    def test_invalid_key_length(self):
        with pytest.raises(ValueError):
            SubstitutionCipher(key="SHORT")

    def test_invalid_key_repeats(self):
        with pytest.raises(ValueError):
            SubstitutionCipher(key="AABCDEFHIJKLMNOPQRSTUVWXYZ")

    def test_empty_string(self):
        cipher = SubstitutionCipher(key="ZYXWVUTSRQPONMLKJIHGFEDCBA")
        assert cipher.encrypt("") == ""
        assert cipher.decrypt("") == ""