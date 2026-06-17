"""Simulator: event-driven simulation engine for digital circuits."""

from __future__ import annotations
from typing import Dict, List, Optional, Callable, Set
from .core import Signal, Wire
from .circuit import Circuit
from .sequential import Clock


class Simulator:
    """
    Event-driven digital circuit simulator.
    
    The simulator maintains a global time counter (in nanoseconds) and
    processes events in time order. It supports:
    - Combinational gate evaluation with propagation delays
    - Sequential element state updates (edge-triggered)
    - Clock-driven simulation
    - Wire value change recording for oscilloscope traces
    """

    def __init__(self, circuit: Circuit, step_ns: int = 1):
        """
        Args:
            circuit: The circuit to simulate.
            step_ns: Minimum time step in nanoseconds (default 1).
        """
        if step_ns < 1:
            raise ValueError("step_ns must be >= 1")

        self.circuit = circuit
        self.step_ns = step_ns
        self.time_ns = 0
        self._traced_wires: Set[str] = set()
        self._breakpoints: List[Callable[[int], bool]] = []

    def trace(self, *wire_names: str) -> None:
        """Enable oscilloscope tracing on named wires."""
        for name in wire_names:
            if name not in self.circuit.wires:
                raise KeyError(f"Wire {name!r} not found in circuit")
            self._traced_wires.add(name)

    def trace_all(self) -> None:
        """Trace all wires in the circuit."""
        self._traced_wires = set(self.circuit.wires.keys())

    def add_breakpoint(self, condition: Callable[[int], bool]) -> None:
        """Add a breakpoint that stops simulation when condition(time_ns) is True."""
        self._breakpoints.append(condition)

    def _record_traces(self) -> None:
        """Record current wire values for traced wires."""
        for name in self._traced_wires:
            self.circuit.wires[name].record(self.time_ns)

    def _evaluate_combinational(self) -> None:
        """Evaluate all combinational gates and propagate through delays."""
        # Multiple passes until stable (handles cascaded gates)
        max_iterations = 20  # prevent infinite loops
        for _ in range(max_iterations):
            changed = False
            for gate in self.circuit.gates:
                gate.evaluate()
            # Process propagation delays
            for gate in self.circuit.gates:
                ready = gate.tick(self.step_ns)
                for wire, signal in ready:
                    if wire.signal != signal:
                        wire.signal = signal
                        changed = True
            if not changed:
                break

    def _evaluate_sequential(self) -> None:
        """Evaluate all sequential elements."""
        for elem in self.circuit.sequential:
            elem.evaluate()
        # Process propagation delays
        for elem in self.circuit.sequential:
            ready = elem.tick(self.step_ns)
            for wire, signal in ready:
                if wire.signal != signal:
                    wire.signal = signal

    def _advance_clocks(self) -> bool:
        """Advance all clocks by step_ns. Returns True if any clock output changed."""
        any_changed = False
        for clk in self.circuit.clocks:
            if clk.tick(self.step_ns):
                any_changed = True
        return any_changed

    def step(self) -> int:
        """
        Advance simulation by one time step.
        Returns the new time in nanoseconds.
        """
        self._record_traces()

        # 1. Advance clocks
        self._advance_clocks()

        # 2. Evaluate sequential elements (edge detection happens here)
        self._evaluate_sequential()

        # 3. Evaluate combinational logic
        self._evaluate_combinational()

        self.time_ns += self.step_ns

        # Check breakpoints
        for bp in self._breakpoints:
            if bp(self.time_ns):
                raise BreakpointHit(self.time_ns)

        return self.time_ns

    def run(self, duration_ns: int) -> int:
        """
        Run the simulation for the given duration.
        Returns the total simulated time in nanoseconds.
        """
        end_time = self.time_ns + duration_ns
        while self.time_ns < end_time:
            self.step()
        return self.time_ns

    def run_until(self, condition: Callable[[], bool], max_ns: int = 100000) -> int:
        """
        Run until condition() returns True or max_ns is reached.
        Returns total simulated time.
        """
        elapsed = 0
        while not condition() and elapsed < max_ns:
            self.step()
            elapsed += self.step_ns
        return self.time_ns

    def reset(self) -> None:
        """Reset simulation time to zero."""
        self.time_ns = 0
        for wire in self.circuit.wires.values():
            wire.signal = Signal.UNDEFINED
            wire.clear_history()
        # Reset sequential element state
        for elem in self.circuit.sequential:
            if hasattr(elem, '_q_state'):
                elem._q_state = Signal.LOW
                elem._qbar_state = Signal.HIGH
            if hasattr(elem, '_prev_clock'):
                elem._prev_clock = Signal.LOW
        # Reset clocks
        for clk in self.circuit.clocks:
            clk.reset()

    def get_trace(self, wire_name: str) -> List[tuple]:
        """Get the oscilloscope trace for a wire."""
        if wire_name not in self.circuit.wires:
            raise KeyError(f"Wire {wire_name!r} not found")
        return self.circuit.wires[wire_name].history

    def probe(self, wire_name: str) -> Signal:
        """Get the current value of a wire."""
        if wire_name not in self.circuit.wires:
            raise KeyError(f"Wire {wire_name!r} not found")
        return self.circuit.wires[wire_name].signal

    def __repr__(self) -> str:
        return (f"Simulator(time={self.time_ns}ns, "
                f"wires={len(self.circuit.wires)}, "
                f"gates={len(self.circuit.gates)}, "
                f"sequential={len(self.circuit.sequential)})")


class BreakpointHit(Exception):
    """Raised when a simulation breakpoint is triggered."""
    def __init__(self, time_ns: int):
        self.time_ns = time_ns
        super().__init__(f"Breakpoint hit at t={time_ns}ns")