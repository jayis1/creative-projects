"""Tests for the CHIP-8 recorder."""

import json
import tempfile
from pathlib import Path

import pytest
from chip8_emulator import CPU
from chip8_emulator.recorder import Recorder, StepRecord
from chip8_emulator.cli import build_test_rom


class TestRecorderBasic:
    """Test basic recorder functionality."""

    def test_recorder_creation(self):
        cpu = CPU()
        rec = Recorder(cpu)
        assert rec.step_count == 0
        assert not rec._recording

    def test_recorder_start_stop(self):
        cpu = CPU()
        rec = Recorder(cpu)
        rec.start()
        assert rec._recording
        rec.stop()
        assert not rec._recording

    def test_recorder_attach(self):
        cpu = CPU()
        rec = Recorder(cpu)
        rec.attach()
        assert cpu._on_step is not None

    def test_recorder_detach(self):
        cpu = CPU()
        rec = Recorder(cpu)
        rec.attach()
        rec.detach()
        assert cpu._on_step is None

    def test_recorder_records_steps(self):
        cpu = CPU()
        rec = Recorder(cpu)
        rec.attach()
        rec.start()
        cpu.load_rom(build_test_rom([0x6005, 0x1210, 0x1210]))
        cpu.run(cycles=5)
        rec.stop()
        rec.detach()
        assert rec.step_count == 5

    def test_recorder_max_steps(self):
        cpu = CPU()
        rec = Recorder(cpu, max_steps=3)
        rec.attach()
        rec.start()
        cpu.load_rom(build_test_rom([0x6005, 0x1210, 0x1210]))
        cpu.run(cycles=10)
        rec.detach()
        assert rec.step_count <= 3


class TestRecorderSerialization:
    """Test recorder save/load."""

    def test_save_and_load(self):
        cpu = CPU()
        rec = Recorder(cpu)
        rec._rom_data = b"\x60\x05\x12\x10"
        rec.attach()
        rec.start()
        cpu.load_rom(build_test_rom([0x6005, 0x1210, 0x1210]))
        cpu.run(cycles=5)
        rec.stop()
        rec.detach()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            rec.save(path)
            loaded = Recorder.load(path)
            assert loaded.step_count == 5
            assert loaded._rom_data == rec._rom_data
            assert loaded._steps[0].opcode == rec._steps[0].opcode
        finally:
            Path(path).unlink(missing_ok=True)

    def test_step_record_fields(self):
        cpu = CPU()
        rec = Recorder(cpu)
        rec._rom_data = b"\x60\x05"
        rec.attach()
        rec.start()
        cpu.load_rom(build_test_rom([0x6005, 0x1210]))
        cpu.run(cycles=1)
        rec.stop()
        rec.detach()

        step = rec.steps[0]
        assert isinstance(step, StepRecord)
        assert step.cycle == 1
        assert step.pc == 0x200
        assert step.opcode == 0x6005


class TestRecorderDiff:
    """Test trace comparison."""

    def test_identical_traces(self):
        cpu1 = CPU()
        rec1 = Recorder(cpu1)
        rec1._rom_data = build_test_rom([0x6005, 0x1210, 0x1210])
        rec1.attach()
        rec1.start()
        cpu1.load_rom(rec1._rom_data)
        cpu1.run(cycles=5)
        rec1.stop()
        rec1.detach()

        cpu2 = CPU()
        rec2 = Recorder(cpu2)
        rec2._rom_data = rec1._rom_data
        rec2.attach()
        rec2.start()
        cpu2.load_rom(rec2._rom_data)
        cpu2.run(cycles=5)
        rec2.stop()
        rec2.detach()

        diffs = rec1.diff(rec2)
        assert len(diffs) == 0

    def test_different_length_traces(self):
        cpu1 = CPU()
        rec1 = Recorder(cpu1)
        rec1._rom_data = build_test_rom([0x6005, 0x1210])
        rec1.attach()
        rec1.start()
        cpu1.load_rom(rec1._rom_data)
        cpu1.run(cycles=3)
        rec1.stop()
        rec1.detach()

        cpu2 = CPU()
        rec2 = Recorder(cpu2)
        rec2._rom_data = rec1._rom_data
        rec2.attach()
        rec2.start()
        cpu2.load_rom(rec2._rom_data)
        cpu2.run(cycles=5)
        rec2.stop()
        rec2.detach()

        diffs = rec1.diff(rec2)
        assert any("length" in d.lower() for d in diffs)


class TestRecorderToDict:
    """Test serialization helpers."""

    def test_to_dict(self):
        cpu = CPU()
        rec = Recorder(cpu)
        rec._rom_data = b"\x60\x05"
        d = rec.to_dict()
        assert "step_count" in d
        assert "super_chip" in d