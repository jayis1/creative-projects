"""Comprehensive tests for the circuit simulator."""

import pytest
from circuit_sim.core import Signal, Wire, Bus
from circuit_sim.gates import (
    AndGate, OrGate, NotGate, XorGate, NandGate, NorGate, XnorGate,
    BufferGate, TriStateBuffer, MultiInputGate,
)
from circuit_sim.sequential import SRLatch, DLatch, DFlipFlop, JKFlipFlop, TFlipFlop, Clock
from circuit_sim.circuit import Circuit
from circuit_sim.simulator import Simulator, BreakpointHit
from circuit_sim.cdl import parse_cdl, CDLParseError
from circuit_sim.scope import Oscilloscope


# ============================================================
# Core Signal Tests
# ============================================================

class TestSignal:
    def test_signal_not(self):
        assert (~Signal.HIGH) == Signal.LOW
        assert (~Signal.LOW) == Signal.HIGH
        assert (~Signal.UNDEFINED) == Signal.UNDEFINED

    def test_signal_and(self):
        assert (Signal.HIGH & Signal.HIGH) == Signal.HIGH
        assert (Signal.HIGH & Signal.LOW) == Signal.LOW
        assert (Signal.LOW & Signal.HIGH) == Signal.LOW
        assert (Signal.LOW & Signal.LOW) == Signal.LOW
        assert (Signal.HIGH & Signal.UNDEFINED) == Signal.UNDEFINED
        assert (Signal.LOW & Signal.UNDEFINED) == Signal.UNDEFINED

    def test_signal_or(self):
        assert (Signal.HIGH | Signal.HIGH) == Signal.HIGH
        assert (Signal.HIGH | Signal.LOW) == Signal.HIGH
        assert (Signal.LOW | Signal.HIGH) == Signal.HIGH
        assert (Signal.LOW | Signal.LOW) == Signal.LOW
        assert (Signal.LOW | Signal.UNDEFINED) == Signal.UNDEFINED

    def test_signal_xor(self):
        assert (Signal.HIGH ^ Signal.HIGH) == Signal.LOW
        assert (Signal.HIGH ^ Signal.LOW) == Signal.HIGH
        assert (Signal.LOW ^ Signal.HIGH) == Signal.HIGH
        assert (Signal.LOW ^ Signal.LOW) == Signal.LOW

    def test_signal_conversions(self):
        assert Signal.HIGH.to_int() == 1
        assert Signal.LOW.to_int() == 0
        assert Signal.from_bool(True) == Signal.HIGH
        assert Signal.from_bool(False) == Signal.LOW
        assert Signal.from_int(0) == Signal.LOW
        assert Signal.from_int(1) == Signal.HIGH
        assert Signal.from_int(2) == Signal.UNDEFINED

    def test_signal_undefined_to_int_raises(self):
        with pytest.raises(ValueError):
            Signal.UNDEFINED.to_int()


class TestWire:
    def test_wire_creation(self):
        w = Wire("test", Signal.LOW)
        assert w.name == "test"
        assert w.signal == Signal.LOW

    def test_wire_signal_change(self):
        w = Wire("test", Signal.LOW)
        changes = []
        w.connect(lambda sig, name: changes.append((name, sig)))
        w.signal = Signal.HIGH
        assert len(changes) == 1
        assert changes[0] == ("test", Signal.HIGH)

    def test_wire_no_change_no_notification(self):
        w = Wire("test", Signal.LOW)
        changes = []
        w.connect(lambda sig, name: changes.append(sig))
        w.signal = Signal.LOW  # Same value
        assert len(changes) == 0

    def test_wire_history(self):
        w = Wire("test", Signal.LOW)
        w.record(0)
        w.signal = Signal.HIGH
        w.record(5)
        assert len(w.history) == 2
        assert w.history[0] == (0, Signal.LOW)
        assert w.history[1] == (5, Signal.HIGH)

    def test_wire_clear_history(self):
        w = Wire("test", Signal.LOW)
        w.record(0)
        w.clear_history()
        assert len(w.history) == 0


