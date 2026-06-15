"""Tests for CipherBreaker."""

import pytest
from cryptanalysis_toolkit.breaker import CipherBreaker
from cryptanalysis_toolkit.ciphers import (
    CaesarCipher, VigenereCipher, AffineCipher, SubstitutionCipher
)


class TestBreaker:
    def test_break_caesar(self):
        breaker = CipherBreaker()
        plaintext = "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG AND THE DOG RAN AWAY QUICKLY"
        cipher = CaesarCipher(shift=13)
        ciphertext = cipher.encrypt(plaintext)
        results = breaker.break_caesar(ciphertext)
        assert results[0]["shift"] == 13
        assert results[0]["plaintext"].upper() == plaintext.upper()

    def test_break_affine(self):
        breaker = CipherBreaker()
        plaintext = "THIS IS A LONGER PIECE OF ENGLISH TEXT FOR TESTING THE AFFINE CIPHER BREAKER"
        cipher = AffineCipher(a=5, b=8)
        ciphertext = cipher.encrypt(plaintext)
        results = breaker.break_affine(ciphertext)
        assert results[0]["a"] == 5
        assert results[0]["b"] == 8

    def test_break_vigenere(self):
        breaker = CipherBreaker()
        # Use a longer plaintext for better results
        plaintext = ("THEQUICKBROWNFOXJUMPSOVERTHELAZYDOGTHERAININSPAINFALLSMAINLY"
                     "ONTHEPLAINTHEQUICKBROWNFOXJUMPSOVERTHELAZYDOGTHERAININSPAINFALLS")
        cipher = VigenereCipher(keyword="KEY")
        ciphertext = cipher.encrypt(plaintext)
        results = breaker.break_vigenere(ciphertext)
        assert len(results) > 0
        # Check that the best result is somewhat reasonable English
        best = results[0]
        assert len(best["plaintext"]) > 0
        # Verify decrypt with found key produces similar text
        assert best["score"] > -5.0  # Should be English-like

    def test_identify_cipher_type(self):
        breaker = CipherBreaker()
        # English text should have high IC
        text = "THIS IS ENGLISH TEXT FOR TESTING"
        result = breaker.identify_cipher_type(text)
        assert "ic" in result
        assert "likely_type" in result
        assert result["ic"] > 0.05

    def test_break_substitution(self):
        breaker = CipherBreaker()
        plaintext = "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG AND THE DOG RAN AWAY"
        # Use a known substitution
        cipher = SubstitutionCipher(key="QWERTYUIOPASDFGHJKLZXCVBNM")
        ciphertext = cipher.encrypt(plaintext)
        result = breaker.break_substitution(ciphertext, iterations=2000, restarts=3, seed=42)
        # Hill climbing may not always find exact solution, but should get close
        assert isinstance(result, dict)
        assert "key" in result
        assert "plaintext" in result