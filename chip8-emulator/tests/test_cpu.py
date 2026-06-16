"""Comprehensive tests for the CHIP-8 CPU — all 35 opcodes plus edge cases."""

import pytest
from chip8_emulator.cpu import CPU, CpuError
from chip8_emulator.display import Display
from chip8_emulator.keypad import Keypad
from chip8_emulator.memory import Memory, PROGRAM_START
from chip8_emulator.cli import build_test_rom


# Helper: create a CPU with a ROM loaded
def cpu_with_rom(instructions: list[int]) -> CPU:
    """Create a CPU with a ROM built from a list of 16-bit instruction words."""
    rom = build_test_rom(instructions)
    cpu = CPU()
    cpu.load_rom(rom)
    return cpu


class TestCPUInit:
    """Test CPU initialization and reset."""

    def test_initial_state(self):
        cpu = CPU()
        assert cpu.pc == PROGRAM_START
        assert cpu.I == 0
        assert cpu.sp == 0
        assert all(v == 0 for v in cpu.V)

    def test_reset(self):
        cpu = CPU()
        cpu.V[0] = 42
        cpu.pc = 0x300
        cpu.reset()
        assert cpu.pc == PROGRAM_START
        assert cpu.V[0] == 0

    def test_load_rom(self):
        cpu = CPU()
        rom = build_test_rom([0x6005])  # LD V0, 5
        cpu.load_rom(rom)
        assert cpu.memory.read(PROGRAM_START) == 0x60
        assert cpu.memory.read(PROGRAM_START + 1) == 0x05


class TestOpcode00E0_CLS:
    """Test 00E0 — clear screen."""

    def test_cls(self):
        # Build a ROM with CLS at 0x200, then an infinite loop at 0x202
        rom = build_test_rom([0x00E0, 0x1202])
        cpu = CPU()
        cpu.load_rom(rom)
        cpu.display.set(5, 5, True)
        assert cpu.display.get(5, 5) is True
        cpu.step()  # CLS
        assert cpu.display.get(5, 5) is False


class TestOpcode00EE_RET:
    """Test 00EE — return from subroutine."""

    def test_call_and_ret(self):
        # 0x200: CALL 0x204
        # 0x202: JP 0x202 (halt loop)
        # 0x204: RET
        rom = build_test_rom([0x2204, 0x1202, 0x00EE])
        cpu = CPU()
        cpu.load_rom(rom)
        cpu.step()  # CALL 0x204 → PC=0x204, sp=1
        assert cpu.pc == 0x204
        assert cpu.sp == 1
        cpu.step()  # RET → PC=0x202
        assert cpu.pc == 0x202
        assert cpu.sp == 0


class TestOpcode1NNN_JP:
    """Test 1NNN — jump."""

    def test_jump(self):
        cpu = cpu_with_rom([0x1206, 0x0000, 0x0000, 0x1210])
        cpu.step()  # JP 0x206
        assert cpu.pc == 0x206


class TestOpcode2NNN_CALL:
    """Test 2NNN — call subroutine."""

    def test_call(self):
        # 0x200: CALL 0x206
        # 0x202: halt
        # 0x206: some instruction
        rom = build_test_rom([0x2206, 0x1202, 0x0000, 0x1210])
        cpu = CPU()
        cpu.load_rom(rom)
        cpu.step()  # CALL 0x206
        assert cpu.pc == 0x206
        assert cpu.sp == 1
        assert cpu.stack[0] == 0x202


class TestOpcode3xkk_SE:
    """Test 3xkk — skip if equal."""

    def test_skip_when_equal(self):
        # 0x3005 = SE V0, 5 — note x = (0x3005 >> 8) & 0xF = 0
        cpu = cpu_with_rom([0x6005, 0x3005])  # LD V0, 5; SE V0, 5
        cpu.step()  # LD V0, 5
        cpu.step()  # SE V0, 5 → should skip
        assert cpu.pc == 0x206  # Skipped past 0x204

    def test_no_skip_when_not_equal(self):
        cpu = cpu_with_rom([0x6005, 0x3006])  # LD V0, 5; SE V0, 6
        cpu.step()
        cpu.step()
        assert cpu.pc == 0x204  # Did NOT skip


class TestOpcode4xkk_SNE:
    """Test 4xkk — skip if not equal."""

    def test_skip_when_not_equal(self):
        cpu = cpu_with_rom([0x6005, 0x4006])  # LD V0, 5; SNE V0, 6
        cpu.step()
        cpu.step()
        assert cpu.pc == 0x206

    def test_no_skip_when_equal(self):
        cpu = cpu_with_rom([0x6005, 0x4005])  # LD V0, 5; SNE V0, 5
        cpu.step()
        cpu.step()
        assert cpu.pc == 0x204


