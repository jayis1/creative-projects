"""Tests for CHIP-8 display subsystem."""

import pytest
from chip8_emulator.display import Display


class TestDisplayInit:
    """Test Display initialization."""

    def test_dimensions(self):
        d = Display()
        assert d.WIDTH == 64
        assert d.HEIGHT == 32

    def test_initial_clear(self):
        d = Display()
        for y in range(d.HEIGHT):
            for x in range(d.WIDTH):
                assert d.get(x, y) is False


class TestDisplayPixelAccess:
    """Test pixel get/set with wrapping."""

    def test_set_get(self):
        d = Display()
        d.set(0, 0, True)
        assert d.get(0, 0) is True

    def test_wrap_x(self):
        d = Display()
        d.set(64, 0, True)
        assert d.get(0, 0) is True

    def test_wrap_y(self):
        d = Display()
        d.set(0, 32, True)
        assert d.get(0, 0) is True

    def test_clear(self):
        d = Display()
        d.set(10, 10, True)
        d.clear()
        assert d.get(10, 10) is False


class TestDisplayDrawSprite:
    """Test sprite drawing (XOR mode) and collision detection."""

    def test_draw_simple_sprite(self):
        d = Display()
        # Draw a single byte: 0x80 = 10000000
        collision = d.draw_sprite(0, 0, bytes([0x80]))
        assert collision is False
        assert d.get(0, 0) is True
        assert d.get(1, 0) is False

    def test_draw_xor_collision(self):
        d = Display()
        # Draw same sprite twice at same position — XOR should turn pixels off
        d.draw_sprite(0, 0, bytes([0xFF]))
        collision = d.draw_sprite(0, 0, bytes([0xFF]))
        assert collision is True  # Pixels were already on
        # All pixels should now be off (XOR)
        for x in range(8):
            assert d.get(x, 0) is False

    def test_draw_multi_row_sprite(self):
        d = Display()
        sprite = bytes([0xFF, 0x00, 0xFF])
        d.draw_sprite(0, 0, sprite)
        assert d.get(0, 0) is True   # Row 0
        assert d.get(0, 1) is False   # Row 1
        assert d.get(0, 2) is True    # Row 2

    def test_draw_sprite_with_offset(self):
        d = Display()
        # Draw at offset position
        d.draw_sprite(5, 3, bytes([0x80]))
        assert d.get(5, 3) is True

    def test_draw_sprite_wrapping(self):
        d = Display()
        # Draw at x=63 so pixels wrap: bit 7 (0x80) at x=63, bit 6 (0x40) at x=0
        d.draw_sprite(63, 0, bytes([0xC0]))
        assert d.get(63, 0) is True   # Bit 7 (MSB)
        assert d.get(0, 0) is True    # Bit 6 wraps to x=0


class TestDisplayScrolling:
    """Test SUPER-CHIP scroll extensions."""

    def test_scroll_down(self):
        d = Display()
        d.set(5, 0, True)
        d.scroll_down(2)
        assert d.get(5, 2) is True
        assert d.get(5, 0) is False

    def test_scroll_left(self):
        d = Display()
        d.set(10, 5, True)
        d.scroll_left()
        assert d.get(6, 5) is True
        assert d.get(10, 5) is False

    def test_scroll_right(self):
        d = Display()
        d.set(10, 5, True)
        d.scroll_right()
        assert d.get(14, 5) is True
        assert d.get(10, 5) is False


class TestDisplayRender:
    """Test display rendering."""

    def test_render(self):
        d = Display()
        d.set(0, 0, True)
        text = d.render(on="#", off=".")
        lines = text.split("\n")
        assert lines[0][0] == "#"
        assert lines[0][1] == "."

    def test_to_rows(self):
        d = Display()
        rows = d.to_rows()
        assert len(rows) == 32
        assert len(rows[0]) == 64