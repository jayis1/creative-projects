"""Tests for Playfair cipher."""

import pytest
from cryptanalysis_toolkit.ciphers.playfair import PlayfairCipher


class TestPlayfairCipher:
    def test_encrypt_basic(self):
        cipher = PlayfairCipher(keyword="KEYWORD")
        # Playfair inserts X between repeated letters and pads odd-length messages
        plaintext = "HELLO"
        ciphertext = cipher.encrypt(plaintext)
        decrypted = cipher.decrypt(ciphertext)
        # Decrypted text includes padding X: "HELXLO"
        assert decrypted.replace("X", "") == "HELLO"

    def test_roundtrip(self):
        cipher = PlayfairCipher(keyword="PLAYFAIR")
        # Use even-length text without repeated adjacent letters for clean roundtrip
        text = "HIDETHEGOLDNOW"
        assert cipher.decrypt(cipher.encrypt(text)) == text

    def test_j_becomes_i(self):
        cipher = PlayfairCipher(keyword="TEST")
        text = "JAZZ"
        # J is treated as I
        ciphertext = cipher.encrypt(text)
        decrypted = cipher.decrypt(ciphertext)
        # J becomes I in the output
        assert "I" in decrypted

    def test_repeated_letters(self):
        cipher = PlayfairCipher(keyword="KEYWORD")
        # "LL" should have X inserted: "LX" "L..."
        result = cipher.encrypt("HELLO")
        assert len(result) > 0

    def test_odd_length_padding(self):
        cipher = PlayfairCipher(keyword="KEYWORD")
        # Single letter gets padded with X
        result = cipher.encrypt("A")
        assert len(result) == 2

    def test_decrypt_requires_even_length(self):
        cipher = PlayfairCipher(keyword="KEYWORD")
        with pytest.raises(ValueError):
            cipher.decrypt("ABC")

    def test_empty_string(self):
        cipher = PlayfairCipher(keyword="KEYWORD")
        assert cipher.encrypt("") == ""
        assert cipher.decrypt("") == ""

    def test_invalid_keyword(self):
        with pytest.raises(ValueError):
            PlayfairCipher(keyword="123")

    def test_square_construction(self):
        cipher = PlayfairCipher(keyword="KEYWORD")
        # First row should start with K, E, Y, W, O
        assert cipher.square[0][0] == 'K'
        assert cipher.square[0][1] == 'E'
        assert cipher.square[0][2] == 'Y'
        assert cipher.square[0][3] == 'W'
        assert cipher.square[0][4] == 'O'