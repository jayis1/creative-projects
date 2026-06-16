"""Tests for the CHIP-8 tracer/profiler."""

import pytest
from chip8_emulator import CPU
from chip8_emulator.tracer import Tracer, ProfileStats, _classify_opcode
from chip8_emulator.cli import build_test_rom


class TestTracerBasic:
    """Test basic tracer functionality."""

    def test_tracer_creation(self):
        cpu = CPU()
        tracer = Tracer(cpu)
        assert tracer.stats.total_cycles == 0

    def test_tracer_attach(self):
        cpu = CPU()
        tracer = Tracer(cpu)
        tracer.attach()
        assert cpu._on_step is not None

    def test_tracer_detach(self):
        cpu = CPU()
        tracer = Tracer(cpu)
        tracer.attach()
        tracer.detach()
        assert cpu._on_step is None

    def test_tracer_records_cycles(self):
        cpu = CPU()
        tracer = Tracer(cpu)
        tracer.attach()
        # Load simple ROM: LD V0, 5
        cpu.load_rom(build_test_rom([0x6005, 0x1210, 0x1210]))
        cpu.run(cycles=5)
        tracer.detach()
        assert tracer.stats.total_cycles == 5

    def test_tracer_opcode_frequency(self):
        cpu = CPU()
        tracer = Tracer(cpu)
        tracer.attach()
        # LD V0, 5 / JP 0x210 / JP 0x210 (halt loop)
        cpu.load_rom(build_test_rom([0x6005, 0x1210, 0x1210]))
        cpu.run(cycles=10)
        tracer.detach()
        assert tracer.stats.opcode_counts["LD byte"] > 0
        assert tracer.stats.opcode_counts["JP"] > 0

    def test_tracer_address_tracking(self):
        cpu = CPU()
        tracer = Tracer(cpu)
        tracer.attach()
        cpu.load_rom(build_test_rom([0x6005, 0x1210, 0x1210]))
        cpu.run(cycles=10)
        tracer.detach()
        # 0x200 should be the most hit address (LD V0, 5)
        top = tracer.stats.top_addresses(1)
        assert len(top) == 1
        assert top[0][0] == 0x200

    def test_tracer_draw_count(self):
        cpu = CPU()
        tracer = Tracer(cpu)
        tracer.attach()
        # ROM with draw: CLS / DRW V0, V1, 5 / JP 0x202 (halt loop)
        rom = build_test_rom([0x00E0, 0xD015, 0x1204])
        cpu.load_rom(rom)
        cpu.run(cycles=10)
        tracer.detach()
        assert tracer.stats.draw_calls > 0

    def test_tracer_max_entries(self):
        cpu = CPU()
        tracer = Tracer(cpu, max_entries=5)
        tracer.attach()
        cpu.load_rom(build_test_rom([0x6005, 0x1210, 0x1210]))
        cpu.run(cycles=20)
        tracer.detach()
        assert len(tracer.trace) <= 5

    def test_tracer_clear(self):
        cpu = CPU()
        tracer = Tracer(cpu)
        tracer.attach()
        cpu.load_rom(build_test_rom([0x6005, 0x1210, 0x1210]))
        cpu.run(cycles=5)
        tracer.detach()
        assert tracer.stats.total_cycles > 0
        tracer.clear()
        assert tracer.stats.total_cycles == 0


class TestTracerSummary:
    """Test tracer summary output."""

    def test_summary_output(self):
        cpu = CPU()
        tracer = Tracer(cpu)
        tracer.attach()
        cpu.load_rom(build_test_rom([0x6005, 0x1210, 0x1210]))
        cpu.run(cycles=10)
        tracer.detach()
        summary = tracer.summary()
        assert "CHIP-8 Execution Profile" in summary
        assert "Total cycles" in summary

    def test_stats_to_dict(self):
        cpu = CPU()
        tracer = Tracer(cpu)
        tracer.attach()
        cpu.load_rom(build_test_rom([0x6005, 0x1210, 0x1210]))
        cpu.run(cycles=5)
        tracer.detach()
        d = tracer.stats.to_dict()
        assert "total_cycles" in d
        assert "opcode_counts" in d

    def test_stats_to_json(self):
        cpu = CPU()
        tracer = Tracer(cpu)
        tracer.attach()
        cpu.load_rom(build_test_rom([0x6005, 0x1210, 0x1210]))
        cpu.run(cycles=5)
        tracer.detach()
        json_str = tracer.stats.to_json()
        assert "total_cycles" in json_str


class TestClassifyOpcode:
    """Test opcode classification."""

    def test_cls(self):
        assert _classify_opcode(0x00E0) == "CLS"

    def test_ret(self):
        assert _classify_opcode(0x00EE) == "RET"

    def test_jump(self):
        assert _classify_opcode(0x1200) == "JP"

    def test_ld_byte(self):
        assert _classify_opcode(0x6005) == "LD byte"

    def test_drw(self):
        assert _classify_opcode(0xD015) == "DRW"

    def test_add_reg(self):
        assert _classify_opcode(0x8014) == "ADD reg"

    def test_exit(self):
        assert _classify_opcode(0x00FD) == "EXIT"