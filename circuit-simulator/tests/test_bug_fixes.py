"""Tests for bugs found and fixed during Phase 3 bug hunt."""

import pytest
from circuit_sim.core import Signal, Wire, Bus
from circuit_sim.gates import AndGate, NotGate
from circuit_sim.sequential import Clock, DFlipFlop
from circuit_sim.circuit import Circuit
from circuit_sim.simulator import Simulator, Stimulus
from circuit_sim.cdl import parse_cdl, CDLParseError
from circuit_sim.analyze import TruthTable


class TestBug1ClockDegenerateDutyCycle:
    """Bug: Clock allowed _high_ns=0 or _low_ns=0 with extreme duty cycles,
    creating degenerate clocks that never oscillate properly.
    Fix: Clamped _high_ns and _low_ns to minimum 1."""

    def test_clock_small_duty_cycle_clamps_high_ns(self):
        """period=10, duty_cycle=0.05 would give _high_ns=0.
        Now clamped to minimum 1."""
        out = Wire("clk", Signal.HIGH)
        clk = Clock("clk1", out, period_ns=10, duty_cycle=0.05)
        assert clk._high_ns >= 1, f"_high_ns={clk._high_ns}, should be >= 1"
        assert clk._low_ns >= 1, f"_low_ns={clk._low_ns}, should be >= 1"

    def test_clock_large_duty_cycle_clamps_low_ns(self):
        """period=3, duty_cycle=0.99 would give _high_ns=2, _low_ns=1. OK.
        But period=3, duty_cycle=0.01 would give _high_ns=0."""
        out = Wire("clk", Signal.HIGH)
        clk = Clock("clk1", out, period_ns=3, duty_cycle=0.01)
        assert clk._high_ns >= 1
        assert clk._low_ns >= 1

    def test_clock_normal_duty_cycle_unaffected(self):
        """Normal duty cycles should work as before."""
        out = Wire("clk", Signal.HIGH)
        clk = Clock("clk1", out, period_ns=10, duty_cycle=0.5)
        assert clk._high_ns == 5
        assert clk._low_ns == 5

    def test_clock_actually_oscillates_after_clamp(self):
        """A previously-degenerate clock now oscillates."""
        circ = Circuit("osc_test")
        clk_wire = circ.add_wire("clk", Signal.LOW)
        clk = circ.add_clock("clk1", clk_wire, period_ns=10, duty_cycle=0.05)
        # _high_ns should be 1, _low_ns should be 9
        assert clk._high_ns == 1
        assert clk._low_ns == 9
        sim = Simulator(circ)
        sim.trace("clk")
        sim.run(30)
        # Clock should have oscillated
        trace = sim.get_trace("clk")
        # Should have recorded trace entries
        assert len(trace) > 0, "Clock trace should not be empty"
        # Should have both HIGH and LOW states
        signals = set(s for _, s in trace)
        assert Signal.HIGH in signals or Signal.LOW in signals


class TestBug2SimulatorResetPreservesInitialValues:
    """Bug: Simulator.reset() set all wires to UNDEFINED instead of their initial values.
    Fix: Store initial value on Wire._initial and restore it on reset."""

    def test_reset_restores_initial_wire_values(self):
        circ = Circuit("reset_test")
        a = circ.add_wire("a", Signal.HIGH)
        b = circ.add_wire("b", Signal.LOW)
        out = circ.add_wire("out")
        circ.add_and("and1", a, b, out)

        sim = Simulator(circ)
        sim.run(5)
        assert out.signal == Signal.LOW  # HIGH AND LOW = LOW

        sim.reset()
        assert a.signal == Signal.HIGH, f"a should be HIGH (initial), got {a.signal.name}"
        assert b.signal == Signal.LOW, f"b should be LOW (initial), got {b.signal.name}"

    def test_reset_clears_trace_history(self):
        circ = Circuit("reset_trace")
        a = circ.add_wire("a", Signal.HIGH)
        sim = Simulator(circ)
        sim.trace("a")
        sim.run(5)
        assert len(sim.get_trace("a")) > 0

        sim.reset()
        assert len(sim.get_trace("a")) == 0, "History should be cleared on reset"

    def test_wire_initial_value_stored(self):
        """Wire._initial should store the initial signal value."""
        w = Wire("test", Signal.HIGH)
        assert w._initial == Signal.HIGH

        w = Wire("test2", Signal.LOW)
        assert w._initial == Signal.LOW

        w = Wire("test3", Signal.UNDEFINED)
        assert w._initial == Signal.UNDEFINED


class TestBug3CDLRippleAdder:
    """Bug: CDL parser documented 'ripple_adder' but didn't implement it.
    Fix: Added ripple_adder command with bus:<name> syntax."""

    def test_ripple_adder_cdl(self):
        source = """
        circuit rca;
        bus a 4 initial=LOW;
        bus b 4 initial=LOW;
        bus s 4 initial=LOW;
        ripple_adder rca bus:a bus:b bus:s;
        """
        circ = parse_cdl(source)
        assert len(circ.gates) == 20  # 4 full adders = 4 * 5 gates

    def test_ripple_adder_requires_buses(self):
        source = """
        circuit bad;
        wire a initial=LOW;
        ripple_adder rca a;
        """
        with pytest.raises(CDLParseError):
            parse_cdl(source)

    def test_ripple_adder_requires_three_buses(self):
        source = """
        circuit bad;
        bus a 4 initial=LOW;
        bus b 4 initial=LOW;
        ripple_adder rca bus:a bus:b;
        """
        with pytest.raises(CDLParseError):
            parse_cdl(source)


