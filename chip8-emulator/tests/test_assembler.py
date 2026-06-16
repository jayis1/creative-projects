"""Tests for the CHIP-8 assembler."""

import pytest
from chip8_emulator.assembler import Assembler, AssemblerError, assemble, AssemblyResult


class TestAssemblerBasic:
    """Test basic assembler functionality."""

    def test_cls_instruction(self):
        result = assemble("CLS")
        assert result.ok
        assert result.rom == bytes([0x00, 0xE0])

    def test_ret_instruction(self):
        result = assemble("RET")
        assert result.ok
        assert result.rom == bytes([0x00, 0xEE])

    def test_jump_instruction(self):
        result = assemble("JP 0x200")
        assert result.ok
        assert result.rom == bytes([0x12, 0x00])

    def test_jump_with_label(self):
        source = """
        JP loop
        loop:
        CLS
        """
        result = assemble(source)
        assert result.ok
        assert len(result.rom) == 4
        assert result.rom[:2] == bytes([0x12, 0x02])  # JP 0x202

    def test_call_instruction(self):
        result = assemble("CALL 0x300")
        assert result.ok
        assert result.rom == bytes([0x23, 0x00])

    def test_se_byte_instruction(self):
        result = assemble("SE V0, 0x05")
        assert result.ok
        assert result.rom == bytes([0x30, 0x05])

    def test_se_register_instruction(self):
        result = assemble("SE V0, V1")
        assert result.ok
        assert result.rom == bytes([0x50, 0x10])

    def test_sne_byte_instruction(self):
        result = assemble("SNE V3, 0xFF")
        assert result.ok
        assert result.rom == bytes([0x43, 0xFF])

    def test_sne_register_instruction(self):
        result = assemble("SNE V2, V3")
        assert result.ok
        assert result.rom == bytes([0x92, 0x30])

    def test_ld_byte_instruction(self):
        result = assemble("LD V0, 0x0A")
        assert result.ok
        assert result.rom == bytes([0x60, 0x0A])

    def test_ld_register_instruction(self):
        result = assemble("LD V1, V2")
        assert result.ok
        assert result.rom == bytes([0x81, 0x20])

    def test_ld_i_instruction(self):
        result = assemble("LD I, 0x300")
        assert result.ok
        assert result.rom == bytes([0xA3, 0x00])

    def test_ld_dt_instruction(self):
        result = assemble("LD V0, DT")
        assert result.ok
        assert result.rom == bytes([0xF0, 0x07])

    def test_ld_st_instruction(self):
        result = assemble("LD ST, V1")
        assert result.ok
        assert result.rom == bytes([0xF1, 0x18])

    def test_add_byte_instruction(self):
        result = assemble("ADD V0, 0x05")
        assert result.ok
        assert result.rom == bytes([0x70, 0x05])

    def test_add_register_instruction(self):
        result = assemble("ADD V0, V1")
        assert result.ok
        assert result.rom == bytes([0x80, 0x14])

    def test_add_i_instruction(self):
        result = assemble("ADD I, V0")
        assert result.ok
        assert result.rom == bytes([0xF0, 0x1E])

    def test_rnd_instruction(self):
        result = assemble("RND V0, 0xFF")
        assert result.ok
        assert result.rom == bytes([0xC0, 0xFF])

    def test_drw_instruction(self):
        result = assemble("DRW V0, V1, 5")
        assert result.ok
        assert result.rom == bytes([0xD0, 0x15])

    def test_skp_instruction(self):
        result = assemble("SKP V0")
        assert result.ok
        assert result.rom == bytes([0xE0, 0x9E])

    def test_skn_instruction(self):
        result = assemble("SKNP V0")
        assert result.ok
        assert result.rom == bytes([0xE0, 0xA1])


class TestAssemblerSuperChip:
    """Test SUPER-CHIP extension mnemonics."""

    def test_exit_instruction(self):
        result = assemble("EXIT")
        assert result.ok
        assert result.rom == bytes([0x00, 0xFD])

    def test_exmode_instruction(self):
        result = assemble("EXMODE")
        assert result.ok
        assert result.rom == bytes([0x00, 0xFF])

    def test_scroll_left(self):
        result = assemble("SCROLL_LEFT")
        assert result.ok
        assert result.rom == bytes([0x00, 0xFB])

    def test_scroll_right(self):
        result = assemble("SCROLL_RIGHT")
        assert result.ok
        assert result.rom == bytes([0x00, 0xFC])

    def test_scroll_down(self):
        result = assemble("SCROLL_DOWN 2")
        assert result.ok
        assert result.rom == bytes([0x00, 0xC2])

    def test_ld_hf(self):
        result = assemble("LD HF, V0")
        assert result.ok
        assert result.rom == bytes([0xF0, 0x30])

    def test_ld_r(self):
        result = assemble("LD R, V0")
        assert result.ok
        assert result.rom == bytes([0xF0, 0x75])

    def test_ld_vx_r(self):
        result = assemble("LD V0, R")
        assert result.ok
        assert result.rom == bytes([0xF0, 0x85])


