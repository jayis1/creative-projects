"""Tests for bugs found and fixed during Phase 3 bug hunt."""

import pytest
from chip8_emulator.cpu import CPU, CpuError
from chip8_emulator.memory import Memory, Chip8MemoryError
from chip8_emulator.display import Display
from chip8_emulator.cli import build_test_rom


class TestMemoryErrorNotBuiltin:
    """Bug: MemoryError should not shadow built-in MemoryError."""

    def test_chip8_memory_error_is_distinct_from_builtin(self):
        """Chip8MemoryError must NOT be the same as builtins.MemoryError."""
        import builtins
        from chip8_emulator.memory import Chip8MemoryError
        assert Chip8MemoryError is not builtins.MemoryError

    def test_chip8_memory_error_can_be_raised(self):
        """Chip8MemoryError can be raised and caught independently."""
        from chip8_emulator.memory import Chip8MemoryError
        with pytest.raises(Chip8MemoryError):
            raise Chip8MemoryError("test error")

    def test_builtin_memory_error_still_works(self):
        """Built-in MemoryError is still usable."""
        with pytest.raises(MemoryError):
            raise MemoryError("builtin")


class TestValidatorSuperChipOpcodes:
    """Bug: Validator flagged valid SUPER-CHIP opcodes as invalid."""

    def test_fx30_not_flagged_invalid(self):
        """Fx30 (LD HF, Vx) should not be flagged as an invalid opcode."""
        from chip8_emulator.validator import validate_rom_bytes
        rom = bytes([0xF0, 0x30])  # LD HF, V0
        result = validate_rom_bytes(rom)
        invalid_warnings = [w for w in result.warnings if "invalid" in w.lower()]
        assert len(invalid_warnings) == 0

    def test_fx75_not_flagged_invalid(self):
        """Fx75 (LD R, Vx) should not be flagged as an invalid opcode."""
        from chip8_emulator.validator import validate_rom_bytes
        rom = bytes([0xF0, 0x75])  # LD R, V0
        result = validate_rom_bytes(rom)
        invalid_warnings = [w for w in result.warnings if "invalid" in w.lower()]
        assert len(invalid_warnings) == 0

    def test_fx85_not_flagged_invalid(self):
        """Fx85 (LD Vx, R) should not be flagged as an invalid opcode."""
        from chip8_emulator.validator import validate_rom_bytes
        rom = bytes([0xF0, 0x85])  # LD V0, R
        result = validate_rom_bytes(rom)
        invalid_warnings = [w for w in result.warnings if "invalid" in w.lower()]
        assert len(invalid_warnings) == 0

    def test_00fd_not_flagged_invalid(self):
        """00FD (EXIT) should not be flagged as an invalid 0-prefix opcode."""
        from chip8_emulator.validator import validate_rom_bytes
        rom = bytes([0x00, 0xFD])  # EXIT (SUPER-CHIP)
        result = validate_rom_bytes(rom)
        invalid_warnings = [w for w in result.warnings if "invalid" in w.lower()]
        assert len(invalid_warnings) == 0

    def test_00ff_not_flagged_invalid(self):
        """00FF (EXMODE) should not be flagged as invalid."""
        from chip8_emulator.validator import validate_rom_bytes
        rom = bytes([0x00, 0xFF])  # EXMODE (SUPER-CHIP)
        result = validate_rom_bytes(rom)
        invalid_warnings = [w for w in result.warnings if "invalid" in w.lower()]
        assert len(invalid_warnings) == 0


class TestAddVfClobber:
    """Bug: ADD/SUB with VF as destination — VF should be carry/borrow flag."""

    def test_add_vf_no_carry(self):
        """ADD VF, V1 where result < 256 — VF should be 0 (no carry)."""
        cpu = CPU()
        cpu.V[0xF] = 0x10
        cpu.V[0x1] = 0x10
        cpu._opcode = 0x8F14
        cpu.op_8xy4()
        assert cpu.V[0xF] == 0, f"VF should be 0 (no carry), got {cpu.V[0xF]:02X}"

    def test_add_vf_with_carry(self):
        """ADD VF, V1 where result >= 256 — VF should be 1 (carry)."""
        cpu = CPU()
        cpu.V[0xF] = 0xFF
        cpu.V[0x1] = 0x01
        cpu._opcode = 0x8F14
        cpu.op_8xy4()
        assert cpu.V[0xF] == 1, f"VF should be 1 (carry), got {cpu.V[0xF]:02X}"

    def test_sub_vf_no_borrow(self):
        """SUB VF, V1 — VF should be 1 (no borrow) when VF >= V1."""
        cpu = CPU()
        cpu.V[0xF] = 0x05
        cpu.V[0x1] = 0x03
        cpu._opcode = 0x8F15
        cpu.op_8xy5()
        assert cpu.V[0xF] == 1, f"VF should be 1 (no borrow), got {cpu.V[0xF]:02X}"

    def test_sub_vf_with_borrow(self):
        """SUB VF, V1 — VF should be 0 (borrow) when VF < V1."""
        cpu = CPU()
        cpu.V[0xF] = 0x03
        cpu.V[0x1] = 0x05
        cpu._opcode = 0x8F15
        cpu.op_8xy5()
        assert cpu.V[0xF] == 0, f"VF should be 0 (borrow), got {cpu.V[0xF]:02X}"


class TestEdgeCases:
    """Edge case tests discovered during bug hunt."""

    def test_drw_n_zero(self):
        """DRW with n=0 should draw nothing and set VF=0."""
        cpu = CPU()
        cpu.V[0] = 5
        cpu.V[1] = 5
        cpu._opcode = 0xD010
        cpu.op_Dxxx()
        assert cpu.V[0xF] == 0

    def test_scroll_down_zero(self):
        """scroll_down(0) should be a no-op."""
        d = Display()
        d.set(5, 5, True)
        d.scroll_down(0)
        assert d.get(5, 5) is True

    def test_fx1e_i_overflow(self):
        """Fx1E ADD I, Vx should wrap I at 0xFFF."""
        cpu = CPU()
        cpu.I = 0xFF0
        cpu.V[0] = 0xFF
        cpu._opcode = 0xF01E
        cpu.op_Fx1E()
        assert cpu.I == 0x0EF, f"I should wrap to 0x0EF, got {cpu.I:#06x}"

    def test_draw_sprite_boundary_wrap(self):
        """Drawing sprite at x=63 should wrap to x=0."""
        d = Display()
        collision = d.draw_sprite(63, 0, bytes([0xFF]))
        assert d.get(63, 0) is True  # MSB at x=63
        assert d.get(0, 0) is True   # Wrapped to x=0

    def test_bnnn_standard_mode(self):
        """BNNN in standard mode uses V0 as offset."""
        cpu = CPU()
        rom = build_test_rom([0x6005, 0xB100])
        cpu.load_rom(rom)
        cpu.step()  # LD V0, 5
        cpu.step()  # B100: JP V0, 0x100
        assert cpu.pc == 0x105

    def test_bnnn_extended_mode(self):
        """BxNN in extended mode uses Vx as offset."""
        cpu = CPU(super_chip=True)
        rom = build_test_rom([0x6105, 0xB100])
        cpu.load_rom(rom)
        cpu.extended_mode = True
        cpu.step()  # LD V1, 5
        cpu.step()  # B100: JP V1, 0x100
        assert cpu.pc == 0x105