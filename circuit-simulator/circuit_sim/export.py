"""Circuit export: JSON serialization, Graphviz DOT export, and ASCII art."""

from __future__ import annotations
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from .core import Signal, Wire, Bus
from .circuit import Circuit
from .gates import (
    Gate, AndGate, OrGate, NotGate, XorGate, NandGate, NorGate, XnorGate,
    BufferGate, TriStateBuffer, MultiInputGate,
)
from .sequential import SRLatch, DLatch, DFlipFlop, JKFlipFlop, TFlipFlop, Clock

logger = logging.getLogger(__name__)


def circuit_to_dict(circuit: Circuit) -> Dict[str, Any]:
    """Serialize a Circuit to a JSON-compatible dictionary.

    Args:
        circuit: The circuit to serialize.

    Returns:
        A dictionary representation that can be dumped to JSON.
    """
    wires_data = {}
    for name, wire in circuit.wires.items():
        wires_data[name] = {
            "initial": wire._initial.name,
            "delay_ns": wire._delay_ns,
        }

    buses_data = {}
    for name, bus in circuit.buses.items():
        buses_data[name] = {
            "width": bus.width,
            "initial": bus.wires[0]._initial.name,
        }

    gates_data = []
    for gate in circuit.gates:
        gate_dict = {
            "type": type(gate).__name__,
            "name": gate.name,
            "inputs": [w.name for w in gate._input_wires],
            "outputs": [w.name for w in gate._output_wires],
            "delay_ns": gate.delay_ns,
        }
        if isinstance(gate, MultiInputGate):
            gate_dict["gate_type"] = gate._gate_type
        if isinstance(gate, TriStateBuffer):
            pass  # inputs[0]=data, inputs[1]=enable
        gates_data.append(gate_dict)

    sequential_data = []
    for elem in circuit.sequential:
        seq_dict = {
            "type": type(elem).__name__,
            "name": elem.name,
            "inputs": [w.name for w in elem._input_wires],
            "outputs": [w.name for w in elem._output_wires],
            "delay_ns": elem.delay_ns,
        }
        sequential_data.append(seq_dict)

    clocks_data = []
    for clk in circuit.clocks:
        clocks_data.append({
            "name": clk.name,
            "output": clk.output.name,
            "period_ns": clk.period_ns,
            "duty_cycle": clk.duty_cycle,
        })

    return {
        "name": circuit.name,
        "wires": wires_data,
        "buses": buses_data,
        "gates": gates_data,
        "sequential": sequential_data,
        "clocks": clocks_data,
    }


def circuit_to_json(circuit: Circuit, path: Optional[str] = None, indent: int = 2) -> str:
    """Serialize a Circuit to JSON. Optionally write to a file.

    Args:
        circuit: The circuit to serialize.
        path: Optional file path to write JSON to.
        indent: JSON indentation level.

    Returns:
        JSON string.
    """
    data = circuit_to_dict(circuit)
    json_str = json.dumps(data, indent=indent)
    if path:
        Path(path).write_text(json_str)
        logger.info("Circuit exported to %s", path)
    return json_str


