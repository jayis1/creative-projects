"""Truth table generator and circuit analyzer."""

from __future__ import annotations
from typing import Dict, List, Tuple, Optional
from itertools import product
from .core import Signal, Wire
from .circuit import Circuit
from .simulator import Simulator


class TruthTable:
    """
    Generate truth tables for combinational circuits.
    Automatically enumerates all input combinations and records outputs.
    """

    def __init__(self, circuit: Circuit, input_names: List[str], output_names: List[str]):
        """
        Args:
            circuit: The circuit to analyze.
            input_names: Names of input wires (in order, LSB first for buses).
            output_names: Names of output wires to record.
        """
        self.circuit = circuit
        self.input_names = input_names
        self.output_names = output_names
        self.rows: List[Dict[str, Signal]] = []

    def generate(self, settle_steps: int = 10) -> List[Dict[str, Signal]]:
        """
        Generate the full truth table by enumerating all input combinations.
        Returns list of dicts mapping wire names to Signal values.
        """
        self.rows = []
        n_inputs = len(self.input_names)

        for combo in product([Signal.LOW, Signal.HIGH], repeat=n_inputs):
            sim = Simulator(self.circuit, step_ns=1)

            # Set input values
            for name, value in zip(self.input_names, combo):
                if name in self.circuit.wires:
                    self.circuit.wires[name].signal = value

            # Run simulation to let outputs settle
            sim.run(settle_steps)

            # Record output values
            row = {}
            for name, value in zip(self.input_names, combo):
                row[name] = value
            for name in self.output_names:
                if name in self.circuit.wires:
                    row[name] = self.circuit.wires[name].signal
                else:
                    row[name] = Signal.UNDEFINED
            self.rows.append(row)

        return self.rows

    def to_ascii(self) -> str:
        """Render the truth table as an ASCII table."""
        if not self.rows:
            self.generate()

        all_names = self.input_names + self.output_names
        col_widths = {name: max(len(name), 5) for name in all_names}

        # Header
        header = " | ".join(name.center(col_widths[name]) for name in all_names)
        separator = "-+-".join("-" * col_widths[name] for name in all_names)

        lines = [header, separator]
        for row in self.rows:
            values = []
            for name in all_names:
                sig = row.get(name, Signal.UNDEFINED)
                # Use short names
                short = {Signal.HIGH: "1", Signal.LOW: "0", 
                         Signal.UNDEFINED: "?", Signal.HIGH_IMPEDANCE: "Z"}
                values.append(short.get(sig, "?").center(col_widths[name]))
            lines.append(" | ".join(values))

        return "\n".join(lines)

    def to_csv(self) -> str:
        """Export truth table as CSV."""
        if not self.rows:
            self.generate()

        all_names = self.input_names + self.output_names
        lines = [",".join(all_names)]
        for row in self.rows:
            values = []
            for name in all_names:
                sig = row.get(name, Signal.UNDEFINED)
                values.append(str(sig.to_int()) if sig in (Signal.HIGH, Signal.LOW) else "?")
            lines.append(",".join(values))
        return "\n".join(lines)


class CircuitStats:
    """
    Analyze circuit statistics: gate count, depth, fan-out, critical path.
    """

    def __init__(self, circuit: Circuit):
        self.circuit = circuit

    def gate_count(self) -> Dict[str, int]:
        """Count gates by type."""
        counts: Dict[str, int] = {}
        for gate in self.circuit.gates:
            name = type(gate).__name__
            counts[name] = counts.get(name, 0) + 1
        for elem in self.circuit.sequential:
            name = type(elem).__name__
            counts[name] = counts.get(name, 0) + 1
        return counts

    def wire_count(self) -> int:
        """Return the total number of wires."""
        return len(self.circuit.wires)

    def total_gates(self) -> int:
        """Return the total number of gates (combinational + sequential)."""
        return len(self.circuit.gates) + len(self.circuit.sequential)

    def compute_depth(self) -> int:
        """
        Compute the combinational depth (longest path from inputs to outputs).
        Uses topological sort on the gate dependency graph.
        """
        # Build wire -> gate mapping
        wire_to_gate: Dict[str, int] = {}
        for i, gate in enumerate(self.circuit.gates):
            for wire in gate.outputs:
                wire_to_gate[wire.name] = i

        # Compute depth for each gate using memoization
        depths: Dict[str, int] = {}
        
        def wire_depth(wire_name: str) -> int:
            if wire_name in depths:
                return depths[wire_name]
            if wire_name not in wire_to_gate:
                depths[wire_name] = 0
                return 0
            gate_idx = wire_to_gate[wire_name]
            gate = self.circuit.gates[gate_idx]
            max_input_depth = 0
            for input_wire in gate.inputs:
                max_input_depth = max(max_input_depth, wire_depth(input_wire.name))
            depth = max_input_depth + 1
            depths[wire_name] = depth
            return depth

        max_depth = 0
        for gate in self.circuit.gates:
            for wire in gate.outputs:
                max_depth = max(max_depth, wire_depth(wire.name))
        
        return max_depth

    def summary(self) -> str:
        """Generate a summary string of circuit statistics."""
        counts = self.gate_count()
        lines = [
            f"Circuit: {self.circuit.name}",
            f"  Wires: {self.wire_count()}",
            f"  Total gates: {self.total_gates()}",
            f"  Combinational depth: {self.compute_depth()}",
            f"  Gate breakdown:",
        ]
        for gate_type, count in sorted(counts.items()):
            lines.append(f"    {gate_type}: {count}")
        return "\n".join(lines)