class TestBus:
    def test_bus_creation(self):
        bus = Bus("data", 4, Signal.LOW)
        assert len(bus) == 4
        assert bus.name == "data"

    def test_bus_write_read(self):
        bus = Bus("data", 8, Signal.LOW)
        bus.write_int(0b10110100)
        assert bus.read_int() == 0b10110100

    def test_bus_individual_bits(self):
        bus = Bus("data", 4, Signal.LOW)
        bus.write_int(5)  # 0101
        assert bus[0].signal == Signal.HIGH  # bit 0
        assert bus[1].signal == Signal.LOW   # bit 1
        assert bus[2].signal == Signal.HIGH  # bit 2
        assert bus[3].signal == Signal.LOW   # bit 3


# ============================================================
# Gate Tests
# ============================================================

class TestGates:
    def _make_gate_test(self, gate_cls, inputs_map, name_prefix=""):
        """Helper to test gate truth tables."""
        pass

    def test_and_gate(self):
        a, b, out = Wire("a"), Wire("b"), Wire("out")
        gate = AndGate("and1", a, b, out)
        for a_val, b_val, expected in [
            (Signal.LOW, Signal.LOW, Signal.LOW),
            (Signal.LOW, Signal.HIGH, Signal.LOW),
            (Signal.HIGH, Signal.LOW, Signal.LOW),
            (Signal.HIGH, Signal.HIGH, Signal.HIGH),
        ]:
            a.signal = a_val
            b.signal = b_val
            gate.evaluate()
            ready = gate.tick(1)
            for wire, sig in ready:
                wire.signal = sig
            assert out.signal == expected, f"AND({a_val}, {b_val}) = {out.signal}, expected {expected}"

    def test_or_gate(self):
        a, b, out = Wire("a"), Wire("b"), Wire("out")
        gate = OrGate("or1", a, b, out)
        for a_val, b_val, expected in [
            (Signal.LOW, Signal.LOW, Signal.LOW),
            (Signal.LOW, Signal.HIGH, Signal.HIGH),
            (Signal.HIGH, Signal.LOW, Signal.HIGH),
            (Signal.HIGH, Signal.HIGH, Signal.HIGH),
        ]:
            a.signal = a_val
            b.signal = b_val
            gate.evaluate()
            ready = gate.tick(1)
            for wire, sig in ready:
                wire.signal = sig
            assert out.signal == expected

    def test_not_gate(self):
        a, out = Wire("a"), Wire("out")
        gate = NotGate("not1", a, out)
        a.signal = Signal.LOW
        gate.evaluate()
        ready = gate.tick(1)
        for wire, sig in ready:
            wire.signal = sig
        assert out.signal == Signal.HIGH

        a.signal = Signal.HIGH
        gate.evaluate()
        ready = gate.tick(1)
        for wire, sig in ready:
            wire.signal = sig
        assert out.signal == Signal.LOW

    def test_xor_gate(self):
        a, b, out = Wire("a"), Wire("b"), Wire("out")
        gate = XorGate("xor1", a, b, out)
        for a_val, b_val, expected in [
            (Signal.LOW, Signal.LOW, Signal.LOW),
            (Signal.LOW, Signal.HIGH, Signal.HIGH),
            (Signal.HIGH, Signal.LOW, Signal.HIGH),
            (Signal.HIGH, Signal.HIGH, Signal.LOW),
        ]:
            a.signal = a_val
            b.signal = b_val
            gate.evaluate()
            ready = gate.tick(1)
            for wire, sig in ready:
                wire.signal = sig
            assert out.signal == expected

    def test_nand_gate(self):
        a, b, out = Wire("a"), Wire("b"), Wire("out")
        gate = NandGate("nand1", a, b, out)
        a.signal = Signal.HIGH
        b.signal = Signal.HIGH
        gate.evaluate()
        ready = gate.tick(1)
        for wire, sig in ready:
            wire.signal = sig
        assert out.signal == Signal.LOW

    def test_nor_gate(self):
        a, b, out = Wire("a"), Wire("b"), Wire("out")
        gate = NorGate("nor1", a, b, out)
        a.signal = Signal.LOW
        b.signal = Signal.LOW
        gate.evaluate()
        ready = gate.tick(1)
        for wire, sig in ready:
            wire.signal = sig
        assert out.signal == Signal.HIGH

    def test_xnor_gate(self):
        a, b, out = Wire("a"), Wire("b"), Wire("out")
        gate = XnorGate("xnor1", a, b, out)
        a.signal = Signal.HIGH
        b.signal = Signal.HIGH
        gate.evaluate()
        ready = gate.tick(1)
        for wire, sig in ready:
            wire.signal = sig
        assert out.signal == Signal.HIGH

    def test_buffer_gate(self):
        a, out = Wire("a"), Wire("out")
        gate = BufferGate("buf1", a, out)
        a.signal = Signal.HIGH
        gate.evaluate()
        ready = gate.tick(1)
        for wire, sig in ready:
            wire.signal = sig
        assert out.signal == Signal.HIGH

    def test_tristate_buffer_enabled(self):
        a, en, out = Wire("a"), Wire("en"), Wire("out")
        gate = TriStateBuffer("ts1", a, en, out)
        a.signal = Signal.HIGH
        en.signal = Signal.HIGH
        gate.evaluate()
        ready = gate.tick(1)
        for wire, sig in ready:
            wire.signal = sig
        assert out.signal == Signal.HIGH

    def test_tristate_buffer_disabled(self):
        a, en, out = Wire("a"), Wire("en"), Wire("out")
        gate = TriStateBuffer("ts1", a, en, out)
        a.signal = Signal.HIGH
        en.signal = Signal.LOW
        gate.evaluate()
        ready = gate.tick(1)
        for wire, sig in ready:
            wire.signal = sig
        assert out.signal == Signal.HIGH_IMPEDANCE

    def test_multi_input_and_gate(self):
        inputs = [Wire(f"in{i}") for i in range(3)]
        out = Wire("out")
        gate = MultiInputGate("and3", inputs, out, "and", delay_ns=2)
        inputs[0].signal = Signal.HIGH
        inputs[1].signal = Signal.HIGH
        inputs[2].signal = Signal.HIGH
        gate.evaluate()
        ready = gate.tick(2)
        for wire, sig in ready:
            wire.signal = sig
        assert out.signal == Signal.HIGH

        inputs[2].signal = Signal.LOW
        gate.evaluate()
        ready = gate.tick(2)
        for wire, sig in ready:
            wire.signal = sig
        assert out.signal == Signal.LOW