def circuit_from_json(path_or_str: str) -> Circuit:
    """Deserialize a Circuit from a JSON file path or JSON string.

    Args:
        path_or_str: Path to JSON file or JSON string.

    Returns:
        A reconstructed Circuit object.
    """
    try:
        p = Path(path_or_str)
        if p.exists():
            data = json.loads(p.read_text())
        else:
            data = json.loads(path_or_str)
    except (OSError, ValueError):
        data = json.loads(path_or_str)

    circuit = Circuit(data["name"])

    # Create wires
    for name, wire_data in data.get("wires", {}).items():
        initial = Signal[wire_data["initial"]]
        # Skip wires that belong to buses — they'll be created with the bus
        circuit.add_wire(name, initial)

    # Create buses
    for name, bus_data in data.get("buses", {}).items():
        initial = Signal[bus_data["initial"]]
        width = bus_data["width"]
        # Remove bus wires that were already added as plain wires
        for i in range(width):
            bus_wire_name = f"{name}[{i}]"
            if bus_wire_name in circuit.wires:
                del circuit.wires[bus_wire_name]
        circuit.add_bus(name, width, initial)

    # Recreate gates
    gate_class_map = {
        "AndGate": AndGate, "OrGate": OrGate, "NotGate": NotGate,
        "XorGate": XorGate, "NandGate": NandGate, "NorGate": NorGate,
        "XnorGate": XnorGate, "BufferGate": BufferGate,
        "TriStateBuffer": TriStateBuffer, "MultiInputGate": MultiInputGate,
    }

    for gate_data in data.get("gates", []):
        gate_type = gate_data["type"]
        gate_name = gate_data["name"]
        input_names = gate_data["inputs"]
        output_name = gate_data["outputs"][0]
        delay_ns = gate_data.get("delay_ns", 1)

        input_wires = [circuit.wire(n) for n in input_names]
        output_wire = circuit.wire(output_name)

        if gate_type == "MultiInputGate":
            circuit.add_multi_gate(
                gate_name, input_wires, output_wire,
                gate_type=gate_data.get("gate_type", "and"),
                delay_ns=delay_ns,
            )
        elif gate_type == "TriStateBuffer":
            circuit.add_tristate(gate_name, input_wires[0], input_wires[1], output_wire, delay_ns=delay_ns)
        elif gate_type in ("NotGate", "BufferGate"):
            cls = gate_class_map[gate_type]
            circuit._add_gate(cls(gate_name, input_wires[0], output_wire, delay_ns=delay_ns))
        else:
            cls = gate_class_map[gate_type]
            circuit._add_gate(cls(gate_name, input_wires[0], input_wires[1], output_wire, delay_ns=delay_ns))

    # Recreate sequential elements
    seq_class_map = {
        "SRLatch": ("add_sr_latch", 2),
        "DLatch": ("add_d_latch", 2),
        "DFlipFlop": ("add_d_flipflop", 2),
        "JKFlipFlop": ("add_jk_flipflop", 3),
        "TFlipFlop": ("add_t_flipflop", 2),
    }

    for seq_data in data.get("sequential", []):
        seq_type = seq_data["type"]
        seq_name = seq_data["name"]
        input_names = seq_data["inputs"]
        output_names = seq_data["outputs"]
        delay_ns = seq_data.get("delay_ns", 3)

        input_wires = [circuit.wire(n) for n in input_names]
        output_wires = [circuit.wire(n) for n in output_names]

        if seq_type == "SRLatch":
            circuit.add_sr_latch(seq_name, input_wires[0], input_wires[1],
                                output_wires[0], output_wires[1], delay_ns=delay_ns)
        elif seq_type == "DLatch":
            circuit.add_d_latch(seq_name, input_wires[0], input_wires[1],
                              output_wires[0], output_wires[1], delay_ns=delay_ns)
        elif seq_type == "DFlipFlop":
            circuit.add_d_flipflop(seq_name, input_wires[0], input_wires[1],
                                  output_wires[0], output_wires[1], delay_ns=delay_ns)
        elif seq_type == "JKFlipFlop":
            circuit.add_jk_flipflop(seq_name, input_wires[0], input_wires[1],
                                  input_wires[2], output_wires[0], output_wires[1], delay_ns=delay_ns)
        elif seq_type == "TFlipFlop":
            circuit.add_t_flipflop(seq_name, input_wires[0], input_wires[1],
                                  output_wires[0], output_wires[1], delay_ns=delay_ns)

    # Recreate clocks
    for clk_data in data.get("clocks", []):
        circuit.add_clock(
            clk_data["name"],
            circuit.wire(clk_data["output"]),
            clk_data["period_ns"],
            clk_data["duty_cycle"],
        )

    return circuit


