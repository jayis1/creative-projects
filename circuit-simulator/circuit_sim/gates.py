"""Logic gate implementations with propagation delay support."""

from __future__ import annotations
from typing import List, Optional
from .core import Signal, Wire


class Gate:
    """Base class for all logic gates."""

    def __init__(self, name: str, delay_ns: int = 1):
        self.name = name
        self.delay_ns = delay_ns
        self._input_wires: List[Wire] = []
        self._output_wires: List[Wire] = []
        self._propagation_queue: List[tuple] = []  # [(output_wire, old_signal, new_signal, time_remaining)]

    @property
    def inputs(self) -> List[Wire]:
        return list(self._input_wires)

    @property
    def outputs(self) -> List[Wire]:
        return list(self._output_wires)

    def evaluate(self) -> List[tuple]:
        """
        Evaluate the gate and return a list of (output_wire, new_signal) tuples.
        Does NOT immediately set wire values — the simulator handles propagation delay.
        Subclasses must implement this.
        """
        raise NotImplementedError

    def tick(self, elapsed_ns: int) -> List[tuple]:
        """
        Advance the gate's internal delay state by elapsed_ns.
        Returns list of (wire, signal) pairs whose outputs are now ready.
        """
        ready = []
        remaining = []
        for wire, new_signal, time_left in self._propagation_queue:
            if time_left <= elapsed_ns:
                ready.append((wire, new_signal))
            else:
                remaining.append((wire, new_signal, time_left - elapsed_ns))
        self._propagation_queue = remaining
        return ready

    def _propagate(self, wire: Wire, signal: Signal) -> None:
        """Schedule a signal change on a wire after propagation delay."""
        if wire.signal != signal:
            self._propagation_queue.append((wire, signal, self.delay_ns))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name!r})"


class AndGate(Gate):
    """2-input AND gate."""

    def __init__(self, name: str, input_a: Wire, input_b: Wire, output: Wire, delay_ns: int = 1):
        super().__init__(name, delay_ns)
        self._input_wires = [input_a, input_b]
        self._output_wires = [output]

    def evaluate(self) -> List[tuple]:
        result = self._input_wires[0].signal & self._input_wires[1].signal
        self._propagate(self._output_wires[0], result)
        return []


class OrGate(Gate):
    """2-input OR gate."""

    def __init__(self, name: str, input_a: Wire, input_b: Wire, output: Wire, delay_ns: int = 1):
        super().__init__(name, delay_ns)
        self._input_wires = [input_a, input_b]
        self._output_wires = [output]

    def evaluate(self) -> List[tuple]:
        result = self._input_wires[0].signal | self._input_wires[1].signal
        self._propagate(self._output_wires[0], result)
        return []


class NotGate(Gate):
    """Inverter gate."""

    def __init__(self, name: str, input_a: Wire, output: Wire, delay_ns: int = 1):
        super().__init__(name, delay_ns)
        self._input_wires = [input_a]
        self._output_wires = [output]

    def evaluate(self) -> List[tuple]:
        result = ~self._input_wires[0].signal
        self._propagate(self._output_wires[0], result)
        return []


class XorGate(Gate):
    """2-input XOR gate."""

    def __init__(self, name: str, input_a: Wire, input_b: Wire, output: Wire, delay_ns: int = 1):
        super().__init__(name, delay_ns)
        self._input_wires = [input_a, input_b]
        self._output_wires = [output]

    def evaluate(self) -> List[tuple]:
        result = self._input_wires[0].signal ^ self._input_wires[1].signal
        self._propagate(self._output_wires[0], result)
        return []


class NandGate(Gate):
    """2-input NAND gate."""

    def __init__(self, name: str, input_a: Wire, input_b: Wire, output: Wire, delay_ns: int = 1):
        super().__init__(name, delay_ns)
        self._input_wires = [input_a, input_b]
        self._output_wires = [output]

    def evaluate(self) -> List[tuple]:
        result = self._input_wires[0].signal & self._input_wires[1].signal
        self._propagate(self._output_wires[0], ~result)
        return []


class NorGate(Gate):
    """2-input NOR gate."""

    def __init__(self, name: str, input_a: Wire, input_b: Wire, output: Wire, delay_ns: int = 1):
        super().__init__(name, delay_ns)
        self._input_wires = [input_a, input_b]
        self._output_wires = [output]

    def evaluate(self) -> List[tuple]:
        result = self._input_wires[0].signal | self._input_wires[1].signal
        self._propagate(self._output_wires[0], ~result)
        return []


class XnorGate(Gate):
    """2-input XNOR gate."""

    def __init__(self, name: str, input_a: Wire, input_b: Wire, output: Wire, delay_ns: int = 1):
        super().__init__(name, delay_ns)
        self._input_wires = [input_a, input_b]
        self._output_wires = [output]

    def evaluate(self) -> List[tuple]:
        result = self._input_wires[0].signal ^ self._input_wires[1].signal
        self._propagate(self._output_wires[0], ~result)
        return []


class BufferGate(Gate):
    """Buffer gate (identity with delay)."""

    def __init__(self, name: str, input_a: Wire, output: Wire, delay_ns: int = 1):
        super().__init__(name, delay_ns)
        self._input_wires = [input_a]
        self._output_wires = [output]

    def evaluate(self) -> List[tuple]:
        result = self._input_wires[0].signal
        self._propagate(self._output_wires[0], result)
        return []


class TriStateBuffer(Gate):
    """
    Tri-state buffer. When enable is HIGH, output follows input.
    When enable is LOW, output is high-impedance.
    """

    def __init__(self, name: str, input_a: Wire, enable: Wire, output: Wire, delay_ns: int = 1):
        super().__init__(name, delay_ns)
        self._input_wires = [input_a, enable]
        self._output_wires = [output]

    def evaluate(self) -> List[tuple]:
        if self._input_wires[1].signal == Signal.HIGH:
            result = self._input_wires[0].signal
        else:
            result = Signal.HIGH_IMPEDANCE
        self._propagate(self._output_wires[0], result)
        return []


class MultiInputGate(Gate):
    """Gate that supports more than 2 inputs (AND, OR, NAND, NOR variants)."""

    def __init__(self, name: str, inputs: List[Wire], output: Wire,
                 gate_type: str = "and", delay_ns: int = 2):
        super().__init__(name, delay_ns)
        self._input_wires = list(inputs)
        self._output_wires = [output]
        self._gate_type = gate_type

    def evaluate(self) -> List[tuple]:
        signals = [w.signal for w in self._input_wires]
        if self._gate_type == "and":
            result = Signal.HIGH
            for s in signals:
                result = result & s
        elif self._gate_type == "or":
            result = Signal.LOW
            for s in signals:
                result = result | s
        elif self._gate_type == "nand":
            result = Signal.HIGH
            for s in signals:
                result = result & s
            result = ~result
        elif self._gate_type == "nor":
            result = Signal.LOW
            for s in signals:
                result = result | s
            result = ~result
        else:
            raise ValueError(f"Unknown gate type: {self._gate_type}")
        self._propagate(self._output_wires[0], result)
        return []