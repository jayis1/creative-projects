"""Tests for new features: CLI, export, waveform, config."""

import pytest
import json
import tempfile
from pathlib import Path

from circuit_sim.core import Signal, Wire, Bus
from circuit_sim.circuit import Circuit
from circuit_sim.simulator import Simulator, Stimulus
from circuit_sim.cdl import parse_cdl
from circuit_sim.scope import Oscilloscope
from circuit_sim.analyze import TruthTable, CircuitStats
from circuit_sim.export import (
    circuit_to_dict, circuit_to_json, circuit_from_json,
    circuit_to_dot, circuit_to_ascii,
)
from circuit_sim.waveform import compare_traces, analyze_trace, format_trace_analysis
from circuit_sim.config import SimConfig
from circuit_sim.presets import build_alu_1bit


# ============================================================
# Export Tests
# ============================================================

class TestJsonExport:
    def test_round_trip_simple(self):
        """Export a circuit to JSON and reimport it."""
        circ = Circuit("test_json")
        a = circ.add_wire("a", Signal.LOW)
        b = circ.add_wire("b", Signal.LOW)
        out = circ.add_wire("out")
        circ.add_and("and1", a, b, out)

        json_str = circuit_to_json(circ)
        data = json.loads(json_str)
        assert data["name"] == "test_json"
        assert len(data["gates"]) == 1
        assert data["gates"][0]["type"] == "AndGate"

    def test_round_trip_file(self, tmp_path):
        """Export to file and reimport."""
        circ = Circuit("file_test")
        a = circ.add_wire("a", Signal.LOW)
        out = circ.add_wire("out")
        circ.add_not("not1", a, out)

        filepath = str(tmp_path / "test_circuit.json")
        circuit_to_json(circ, filepath)

        loaded = circuit_from_json(filepath)
        assert loaded.name == "file_test"
        assert len(loaded.wires) == 2
        assert len(loaded.gates) == 1

    def test_bus_export(self):
        """Export a circuit with a bus."""
        circ = Circuit("bus_export")
        bus = circ.add_bus("data", 4)
        json_str = circuit_to_json(circ)
        data = json.loads(json_str)
        assert "data" in data["buses"]
        assert data["buses"]["data"]["width"] == 4

    def test_sequential_export(self):
        """Export a circuit with sequential elements."""
        circ = Circuit("seq_export")
        d = circ.add_wire("d", Signal.LOW)
        clk = circ.add_wire("clk", Signal.LOW)
        q = circ.add_wire("q", Signal.LOW)
        qbar = circ.add_wire("qbar", Signal.HIGH)
        circ.add_d_flipflop("dff", d, clk, q, qbar)

        json_str = circuit_to_json(circ)
        data = json.loads(json_str)
        assert len(data["sequential"]) == 1
        assert data["sequential"][0]["type"] == "DFlipFlop"

    def test_clock_export(self):
        """Export a circuit with a clock."""
        circ = Circuit("clk_export")
        clk = circ.add_wire("clk", Signal.LOW)
        circ.add_clock("sysclk", clk, period_ns=20, duty_cycle=0.5)

        json_str = circuit_to_json(circ)
        data = json.loads(json_str)
        assert len(data["clocks"]) == 1
        assert data["clocks"][0]["period_ns"] == 20


class TestDotExport:
    def test_basic_dot(self):
        """Export a circuit to DOT format."""
        circ = Circuit("dot_test")
        a = circ.add_wire("a", Signal.LOW)
        b = circ.add_wire("b", Signal.LOW)
        out = circ.add_wire("out")
        circ.add_and("and1", a, b, out)

        dot = circuit_to_dot(circ)
        assert "digraph" in dot
        assert "and1" in dot
        assert '"a"' in dot
        assert '"b"' in dot

    def test_dot_with_sequential(self):
        """Export circuit with sequential elements."""
        circ = Circuit("dot_seq")
        d = circ.add_wire("d", Signal.LOW)
        clk = circ.add_wire("clk", Signal.LOW)
        q = circ.add_wire("q", Signal.LOW)
        qbar = circ.add_wire("qbar", Signal.HIGH)
        circ.add_d_flipflop("dff", d, clk, q, qbar)
        circ.add_clock("clk1", clk, period_ns=20)

        dot = circuit_to_dot(circ)
        assert "DFlipFlop" in dot
        assert "CLK" in dot