class TestOpcode5xy0_SE_reg:
    """Test 5xy0 — skip if Vx == Vy."""

    def test_skip_when_equal(self):
        cpu = cpu_with_rom([0x6005, 0x6105, 0x5010])  # LD V0,5; LD V1,5; SE V0,V1
        cpu.step()
        cpu.step()
        cpu.step()
        assert cpu.pc == 0x208

    def test_no_skip_when_not_equal(self):
        cpu = cpu_with_rom([0x6005, 0x6107, 0x5010])  # LD V0,5; LD V1,7; SE V0,V1
        cpu.step()
        cpu.step()
        cpu.step()
        assert cpu.pc == 0x206


class TestOpcode6xkk_LD:
    """Test 6xkk — load byte."""

    def test_ld(self):
        cpu = cpu_with_rom([0x60AB])  # LD V0, 0xAB
        cpu.step()
        assert cpu.V[0] == 0xAB

    def test_ld_various_registers(self):
        cpu = cpu_with_rom([0x60FF, 0x61AB, 0x62CD])  # LD V0,FF; LD V1,AB; LD V2,CD
        cpu.step()
        cpu.step()
        cpu.step()
        assert cpu.V[0] == 0xFF
        assert cpu.V[1] == 0xAB
        assert cpu.V[2] == 0xCD


class TestOpcode7xkk_ADD:
    """Test 7xkk — add byte (no carry)."""

    def test_add_no_overflow(self):
        cpu = cpu_with_rom([0x6005, 0x7003])  # LD V0,5; ADD V0,3
        cpu.step()
        cpu.step()
        assert cpu.V[0] == 8

    def test_add_overflow_wraps(self):
        cpu = cpu_with_rom([0x60FE, 0x7005])  # LD V0, 0xFE; ADD V0, 5
        cpu.step()
        cpu.step()
        assert cpu.V[0] == (0xFE + 5) & 0xFF
        assert cpu.V[0xF] == 0  # VF not affected by 7xkk


class TestOpcode8xy0_LD_reg:
    """Test 8xy0 — LD Vx, Vy."""

    def test_ld_reg(self):
        cpu = cpu_with_rom([0x61AB, 0x8010])  # LD V1,0xAB; LD V0, V1
        cpu.step()
        cpu.step()
        assert cpu.V[0] == 0xAB


class TestOpcode8xy1_OR:
    """Test 8xy1 — OR."""

    def test_or_values(self):
        cpu = cpu_with_rom([0x60F0, 0x610F, 0x8011])
        cpu.step()
        cpu.step()
        cpu.step()
        assert cpu.V[0] == 0xF0 | 0x0F  # 0xFF


class TestOpcode8xy2_AND:
    """Test 8xy2 — AND."""

    def test_and(self):
        cpu = cpu_with_rom([0x60FF, 0x610F, 0x8012])
        cpu.step()
        cpu.step()
        cpu.step()
        assert cpu.V[0] == 0xFF & 0x0F  # 0x0F


class TestOpcode8xy3_XOR:
    """Test 8xy3 — XOR."""

    def test_xor(self):
        cpu = cpu_with_rom([0x60F0, 0x61F0, 0x8013])
        cpu.step()
        cpu.step()
        cpu.step()
        assert cpu.V[0] == 0xF0 ^ 0xF0  # 0x00


class TestOpcode8xy4_ADD_reg:
    """Test 8xy4 — ADD Vx, Vy with carry."""

    def test_add_no_carry(self):
        cpu = cpu_with_rom([0x6005, 0x6103, 0x8014])  # V0=5, V1=3, ADD V0,V1
        cpu.step()
        cpu.step()
        cpu.step()
        assert cpu.V[0] == 8
        assert cpu.V[0xF] == 0

    def test_add_with_carry(self):
        cpu = cpu_with_rom([0x60FF, 0x6102, 0x8014])  # V0=0xFF, V1=2, ADD V0,V1
        cpu.step()
        cpu.step()
        cpu.step()
        assert cpu.V[0] == 1
        assert cpu.V[0xF] == 1


