"""Simplified Enigma-like rotor machine cipher."""

from __future__ import annotations
from typing import List, Optional


class EnigmaCipher:
    """Simplified Enigma machine implementation.

    Simulates a 3-rotor Enigma machine with plugboard, reflector, and
    rotating rotors. Supports customizable rotor wirings and positions.

    Note: This is a simplified educational model, not a historically
    accurate Enigma implementation.

    Args:
        rotor_order: List of 3 rotor numbers (1-5) in left-to-right order.
        ring_settings: List of 3 ring settings (0-25 for A-Z).
        plugboard_pairs: List of (letter1, letter2) pairs for plugboard swaps.
        initial_positions: List of 3 initial rotor positions (0-25 for A-Z).

    Raises:
        ValueError: If any parameter is invalid.
    """

    # Standard Enigma rotor wirings (rotors I-V)
    ROTOR_WIRINGS = {
        1: "EKMFLGDQVZNTOWYHXUSPAIBRCJ",
        2: "AJDKSIRUXBLHWTMCQGZNPYFVOE",
        3: "BDFHJLCPRTXVZNYEIWGAKMUSQO",
        4: "ESOVPZJAYQUIRHXLNFTGKDCMWB",
        5: "VZBRGITYUPSDNHLXAWMJQOFECK",
    }

    # Rotor turnover positions (when the rotor to the left should advance)
    TURNOVER = {1: 16, 2: 4, 3: 21, 4: 9, 5: 25}  # Q, E, V, J, Z

    # Reflector B
    REFLECTOR_B = "YRUHQSLDPXNGOKMIEBFZCWVJAT"

    def __init__(
        self,
        rotor_order: Optional[List[int]] = None,
        ring_settings: Optional[List[int]] = None,
        plugboard_pairs: Optional[List[tuple]] = None,
        initial_positions: Optional[List[int]] = None,
    ) -> None:
        self.rotor_order = rotor_order or [1, 2, 3]
        if len(self.rotor_order) != 3:
            raise ValueError("Must specify exactly 3 rotors")
        for r in self.rotor_order:
            if r not in self.ROTOR_WIRINGS:
                raise ValueError(f"Invalid rotor number: {r}. Must be 1-5.")

        self.ring_settings = ring_settings or [0, 0, 0]
        if len(self.ring_settings) != 3:
            raise ValueError("Must specify exactly 3 ring settings")
        for s in self.ring_settings:
            if not 0 <= s <= 25:
                raise ValueError(f"Ring setting must be 0-25, got {s}")

        self.initial_positions = initial_positions or [0, 0, 0]
        if len(self.initial_positions) != 3:
            raise ValueError("Must specify exactly 3 initial positions")
        for p in self.initial_positions:
            if not 0 <= p <= 25:
                raise ValueError(f"Initial position must be 0-25, got {p}")

        # Build plugboard mapping
        self.plugboard: dict = {}
        if plugboard_pairs:
            seen: set = set()
            for a, b in plugboard_pairs:
                a = a.upper() if isinstance(a, str) else chr(a + ord('A'))
                b = b.upper() if isinstance(b, str) else chr(b + ord('A'))
                if a in seen or b in seen:
                    raise ValueError(f"Plugboard letter used more than once: {a}, {b}")
                seen.add(a)
                seen.add(b)
                self.plugboard[a] = b
                self.plugboard[b] = a

        # Build rotor forward and reverse mappings
        self.rotors_forward: List[dict] = []
        self.rotors_reverse: List[dict] = []
        for r in self.rotor_order:
            wiring = self.ROTOR_WIRINGS[r]
            ring = self.ring_settings[self.rotor_order.index(r)]
            fwd = {}
            rev = {}
            for i, out_char in enumerate(wiring):
                in_pos = (i - ring) % 26
                out_pos = (ord(out_char) - ord('A') - ring) % 26
                fwd[in_pos] = out_pos
                rev[out_pos] = in_pos
            self.rotors_forward.append(fwd)
            self.rotors_reverse.append(rev)

        # Current rotor positions (mutable)
        self.positions = list(self.initial_positions)

    def _apply_plugboard(self, char_code: int) -> int:
        """Apply plugboard substitution."""
        char = chr(char_code + ord('A'))
        if char in self.plugboard:
            return ord(self.plugboard[char]) - ord('A')
        return char_code

    def _advance_rotors(self) -> None:
        """Advance rotors according to Enigma stepping rules."""
        # Check if middle rotor is at turnover (double stepping)
        middle_turnover = self.TURNOVER[self.rotor_order[1]]
        right_turnover = self.TURNOVER[self.rotor_order[2]]

        # Middle rotor at turnover causes left AND middle to advance
        if self.positions[1] == middle_turnover:
            self.positions[0] = (self.positions[0] + 1) % 26
            self.positions[1] = (self.positions[1] + 1) % 26
        # Right rotor at turnover causes middle to advance
        elif self.positions[2] == right_turnover:
            self.positions[1] = (self.positions[1] + 1) % 26

        # Right rotor always advances
        self.positions[2] = (self.positions[2] + 1) % 26

    def _through_rotors_right(self, char_code: int) -> int:
        """Pass signal through rotors from right to left."""
        for i in range(2, -1, -1):
            # Adjust for rotor position
            offset = self.positions[i]
            input_pos = (char_code + offset) % 26
            output_pos = self.rotors_forward[i][input_pos]
            char_code = (output_pos - offset) % 26
        return char_code

    def _through_reflector(self, char_code: int) -> int:
        """Pass signal through reflector."""
        return ord(self.REFLECTOR_B[char_code]) - ord('A')

    def _through_rotors_left(self, char_code: int) -> int:
        """Pass signal through rotors from left to right (reverse path)."""
        for i in range(3):
            offset = self.positions[i]
            input_pos = (char_code + offset) % 26
            output_pos = self.rotors_reverse[i][input_pos]
            char_code = (output_pos - offset) % 26
        return char_code

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext using Enigma machine.

        Args:
            plaintext: The text to encrypt. Only letters are processed.

        Returns:
            Encrypted ciphertext string (uppercase).
        """
        # Reset positions
        self.positions = list(self.initial_positions)

        result = []
        for ch in plaintext:
            if ch.isalpha():
                self._advance_rotors()
                char_code = ord(ch.upper()) - ord('A')

                # Plugboard in
                char_code = self._apply_plugboard(char_code)

                # Through rotors right to left
                char_code = self._through_rotors_right(char_code)

                # Reflector
                char_code = self._through_reflector(char_code)

                # Through rotors left to right
                char_code = self._through_rotors_left(char_code)

                # Plugboard out
                char_code = self._apply_plugboard(char_code)

                result.append(chr(char_code + ord('A')))
            else:
                result.append(ch)

        return "".join(result)

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext using Enigma machine.

        Since Enigma is reciprocal, decryption is identical to encryption
        with the same initial settings.

        Args:
            ciphertext: The text to decrypt.

        Returns:
            Decrypted plaintext string (uppercase).
        """
        return self.encrypt(ciphertext)

    def __repr__(self) -> str:
        rotors = "-".join(str(r) for r in self.rotor_order)
        positions = "".join(chr(p + ord('A')) for p in self.initial_positions)
        return f"EnigmaCipher(rotors={rotors}, positions={positions})"