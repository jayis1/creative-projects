"""Tests for Enigma cipher."""

import pytest
from cryptanalysis_toolkit.ciphers.enigma import EnigmaCipher


class TestEnigmaCipher:
    def test_basic_roundtrip(self):
        cipher = EnigmaCipher(
            rotor_order=[1, 2, 3],
            initial_positions=[0, 0, 0],
        )
        plaintext = "HELLO"
        ciphertext = cipher.encrypt(plaintext)
        # Re-create with same settings for decryption
        cipher2 = EnigmaCipher(
            rotor_order=[1, 2, 3],
            initial_positions=[0, 0, 0],
        )
        decrypted = cipher2.decrypt(ciphertext)
        assert decrypted == plaintext

    def test_reciprocal(self):
        """Enigma is reciprocal: encrypting twice with same settings = original."""
        cipher1 = EnigmaCipher(
            rotor_order=[1, 2, 3],
            initial_positions=[0, 0, 0],
        )
        cipher2 = EnigmaCipher(
            rotor_order=[1, 2, 3],
            initial_positions=[0, 0, 0],
        )
        text = "ENIGMA"
        ct1 = cipher1.encrypt(text)
        ct2 = cipher2.encrypt(ct1)
        assert ct2 == text

    def test_no_letter_maps_to_itself(self):
        """In Enigma, no letter should ever encrypt to itself."""
        cipher = EnigmaCipher(
            rotor_order=[1, 2, 3],
            initial_positions=[0, 0, 0],
        )
        text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        ct = cipher.encrypt(text)
        for i, (plain, cipher_ch) in enumerate(zip(text, ct)):
            assert plain != cipher_ch, f"Letter {plain} mapped to itself at position {i}"

    def test_different_positions_different_output(self):
        cipher1 = EnigmaCipher(rotor_order=[1, 2, 3], initial_positions=[0, 0, 0])
        cipher2 = EnigmaCipher(rotor_order=[1, 2, 3], initial_positions=[1, 0, 0])
        text = "HELLO"
        assert cipher1.encrypt(text) != cipher2.encrypt(text)

    def test_with_plugboard(self):
        cipher1 = EnigmaCipher(
            rotor_order=[1, 2, 3],
            initial_positions=[0, 0, 0],
            plugboard_pairs=[("A", "B"), ("C", "D")],
        )
        cipher2 = EnigmaCipher(
            rotor_order=[1, 2, 3],
            initial_positions=[0, 0, 0],
            plugboard_pairs=[("A", "B"), ("C", "D")],
        )
        text = "HELLO"
        ct = cipher1.encrypt(text)
        pt = cipher2.decrypt(ct)
        assert pt == text

    def test_invalid_rotor_count(self):
        with pytest.raises(ValueError):
            EnigmaCipher(rotor_order=[1, 2])

    def test_invalid_rotor_number(self):
        with pytest.raises(ValueError):
            EnigmaCipher(rotor_order=[1, 2, 6])

    def test_invalid_ring_settings(self):
        with pytest.raises(ValueError):
            EnigmaCipher(ring_settings=[0, 0])

    def test_invalid_positions(self):
        with pytest.raises(ValueError):
            EnigmaCipher(initial_positions=[0, 0])

    def test_preserves_nonalpha(self):
        cipher1 = EnigmaCipher(rotor_order=[1, 2, 3], initial_positions=[0, 0, 0])
        cipher2 = EnigmaCipher(rotor_order=[1, 2, 3], initial_positions=[0, 0, 0])
        text = "HELLO WORLD"
        ct = cipher1.encrypt(text)
        assert " " in ct  # Spaces pass through