class TestOpcode8xy5_SUB:
    """Test 8xy5 — SUB Vx, Vy with borrow."""

    def test_sub_no_borrow(self):
        cpu = cpu_with_rom([0x6005, 0x6103, 0x8015])  # V0=5, V1=3, SUB V0,V1
        cpu.step()
        cpu.step()
        cpu.step()
        assert cpu.V[0] == 2
        assert cpu.V[0xF] == 1

    def test_sub_with_borrow(self):
        cpu = cpu_with_rom([0x6003, 0x6105, 0x8015])  # V0=3, V1=5, SUB V0,V1
        cpu.step()
        cpu.step()
        cpu.step()
        assert cpu.V[0] == (3 - 5) & 0xFF  # 0xFE
        assert cpu.V[0xF] == 0


class TestOpcode8xy6_SHR:
    """Test 8xy6 — SHR (shift right, CHIP-48 convention)."""

    def test_shr_lsb_0(self):
        cpu = cpu_with_rom([0x6008, 0x8016])  # V0=8 (LSB=0), SHR
        cpu.step()
        cpu.step()
        assert cpu.V[0] == 4
        assert cpu.V[0xF] == 0

    def test_shr_lsb_1(self):
        cpu = cpu_with_rom([0x6009, 0x8016])  # V0=9 (LSB=1), SHR
        cpu.step()
        cpu.step()
        assert cpu.V[0] == 4
        assert cpu.V[0xF] == 1


class TestOpcode8xy7_SUBN:
    """Test 8xy7 — SUBN Vx, Vy."""

    def test_subn_no_borrow(self):
        cpu = cpu_with_rom([0x6003, 0x6105, 0x8017])  # V0=3, V1=5, SUBN V0,V1 → V0=5-3=2
        cpu.step()
        cpu.step()
        cpu.step()
        assert cpu.V[0] == 2
        assert cpu.V[0xF] == 1

    def test_subn_with_borrow(self):
        cpu = cpu_with_rom([0x6005, 0x6103, 0x8017])  # V0=5, V1=3, SUBN V0,V1 → V0=3-5
        cpu.step()
        cpu.step()
        cpu.step()
        assert cpu.V[0] == (3 - 5) & 0xFF
        assert cpu.V[0xF] == 0


class TestOpcode8xyE_SHL:
    """Test 8xyE — SHL (shift left)."""

    def test_shl_msb_0(self):
        cpu = cpu_with_rom([0x6004, 0x801E])  # V0=4 (MSB=0), SHL
        cpu.step()
        cpu.step()
        assert cpu.V[0] == 8
        assert cpu.V[0xF] == 0

    def test_shl_msb_1(self):
        cpu = cpu_with_rom([0x6080, 0x801E])  # V0=0x80 (MSB=1), SHL
        cpu.step()
        cpu.step()
        assert cpu.V[0] == 0  # 0x80 << 1 = 0x100, wrapped to 0
        assert cpu.V[0xF] == 1


class TestOpcode9xy0_SNE_reg:
    """Test 9xy0 — skip if Vx != Vy."""

    def test_skip_when_not_equal(self):
        cpu = cpu_with_rom([0x6005, 0x6107, 0x9010])
        cpu.step()
        cpu.step()
        cpu.step()
        assert cpu.pc == 0x208

    def test_no_skip_when_equal(self):
        cpu = cpu_with_rom([0x6005, 0x6105, 0x9010])
        cpu.step()
        cpu.step()
        cpu.step()
        assert cpu.pc == 0x206


class TestOpcodeANNN_LD_I:
    """Test ANNN — LD I, addr."""

    def test_ld_i(self):
        cpu = cpu_with_rom([0xA300])  # LD I, 0x300
        cpu.step()
        assert cpu.I == 0x300


class TestOpcodeBNNN_JP_V0:
    """Test BNNN — JP V0, addr."""

    def test_jump_with_offset(self):
        cpu = cpu_with_rom([0x6005, 0xB200])  # LD V0, 5; JP V0, 0x200
        cpu.step()
        cpu.step()
        assert cpu.pc == 0x200 + 5


class TestOpcodeCxkk_RND:
    """Test Cxkk — RND Vx, byte."""

    def test_random_masked(self):
        cpu = cpu_with_rom([0xC00F])  # RND V0, 0x0F
        cpu.step()
        assert 0 <= cpu.V[0] <= 0x0F


