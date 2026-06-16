"""Tests for CHIP-8 memory subsystem."""

import pytest
from chip8_emulator.memory import Memory, Chip8MemoryError, FONT_START, PROGRAM_START, MEMORY_SIZE


class TestMemoryInit:
    """Test Memory initialization and font loading."""

    def test_default_size(self):
        mem = Memory()
        assert len(mem) == MEMORY_SIZE

    def test_font_sprites_loaded(self):
        mem = Memory()
        # Font sprite for "0" should be at 0x050: F0 90 90 90 F0
        assert mem.read(FONT_START) == 0xF0
        assert mem.read(FONT_START + 1) == 0x90

    def test_font_sprite_for_1(self):
        mem = Memory()
        addr = mem.font_sprite_addr(1)
        assert addr == FONT_START + 5
        assert mem.read(addr) == 0x20  # First byte of "1"

    def test_all_font_digits(self):
        mem = Memory()
        for d in range(16):
            addr = mem.font_sprite_addr(d)
            assert addr == FONT_START + d * 5

    def test_custom_size(self):
        mem = Memory(2048)
        assert len(mem) == 2048


class TestMemoryReadWrite:
    """Test byte and word read/write operations."""

    def test_write_read_byte(self):
        mem = Memory()
        mem.write(0x300, 0xAB)
        assert mem.read(0x300) == 0xAB

    def test_write_read_word(self):
        mem = Memory()
        mem.write(0x300, 0xAB)
        mem.write(0x301, 0xCD)
        assert mem.read_word(0x300) == 0xABCD

    def test_read_word_big_endian(self):
        mem = Memory()
        mem.write(0x500, 0x12)
        mem.write(0x501, 0x34)
        assert mem.read_word(0x500) == 0x1234

    def test_write_out_of_range_value(self):
        mem = Memory()
        with pytest.raises(Chip8MemoryError):
            mem.write(0x300, 0x100)

    def test_read_out_of_range_address(self):
        mem = Memory()
        with pytest.raises(Chip8MemoryError):
            mem.read(MEMORY_SIZE)

    def test_write_out_of_range_address(self):
        mem = Memory()
        with pytest.raises(Chip8MemoryError):
            mem.write(MEMORY_SIZE, 0x00)

    def test_read_word_out_of_range(self):
        mem = Memory()
        with pytest.raises(Chip8MemoryError):
            mem.read_word(MEMORY_SIZE - 1)

    def test_boundary_write(self):
        mem = Memory()
        mem.write(MEMORY_SIZE - 1, 0xFF)
        assert mem.read(MEMORY_SIZE - 1) == 0xFF

    def test_zero_address(self):
        mem = Memory()
        mem.write(0, 0x42)
        assert mem.read(0) == 0x42


class TestMemoryRomLoading:
    """Test ROM loading."""

    def test_load_rom(self):
        mem = Memory()
        rom = bytes([0x12, 0x34, 0x56, 0x78])
        mem.load_rom(rom, PROGRAM_START)
        assert mem.read(PROGRAM_START) == 0x12
        assert mem.read(PROGRAM_START + 1) == 0x34

    def test_load_rom_default_offset(self):
        mem = Memory()
        rom = bytes([0xAA, 0xBB])
        mem.load_rom(rom)
        assert mem.read(PROGRAM_START) == 0xAA

    def test_load_rom_from_file(self, tmp_path):
        rom = bytes([0xCC, 0xDD])
        path = tmp_path / "test.ch8"
        path.write_bytes(rom)
        mem = Memory()
        mem.load_rom_from_file(str(path))
        assert mem.read(PROGRAM_START) == 0xCC

    def test_load_rom_overflow(self):
        mem = Memory()
        huge_rom = bytes(5000)
        with pytest.raises(Chip8MemoryError):
            mem.load_rom(huge_rom)

    def test_load_rom_invalid_offset(self):
        mem = Memory()
        with pytest.raises(Chip8MemoryError):
            mem.load_rom(bytes(10), 4090)  # 4090 + 10 > 4096


class TestFontSpriteAddr:
    """Test font sprite address lookup."""

    def test_valid_digits(self):
        mem = Memory()
        for d in range(16):
            assert mem.font_sprite_addr(d) == FONT_START + d * 5

    def test_invalid_digit(self):
        mem = Memory()
        with pytest.raises(Chip8MemoryError):
            mem.font_sprite_addr(16)

    def test_negative_digit(self):
        mem = Memory()
        with pytest.raises(Chip8MemoryError):
            mem.font_sprite_addr(-1)