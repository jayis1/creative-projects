"""Sequential logic components: latches, flip-flops, and clocks."""

from __future__ import annotations
from typing import Optional
from .core import Signal, Wire
from .gates import Gate


class SRLatch(Gate):
    """
    SR (Set-Reset) latch built from cross-coupled gates.
    
    Truth table:
      S=0 R=0 -> hold previous state
      S=1 R=0 -> Q=1 (set)
      S=0 R=1 -> Q=0 (reset)
      S=1 R=1 -> invalid (both outputs go low)
    """

    def __init__(self, name: str, set_input: Wire, reset_input: Wire,
                 q_output: Wire, qbar_output: Wire, delay_ns: int = 2):
        super().__init__(name, delay_ns)
        self._input_wires = [set_input, reset_input]
        self._output_wires = [q_output, qbar_output]
        # Internal state
        self._q_state = Signal.LOW
        self._qbar_state = Signal.HIGH

    def evaluate(self) -> list:
        s = self._input_wires[0].signal
        r = self._input_wires[1].signal

        if s == Signal.HIGH and r == Signal.HIGH:
            # Invalid state — both go LOW
            self._q_state = Signal.LOW
            self._qbar_state = Signal.LOW
        elif s == Signal.HIGH and r == Signal.LOW:
            # Set
            self._q_state = Signal.HIGH
            self._qbar_state = Signal.LOW
        elif s == Signal.LOW and r == Signal.HIGH:
            # Reset
            self._q_state = Signal.LOW
            self._qbar_state = Signal.HIGH
        else:
            # Hold
            pass

        self._propagate(self._output_wires[0], self._q_state)
        self._propagate(self._output_wires[1], self._qbar_state)
        return []


class DLatch(Gate):
    """
    D latch (transparent latch). When enable is HIGH, Q follows D.
    When enable is LOW, Q holds its previous value.
    """

    def __init__(self, name: str, d_input: Wire, enable: Wire,
                 q_output: Wire, qbar_output: Wire, delay_ns: int = 2):
        super().__init__(name, delay_ns)
        self._input_wires = [d_input, enable]
        self._output_wires = [q_output, qbar_output]
        self._q_state = Signal.LOW
        self._qbar_state = Signal.HIGH

    def evaluate(self) -> list:
        d = self._input_wires[0].signal
        en = self._input_wires[1].signal

        if en == Signal.HIGH:
            self._q_state = d
            self._qbar_state = ~d if d in (Signal.HIGH, Signal.LOW) else Signal.UNDEFINED
        # else: hold

        self._propagate(self._output_wires[0], self._q_state)
        self._propagate(self._output_wires[1], self._qbar_state)
        return []


class DFlipFlop(Gate):
    """
    Edge-triggered D flip-flop. Captures D on the rising edge of the clock.
    """

    def __init__(self, name: str, d_input: Wire, clock: Wire,
                 q_output: Wire, qbar_output: Wire,
                 reset: Optional[Wire] = None, delay_ns: int = 3):
        super().__init__(name, delay_ns)
        self._input_wires = [d_input, clock]
        if reset:
            self._input_wires.append(reset)
        self._has_reset = reset is not None
        self._output_wires = [q_output, qbar_output]
        self._q_state = Signal.LOW
        self._qbar_state = Signal.HIGH
        self._prev_clock = Signal.LOW

    def evaluate(self) -> list:
        # Check for async reset
        if self._has_reset:
            reset_signal = self._input_wires[2].signal
            if reset_signal == Signal.HIGH:
                self._q_state = Signal.LOW
                self._qbar_state = Signal.HIGH
                self._propagate(self._output_wires[0], self._q_state)
                self._propagate(self._output_wires[1], self._qbar_state)
                self._prev_clock = self._input_wires[1].signal
                return []

        clock = self._input_wires[1].signal

        # Detect rising edge
        if clock == Signal.HIGH and self._prev_clock == Signal.LOW:
            d = self._input_wires[0].signal
            self._q_state = d
            self._qbar_state = ~d if d in (Signal.HIGH, Signal.LOW) else Signal.UNDEFINED

        self._prev_clock = clock
        self._propagate(self._output_wires[0], self._q_state)
        self._propagate(self._output_wires[1], self._qbar_state)
        return []