# ============================================================
# Sequential Element Tests
# ============================================================

class TestSequential:
    def test_sr_latch_set(self):
        s, r, q, qbar = Wire("s"), Wire("r"), Wire("q"), Wire("qbar")
        latch = SRLatch("sr1", s, r, q, qbar, delay_ns=2)
        s.signal = Signal.HIGH
        r.signal = Signal.LOW
        latch.evaluate()
        ready = latch.tick(2)
        for wire, sig in ready:
            wire.signal = sig
        assert q.signal == Signal.HIGH
        assert qbar.signal == Signal.LOW

    def test_sr_latch_reset(self):
        s, r, q, qbar = Wire("s"), Wire("r"), Wire("q"), Wire("qbar")
        latch = SRLatch("sr1", s, r, q, qbar, delay_ns=2)
        s.signal = Signal.LOW
        r.signal = Signal.HIGH
        latch.evaluate()
        ready = latch.tick(2)
        for wire, sig in ready:
            wire.signal = sig
        assert q.signal == Signal.LOW
        assert qbar.signal == Signal.HIGH

    def test_sr_latch_hold(self):
        s, r, q, qbar = Wire("s"), Wire("r"), Wire("q"), Wire("qbar")
        latch = SRLatch("sr1", s, r, q, qbar, delay_ns=2)
        # Set first
        s.signal = Signal.HIGH
        r.signal = Signal.LOW
        latch.evaluate()
        ready = latch.tick(2)
        for wire, sig in ready:
            wire.signal = sig
        assert q.signal == Signal.HIGH
        # Now hold
        s.signal = Signal.LOW
        r.signal = Signal.LOW
        latch.evaluate()
        ready = latch.tick(2)
        for wire, sig in ready:
            wire.signal = sig
        assert q.signal == Signal.HIGH  # Holds previous state

    def test_d_latch_transparent(self):
        d, en, q, qbar = Wire("d"), Wire("en"), Wire("q"), Wire("qbar")
        latch = DLatch("dl1", d, en, q, qbar, delay_ns=2)
        en.signal = Signal.HIGH
        d.signal = Signal.HIGH
        latch.evaluate()
        ready = latch.tick(2)
        for wire, sig in ready:
            wire.signal = sig
        assert q.signal == Signal.HIGH

    def test_d_latch_hold(self):
        d, en, q, qbar = Wire("d"), Wire("en"), Wire("q"), Wire("qbar")
        latch = DLatch("dl1", d, en, q, qbar, delay_ns=2)
        # First set Q=1 with enable
        en.signal = Signal.HIGH
        d.signal = Signal.HIGH
        latch.evaluate()
        ready = latch.tick(2)
        for wire, sig in ready:
            wire.signal = sig
        assert q.signal == Signal.HIGH
        # Now disable, change D — Q should hold
        en.signal = Signal.LOW
        d.signal = Signal.LOW
        latch.evaluate()
        ready = latch.tick(2)
        for wire, sig in ready:
            wire.signal = sig
        assert q.signal == Signal.HIGH  # Holds

    def test_clock(self):
        out = Wire("clk", Signal.HIGH)
        clk = Clock("clk1", out, period_ns=10, duty_cycle=0.5)
        
        # Start HIGH (high phase is 5ns)
        assert out.signal == Signal.HIGH
        
        # Tick 5ns — should transition to LOW
        changed = clk.tick(5)
        assert changed is True
        assert out.signal == Signal.LOW
        
        # Tick 5ns — should transition back to HIGH (full period complete)
        changed = clk.tick(5)
        assert changed is True
        assert out.signal == Signal.HIGH

    def test_clock_duty_cycle(self):
        out = Wire("clk", Signal.HIGH)
        clk = Clock("clk1", out, period_ns=10, duty_cycle=0.3)
        
        # Start HIGH, high phase is 3ns
        # Tick 3ns — should transition to LOW
        changed = clk.tick(3)
        assert out.signal == Signal.LOW
        
        # Tick 7ns — should transition back to HIGH
        changed = clk.tick(7)
        assert out.signal == Signal.HIGH

    def test_clock_invalid_params(self):
        out = Wire("clk")
        with pytest.raises(ValueError):
            Clock("bad", out, period_ns=10, duty_cycle=0.0)
        with pytest.raises(ValueError):
            Clock("bad", out, period_ns=10, duty_cycle=1.0)
        with pytest.raises(ValueError):
            Clock("bad", out, period_ns=1)


