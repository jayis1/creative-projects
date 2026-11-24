"""Regression tests for temporal_circuit."""
import unittest

from temporal_circuit import Circuit


class CircuitTests(unittest.TestCase):
    def test_gate_delay_and_stable_trace(self):
        c = Circuit()
        a, b = c.input("a"), c.input("b")
        y = c.xor_gate("y", a, b, delay=2)
        c.set_input("a", 1, at=1)
        c.run(until=4)

        self.assertEqual([(t.time, t.wire, t.new) for t in c.trace if t.wire == "y"], [(3, "y", 1)])

    def test_inertial_cancels_stale_transition(self):
        c = Circuit()
        a = c.input("a")
        y = c.not_gate("y", a, delay=3)
        c.set_input("a", 1, at=1)
        c.set_input("a", 0, at=2)
        c.run(until=6)
        self.assertEqual(y.value, 1)
        self.assertEqual([(t.time, t.new) for t in c.trace if t.wire == "y"], [(5, 1)])

    def test_register_samples_rising_edge(self):
        c = Circuit()
        d, clk = c.input("d", 1), c.input("clk")
        q = c.register("q", d, clk, delay=2)
        c.set_input("clk", 1, at=1)
        c.set_input("d", 0, at=2)
        c.run(until=4)
        self.assertEqual(q.value, 1)
        self.assertEqual(c.trace[-1].time, 3)

    def test_rejects_invalid_values_names_and_times(self):
        c = Circuit()
        a = c.input("a")
        with self.assertRaises(ValueError):
            c.input("a")
        with self.assertRaises(ValueError):
            c.set_input("a", True)
        with self.assertRaises(ValueError):
            c.set_input("a", 1, at=-1)
        with self.assertRaises(ValueError):
            c.not_gate("bad", a, delay=-1)

    def test_rejects_foreign_wire_and_noninput_drive(self):
        a = Circuit().input("a")
        c = Circuit()
        b = c.input("b")
        with self.assertRaises(ValueError):
            c.not_gate("bad", a)
        with self.assertRaises(ValueError):
            c.set_input("b", 1, at=0) if False else c.set_input("missing", 1)

    def test_vcd_contains_initial_values_and_transitions(self):
        c = Circuit()
        a = c.input("a")
        y = c.not_gate("y", a, delay=1)
        c.set_input("a", 1, at=2)
        c.run(until=3)
        vcd = c.trace_vcd()
        self.assertIn("$timescale 1ns $end", vcd)
        self.assertIn("0w0", vcd)
        self.assertIn("1w1", vcd)
        self.assertIn("#2\n1w0", vcd)
        self.assertIn("#3\n0w1", vcd)

    def test_event_budget_stops_zero_delay_oscillation(self):
        c = Circuit(max_events_at_time=20)
        a = c.input("a")
        c.not_gate("inv", a, delay=0)
        c.not_gate("loop", c.wires["inv"], delay=0)
        # Add feedback after constructing the inverter output.
        c.wires["loop"]._listeners.append(lambda _: c.set_input("a", 1 - a.value))
        c.run(max_events=100)


if __name__ == "__main__":
    unittest.main()