class TestAsciiExport:
    def test_ascii_schematic(self):
        """Generate ASCII schematic."""
        circ = Circuit("ascii_test")
        a = circ.add_wire("a", Signal.LOW)
        b = circ.add_wire("b", Signal.LOW)
        out = circ.add_wire("out")
        circ.add_or("or1", a, b, out)

        ascii_art = circuit_to_ascii(circ)
        assert "ascii_test" in ascii_art
        assert "or1" in ascii_art
        assert "INPUTS" in ascii_art
        assert "OUTPUTS" in ascii_art


class TestCircuitToDict:
    def test_to_dict(self):
        """Test circuit_to_dict returns proper dict."""
        circ = Circuit("dict_test")
        a = circ.add_wire("a", Signal.LOW)
        out = circ.add_wire("out")
        circ.add_not("not1", a, out)

        d = circuit_to_dict(circ)
        assert d["name"] == "dict_test"
        assert "a" in d["wires"]
        assert len(d["gates"]) == 1


# ============================================================
# Waveform Analysis Tests
# ============================================================

class TestWaveformAnalysis:
    def test_analyze_trace_empty(self):
        """Analyze an empty trace."""
        result = analyze_trace([], "empty")
        assert result["transitions"] == 0
        assert result["name"] == "empty"

    def test_analyze_trace_single(self):
        """Analyze a single-event trace."""
        trace = [(0, Signal.HIGH)]
        result = analyze_trace(trace, "single")
        assert result["transitions"] == 0
        assert result["start_signal"] == "HIGH"
        assert result["end_signal"] == "HIGH"

    def test_analyze_trace_transitions(self):
        """Analyze a trace with transitions."""
        trace = [
            (0, Signal.LOW),
            (10, Signal.HIGH),
            (20, Signal.LOW),
            (30, Signal.HIGH),
        ]
        result = analyze_trace(trace, "clock")
        assert result["transitions"] == 3  # LOW->HIGH, HIGH->LOW, LOW->HIGH
        assert result["rising_edges"] == 2
        assert result["falling_edges"] == 1

    def test_compare_identical_traces(self):
        """Compare two identical traces."""
        trace = [(0, Signal.LOW), (10, Signal.HIGH)]
        result = compare_traces(trace, trace)
        assert result["match"] is True
        assert len(result["differences"]) == 0

    def test_compare_different_traces(self):
        """Compare two different traces."""
        trace_a = [(0, Signal.LOW), (10, Signal.HIGH)]
        trace_b = [(0, Signal.HIGH)]
        result = compare_traces(trace_a, trace_b)
        assert result["match"] is False
        assert len(result["differences"]) > 0

    def test_format_analysis(self):
        """Format analysis results."""
        trace = [(0, Signal.HIGH)]
        result = analyze_trace(trace, "test_sig")
        formatted = format_trace_analysis(result)
        assert "test_sig" in formatted
        assert "Transitions" in formatted


# ============================================================
# Config Tests
# ============================================================

class TestSimConfig:
    def test_default_config(self):
        """Test default configuration values."""
        config = SimConfig()
        assert config.step_ns == 1
        assert config.default_gate_delay_ns == 1
        assert config.default_clock_period_ns == 20

    def test_config_to_dict(self):
        """Test config serialization to dict."""
        config = SimConfig(step_ns=5)
        d = config.to_dict()
        assert d["step_ns"] == 5

    def test_config_from_dict(self):
        """Test config deserialization from dict."""
        config = SimConfig.from_dict({"step_ns": 10, "default_gate_delay_ns": 3})
        assert config.step_ns == 10
        assert config.default_gate_delay_ns == 3
        # Other fields should be defaults
        assert config.default_clock_period_ns == 20

    def test_config_json_roundtrip(self, tmp_path):
        """Test config JSON round-trip."""
        config = SimConfig(step_ns=2, log_level="DEBUG")
        json_str = config.to_json()
        config2 = SimConfig.from_json(json_str)
        assert config2.step_ns == 2
        assert config2.log_level == "DEBUG"

    def test_config_json_file(self, tmp_path):
        """Test config JSON file I/O."""
        config = SimConfig(step_ns=5)
        filepath = str(tmp_path / "config.json")
        config.to_json(filepath)

        config2 = SimConfig.from_json(filepath)
        assert config2.step_ns == 5

    def test_config_ignores_unknown_keys(self):
        """Config should ignore unknown keys in dict."""
        config = SimConfig.from_dict({"step_ns": 3, "unknown_key": "ignored"})
        assert config.step_ns == 3


# ============================================================
# Integration: CLI Features
# ============================================================