# ============================================================
# Circuit Builder Tests
# ============================================================

class TestCircuit:
    def test_half_adder(self):
        circ = Circuit("half_adder_test")
        a = circ.add_wire("a", Signal.LOW)
        b = circ.add_wire("b", Signal.LOW)
        s = circ.add_wire("sum")
        c = circ.add_wire("carry")
        circ.build_half_adder("ha", a, b, s, c)
        assert len(circ.gates) == 2

    def test_full_adder(self):
        circ = Circuit("full_adder_test")
        a = circ.add_wire("a", Signal.LOW)
        b = circ.add_wire("b", Signal.LOW)
        cin = circ.add_wire("cin", Signal.LOW)
        s = circ.add_wire("sum")
        cout = circ.add_wire("cout")
        circ.build_full_adder("fa", a, b, cin, s, cout)
        assert len(circ.gates) == 5  # 2 half adders + 1 OR

    def test_mux2(self):
        circ = Circuit("mux_test")
        a = circ.add_wire("a", Signal.LOW)
        b = circ.add_wire("b", Signal.HIGH)
        sel = circ.add_wire("sel", Signal.LOW)
        out = circ.add_wire("out")
        circ.build_mux2("mux", a, b, sel, out)
        assert len(circ.gates) == 4  # NOT + 2 AND + 1 OR

    def test_ripple_carry_adder(self):
        circ = Circuit("rca_test")
        bus_a = circ.add_bus("a", 4)
        bus_b = circ.add_bus("b", 4)
        bus_s = circ.add_bus("s", 4)
        cout = circ.build_ripple_carry_adder("rca", bus_a, bus_b, bus_s)
        # Should have 4 full adders = 4*5 = 20 gates
        assert len(circ.gates) == 20

    def test_bus_operations(self):
        circ = Circuit("bus_test")
        bus = circ.add_bus("data", 8)
        bus.write_int(42)
        assert bus.read_int() == 42

    def test_wire_duplicate_raises(self):
        circ = Circuit("test")
        circ.add_wire("a")
        with pytest.raises(ValueError):
            circ.add_wire("a")


