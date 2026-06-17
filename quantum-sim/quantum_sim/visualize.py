"""
ASCII circuit visualization for QuantumCircuit.

Renders a quantum circuit as a text diagram, showing gate labels on
horizontal qubit wires, vertical connections for multi-qubit gates,
and control-target relationships.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .circuit import QuantumCircuit, Operation
from .gates import GATES

__all__ = ["draw_circuit", "circuit_ascii"]


# Single-character gate symbols for common gates
_GATE_SYMBOLS: Dict[str, str] = {
    "H": "H", "X": "X", "Y": "Y", "Z": "Z", "S": "S", "T": "T", "SX": "SX",
    "I": "I", "I1": "I", "id": "I",
    "CNOT": "@", "CX": "@", "C-X": "@",
    "CZ": "z", "SWAP": "x", "iSWAP": "i", "TOFFOLI": "@", "CCX": "@",
    "FREDKIN": "x", "CSWAP": "x",
    "barrier": "≡",
    "measure": "M",
}


def _gate_symbol(op: Operation) -> str:
    """Get the display symbol for a gate."""
    if op.name in _GATE_SYMBOLS:
        return _GATE_SYMBOLS[op.name]
    # Parameterized gates have names like "RX(1.57)"
    name_base = op.name.split("(")[0]
    if name_base in _GATE_SYMBOLS:
        return _GATE_SYMBOLS[name_base]
    # Truncate long names
    if len(op.name) > 4:
        return op.name[:3] + "."
    return op.name


def draw_circuit(circuit: QuantumCircuit, width: int = 0) -> str:
    """
    Render a quantum circuit as an ASCII diagram.

    Parameters
    ----------
    circuit : QuantumCircuit
    width : int, optional
        Minimum column width.  If 0, auto-sized.
    """
    n = circuit.n_qubits
    ops = circuit.operations

    if not ops:
        return "\n".join(f"q{i}: ────" for i in range(n))

    # Assign each operation a column
    # Group operations into layers: operations on disjoint qubits can share
    # a column, but for simplicity we give each operation its own column.
    columns: List[List[Operation]] = []
    current_layer: List[Operation] = []
    used_qubits: set[int] = set()

    for op in ops:
        op_qubits = set(op.targets) | set(op.controls)
        if op.name in ("barrier",):
            if current_layer:
                columns.append(current_layer)
                current_layer = []
                used_qubits = set()
            columns.append([op])
            continue
        if op_qubits & used_qubits:
            columns.append(current_layer)
            current_layer = [op]
            used_qubits = op_qubits
        else:
            current_layer.append(op)
            used_qubits |= op_qubits
    if current_layer:
        columns.append(current_layer)

    # Build the grid
    n_cols = len(columns)
    col_width = max(3, width)  # at least 3 chars per column

    # Each qubit gets a line; we build a character grid
    grid: List[List[str]] = [[" "] * (n_cols * (col_width + 2) + 1) for _ in range(n)]

    for col_idx, layer in enumerate(columns):
        x_start = col_idx * (col_width + 2) + 1
        x_mid = x_start + col_width // 2

        for op in layer:
            if op.name == "barrier":
                for q in range(n):
                    grid[q][x_mid] = "≡"
                continue

            symbol = _gate_symbol(op)

            # Place the gate symbol on each target qubit
            for t in op.targets:
                for dx in range(col_width):
                    if 0 <= x_start + dx < len(grid[t]):
                        if dx == col_width // 2:
                            grid[t][x_mid] = symbol[0] if len(symbol) == 1 else symbol[0]
                        elif grid[t][x_start + dx] == " ":
                            grid[t][x_start + dx] = "─"

            # Place control markers
            for c in op.controls:
                if 0 <= c < n:
                    grid[c][x_mid] = "●"
                    # Connect control to target with vertical lines
                    targets_sorted = sorted(op.targets)
                    all_qubits = sorted(list(op.controls) + list(op.targets))
                    min_q = min(all_qubits)
                    max_q = max(all_qubits)
                    for q in range(min_q, max_q + 1):
                        if q in op.controls or q in op.targets:
                            if grid[q][x_mid] == " ":
                                grid[q][x_mid] = "│"
                        else:
                            grid[q][x_mid] = "│"

    # Assemble output lines with qubit labels and wire connections
    lines = []
    for q in range(n):
        chars = list(grid[q])
        # Replace remaining spaces with ─ for wire continuity, but only
        # between the first and last non-space character
        first_non_space = 0
        last_non_space = 0
        for i, c in enumerate(chars):
            if c != " ":
                last_non_space = i
        # Fill gaps with ─
        for i in range(first_non_space, last_non_space + 1):
            if chars[i] == " ":
                chars[i] = "─"
        line = f"q{q}: " + "".join(chars).rstrip()
        lines.append(line)

    return "\n".join(lines)


# Alias
circuit_ascii = draw_circuit