class TestOpcodeDxyn_DRW:
    """Test Dxyn — draw sprite."""

    def test_draw_no_collision(self):
        rom = build_test_rom([
            0x600A,  # LD V0, 10 (x)
            0x610A,  # LD V1, 10 (y)
            0xA20C,  # LD I, 0x20C (sprite data address)
            0xD015,  # DRW V0, V1, 5
        ])
        # Append sprite data at 0x20C (0x0C bytes from 0x200)
        rom = rom + bytes([0xFF, 0xFF, 0xFF, 0xFF, 0xFF])
        cpu = CPU()
        cpu.load_rom(rom)
        for _ in range(4):
            cpu.step()
        assert cpu.V[0xF] == 0  # No collision

    def test_draw_collision(self):
        # Draw same sprite twice at same position
        # 6 instructions = 12 bytes, sprite at offset 12 → address 0x20C
        rom = build_test_rom([
            0x600A,  # LD V0, 10
            0x610A,  # LD V1, 10
            0xA20C,  # LD I, 0x20C (sprite data)
            0xD015,  # DRW V0, V1, 5
            0xD015,  # DRW V0, V1, 5  — collision!
            0x1218,  # halt loop
        ])
        rom = rom + bytes([0xFF, 0xFF, 0xFF, 0xFF, 0xFF])
        cpu = CPU()
        cpu.load_rom(rom)
        for _ in range(5):
            cpu.step()
        assert cpu.V[0xF] == 1  # Collision detected


class TestOpcodeEx9E_SKP:
    """Test Ex9E — skip if key pressed."""

    def test_skip_pressed(self):
        cpu = cpu_with_rom([0x6005, 0xE09E])  # LD V0, 5; SKP V0
        cpu.keypad.press(5)
        cpu.step()
        cpu.step()
        assert cpu.pc == 0x206  # Skipped

    def test_no_skip_not_pressed(self):
        cpu = cpu_with_rom([0x6005, 0xE09E])
        cpu.step()
        cpu.step()
        assert cpu.pc == 0x204


class TestOpcodeExA1_SKNP:
    """Test ExA1 — skip if key NOT pressed."""

    def test_skip_not_pressed(self):
        cpu = cpu_with_rom([0x6005, 0xE0A1])
        cpu.step()
        cpu.step()
        assert cpu.pc == 0x206

    def test_no_skip_pressed(self):
        cpu = cpu_with_rom([0x6005, 0xE0A1])
        cpu.keypad.press(5)
        cpu.step()
        cpu.step()
        assert cpu.pc == 0x204


class TestOpcodeFx07_LD_DT:
    """Test Fx07 — LD Vx, DT."""

    def test_read_delay_timer(self):
        cpu = cpu_with_rom([0xF007])
        cpu.dt.set(42)
        cpu.step()
        assert cpu.V[0] == 42


class TestOpcodeFx0A_LD_K:
    """Test Fx0A — LD Vx, K (wait for key)."""

    def test_no_key_loops(self):
        cpu = cpu_with_rom([0xF00A])
        cpu.step()
        assert cpu.pc == 0x200  # Backed up

    def test_key_pressed(self):
        cpu = cpu_with_rom([0xF00A])
        cpu.keypad.press(7)
        cpu.step()
        assert cpu.V[0] == 7
        assert cpu.pc == 0x202


class TestOpcodeFx15_LD_DT_Vx:
    """Test Fx15 — LD DT, Vx."""

    def test_set_delay_timer(self):
        cpu = cpu_with_rom([0x600A, 0xF015])
        cpu.step()
        cpu.step()
        assert cpu.dt.get() == 10


class TestOpcodeFx18_LD_ST_Vx:
    """Test Fx18 — LD ST, Vx."""

    def test_set_sound_timer(self):
        cpu = cpu_with_rom([0x6005, 0xF018])
        cpu.step()
        cpu.step()
        assert cpu.st.get() == 5


class TestOpcodeFx1E_ADD_I:
    """Test Fx1E — ADD I, Vx."""

    def test_add_to_i(self):
        cpu = cpu_with_rom([0xA200, 0x6010, 0xF01E])
        cpu.step()
        cpu.step()
        cpu.step()
        assert cpu.I == 0x210


class TestOpcodeFx29_LD_F:
    """Test Fx29 — LD F, Vx (font sprite)."""

    def test_font_sprite_addr(self):
        cpu = cpu_with_rom([0x6003, 0xF029])
        cpu.step()
        cpu.step()
        assert cpu.I == 0x050 + 3 * 5


class TestOpcodeFx33_BCD:
    """Test Fx33 — BCD conversion."""

    def test_bcd_255(self):
        cpu = cpu_with_rom([0x60FF, 0xA300, 0xF033])
        cpu.step()
        cpu.step()
        cpu.step()
        assert cpu.memory.read(0x300) == 2
        assert cpu.memory.read(0x301) == 5
        assert cpu.memory.read(0x302) == 5

    def test_bcd_123(self):
        cpu = cpu_with_rom([0x607B, 0xA300, 0xF033])
        cpu.step()
        cpu.step()
        cpu.step()
        assert cpu.memory.read(0x300) == 1
        assert cpu.memory.read(0x301) == 2
        assert cpu.memory.read(0x302) == 3

    def test_bcd_0(self):
        cpu = cpu_with_rom([0x6000, 0xA300, 0xF033])
        cpu.step()
        cpu.step()
        cpu.step()
        assert cpu.memory.read(0x300) == 0
        assert cpu.memory.read(0x301) == 0
        assert cpu.memory.read(0x302) == 0