class JKFlipFlop(Gate):
    """
    JK flip-flop. Rising-edge triggered.
      J=0 K=0 -> hold
      J=1 K=0 -> set (Q=1)
      J=0 K=1 -> reset (Q=0)
      J=1 K=1 -> toggle
    """

    def __init__(self, name: str, j_input: Wire, k_input: Wire, clock: Wire,
                 q_output: Wire, qbar_output: Wire, delay_ns: int = 3):
        super().__init__(name, delay_ns)
        self._input_wires = [j_input, k_input, clock]
        self._output_wires = [q_output, qbar_output]
        self._q_state = Signal.LOW
        self._qbar_state = Signal.HIGH
        self._prev_clock = Signal.LOW

    def evaluate(self) -> list:
        clock = self._input_wires[2].signal

        if clock == Signal.HIGH and self._prev_clock == Signal.LOW:
            j = self._input_wires[0].signal
            k = self._input_wires[1].signal

            if j == Signal.HIGH and k == Signal.LOW:
                self._q_state = Signal.HIGH
                self._qbar_state = Signal.LOW
            elif j == Signal.LOW and k == Signal.HIGH:
                self._q_state = Signal.LOW
                self._qbar_state = Signal.HIGH
            elif j == Signal.HIGH and k == Signal.HIGH:
                # Toggle
                self._q_state = ~self._q_state
                self._qbar_state = ~self._qbar_state
            # else: hold

        self._prev_clock = clock
        self._propagate(self._output_wires[0], self._q_state)
        self._propagate(self._output_wires[1], self._qbar_state)
        return []


class TFlipFlop(Gate):
    """
    T (toggle) flip-flop. Rising-edge triggered.
    When T=1 on rising clock edge, Q toggles.
    When T=0, Q holds.
    """

    def __init__(self, name: str, t_input: Wire, clock: Wire,
                 q_output: Wire, qbar_output: Wire, delay_ns: int = 3):
        super().__init__(name, delay_ns)
        self._input_wires = [t_input, clock]
        self._output_wires = [q_output, qbar_output]
        self._q_state = Signal.LOW
        self._qbar_state = Signal.HIGH
        self._prev_clock = Signal.LOW

    def evaluate(self) -> list:
        clock = self._input_wires[1].signal

        if clock == Signal.HIGH and self._prev_clock == Signal.LOW:
            t = self._input_wires[0].signal
            if t == Signal.HIGH:
                self._q_state = ~self._q_state
                self._qbar_state = ~self._qbar_state

        self._prev_clock = clock
        self._propagate(self._output_wires[0], self._q_state)
        self._propagate(self._output_wires[1], self._qbar_state)
        return []


class Clock:
    """
    A clock signal generator. Produces a periodic square wave on the output wire.
    """

    def __init__(self, name: str, output: Wire, period_ns: int = 20, duty_cycle: float = 0.5):
        """
        Args:
            name: Name of the clock.
            output: Wire to drive.
            period_ns: Full period in nanoseconds.
            duty_cycle: Fraction of period that is HIGH (0.0 to 1.0).
        """
        if not 0.0 < duty_cycle < 1.0:
            raise ValueError("Duty cycle must be between 0.0 and 1.0 (exclusive)")
        if period_ns < 2:
            raise ValueError("Period must be at least 2 ns")

        self.name = name
        self.output = output
        self.period_ns = period_ns
        self.duty_cycle = duty_cycle
        self._high_ns = int(period_ns * duty_cycle)
        self._low_ns = period_ns - self._high_ns
        self._phase = 0  # 0 = high phase, 1 = low phase
        self._time_in_phase = 0  # Start at the beginning of the high phase

        self.output.signal = Signal.HIGH  # Start HIGH

    def tick(self, elapsed_ns: int) -> bool:
        """
        Advance the clock by elapsed_ns. Returns True if the output changed.
        """
        changed = False
        remaining = elapsed_ns

        while remaining > 0:
            phase_duration = self._high_ns if self._phase == 0 else self._low_ns
            time_left_in_phase = phase_duration - self._time_in_phase

            if time_left_in_phase == 0:
                # Transition immediately to next phase
                self._phase = 1 - self._phase
                self._time_in_phase = 0
                new_signal = Signal.HIGH if self._phase == 0 else Signal.LOW
                if self.output.signal != new_signal:
                    self.output.signal = new_signal
                    changed = True
                continue

            if remaining >= time_left_in_phase:
                remaining -= time_left_in_phase
                self._phase = 1 - self._phase
                self._time_in_phase = 0
                new_signal = Signal.HIGH if self._phase == 0 else Signal.LOW
                if self.output.signal != new_signal:
                    self.output.signal = new_signal
                    changed = True
            else:
                self._time_in_phase += remaining
                remaining = 0

        return changed

    def reset(self) -> None:
        """Reset clock to initial state."""
        self._phase = 0
        self._time_in_phase = 0
        self.output.signal = Signal.HIGH