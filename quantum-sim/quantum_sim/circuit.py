"""
QuantumCircuit: a declarative description of a quantum circuit.

A circuit is a sequence of layers, where each layer is a list of
operations applied "simultaneously" (they act on disjoint qubits
or are combined into a single tensor-product unitary).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional, Tuple, Union

import numpy as np

from .gates import GATES, Gate, controlled, rx, ry, rz, phase, u1, u2, u3

__all__ = ["QuantumCircuit", "Operation", "CircuitBuilder"]

# Type alias for a gate spec: either a Gate object, a string key into GATES,
# or a callable that produces a Gate (for parameterized gates).
GateSpec = Union[str, Gate, callable]  # type: ignore[valid-type]


@dataclass
class Operation:
    """A single gate application: apply *gate* to *targets* qubits."""
    gate: Gate
    targets: Tuple[int, ...]
    controls: Tuple[int, ...] = ()
    name: str = ""

    def __post_init__(self) -> None:
        self.targets = tuple(self.targets)
        self.controls = tuple(self.controls)
        if not self.name:
            self.name = self.gate.name

    def __repr__(self) -> str:
        ctrl_str = ""
        if self.controls:
            ctrl_str = f"controls={self.controls}, "
        return f"Op({self.name}, targets={self.targets}, {ctrl_str})"


class QuantumCircuit:
    """
    A quantum circuit: ordered list of operations on *n_qubits*.

    Example::

        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
    """

    def __init__(self, n_qubits: int) -> None:
        if n_qubits <= 0:
            raise ValueError("n_qubits must be positive")
        self.n_qubits = n_qubits
        self.operations: List[Operation] = []
        self._measurements: Dict[int, Optional[int]] = {}

    # -- gate application helpers ------------------------------------------

    def _resolve_gate(self, gate: Union[str, Gate, callable], params=()) -> Gate:  # type: ignore[valid-type]
        if isinstance(gate, Gate):
            return gate
        if isinstance(gate, str):
            obj = GATES.get(gate)
            if obj is None:
                raise KeyError(f"Unknown gate '{gate}'. Known: {list(GATES.keys())}")
            if isinstance(obj, Gate):
                return obj
            # parameterized constructor
            return obj(*params)
        if callable(gate):
            return gate(*params)
        raise TypeError(f"Cannot resolve gate from {gate!r}")

    def _check_qubits(self, *qubits: int) -> None:
        for q in qubits:
            if not (0 <= q < self.n_qubits):
                raise ValueError(f"Qubit {q} out of range [0, {self.n_qubits})")
        if len(set(qubits)) != len(qubits):
            raise ValueError(f"Duplicate qubit indices: {qubits}")

    def add(self, gate: Union[str, Gate, callable], *targets: int, controls: Tuple[int, ...] = (), params=()) -> "QuantumCircuit":  # type: ignore[valid-type]
        """Add a gate to the circuit."""
        resolved = self._resolve_gate(gate, params)
        self._check_qubits(*targets, *controls)
        self.operations.append(Operation(gate=resolved, targets=targets, controls=controls))
        return self

    # -- named convenience methods ----------------------------------------

    def h(self, q: int) -> "QuantumCircuit":
        return self.add("H", q)

    def x(self, q: int) -> "QuantumCircuit":
        return self.add("X", q)

    def y(self, q: int) -> "QuantumCircuit":
        return self.add("Y", q)

    def z(self, q: int) -> "QuantumCircuit":
        return self.add("Z", q)

    def s(self, q: int) -> "QuantumCircuit":
        return self.add("S", q)

    def t(self, q: int) -> "QuantumCircuit":
        return self.add("T", q)

    def sx(self, q: int) -> "QuantumCircuit":
        return self.add("SX", q)

    def cx(self, control: int, target: int) -> "QuantumCircuit":
        return self.add("CNOT", target, controls=(control,))

    def cy(self, control: int, target: int) -> "QuantumCircuit":
        return self.add(controlled(GATES["Y"]), target, controls=(control,))

    def cz(self, control: int, target: int) -> "QuantumCircuit":
        return self.add("CZ", target, controls=(control,))

    def swap(self, q1: int, q2: int) -> "QuantumCircuit":
        return self.add("SWAP", q1, q2)

    def iswap(self, q1: int, q2: int) -> "QuantumCircuit":
        return self.add("iSWAP", q1, q2)

    def toffoli(self, c1: int, c2: int, target: int) -> "QuantumCircuit":
        return self.add("TOFFOLI", target, controls=(c1, c2))

    def fredkin(self, control: int, q1: int, q2: int) -> "QuantumCircuit":
        return self.add("FREDKIN", q1, q2, controls=(control,))

    def rx(self, q: int, theta: float) -> "QuantumCircuit":
        return self.add(rx, q, params=(theta,))

    def ry(self, q: int, theta: float) -> "QuantumCircuit":
        return self.add(ry, q, params=(theta,))

    def rz(self, q: int, theta: float) -> "QuantumCircuit":
        return self.add(rz, q, params=(theta,))

    def phase(self, q: int, theta: float) -> "QuantumCircuit":
        return self.add(phase, q, params=(theta,))

    def u1(self, q: int, theta: float) -> "QuantumCircuit":
        return self.add(u1, q, params=(theta,))

    def u2(self, q: int, phi: float, lam: float) -> "QuantumCircuit":
        return self.add(u2, q, params=(phi, lam))

    def u3(self, q: int, theta: float, phi: float, lam: float) -> "QuantumCircuit":
        return self.add(u3, q, params=(theta, phi, lam))

    def barrier(self) -> "QuantumCircuit":
        """No-op marker (does not affect simulation)."""
        self.operations.append(Operation(gate=GATES["I1"], targets=(0,), name="barrier"))
        return self

    def measure(self, q: int, cbit: Optional[int] = None) -> "QuantumCircuit":
        """Record a measurement request for qubit *q*."""
        self._measurements[q] = cbit
        self.operations.append(Operation(gate=GATES["I1"], targets=(q,), name="measure"))
        return self

    # -- introspection ----------------------------------------------------

    def depth(self) -> int:
        """Approximate circuit depth = number of operations."""
        return len(self.operations)

    @property
    def measurements(self) -> Dict[int, Optional[int]]:
        return dict(self._measurements)

    def __len__(self) -> int:
        return len(self.operations)

    def __iter__(self) -> Iterator[Operation]:
        return iter(self.operations)

    def __repr__(self) -> str:
        return f"QuantumCircuit(n_qubits={self.n_qubits}, ops={len(self.operations)})"

    def __str__(self) -> str:
        lines = [f"QuantumCircuit(n_qubits={self.n_qubits}, depth={self.depth()})"]
        for op in self.operations:
            if op.controls:
                lines.append(f"  {op.name}: {op.controls} -> {op.targets}")
            else:
                lines.append(f"  {op.name}: {op.targets}")
        return "\n".join(lines)

    def to_qasm(self) -> str:
        """Emit an OpenQASM 2.0 string for the circuit."""
        lines = ["OPENQASM 2.0;", 'include "qelib1.inc";']
        lines.append(f"qreg q[{self.n_qubits}];")
        n_clbits = max((c for c in self._measurements.values() if c is not None), default=-1) + 1
        if n_clbits > 0:
            lines.append(f"creg c[{n_clbits}];")
        qasm_names = {
            "I": "id", "H": "h", "X": "x", "Y": "y", "Z": "z",
            "S": "s", "T": "t", "SX": "sx", "CNOT": "cx", "CZ": "cz",
            "SWAP": "swap", "iSWAP": "iswap", "TOFFOLI": "ccx",
            "FREDKIN": "cswap",
        }
        for op in self.operations:
            if op.name == "barrier":
                lines.append(f"barrier q;")
                continue
            if op.name == "measure":
                q = op.targets[0]
                c = self._measurements.get(q)
                cbit = c if c is not None else q
                lines.append(f"measure q[{q}] -> c[{cbit}];")
                continue
            qn = qasm_names.get(op.name, op.name.lower())
            targs = ",".join(f"q[{t}]" for t in op.targets)
            ctrls = ",".join(f"q[{c}]" for c in op.controls)
            if ctrls:
                lines.append(f"{qn} {ctrls},{targs};")
            else:
                lines.append(f"{qn} {targs};")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialize the circuit to a JSON-compatible dictionary."""
        ops_data = []
        for op in self.operations:
            # Detect parameterized gates by checking if the gate name contains
            # a parameter pattern like "RX(0.7854)".  Extract the base name and
            # parameters for roundtrip serialization.
            gate_name = op.gate.name
            params = self._extract_gate_params(op)
            ops_data.append({
                "name": op.name,
                "gate_name": gate_name,
                "targets": list(op.targets),
                "controls": list(op.controls),
                "params": params,
            })
        return {
            "n_qubits": self.n_qubits,
            "operations": ops_data,
            "version": "2.0",
        }

    @staticmethod
    def _extract_gate_params(op: "Operation") -> list:
        """Extract numeric parameters from a parameterized gate's name.

        Returns an empty list for non-parameterized gates.
        """
        name = op.gate.name
        # Parameterized gates have names like "RX(0.7854)" or "U3(1.57,0.5,0.3)"
        if "(" not in name:
            return []
        param_str = name[name.index("(") + 1:name.rindex(")")]
        if not param_str:
            return []
        parts = param_str.split(",")
        try:
            return [float(p.strip()) for p in parts]
        except ValueError:
            return []

    @classmethod
    def from_dict(cls, data: dict) -> "QuantumCircuit":
        """Deserialize a circuit from a dictionary."""
        from .gates import GATES, Gate, rx, ry, rz, phase, u1, u2, u3

        # Map from gate name prefix to the parameterized constructor
        param_constructors = {
            "RX": rx, "RY": ry, "RZ": rz,
            "P": phase, "PHASE": phase,
            "U1": u1, "U2": u2, "U3": u3,
        }

        qc = cls(data["n_qubits"])
        for op_data in data["operations"]:
            name = op_data["name"]
            targets = tuple(op_data["targets"])
            controls = tuple(op_data["controls"])
            params = op_data.get("params", [])

            if name in ("barrier",):
                qc.barrier()
            elif name == "measure":
                qc.measure(targets[0])
            else:
                gate_name = op_data["gate_name"]
                # First try direct lookup in GATES (for standard non-parameterized gates)
                gate = GATES.get(gate_name)
                if gate is not None and isinstance(gate, Gate):
                    qc.operations.append(Operation(gate=gate, targets=targets, controls=controls))
                    continue

                # If not found, try parameterized gate reconstruction
                # Extract the base name (e.g., "RY" from "RY(0.7854)")
                base_name = gate_name.split("(")[0] if "(" in gate_name else gate_name
                constructor = param_constructors.get(base_name)
                if constructor is not None and params:
                    # Reconstruct the parameterized gate
                    gate = constructor(*params)
                    qc.operations.append(Operation(gate=gate, targets=targets, controls=controls))
                    continue

                # Also try looking up by the op name (without parameters)
                gate = GATES.get(name)
                if gate is not None and isinstance(gate, Gate):
                    qc.operations.append(Operation(gate=gate, targets=targets, controls=controls))
                    continue

                raise ValueError(f"Cannot deserialize gate '{gate_name}'")
        return qc

    def to_json(self) -> str:
        """Serialize to a JSON string."""
        import json
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "QuantumCircuit":
        """Deserialize from a JSON string."""
        import json
        return cls.from_dict(json.loads(json_str))


class CircuitBuilder:
    """Fluent builder that mirrors QuantumCircuit methods but returns self."""

    def __init__(self, n_qubits: int) -> None:
        self.circuit = QuantumCircuit(n_qubits)

    def h(self, q: int) -> "CircuitBuilder":
        self.circuit.h(q)
        return self

    def cx(self, c: int, t: int) -> "CircuitBuilder":
        self.circuit.cx(c, t)
        return self

    def x(self, q: int) -> "CircuitBuilder":
        self.circuit.x(q)
        return self

    def ry(self, q: int, theta: float) -> "CircuitBuilder":
        self.circuit.ry(q, theta)
        return self

    def measure(self, q: int) -> "CircuitBuilder":
        self.circuit.measure(q)
        return self

    def build(self) -> QuantumCircuit:
        return self.circuit