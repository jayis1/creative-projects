"""Simulator: event-driven simulation engine for digital circuits."""

from __future__ import annotations
from typing import Dict, List, Optional, Callable, Set, Tuple
from .core import Signal, Wire, Bus
from .circuit import Circuit
from .sequential import Clock


class Stimulus:
    """
    A stimulus is a sequence of timed signal changes applied to wires.
    Used to drive simulation inputs automatically.
    """

    def __init__(self):
        self._events: List[Tuple[int, str, Signal]] = []
        self._bus_events: List[Tuple[int, str, int]] = []

    def set_wire(self, time_ns: int, wire_name: str, value: Signal) -> 'Stimulus':
        """Schedule a wire value change at a specific time."""
        self._events.append((time_ns, wire_name, value))
        return self

    def set_bus(self, time_ns: int, bus_name: str, value: int) -> 'Stimulus':
        """Schedule a bus value change at a specific time."""
        self._bus_events.append((time_ns, bus_name, value))
        return self

    def pulse_wire(self, start_ns: int, end_ns: int, wire_name: str,
                   high_value: Signal = Signal.HIGH,
                   low_value: Signal = Signal.LOW) -> 'Stimulus':
        """Generate a pulse on a wire: go HIGH at start_ns, back to LOW at end_ns."""
        self.set_wire(start_ns, wire_name, high_value)
        self.set_wire(end_ns, wire_name, low_value)
        return self

    def clock_pulse(self, period_ns: int, wire_name: str,
                    num_cycles: int = 1,
                    duty_cycle: float = 0.5) -> 'Stimulus':
        """Generate a clock-like pulse train on a wire."""
        high_ns = int(period_ns * duty_cycle)
        for i in range(num_cycles):
            t_rise = i * period_ns
            t_fall = t_rise + high_ns
            self.set_wire(t_rise, wire_name, Signal.HIGH)
            self.set_wire(t_fall, wire_name, Signal.LOW)
        return self

    @property
    def events(self) -> List[Tuple[int, str, Signal]]:
        """Return sorted events."""
        return sorted(self._events, key=lambda e: e[0])

    @property
    def bus_events(self) -> List[Tuple[int, str, int]]:
        """Return sorted bus events."""
        return sorted(self._bus_events, key=lambda e: e[0])


class Simulator:
    """
    Event-driven digital circuit simulator.
    
    The simulator maintains a global time counter (in nanoseconds) and
    processes events in time order. It supports:
    - Combinational gate evaluation with propagation delays
    - Sequential element state updates (edge-triggered)
    - Clock-driven simulation
    - Wire value change recording for oscilloscope traces
    - Stimulus-driven simulation
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
        self._stimulus_index: int = 0
        self._bus_stimulus_index: int = 0

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

    def _apply_stimulus(self, stimulus: 'Stimulus') -> None:
        """Apply any stimulus events that are due at the current time."""
        events = stimulus.events
        while (self._stimulus_index < len(events) and
               events[self._stimulus_index][0] <= self.time_ns):
            _, wire_name, value = events[self._stimulus_index]
            if wire_name in self.circuit.wires:
                self.circuit.wires[wire_name].signal = value
            self._stimulus_index += 1

        bus_events = stimulus.bus_events
        while (self._bus_stimulus_index < len(bus_events) and
               bus_events[self._bus_stimulus_index][0] <= self.time_ns):
            _, bus_name, value = bus_events[self._bus_stimulus_index]
            if bus_name in self.circuit.buses:
                self.circuit.buses[bus_name].write_int(value)
            self._bus_stimulus_index += 1

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

    def run_with_stimulus(self, stimulus: Stimulus, duration_ns: int) -> int:
        """
        Run the simulation with a stimulus applied.
        Stimulus events are applied at their scheduled times.
        """
        self._stimulus_index = 0
        self._bus_stimulus_index = 0
        end_time = self.time_ns + duration_ns
        while self.time_ns < end_time:
            self._apply_stimulus(stimulus)
            self.step()
        # Apply any remaining stimulus events
        self._apply_stimulus(stimulus)
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
        self._stimulus_index = 0
        self._bus_stimulus_index = 0
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
            # Clear propagation queues
            if hasattr(elem, '_propagation_queue'):
                elem._propagation_queue.clear()
        # Reset gate propagation queues
        for gate in self.circuit.gates:
            gate._propagation_queue.clear()
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

    def probe_bus(self, bus_name: str) -> int:
        """Get the current integer value of a bus. Returns -1 if any wire is undefined."""
        if bus_name not in self.circuit.buses:
            raise KeyError(f"Bus {bus_name!r} not found")
        return self.circuit.buses[bus_name].read_int()

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