class TestCLIIntegration:
    def test_cdl_file_loading(self, tmp_path):
        """Test loading a CDL file from disk."""
        cdl_source = """
        circuit cli_test;
        wire a initial=LOW;
        wire b initial=LOW;
        wire out;
        gate and and1 a b -> out;
        """
        filepath = tmp_path / "test.cdl"
        filepath.write_text(cdl_source)

        from circuit_sim.cli import _load_cdl
        circ = _load_cdl(str(filepath))
        assert circ.name == "cli_test"
        assert len(circ.gates) == 1

    def test_cli_demo_command(self):
        """Test the demo command runs without errors."""
        from circuit_sim.cli import cmd_demo
        import argparse
        args = argparse.Namespace(verbose=False)
        cmd_demo(args)  # Should not raise


# ============================================================
# Full Round-Trip: JSON Export/Import
# ============================================================

class TestFullRoundTrip:
    def test_and_gate_simulation_after_json_roundtrip(self):
        """A circuit exported to JSON and reimported should simulate correctly."""
        circ = Circuit("roundtrip_and")
        a = circ.add_wire("a", Signal.LOW)
        b = circ.add_wire("b", Signal.LOW)
        out = circ.add_wire("out")
        circ.add_and("and1", a, b, out)

        json_str = circuit_to_json(circ)
        loaded = circuit_from_json(json_str)

        sim = Simulator(loaded)
        loaded.wire("a").signal = Signal.HIGH
        loaded.wire("b").signal = Signal.HIGH
        sim.run(5)
        assert loaded.wire("out").signal == Signal.HIGH

    def test_xor_gate_roundtrip(self):
        """XOR gate JSON roundtrip."""
        circ = Circuit("roundtrip_xor")
        a = circ.add_wire("a", Signal.LOW)
        b = circ.add_wire("b", Signal.HIGH)
        out = circ.add_wire("out")
        circ.add_xor("xor1", a, b, out)

        json_str = circuit_to_json(circ)
        loaded = circuit_from_json(json_str)

        sim = Simulator(loaded)
        sim.run(5)
        assert loaded.wire("out").signal == Signal.HIGH

    def test_nand_gate_roundtrip(self):
        """NAND gate JSON roundtrip."""
        circ = Circuit("roundtrip_nand")
        a = circ.add_wire("a", Signal.HIGH)
        b = circ.add_wire("b", Signal.HIGH)
        out = circ.add_wire("out")
        circ.add_nand("nand1", a, b, out)

        json_str = circuit_to_json(circ)
        loaded = circuit_from_json(json_str)

        sim = Simulator(loaded)
        sim.run(5)
        assert loaded.wire("out").signal == Signal.LOW


# ============================================================
# CDL + Export Integration
# ============================================================

class TestCDLExport:
    def test_cdl_to_dot(self):
        """Load a CDL circuit and export to DOT."""
        source = """
        circuit dot_cdl;
        wire a initial=LOW;
        wire b initial=LOW;
        wire out;
        gate or or1 a b -> out;
        """
        circ = parse_cdl(source)
        dot = circuit_to_dot(circ)
        assert "digraph" in dot
        assert "dot_cdl" in dot

    def test_cdl_to_ascii_schematic(self):
        """Load a CDL circuit and generate ASCII schematic."""
        source = """
        circuit ascii_cdl;
        wire x initial=LOW;
        wire y initial=LOW;
        wire z;
        gate xor xor1 x y -> z;
        """
        circ = parse_cdl(source)
        ascii_art = circuit_to_ascii(circ)
        assert "ascii_cdl" in ascii_art

    def test_cdl_to_json(self):
        """Load a CDL circuit and export to JSON."""
        source = """
        circuit json_cdl;
        wire a initial=HIGH;
        wire b initial=LOW;
        wire out;
        gate and and1 a b -> out;
        """
        circ = parse_cdl(source)
        json_str = circuit_to_json(circ)
        data = json.loads(json_str)
        assert data["name"] == "json_cdl"
        assert len(data["gates"]) == 1


# ============================================================
# Preset + Export Integration
# ============================================================

class TestPresetExport:
    def test_alu_to_dot(self):
        """Export the 1-bit ALU preset to DOT."""
        circ = build_alu_1bit()
        dot = circuit_to_dot(circ)
        assert "digraph" in dot
        assert len(dot) > 100  # Should be a substantial graph

    def test_alu_to_ascii(self):
        """Export the 1-bit ALU preset to ASCII."""
        circ = build_alu_1bit()
        ascii_art = circuit_to_ascii(circ)
        assert "alu_1bit" in ascii_art
        assert "INPUTS" in ascii_art


if __name__ == "__main__":
    pytest.main([__file__, "-v"])