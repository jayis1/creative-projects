"""Tests for the CHIP-8 debugger."""

import pytest
from chip8_emulator.cpu import CPU
from chip8_emulator.debugger import Debugger
from chip8_emulator.cli import build_test_rom


class TestDebuggerBreakpoints:
    """Test debugger breakpoint functionality."""

    def test_add_breakpoint(self):
        cpu = CPU()
        dbg = Debugger(cpu)
        dbg.add_breakpoint(0x200)
        assert dbg.list_breakpoints() == [0x200]

    def test_remove_breakpoint(self):
        cpu = CPU()
        dbg = Debugger(cpu)
        dbg.add_breakpoint(0x200)
        dbg.remove_breakpoint(0x200)
        assert dbg.list_breakpoints() == []

    def test_clear_breakpoints(self):
        cpu = CPU()
        dbg = Debugger(cpu)
        dbg.add_breakpoint(0x200)
        dbg.add_breakpoint(0x300)
        dbg.clear_breakpoints()
        assert dbg.list_breakpoints() == []

    def test_breakpoint_hit(self):
        # LD V0, 5; halt loop
        cpu = CPU()
        cpu.load_rom(build_test_rom([0x6005, 0x1202]))
        dbg = Debugger(cpu)
        dbg.add_breakpoint(0x202)
        # Run first step (0x200: LD V0, 5)
        dbg.step()
        assert cpu.pc == 0x202
        assert dbg.should_break()


class TestDebuggerTrace:
    """Test opcode tracing."""

    def test_enable_trace(self):
        cpu = CPU()
        cpu.load_rom(build_test_rom([0x6005]))
        dbg = Debugger(cpu)
        dbg.enable_trace()
        dbg.step()
        trace = dbg.get_trace()
        assert len(trace) == 1
        assert "6005" in trace[0]
        assert "LD" in trace[0]

    def test_disable_trace(self):
        cpu = CPU()
        cpu.load_rom(build_test_rom([0x6005]))
        dbg = Debugger(cpu)
        dbg.step()
        assert len(dbg.get_trace()) == 0

    def test_clear_trace(self):
        cpu = CPU()
        cpu.load_rom(build_test_rom([0x6005]))
        dbg = Debugger(cpu)
        dbg.enable_trace()
        dbg.step()
        dbg.clear_trace()
        assert len(dbg.get_trace()) == 0


class TestDebuggerRunUntilBreak:
    """Test run_until_break."""

    def test_run_until_break(self):
        # LD V0, 1; LD V0, 2; LD V0, 3; halt
        cpu = CPU()
        cpu.load_rom(build_test_rom([0x6001, 0x6002, 0x6003, 0x1208]))
        dbg = Debugger(cpu)
        dbg.add_breakpoint(0x204)  # Address of 3rd instruction
        cycles = dbg.run_until_break()
        assert cycles <= 3
        # V0 should have been set at least once (to 1, 2, or 3)
        assert cpu.V[0] in (1, 2, 3)


class TestDebuggerStateInspection:
    """Test state dump methods."""

    def test_dump_registers(self):
        cpu = CPU()
        cpu.load_rom(build_test_rom([0x6005]))
        dbg = Debugger(cpu)
        dump = dbg.dump_registers()
        assert "PC:" in dump
        assert "V0:" in dump

    def test_dump_stack(self):
        cpu = CPU()
        dbg = Debugger(cpu)
        dump = dbg.dump_stack()
        assert "SP:" in dump

    def test_dump_memory(self):
        cpu = CPU()
        dbg = Debugger(cpu)
        dump = dbg.dump_memory(0x200, 16)
        assert "0200:" in dump

    def test_dump_display(self):
        cpu = CPU()
        dbg = Debugger(cpu)
        dump = dbg.dump_display()
        assert len(dump) > 0

    def test_repr(self):
        cpu = CPU()
        dbg = Debugger(cpu)
        assert "Debugger" in repr(dbg)