def circuit_to_dot(circuit: Circuit) -> str:
    """Export a Circuit to Graphviz DOT format for visualization.

    Args:
        circuit: The circuit to export.

    Returns:
        DOT format string that can be rendered with Graphviz.
    """
    lines = [
        'digraph "{}" {{'.format(circuit.name),
        '  rankdir=LR;',
        '  node [shape=box, style=filled, fillcolor="#e8e8e8"];',
        '',
        '  // Input wires (left side)',
        '  subgraph cluster_inputs {',
        '    label="Inputs";',
        '    style=dashed;',
        '    color=gray;',
    ]

    # Identify input wires (not driven by any gate/sequential)
    driven_wires = set()
    for gate in circuit.gates:
        for w in gate._output_wires:
            driven_wires.add(w.name)
    for elem in circuit.sequential:
        for w in elem._output_wires:
            driven_wires.add(w.name)
    for clk in circuit.clocks:
        driven_wires.add(clk.output.name)

    input_wires = [name for name in circuit.wires if name not in driven_wires]
    output_wires = []

    # Find final output wires (not consumed by any gate/sequential)
    consumed_wires = set()
    for gate in circuit.gates:
        for w in gate._input_wires:
            consumed_wires.add(w.name)
    for elem in circuit.sequential:
        for w in elem._input_wires:
            consumed_wires.add(w.name)

    # Intermediate wires
    intermediate_wires = []

    for name, wire in circuit.wires.items():
        is_driven = name in driven_wires
        is_consumed = name in consumed_wires
        if is_driven and not is_consumed:
            output_wires.append(name)
        elif is_driven and is_consumed:
            intermediate_wires.append(name)

    # Input nodes
    for name in sorted(input_wires):
        lines.append(f'    "{name}" [shape=ellipse, fillcolor="#a8d8a8"];')
    lines.append('  }')
    lines.append('')

    # Output wires (right side)
    lines.append('  // Output wires (right side)')
    lines.append('  subgraph cluster_outputs {')
    lines.append('    label="Outputs";')
    lines.append('    style=dashed;')
    lines.append('    color=gray;')
    for name in sorted(output_wires):
        lines.append(f'    "{name}" [shape=ellipse, fillcolor="#a8c8e8"];')
    lines.append('  }')
    lines.append('')

    # Gate nodes
    gate_colors = {
        "and": "#ffe0b2", "or": "#ffe0b2", "not": "#ffccbc",
        "xor": "#ffe0b2", "nand": "#ffe0b2", "nor": "#ffe0b2",
        "xnor": "#ffe0b2", "buffer": "#c8e6c9", "tristate": "#e1bee7",
    }

    for gate in circuit.gates:
        gtype = type(gate).__name__
        label = gtype.replace("Gate", "")
        color = gate_colors.get(gtype.lower(), "#e8e8e8")
        lines.append(f'  "{gate.name}" [label="{label}", fillcolor="{color}"];')

    # Sequential element nodes
    for elem in circuit.sequential:
        etype = type(elem).__name__
        lines.append(f'  "{elem.name}" [label="{etype}", shape=box, fillcolor="#fff9c4"];')

    # Clock nodes
    for clk in circuit.clocks:
        lines.append(f'  "{clk.name}" [label="CLK\\n{clk.period_ns}ns", shape=triangle, fillcolor="#ffccbc"];')

    lines.append('')

    # Edges: inputs -> gates
    for gate in circuit.gates:
        for wire in gate._input_wires:
            lines.append(f'  "{wire.name}" -> "{gate.name}";')
        for wire in gate._output_wires:
            lines.append(f'  "{gate.name}" -> "{wire.name}";')

    for elem in circuit.sequential:
        for wire in elem._input_wires:
            lines.append(f'  "{wire.name}" -> "{elem.name}";')
        for wire in elem._output_wires:
            lines.append(f'  "{elem.name}" -> "{wire.name}";')

    for clk in circuit.clocks:
        lines.append(f'  "{clk.name}" -> "{clk.output.name}";')

    lines.append('}')
    return '\n'.join(lines)