class TestAssemblerLogicalOps:
    """Test logical and arithmetic operations."""

    def test_or(self):
        result = assemble("OR V0, V1")
        assert result.ok
        assert result.rom == bytes([0x80, 0x11])

    def test_and(self):
        result = assemble("AND V0, V1")
        assert result.ok
        assert result.rom == bytes([0x80, 0x12])

    def test_xor(self):
        result = assemble("XOR V0, V1")
        assert result.ok
        assert result.rom == bytes([0x80, 0x13])

    def test_sub(self):
        result = assemble("SUB V0, V1")
        assert result.ok
        assert result.rom == bytes([0x80, 0x15])

    def test_subn(self):
        result = assemble("SUBN V0, V1")
        assert result.ok
        assert result.rom == bytes([0x80, 0x17])

    def test_shr(self):
        result = assemble("SHR V0, V1")
        assert result.ok
        assert result.rom == bytes([0x80, 0x16])

    def test_shl(self):
        result = assemble("SHL V0, V1")
        assert result.ok
        assert result.rom == bytes([0x80, 0x1E])


class TestAssemblerDirectives:
    """Test assembler directives."""

    def test_db_directive(self):
        result = assemble(".db 0xFF, 0x81, 0x81, 0x81, 0xFF")
        assert result.ok
        assert result.rom == bytes([0xFF, 0x81, 0x81, 0x81, 0xFF])

    def test_dw_directive(self):
        result = assemble(".dw 0x00E0")
        assert result.ok
        assert result.rom == bytes([0x00, 0xE0])

    def test_org_directive(self):
        result = assemble("""
        .org 0x300
        CLS
        """)
        assert result.ok
        # ROM should start at 0x300 - 0x200 = 0x100 offset
        assert len(result.rom) > 0

    def test_comments_semicolon(self):
        result = assemble("CLS ; clear screen")
        assert result.ok
        assert result.rom == bytes([0x00, 0xE0])

    def test_comments_double_slash(self):
        result = assemble("CLS // clear screen")
        assert result.ok
        assert result.rom == bytes([0x00, 0xE0])


class TestAssemblerFxOps:
    """Test F-prefixed operations."""

    def test_ld_b(self):
        result = assemble("LD B, V0")
        assert result.ok
        assert result.rom == bytes([0xF0, 0x33])

    def test_ld_i_store(self):
        result = assemble("LD [I], V3")
        assert result.ok
        assert result.rom == bytes([0xF3, 0x55])

    def test_ld_i_load(self):
        result = assemble("LD V3, [I]")
        assert result.ok
        assert result.rom == bytes([0xF3, 0x65])

    def test_ld_k(self):
        result = assemble("LD V0, K")
        assert result.ok
        assert result.rom == bytes([0xF0, 0x0A])

    def test_ld_f(self):
        result = assemble("LD F, V0")
        assert result.ok
        assert result.rom == bytes([0xF0, 0x29])


class TestAssemblerComplex:
    """Test complex multi-instruction programs."""

    def test_maze_program(self):
        source = """
        ; Maze generator
        LD V0, 0x00
        LD V1, 0x00
        LD I, 0x210
        RND V2, 0x01
        SE V2, 0x01
        LD I, 0x20E
        DRW V0, V1, 0x04
        ADD V0, 0x04
        SE V0, 0x40
        JP 0x200
        LD V0, 0x00
        ADD V1, 0x04
        SE V1, 0x20
        JP 0x200
        JP 0x210
        """
        result = assemble(source, origin=0x200)
        assert result.ok
        assert len(result.rom) > 0
        # First instruction should be LD V0, 0x00
        assert result.rom[0] == 0x60
        assert result.rom[1] == 0x00

    def test_hex_number_formats(self):
        result = assemble("LD V0, 0x0A")
        assert result.ok
        result2 = assemble("LD V0, 10")
        assert result2.ok
        assert result.rom == result2.rom

    def test_case_insensitive(self):
        result1 = assemble("LD V0, 0x05")
        result2 = assemble("ld v0, 0x05")
        assert result1.ok
        assert result2.ok
        assert result1.rom == result2.rom


class TestAssemblerErrors:
    """Test error handling."""

    def test_invalid_mnemonic(self):
        result = assemble("INVALID V0, V1")
        assert len(result.errors) > 0

    def test_invalid_register(self):
        result = assemble("LD VG, 0x05")
        assert len(result.errors) > 0

    def test_empty_source(self):
        result = assemble("")
        assert result.ok
        assert len(result.rom) == 0