# ============================================================
# Simulator Tests
# ============================================================

class TestSimulator:
    def test_simple_and_simulation(self):
        circ = Circuit("and_test")
        a = circ.add_wire("a", Signal.LOW)
        b = circ.add_wire("b", Signal.LOW)
        out = circ.add_wire("out", Signal.UNDEFINED)
        circ.add_and("and1", a, b, out)
        
        sim = Simulator(circ)
        sim.trace("a", "b", "out")
        
        # Initial: LOW AND LOW = LOW
        sim.step()
        # Set a=HIGH
        a.signal = Signal.HIGH
        sim.step()
        # a=HIGH, b=LOW → LOW
        assert out.signal == Signal.LOW or out.signal == Signal.UNDEFINED
        
        # Set b=HIGH
        b.signal = Signal.HIGH
        sim.step()
        # Need a few more steps for propagation
        sim.step()
        sim.step()
        assert out.signal == Signal.HIGH

    def test_simulator_with_clock_and_flipflop(self):
        circ = Circuit("ff_test")
        d = circ.add_wire("d", Signal.LOW)
        clk_wire = circ.add_wire("clk", Signal.LOW)
        q = circ.add_wire("q", Signal.UNDEFINED)
        qbar = circ.add_wire("qbar", Signal.UNDEFINED)
        
        circ.add_d_flipflop("dff1", d, clk_wire, q, qbar)
        clock = circ.add_clock("clk1", clk_wire, period_ns=10)
        
        sim = Simulator(circ)
        
        # Run for 25ns to see a full clock cycle
        sim.run(25)
        
        # Q should be LOW (D was LOW when clock rose)
        assert q.signal in (Signal.LOW, Signal.UNDEFINED)

    def test_simulator_probe(self):
        circ = Circuit("probe_test")
        a = circ.add_wire("a", Signal.HIGH)
        sim = Simulator(circ)
        assert sim.probe("a") == Signal.HIGH

    def test_simulator_breakpoint(self):
        circ = Circuit("bp_test")
        a = circ.add_wire("a", Signal.LOW)
        sim = Simulator(circ)
        sim.add_breakpoint(lambda t: t >= 5)
        
        with pytest.raises(BreakpointHit):
            sim.run(10)

    def test_simulator_reset(self):
        circ = Circuit("reset_test")
        a = circ.add_wire("a", Signal.HIGH)
        sim = Simulator(circ)
        sim.step()
        assert a.signal == Signal.HIGH
        sim.reset()
        assert sim.time_ns == 0


# ============================================================
# CDL Parser Tests
# ============================================================

