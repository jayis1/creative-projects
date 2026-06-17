"""Circuit: a container for wires, gates, and sequential elements."""

from __future__ import annotations
from typing import Dict, List, Optional, Set
from .core import Signal, Wire, Bus
from .gates import Gate, AndGate, OrGate, NotGate, XorGate, NandGate, NorGate, XnorGate, BufferGate, TriStateBuffer, MultiInputGate
from .sequential import SRLatch, DLatch, DFlipFlop, JKFlipFlop, TFlipFlop, Clock


class Circuit:
    """
    A circuit is a collection of wires, gates, sequential elements, and clocks.
    It provides convenience methods for building common circuit patterns.
    """

    def __init__(self, name: str):
        self.name = name
        self.wires: Dict[str, Wire] = {}
        self.buses: Dict[str, Bus] = {}
        self.gates: List[Gate] = []
        self.sequential: List[Gate] = []
        self.clocks: List[Clock] = []

    def add_wire(self, name: str, initial: Signal = Signal.UNDEFINED, delay_ns: int = 0) -> Wire:
        """Create and register a wire."""
        if name in self.wires:
            raise ValueError(f"Wire {name!r} already exists")
        wire = Wire(name, initial, delay_ns)
        self.wires[name] = wire
        return wire

    def add_bus(self, name: str, width: int, initial: Signal = Signal.LOW) -> Bus:
        """Create and register a bus."""
        if name in self.buses:
            raise ValueError(f"Bus {name!r} already exists")
        bus = Bus(name, width, initial)
        self.buses[name] = bus
        for wire in bus.wires:
            self.wires[wire.name] = wire
        return bus

    def wire(self, name: str) -> Wire:
        """Get an existing wire by name."""
        return self.wires[name]

    def bus(self, name: str) -> Bus:
        """Get an existing bus by name."""
        return self.buses[name]

    def _add_gate(self, gate: Gate) -> Gate:
        """Register a combinational gate."""
        self.gates.append(gate)
        return gate

    def _add_sequential(self, element: Gate) -> Gate:
        """Register a sequential element."""
        self.sequential.append(element)
        return element

    # Combinational gate factories

    def add_and(self, name: str, a: Wire, b: Wire, out: Wire, delay_ns: int = 1) -> AndGate:
        gate = AndGate(name, a, b, out, delay_ns)
        return self._add_gate(gate)

    def add_or(self, name: str, a: Wire, b: Wire, out: Wire, delay_ns: int = 1) -> OrGate:
        gate = OrGate(name, a, b, out, delay_ns)
        return self._add_gate(gate)

    def add_not(self, name: str, a: Wire, out: Wire, delay_ns: int = 1) -> NotGate:
        gate = NotGate(name, a, out, delay_ns)
        return self._add_gate(gate)

    def add_xor(self, name: str, a: Wire, b: Wire, out: Wire, delay_ns: int = 1) -> XorGate:
        gate = XorGate(name, a, b, out, delay_ns)
        return self._add_gate(gate)

    def add_nand(self, name: str, a: Wire, b: Wire, out: Wire, delay_ns: int = 1) -> NandGate:
        gate = NandGate(name, a, b, out, delay_ns)
        return self._add_gate(gate)

    def add_nor(self, name: str, a: Wire, b: Wire, out: Wire, delay_ns: int = 1) -> NorGate:
        gate = NorGate(name, a, b, out, delay_ns)
        return self._add_gate(gate)

    def add_xnor(self, name: str, a: Wire, b: Wire, out: Wire, delay_ns: int = 1) -> XnorGate:
        gate = XnorGate(name, a, b, out, delay_ns)
        return self._add_gate(gate)

    def add_buffer(self, name: str, a: Wire, out: Wire, delay_ns: int = 1) -> BufferGate:
        gate = BufferGate(name, a, out, delay_ns)
        return self._add_gate(gate)

    def add_tristate(self, name: str, a: Wire, en: Wire, out: Wire, delay_ns: int = 1) -> TriStateBuffer:
        gate = TriStateBuffer(name, a, en, out, delay_ns)
        return self._add_gate(gate)

    def add_multi_gate(self, name: str, inputs: List[Wire], out: Wire,
                       gate_type: str = "and", delay_ns: int = 2) -> MultiInputGate:
        gate = MultiInputGate(name, inputs, out, gate_type, delay_ns)
        return self._add_gate(gate)

    # Sequential element factories

    def add_sr_latch(self, name: str, s: Wire, r: Wire, q: Wire, qbar: Wire,
                     delay_ns: int = 2) -> SRLatch:
        elem = SRLatch(name, s, r, q, qbar, delay_ns)
        return self._add_sequential(elem)

    def add_d_latch(self, name: str, d: Wire, en: Wire, q: Wire, qbar: Wire,
                    delay_ns: int = 2) -> DLatch:
        elem = DLatch(name, d, en, q, qbar, delay_ns)
        return self._add_sequential(elem)

    def add_d_flipflop(self, name: str, d: Wire, clk: Wire, q: Wire, qbar: Wire,
                       reset: Optional[Wire] = None, delay_ns: int = 3) -> DFlipFlop:
        elem = DFlipFlop(name, d, clk, q, qbar, reset, delay_ns)
        return self._add_sequential(elem)

    def add_jk_flipflop(self, name: str, j: Wire, k: Wire, clk: Wire,
                        q: Wire, qbar: Wire, delay_ns: int = 3) -> JKFlipFlop:
        elem = JKFlipFlop(name, j, k, clk, q, qbar, delay_ns)
        return self._add_sequential(elem)

    def add_t_flipflop(self, name: str, t: Wire, clk: Wire,
                       q: Wire, qbar: Wire, delay_ns: int = 3) -> TFlipFlop:
        elem = TFlipFlop(name, t, clk, q, qbar, delay_ns)
        return self._add_sequential(elem)

    def add_clock(self, name: str, output: Wire, period_ns: int = 20,
                  duty_cycle: float = 0.5) -> Clock:
        clk = Clock(name, output, period_ns, duty_cycle)
        self.clocks.append(clk)
        return clk

    # Composite circuit builders

    def build_half_adder(self, prefix: str, a: Wire, b: Wire,
                        sum_out: Wire, carry_out: Wire) -> None:
        """Build a half adder: sum = a XOR b, carry = a AND b."""
        self.add_xor(f"{prefix}_xor", a, b, sum_out)
        self.add_and(f"{prefix}_and", a, b, carry_out)

    def build_full_adder(self, prefix: str, a: Wire, b: Wire, cin: Wire,
                        sum_out: Wire, cout: Wire) -> None:
        """Build a full adder from two half adders and an OR gate."""
        s1 = self.add_wire(f"{prefix}_s1")
        c1 = self.add_wire(f"{prefix}_c1")
        c2 = self.add_wire(f"{prefix}_c2")

        self.build_half_adder(f"{prefix}_ha1", a, b, s1, c1)
        self.build_half_adder(f"{prefix}_ha2", s1, cin, sum_out, c2)
        self.add_or(f"{prefix}_or_carry", c1, c2, cout)

    def build_ripple_carry_adder(self, prefix: str, bus_a: Bus, bus_b: Bus,
                                  sum_bus: Bus, carry_in: Optional[Wire] = None) -> Wire:
        """
        Build an N-bit ripple carry adder.
        Returns the final carry-out wire.
        """
        width = len(bus_a)
        if len(bus_b) != width or len(sum_bus) != width:
            raise ValueError("Bus widths must match")

        cin = carry_in if carry_in else self.add_wire(f"{prefix}_cin0", Signal.LOW)
        for i in range(width):
            cout = self.add_wire(f"{prefix}_cout{i}") if i < width - 1 else self.add_wire(f"{prefix}_cout_final")
            self.build_full_adder(f"{prefix}_fa{i}", bus_a[i], bus_b[i], cin, sum_bus[i], cout)
            cin = cout
        return cin  # This is actually the final carry-out

    def build_mux2(self, prefix: str, a: Wire, b: Wire, sel: Wire, out: Wire) -> None:
        """Build a 2-to-1 multiplexer: out = sel ? b : a."""
        not_sel = self.add_wire(f"{prefix}_not_sel")
        and_a = self.add_wire(f"{prefix}_and_a")
        and_b = self.add_wire(f"{prefix}_and_b")

        self.add_not(f"{prefix}_not", sel, not_sel)
        self.add_and(f"{prefix}_and_a", a, not_sel, and_a)
        self.add_and(f"{prefix}_and_b", b, sel, and_b)
        self.add_or(f"{prefix}_or", and_a, and_b, out)

    def build_decoder_2to4(self, prefix: str, a: Wire, b: Wire,
                           y0: Wire, y1: Wire, y2: Wire, y3: Wire) -> None:
        """Build a 2-to-4 decoder."""
        not_a = self.add_wire(f"{prefix}_not_a")
        not_b = self.add_wire(f"{prefix}_not_b")

        self.add_not(f"{prefix}_not_a", a, not_a)
        self.add_not(f"{prefix}_not_b", b, not_b)
        self.add_and(f"{prefix}_y0", not_a, not_b, y0)
        self.add_and(f"{prefix}_y1", a, not_b, y1)
        self.add_and(f"{prefix}_y2", not_a, b, y2)
        self.add_and(f"{prefix}_y3", a, b, y3)

    def __repr__(self) -> str:
        return (f"Circuit({self.name!r}, wires={len(self.wires)}, "
                f"gates={len(self.gates)}, sequential={len(self.sequential)}, "
                f"clocks={len(self.clocks)})")