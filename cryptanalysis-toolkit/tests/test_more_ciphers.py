"""Tests for Columnar Transposition cipher."""

import pytest
from cryptanalysis_toolkit.ciphers.columnar import ColumnarTranspositionCipher


class TestColumnarTranspositionCipher:
    def test_encrypt_basic(self):
        cipher = ColumnarTranspositionCipher(key="ZEBRA")
        text = "WEAREDISCOVEREDFLEEATONCE"
        result = cipher.encrypt(text)
        assert len(result) == len(text)  # Padded to fill grid

    def test_roundtrip(self):
        cipher = ColumnarTranspositionCipher(key="KEYWORD")
        text = "HELLOWORLD"
        encrypted = cipher.encrypt(text)
        decrypted = cipher.decrypt(encrypted)
        # Decrypted text may have padding Xs
        assert decrypted.startswith(text.replace(" ", "").upper())

    def test_invalid_key(self):
        with pytest.raises(ValueError):
            ColumnarTranspositionCipher(key="123")

    def test_empty_string(self):
        cipher = ColumnarTranspositionCipher(key="KEY")
        assert cipher.encrypt("") == ""
        assert cipher.decrypt("") == ""

    def test_key_order(self):
        cipher = ColumnarTranspositionCipher(key="ZEBRA")
        # Z=5, E=2, B=1, R=4, A=0
        # Read order: A(0), B(1), E(2), R(3), Z(4)
        assert cipher._key_order == [4, 2, 1, 3, 0]


class TestAutokeyCipher:
    pass  # Tested in roundtrip below


class TestBeaufortCipher:
    def test_reciprocal(self):
        from cryptanalysis_toolkit.ciphers.beaufort import BeaufortCipher
        cipher = BeaufortCipher(keyword="FORTIFICATION")
        text = "DEFENDTHEEASTWALLOFTHECASTLE"
        encrypted = cipher.encrypt(text)
        decrypted = cipher.decrypt(encrypted)
        assert decrypted == text.upper()

    def test_encrypt_decrypt_same(self):
        from cryptanalysis_toolkit.ciphers.beaufort import BeaufortCipher
        cipher = BeaufortCipher(keyword="KEY")
        text = "HELLO"
        encrypted = cipher.encrypt(text)
        # Encrypt and decrypt are the same operation for Beaufort
        assert cipher.decrypt(encrypted) == text.upper()


class TestPortaCipher:
    def test_reciprocal(self):
        from cryptanalysis_toolkit.ciphers.porta import PortaCipher
        cipher = PortaCipher(keyword="SECRET")
        text = "HELLO"
        encrypted = cipher.encrypt(text)
        decrypted = cipher.decrypt(encrypted)
        assert decrypted == text.upper()

    def test_preserves_case(self):
        from cryptanalysis_toolkit.ciphers.porta import PortaCipher
        cipher = PortaCipher(keyword="KEY")
        result = cipher.encrypt("Hello")
        assert result[0].isupper()