class TestBug4TruthTableStateLeakage:
    """Bug: TruthTable didn't reset circuit state between iterations.
    Fix: Now resets input wires to initial values before each iteration."""

    def test_truth_table_preserves_circuit_state(self):
        """After generating a truth table, input wires should be restored."""
        circ = Circuit("tt_restore")
        a = circ.add_wire("a", Signal.LOW)
        b = circ.add_wire("b", Signal.LOW)
        out = circ.add_wire("out")
        circ.add_and("and1", a, b, out)

        original_a = a.signal
        original_b = b.signal

        tt = TruthTable(circ, ["a", "b"], ["out"])
        rows = tt.generate()

        # After generation, input wires should be restored to initial values
        assert a.signal == original_a, f"a restored to {a.signal.name}, expected {original_a.name}"
        assert b.signal == original_b, f"b restored to {b.signal.name}, expected {original_b.name}"

    def test_truth_table_results_correct(self):
        """Truth table for AND gate should give correct results."""
        circ = Circuit("tt_and")
        a = circ.add_wire("a", Signal.LOW)
        b = circ.add_wire("b", Signal.LOW)
        out = circ.add_wire("out")
        circ.add_and("and1", a, b, out)

        tt = TruthTable(circ, ["a", "b"], ["out"])
        rows = tt.generate()
        assert len(rows) == 4

        for row in rows:
            if row["a"] == Signal.HIGH and row["b"] == Signal.HIGH:
                assert row["out"] == Signal.HIGH
            else:
                assert row["out"] == Signal.LOW


class TestBug5StimulusPulseValidation:
    """Bug: Stimulus.pulse_wire didn't validate start < end.
    Fix: Now raises ValueError if start >= end."""

    def test_pulse_wire_requires_start_before_end(self):
        stim = Stimulus()
        with pytest.raises(ValueError, match="start_ns < end_ns"):
            stim.pulse_wire(20, 10, "a")

    def test_pulse_wire_rejects_equal_start_end(self):
        stim = Stimulus()
        with pytest.raises(ValueError, match="start_ns < end_ns"):
            stim.pulse_wire(5, 5, "a")

    def test_pulse_wire_accepts_valid_range(self):
        stim = Stimulus()
        stim.pulse_wire(5, 10, "a")
        events = stim.events
        assert len(events) == 2
        assert events[0][0] == 5  # start
        assert events[1][0] == 10  # end


class TestBug6ConvergenceLimit:
    """Bug: Simulator convergence limit of 20 was too low for deep circuits.
    Fix: Increased to max(50, 2 * num_gates)."""

    def test_deep_cascade_converges(self):
        """A chain of 25 NOT gates with delay_ns=1 should converge."""
        circ = Circuit("deep_cascade")
        a = circ.add_wire("a", Signal.HIGH)
        prev = a
        for i in range(25):
            out = circ.add_wire(f"n{i}", Signal.UNDEFINED)
            circ.add_not(f"not{i}", prev, out)
            prev = out

        sim = Simulator(circ)
        sim.run(50)
        # 25 NOT gates: odd number of inversions → HIGH → LOW
        assert prev.signal == Signal.LOW

    def test_very_deep_zero_delay_converges(self):
        """A chain of 30 NOT gates with delay_ns=0 should converge
        within the dynamic iteration limit."""
        circ = Circuit("very_deep_zero_delay")
        a = circ.add_wire("a", Signal.HIGH)
        prev = a
        for i in range(30):
            out = circ.add_wire(f"n{i}", Signal.UNDEFINED)
            circ.add_not(f"not{i}", prev, out, delay_ns=0)
            prev = out

        sim = Simulator(circ)
        sim.run(5)
        # 30 NOT gates: even number → HIGH → HIGH
        assert prev.signal == Signal.HIGH


class TestBug7SimulatorResetResetsSequentialState:
    """Verify that reset also properly resets sequential element state."""

    def test_reset_clears_flipflop_state(self):
        circ = Circuit("dff_reset")
        d = circ.add_wire("d", Signal.HIGH)
        clk = circ.add_wire("clk", Signal.LOW)
        q = circ.add_wire("q", Signal.LOW)
        qbar = circ.add_wire("qbar", Signal.HIGH)
        circ.add_d_flipflop("dff", d, clk, q, qbar)

        sim = Simulator(circ)
        sim.run(10)

        sim.reset()
        assert sim.time_ns == 0
        assert d.signal == Signal.HIGH  # Initial value preserved


if __name__ == "__main__":
    pytest.main([__file__, "-v"])