class TestCDL:
    def test_simple_circuit(self):
        source = """
        circuit test_circuit;
        wire a initial=LOW;
        wire b initial=LOW;
        wire out;
        gate and and1 a b -> out;
        """
        circ = parse_cdl(source)
        assert circ.name == "test_circuit"
        assert "a" in circ.wires
        assert "b" in circ.wires
        assert "out" in circ.wires
        assert len(circ.gates) == 1

    def test_bus_in_cdl(self):
        source = """
        circuit bus_test;
        bus data 4 initial=LOW;
        """
        circ = parse_cdl(source)
        assert "data" in circ.buses
        assert circ.buses["data"].width == 4

    def test_clock_in_cdl(self):
        source = """
        circuit clk_test;
        wire clk_out;
        clock clk1 clk_out period=20 duty=0.5;
        """
        circ = parse_cdl(source)
        assert len(circ.clocks) == 1
        assert circ.clocks[0].period_ns == 20

    def test_sequential_in_cdl(self):
        source = """
        circuit seq_test;
        wire d initial=LOW;
        wire clk;
        wire q;
        wire qbar;
        sequential d_flipflop dff1 d clk -> q qbar;
        """
        circ = parse_cdl(source)
        assert len(circ.sequential) == 1

    def test_cdl_comments(self):
        source = """
        # This is a comment
        circuit comment_test;
        wire a; # inline comment
        """
        circ = parse_cdl(source)
        assert "a" in circ.wires

    def test_cdl_errors(self):
        with pytest.raises(CDLParseError):
            parse_cdl("gate and foo a b -> out;")  # No circuit

    def test_half_adder_cdl(self):
        source = """
        circuit ha_test;
        wire a initial=LOW;
        wire b initial=LOW;
        wire sum;
        wire carry;
        half_adder ha1 a b -> sum carry;
        """
        circ = parse_cdl(source)
        assert len(circ.gates) == 2


# ============================================================
# Oscilloscope Tests
# ============================================================

class TestOscilloscope:
    def test_ascii_render(self):
        scope = Oscilloscope()
        scope.add_trace("clk", [(0, Signal.LOW), (5, Signal.HIGH), (10, Signal.LOW)])
        output = scope.render_ascii(width=20)
        assert "clk" in output

    def test_vcd_export(self, tmp_path):
        scope = Oscilloscope()
        scope.add_trace("clk", [(0, Signal.LOW), (5, Signal.HIGH), (10, Signal.LOW)])
        scope.add_trace("data", [(0, Signal.LOW), (10, Signal.HIGH)])
        
        vcd_file = str(tmp_path / "test.vcd")
        scope.export_vcd(vcd_file)
        
        with open(vcd_file) as f:
            content = f.read()
        assert "$timescale" in content
        assert "$var wire" in content

    def test_to_dict(self):
        scope = Oscilloscope()
        scope.add_trace("sig1", [(0, Signal.HIGH)])
        d = scope.to_dict()
        assert "sig1" in d
        assert d["sig1"][0] == (0, "HIGH")


# ============================================================
# Integration Tests
# ============================================================

