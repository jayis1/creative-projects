"""Tests for built-in ROMs."""

import pytest
from chip8_emulator.cpu import CPU
from chip8_emulator.roms import ALL_ROMS, add_test_rom, bcd_test_rom, chip8_hello_rom, draw_test_rom


class TestROMs:
    """Test that all built-in ROMs load and execute without errors."""

    @pytest.mark.parametrize("name,rom_func", list(ALL_ROMS.items()))
    def test_rom_loads(self, name, rom_func):
        """Every built-in ROM should load into memory without error."""
        cpu = CPU()
        rom = rom_func()
        cpu.load_rom(rom)
        assert cpu.pc == 0x200

    def test_hello_rom_runs(self):
        """Hello ROM should run a few cycles without crashing."""
        cpu = CPU()
        cpu.load_rom(chip8_hello_rom())
        for _ in range(20):
            cpu.step()
            if cpu.pc == 0x214:
                break

    def test_add_test_rom(self):
        """Add test ROM: V0=5, V1=7, V0=V0+V1=12, V3=0, V3=V3+V0=12."""
        cpu = CPU()
        cpu.load_rom(add_test_rom())
        for _ in range(6):
            cpu.step()
        assert cpu.V[0] == 12
        assert cpu.V[3] == 12

    def test_bcd_test_rom(self):
        """BCD test ROM should store 255 → 2, 5, 5 in memory."""
        cpu = CPU()
        cpu.load_rom(bcd_test_rom())
        for _ in range(3):
            cpu.step()
        addr = 0x210
        assert cpu.memory.read(addr) == 2
        assert cpu.memory.read(addr + 1) == 5
        assert cpu.memory.read(addr + 2) == 5

    def test_draw_test_rom(self):
        """Draw test ROM: second draw should cause collision (VF=1)."""
        # Build a custom ROM that draws a sprite twice at same location
        from chip8_emulator.cli import build_test_rom
        rom = build_test_rom([
            0x00E0,  # CLS
            0x600A,  # LD V0, 10 (x)
            0x610A,  # LD V1, 10 (y)
            0xA210,  # LD I, 0x210 (sprite data)
            0xD015,  # DRW V0, V1, 5 (first draw — no collision)
            0xD015,  # DRW V0, V1, 5 (second draw — collision!)
            0x1210,  # JP 0x210 (halt)
            0x1210,  # JP 0x210 (halt)
            # Sprite data at 0x210 (10 bytes from 0x200 = offset 0x10)
        ])
        # Append sprite data
        rom = rom + bytes([0xFF, 0xFF, 0xFF, 0xFF, 0xFF])
        cpu = CPU()
        cpu.load_rom(rom)
        for _ in range(6):  # CLS, LD, LD, LD I, DRW, DRW
            cpu.step()
        assert cpu.V[0xF] == 1