"""Tests for Vigenère cipher."""

import pytest
from cryptanalysis_toolkit.ciphers.vigenere import VigenereCipher


class TestVigenereCipher:
    def test_encrypt_basic(self):
        cipher = VigenereCipher(keyword="KEY")
        # K=10, E=4, Y=24
        # H(7)+10=17=R, E(4)+4=8=I, L(11)+24=9=J, L(11)+10=21=V, O(14)+4=18=S
        assert cipher.encrypt("HELLO") == "RIJVS"

    def test_decrypt_basic(self):
        cipher = VigenereCipher(keyword="KEY")
        assert cipher.decrypt("RIJVS") == "HELLO"

    def test_roundtrip(self):
        cipher = VigenereCipher(keyword="SECRET")
        text = "THE QUICK BROWN FOX"
        assert cipher.decrypt(cipher.encrypt(text)) == text

    def test_preserves_case(self):
        cipher = VigenereCipher(keyword="KEY")
        result = cipher.encrypt("Hello World")
        assert result[0].isupper()

    def test_preserves_nonalpha(self):
        cipher = VigenereCipher(keyword="KEY")
        result = cipher.encrypt("HELLO, WORLD!")
        assert "," in result
        assert "!" in result

    def test_single_letter_keyword(self):
        cipher = VigenereCipher(keyword="A")
        assert cipher.encrypt("HELLO") == "HELLO"

    def test_invalid_keyword(self):
        with pytest.raises(ValueError):
            VigenereCipher(keyword="K2Y")
        with pytest.raises(ValueError):
            VigenereCipher(keyword="")

    def test_keyword_to_shifts(self):
        shifts = VigenereCipher.keyword_to_shifts("ABC")
        assert shifts == [0, 1, 2]

    def test_long_text(self):
        cipher = VigenereCipher(keyword="LEMON")
        plaintext = "ATTACK AT DAWN"
        ciphertext = cipher.encrypt(plaintext)
        assert cipher.decrypt(ciphertext) == plaintext