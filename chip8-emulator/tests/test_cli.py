"""Tests for the CLI module."""

import pytest
from chip8_emulator.cli import build_test_rom, disassemble, _disassemble_opcode


class TestBuildTestRom:
    """Test ROM builder utility."""

    def test_build_rom(self):
        rom = build_test_rom([0x00E0, 0x1210])
        assert len(rom) == 4
        assert rom[0] == 0x00
        assert rom[1] == 0xE0
        assert rom[2] == 0x12
        assert rom[3] == 0x10

    def test_build_empty_rom(self):
        rom = build_test_rom([])
        assert len(rom) == 0


class TestDisassemble:
    """Test opcode disassembly."""

    def test_cls(self):
        assert _disassemble_opcode(0x00E0, {}) == "CLS"

    def test_ret(self):
        assert _disassemble_opcode(0x00EE, {}) == "RET"

    def test_jump(self):
        assert _disassemble_opcode(0x1200, {}) == "JP 200"

    def test_call(self):
        assert _disassemble_opcode(0x2300, {}) == "CALL 300"

    def test_se_byte(self):
        assert _disassemble_opcode(0x3105, {}) == "SE V1, 05"

    def test_ld_byte(self):
        assert _disassemble_opcode(0x60AB, {}) == "LD V0, AB"

    def test_drw(self):
        assert _disassemble_opcode(0xD015, {}) == "DRW V0, V1, 5"

    def test_add_i(self):
        assert _disassemble_opcode(0xF01E, {}) == "ADD I, V0"

    def test_unknown_opcode(self):
        result = _disassemble_opcode(0xF000, {})
        assert "???" in result


class TestDisassembleRom:
    """Test full ROM disassembly output."""

    def test_disassemble(self, capsys):
        rom = build_test_rom([0x00E0, 0x1210])
        disassemble(rom)
        captured = capsys.readouterr()
        assert "CLS" in captured.out