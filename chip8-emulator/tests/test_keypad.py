"""Tests for CHIP-8 keypad."""

import pytest
from chip8_emulator.keypad import Keypad


class TestKeypadInit:
    """Test Keypad initialization."""

    def test_default_keymap(self):
        kp = Keypad()
        assert kp.physical_to_hex("1") == 0x1
        assert kp.physical_to_hex("x") == 0x0
        assert kp.physical_to_hex("v") == 0xF

    def test_custom_keymap(self):
        kp = Keypad(keymap={"a": 0x0, "b": 0x1})
        assert kp.physical_to_hex("a") == 0x0
        assert kp.physical_to_hex("b") == 0x1


class TestKeypadPressRelease:
    """Test key press and release."""

    def test_press_release(self):
        kp = Keypad()
        kp.press(0x5)
        assert kp.is_pressed(0x5) is True
        kp.release(0x5)
        assert kp.is_pressed(0x5) is False

    def test_release_all(self):
        kp = Keypad()
        for k in range(16):
            kp.press(k)
        kp.release_all()
        for k in range(16):
            assert kp.is_pressed(k) is False

    def test_invalid_key(self):
        kp = Keypad()
        with pytest.raises(ValueError):
            kp.press(16)
        with pytest.raises(ValueError):
            kp.is_pressed(-1)

    def test_map_key(self):
        kp = Keypad()
        kp.map_key("k", 0x5)
        assert kp.physical_to_hex("k") == 0x5

    def test_map_key_invalid_hex(self):
        kp = Keypad()
        with pytest.raises(ValueError):
            kp.map_key("z", 20)