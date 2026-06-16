"""Tests for SUPER-CHIP extensions and advanced CPU features."""

import pytest
from chip8_emulator.cpu import CPU, CpuError
from chip8_emulator.cli import build_test_rom


class TestSuperChipExtensions:
    """Test SUPER-CHIP extension opcodes."""

    def test_extended_mode_flag(self):
        """00FF — enable extended mode."""
        cpu = CPU(super_chip=True)
        cpu.load_rom(build_test_rom([0x00FF]))
        assert not cpu.extended_mode
        cpu.step()
        assert cpu.extended_mode

    def test_exit_halt(self):
        """00FD — exit interpreter should halt the CPU."""
        cpu = CPU(super_chip=True)
        cpu.load_rom(build_test_rom([0x00FD]))
        cpu._running = True
        cpu.step()
        assert not cpu._running

    def test_scroll_down(self):
        """00Cn — scroll down n lines."""
        cpu = CPU(super_chip=True)
        cpu.display.set(5, 0, True)
        # Manually write scroll-down opcode: 00C2 (scroll down 2 lines)
        cpu.memory.write(0x200, 0x00)
        cpu.memory.write(0x201, 0xC2)
        cpu.step()
        assert cpu.display.get(5, 2) is True
        assert cpu.display.get(5, 0) is False

    def test_scroll_left(self):
        """00FB — scroll left 4 pixels."""
        cpu = CPU(super_chip=True)
        cpu.display.set(10, 5, True)
        cpu.memory.write(0x200, 0x00)
        cpu.memory.write(0x201, 0xFB)
        cpu.step()
        assert cpu.display.get(6, 5) is True
        assert cpu.display.get(10, 5) is False

    def test_scroll_right(self):
        """00FC — scroll right 4 pixels."""
        cpu = CPU(super_chip=True)
        cpu.display.set(10, 5, True)
        cpu.memory.write(0x200, 0x00)
        cpu.memory.write(0x201, 0xFC)
        cpu.step()
        assert cpu.display.get(14, 5) is True
        assert cpu.display.get(10, 5) is False

    def test_rpl_save_load(self):
        """Fx75 / Fx85 — save and load RPL flags."""
        cpu = CPU(super_chip=True)
        # V0=0xAA, V1=0xBB, LD R, V1 (save V0..V1 to R0..R1)
        # Then clear V0,V1 and load back
        rom = build_test_rom([
            0x60AA,  # LD V0, 0xAA
            0x61BB,  # LD V1, 0xBB
            0xF175,  # LD R, V1 (save V0..V1)
            0x6000,  # LD V0, 0
            0x6100,  # LD V1, 0
            0xF185,  # LD V1, R (load R0..R1 into V0..V1)
        ])
        cpu.load_rom(rom)
        for _ in range(6):
            cpu.step()
        assert cpu.V[0] == 0xAA
        assert cpu.V[1] == 0xBB

    def test_large_font_addr(self):
        """Fx30 — LD HF, Vx should set I to large font address."""
        cpu = CPU(super_chip=True)
        cpu.load_rom(build_test_rom([0x6005, 0xF030]))  # LD V0, 5; LD HF, V0
        cpu.step()
        cpu.step()
        assert cpu.I == 0x090 + 5 * 10  # Large font for digit 5

    def test_super_chip_stack_size(self):
        """SUPER-CHIP mode should have a 24-entry stack."""
        cpu = CPU(super_chip=True)
        assert cpu._max_stack == 24

    def test_standard_chip_stack_size(self):
        """Standard mode should have a 16-entry stack."""
        cpu = CPU()
        assert cpu._max_stack == 16

    def test_jump_with_extended_mode(self):
        """Bxkk — in extended mode, jump uses Vx instead of V0."""
        cpu = CPU(super_chip=True)
        rom = build_test_rom([0x6105, 0xB100])
        cpu.load_rom(rom)
        # Set extended mode AFTER load_rom (which calls reset)
        cpu.extended_mode = True
        cpu.step()  # LD V1, 5
        cpu.step()  # JP V1, 0x100 → PC = 0x100 + V1 = 0x105
        assert cpu.pc == 0x105


class TestCycleCounter:
    """Test CPU cycle counting."""

    def test_initial_cycles(self):
        cpu = CPU()
        assert cpu.cycles == 0

    def test_step_increments_cycles(self):
        cpu = CPU()
        cpu.load_rom(build_test_rom([0x6005]))
        cpu.step()
        assert cpu.cycles == 1

    def test_run_counts_cycles(self):
        cpu = CPU()
        cpu.load_rom(build_test_rom([0x6005, 0x1210, 0x1210]))
        count = cpu.run(cycles=3)
        assert count == 3
        assert cpu.cycles == 3

    def test_reset_clears_cycles(self):
        cpu = CPU()
        cpu.load_rom(build_test_rom([0x6005]))
        cpu.step()
        assert cpu.cycles == 1
        cpu.reset()
        assert cpu.cycles == 0


class TestStepCallback:
    """Test on_step callback."""

    def test_callback_called(self):
        calls = []

        def on_step(cpu, opcode):
            calls.append(opcode)

        cpu = CPU(on_step=on_step)
        cpu.load_rom(build_test_rom([0x6005]))
        cpu.step()
        assert len(calls) == 1
        assert calls[0] == 0x6005

    def test_callback_receives_cpu_state(self):
        states = []

        def on_step(cpu, opcode):
            states.append((cpu.pc, cpu.V[0]))

        cpu = CPU(on_step=on_step)
        cpu.load_rom(build_test_rom([0x6005, 0x6107]))
        cpu.step()
        cpu.step()
        assert len(states) == 2
        # After first step (LD V0, 5): pc advanced past 0x200
        assert states[0][1] == 5