def circuit_to_ascii(circuit: Circuit) -> str:
    """Generate a simple ASCII schematic representation of a circuit.

    This creates a text-based block diagram showing the circuit structure.

    Args:
        circuit: The circuit to represent.

    Returns:
        ASCII art string showing the circuit layout.
    """
    lines = []
    lines.append(f"╔══════════════════════════════════════════╗")
    lines.append(f"║  Circuit: {circuit.name:<33s}║")
    lines.append(f"╠══════════════════════════════════════════╣")
    lines.append(f"║  Wires: {len(circuit.wires):<5d}  Gates: {len(circuit.gates):<5d}          ║")
    lines.append(f"║  Sequential: {len(circuit.sequential):<3d}  Clocks: {len(circuit.clocks):<3d}           ║")
    lines.append(f"╠══════════════════════════════════════════╣")

    # Identify wire categories
    driven_wires = set()
    for gate in circuit.gates:
        for w in gate._output_wires:
            driven_wires.add(w.name)
    for elem in circuit.sequential:
        for w in elem._output_wires:
            driven_wires.add(w.name)
    for clk in circuit.clocks:
        driven_wires.add(clk.output.name)

    consumed_wires = set()
    for gate in circuit.gates:
        for w in gate._input_wires:
            consumed_wires.add(w.name)
    for elem in circuit.sequential:
        for w in elem._input_wires:
            consumed_wires.add(w.name)

    inputs = sorted([n for n in circuit.wires if n not in driven_wires])
    outputs = sorted([n for n in circuit.wires if n in driven_wires and n not in consumed_wires])

    lines.append(f"║                                          ║")
    lines.append(f"║  INPUTS:                                 ║")
    if inputs:
        for i in range(0, len(inputs), 4):
            chunk = inputs[i:i+4]
            line = ", ".join(f"{n:<10s}" for n in chunk)
            lines.append(f"║    {line:<38s}║")
    else:
        lines.append(f"║    (none)                                ║")

    lines.append(f"║                                          ║")
    lines.append(f"║  OUTPUTS:                                ║")
    if outputs:
        for i in range(0, len(outputs), 4):
            chunk = outputs[i:i+4]
            line = ", ".join(f"{n:<10s}" for n in chunk)
            lines.append(f"║    {line:<38s}║")
    else:
        lines.append(f"║    (none)                                ║")

    lines.append(f"║                                          ║")
    lines.append(f"╠══════════════════════════════════════════╣")
    lines.append(f"║  COMPONENTS:                             ║")

    for gate in circuit.gates:
        gtype = type(gate).__name__.replace("Gate", "").replace("Buffer", "BUF")
        inputs_str = ", ".join(w.name for w in gate._input_wires)
        outputs_str = ", ".join(w.name for w in gate._output_wires)
        lines.append(f"║  {gtype:>10s} {gate.name:<12s} ║")
        lines.append(f"║    IN:  {inputs_str:<34s}║")
        lines.append(f"║    OUT: {outputs_str:<34s}║")

    for elem in circuit.sequential:
        etype = type(elem).__name__
        inputs_str = ", ".join(w.name for w in elem._input_wires)
        outputs_str = ", ".join(w.name for w in elem._output_wires)
        lines.append(f"║  {etype:>10s} {elem.name:<12s} ║")
        lines.append(f"║    IN:  {inputs_str:<34s}║")
        lines.append(f"║    OUT: {outputs_str:<34s}║")

    for clk in circuit.clocks:
        lines.append(f"║  {'CLK':>10s} {clk.name:<12s} → {clk.output.name:<15s}║")
        lines.append(f"║    period={clk.period_ns}ns  duty={clk.duty_cycle:.0%}                ║")

    lines.append(f"╚══════════════════════════════════════════╝")
    return "\n".join(lines)