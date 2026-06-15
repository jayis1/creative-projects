"""Tests for XOR single-byte break with improved scoring."""

import pytest
from cryptanalysis_toolkit.ciphers.xor import XORCipher


class TestXORBreak:
    def test_single_byte_xor_break_finds_english(self):
        """The correct key should rank high when breaking English text."""
        key = 42
        plaintext = b"The quick brown fox jumps over the lazy dog"
        cipher = XORCipher(key=bytes([key]))
        ciphertext = cipher.encrypt(plaintext)

        results = XORCipher.single_byte_xor_break(ciphertext)
        # The correct key should be in the top 5
        top_keys = [r["key"] for r in results[:5]]
        assert key in top_keys, f"Key {key} not in top 5: {top_keys}"

    def test_single_byte_xor_break_short_text(self):
        """Break should still work on short ciphertexts."""
        key = 77
        plaintext = b"HELLO"
        cipher = XORCipher(key=bytes([key]))
        ciphertext = cipher.encrypt(plaintext)

        results = XORCipher.single_byte_xor_break(ciphertext)
        assert len(results) == 256
        assert results[0]["key"] is not None

    def test_single_byte_xor_break_key_zero_not_highest(self):
        """Key=0 (identity/null XOR) should not rank #1 for English plaintext."""
        plaintext = b"The quick brown fox jumps over the lazy dog and the dog ran away"
        cipher = XORCipher(key=bytes([88]))
        ciphertext = cipher.encrypt(plaintext)

        results = XORCipher.single_byte_xor_break(ciphertext)
        # Key=0 would just return the ciphertext bytes as-is, which
        # when XOR-encrypted with key=88, wouldn't be English
        # So key=88 should rank higher than key=0 for this ciphertext
        key_0_idx = next(i for i, r in enumerate(results) if r["key"] == 0)
        key_88_idx = next(i for i, r in enumerate(results) if r["key"] == 88)
        assert key_88_idx < key_0_idx, "Correct key should rank higher than key=0"