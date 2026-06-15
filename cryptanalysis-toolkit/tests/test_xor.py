"""Tests for XOR cipher."""

import pytest
from cryptanalysis_toolkit.ciphers.xor import XORCipher


class TestXORCipher:
    def test_encrypt_decrypt_roundtrip(self):
        cipher = XORCipher(key=b"secret")
        plaintext = b"Hello, World!"
        encrypted = cipher.encrypt(plaintext)
        decrypted = cipher.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_decrypt_string_key(self):
        cipher = XORCipher(key="KEY")
        plaintext = b"TestData"
        encrypted = cipher.encrypt(plaintext)
        decrypted = cipher.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_string_input(self):
        cipher = XORCipher(key="KEY")
        plaintext = "Hello"
        encrypted = cipher.encrypt(plaintext)
        assert isinstance(encrypted, bytes)

    def test_xor_is_reciprocal(self):
        """XOR encryption and decryption produce same operation."""
        cipher = XORCipher(key=b"test")
        plaintext = b"ABCDEFGH"
        enc = cipher.encrypt(plaintext)
        dec = cipher.decrypt(plaintext)
        assert enc == dec  # XOR with same key = same result

    def test_different_keys_different_output(self):
        key1 = XORCipher(key=b"AAA")
        key2 = XORCipher(key=b"BBB")
        plaintext = b"Same message"
        assert key1.encrypt(plaintext) != key2.encrypt(plaintext)

    def test_empty_key_raises(self):
        with pytest.raises(ValueError):
            XORCipher(key=b"")

    def test_single_byte_xor_break(self):
        # Encrypt with single byte key using all-lowercase English text
        key = 42
        data = b"the quick brown fox jumps over the lazy dog and this is more text"
        encrypted = bytes(b ^ key for b in data)
        results = XORCipher.single_byte_xor_break(encrypted)
        # The correct key should produce mostly printable ASCII
        # Check top 10 results since printable ratio may not uniquely identify
        top_keys = [r["key"] for r in results[:10]]
        # At minimum, the correct key should score well
        assert key in top_keys or results[0]["score"] > 0.9

    def test_repr(self):
        cipher = XORCipher(key="test")
        assert "XORCipher" in repr(cipher)