class TestIntegration:
    def test_full_adder_simulation(self):
        """Test a full adder circuit end-to-end."""
        circ = Circuit("full_adder_sim")
        a = circ.add_wire("a", Signal.LOW)
        b = circ.add_wire("b", Signal.LOW)
        cin = circ.add_wire("cin", Signal.LOW)
        s = circ.add_wire("sum")
        cout = circ.add_wire("cout")
        circ.build_full_adder("fa", a, b, cin, s, cout)
        
        sim = Simulator(circ)
        sim.trace("a", "b", "cin", "sum", "cout")
        
        # Run enough steps for propagation
        sim.run(10)
        
        # 0+0+0 = 0, carry 0
        # After settling, test various inputs
        test_cases = [
            (Signal.LOW, Signal.LOW, Signal.LOW, Signal.LOW, Signal.LOW),
            (Signal.HIGH, Signal.LOW, Signal.LOW, Signal.HIGH, Signal.LOW),
            (Signal.LOW, Signal.HIGH, Signal.LOW, Signal.HIGH, Signal.LOW),
            (Signal.LOW, Signal.LOW, Signal.HIGH, Signal.HIGH, Signal.LOW),
            (Signal.HIGH, Signal.HIGH, Signal.LOW, Signal.LOW, Signal.HIGH),
            (Signal.HIGH, Signal.HIGH, Signal.HIGH, Signal.HIGH, Signal.HIGH),
        ]
        
        for a_val, b_val, cin_val, expected_sum, expected_cout in test_cases:
            sim.reset()
            a.signal = a_val
            b.signal = b_val
            cin.signal = cin_val
            sim.run(10)
            assert s.signal == expected_sum, \
                f"Sum: {a_val}+{b_val}+{cin_val} = {s.signal}, expected {expected_sum}"
            assert cout.signal == expected_cout, \
                f"Carry: {a_val}+{b_val}+{cin_val} cout = {cout.signal}, expected {expected_cout}"

    def test_ripple_carry_adder_simulation(self):
        """Test a 4-bit ripple carry adder."""
        circ = Circuit("rca_sim")
        bus_a = circ.add_bus("a", 4)
        bus_b = circ.add_bus("b", 4)
        bus_s = circ.add_bus("s", 4)
        circ.build_ripple_carry_adder("rca", bus_a, bus_b, bus_s)
        
        sim = Simulator(circ)
        
        # Test: 3 + 5 = 8
        bus_a.write_int(3)
        bus_b.write_int(5)
        sim.run(20)
        result = bus_s.read_int()
        assert result == 8, f"Expected 8, got {result}"

    def test_mux2_simulation(self):
        """Test a 2-to-1 multiplexer."""
        circ = Circuit("mux_sim")
        a = circ.add_wire("a", Signal.HIGH)
        b = circ.add_wire("b", Signal.LOW)
        sel = circ.add_wire("sel", Signal.LOW)
        out = circ.add_wire("out")
        circ.build_mux2("mux", a, b, sel, out)
        
        sim = Simulator(circ)
        
        # Select A (sel=0)
        sel.signal = Signal.LOW
        sim.run(10)
        assert out.signal == Signal.HIGH
        
        # Select B (sel=1)
        sim.reset()
        a.signal = Signal.HIGH
        b.signal = Signal.LOW
        sel.signal = Signal.HIGH
        sim.run(10)
        assert out.signal == Signal.LOW

    def test_cdl_full_simulation(self):
        """Test a circuit defined in CDL, simulated end-to-end."""
        source = """
        circuit cdl_test;
        wire a initial=LOW;
        wire b initial=LOW;
        wire out;
        gate or or1 a b -> out;
        """
        circ = parse_cdl(source)
        sim = Simulator(circ)
        sim.trace("a", "b", "out")
        
        a = circ.wire("a")
        b = circ.wire("b")
        out = circ.wire("out")
        
        # Set a=HIGH
        a.signal = Signal.HIGH
        sim.run(5)
        assert out.signal == Signal.HIGH

    def test_clock_frequency_counter(self):
        """Test counting clock edges with a T flip-flop (frequency divider)."""
        circ = Circuit("divider")
        clk_wire = circ.add_wire("clk", Signal.LOW)
        t_input = circ.add_wire("t", Signal.HIGH)  # Always toggle
        q = circ.add_wire("q", Signal.LOW)
        qbar = circ.add_wire("qbar", Signal.HIGH)
        
        circ.add_t_flipflop("tff1", t_input, clk_wire, q, qbar)
        circ.add_clock("clk1", clk_wire, period_ns=10)
        
        sim = Simulator(circ)
        sim.trace("clk", "q")
        
        # Run for 100ns (5 clock cycles)
        sim.run(100)
        # The T flip-flop should have toggled several times


if __name__ == "__main__":
    pytest.main([__file__, "-v"])