class TestOpcodeFx55_LD_I_Vx:
    """Test Fx55 — store V0..Vx in memory at I."""

    def test_store_registers(self):
        cpu = cpu_with_rom([0x6001, 0x6102, 0x6203, 0xA300, 0xF255])
        for _ in range(5):
            cpu.step()
        assert cpu.memory.read(0x300) == 1  # V0
        assert cpu.memory.read(0x301) == 2  # V1
        assert cpu.memory.read(0x302) == 3  # V2


class TestOpcodeFx65_LD_Vx_I:
    """Test Fx65 — load V0..Vx from memory at I."""

    def test_load_registers(self):
        cpu = CPU()
        cpu.memory.write(0x300, 0xAA)
        cpu.memory.write(0x301, 0xBB)
        cpu.memory.write(0x302, 0xCC)
        rom = build_test_rom([0xA300, 0xF265])
        cpu.load_rom(rom)
        cpu.step()
        cpu.step()
        assert cpu.V[0] == 0xAA
        assert cpu.V[1] == 0xBB
        assert cpu.V[2] == 0xCC


class TestStackOperations:
    """Test call stack behavior."""
    def test_nested_calls(self):
        # Layout:
        # 0x200: CALL 0x206  (pushes 0x202, jumps to 0x206)
        # 0x202: JP 0x202    (halt loop)
        # 0x206: CALL 0x20C  (pushes 0x208, jumps to 0x20C)
        # 0x208: RET
        # 0x20A: NOP (padding)
        # 0x20C: RET
        rom = build_test_rom([
            0x2206,  # 0x200: CALL 0x206
            0x1202,  # 0x202: JP 0x202 (halt loop)
            0x220C,  # 0x204: (unused, but harmless)
        ])
        # We need to place instructions at specific addresses.
        # Manually build the ROM:
        data = bytearray(16)  # 16 bytes from 0x200 to 0x20F
        # 0x200-0x201: CALL 0x206
        data[0] = 0x22; data[1] = 0x06
        # 0x202-0x203: JP 0x202
        data[2] = 0x12; data[3] = 0x02
        # 0x206-0x207: CALL 0x20C
        data[6] = 0x22; data[7] = 0x0C
        # 0x208-0x209: RET
        data[8] = 0x00; data[9] = 0xEE
        # 0x20C-0x20D: RET
        data[12] = 0x00; data[13] = 0xEE
        cpu = CPU()
        cpu.load_rom(bytes(data))

        cpu.step()  # CALL 0x206
        assert cpu.pc == 0x206
        assert cpu.sp == 1

        cpu.step()  # CALL 0x20C
        assert cpu.pc == 0x20C
        assert cpu.sp == 2

        cpu.step()  # RET from 0x20C
        assert cpu.pc == 0x208
        assert cpu.sp == 1

        cpu.step()  # RET from 0x208
        assert cpu.pc == 0x202
        assert cpu.sp == 0

    def test_stack_underflow(self):
        cpu = cpu_with_rom([0x00EE])  # RET with empty stack
        with pytest.raises(CpuError, match="Stack underflow"):
            cpu.step()

    def test_stack_overflow(self):
        # Build a ROM that calls itself repeatedly
        # 0x200: CALL 0x200
        # This will overflow the 16-level stack
        rom = build_test_rom([0x2200, 0x0000])
        cpu = CPU()
        cpu.load_rom(rom)
        with pytest.raises(CpuError, match="Stack overflow"):
            for _ in range(20):
                cpu.step()


class TestUnknownOpcode:
    """Test handling of unknown opcodes."""

    def test_unknown_opcode(self):
        cpu = CPU()
        cpu.memory.write(PROGRAM_START, 0xF0)
        cpu.memory.write(PROGRAM_START + 1, 0x00)
        with pytest.raises(CpuError, match="Unknown F-prefixed opcode"):
            cpu.step()


class TestCPUHaltAndRun:
    """Test CPU run loop."""

    def test_run_with_cycle_limit(self):
        cpu = cpu_with_rom([0x6005, 0x1210, 0x1210])
        cpu.run(cycles=3)
        assert cpu.V[0] == 5