"""Tests for Rail Fence cipher."""

import pytest
from cryptanalysis_toolkit.ciphers.railfence import RailFenceCipher


class TestRailFenceCipher:
    def test_encrypt_basic(self):
        cipher = RailFenceCipher(rails=3)
        # "HELLO WORLD" with 3 rails
        result = cipher.encrypt("HELLOWORLD")
        assert isinstance(result, str)

    def test_decrypt_basic(self):
        cipher = RailFenceCipher(rails=3)
        text = "HELLOWORLD"
        assert cipher.decrypt(cipher.encrypt(text)) == text

    def test_roundtrip_various_lengths(self):
        cipher = RailFenceCipher(rails=4)
        for text in ["A", "AB", "ABC", "ABCD", "HELLO", "THEQUICKBROWNFOX"]:
            assert cipher.decrypt(cipher.encrypt(text)) == text

    def test_two_rails(self):
        cipher = RailFenceCipher(rails=2)
        text = "HELLO"
        # H L O on rail 0, E L on rail 1
        encrypted = cipher.encrypt(text)
        assert len(encrypted) == len(text)

    def test_many_rails(self):
        # Rails equal to text length
        cipher = RailFenceCipher(rails=5)
        text = "ABCDE"
        result = cipher.encrypt(text)
        assert result == text  # Each char on its own rail, read in order

    def test_invalid_rails(self):
        with pytest.raises(ValueError):
            RailFenceCipher(rails=1)
        with pytest.raises(ValueError):
            RailFenceCipher(rails=0)

    def test_empty_string(self):
        cipher = RailFenceCipher(rails=3)
        assert cipher.encrypt("") == ""
        assert cipher.decrypt("") == ""

    def test_known_example(self):
        # "WEAREDISCOVEREDFLEEATONCE" with 3 rails
        cipher = RailFenceCipher(rails=3)
        text = "WEAREDISCOVEREDFLEEATONCE"
        expected = "WECRLTEERDSOEEFEAOCAIVDEN"
        assert cipher.encrypt(text) == expected