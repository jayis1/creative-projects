"""Command-line interface for the circuit simulator.

Usage:
    circuit-sim run <cdl_file> [--duration N] [--trace WIRE1,WIRE2,...] [--vcd FILE] [--json FILE]
    circuit-sim truth-table <cdl_file> --inputs WIRE1,WIRE2 --outputs WIRE1,WIRE2
    circuit-sim stats <cdl_file>
    circuit-sim info <cdl_file>
    circuit-sim export-dot <cdl_file> [--output FILE]
    circuit-sim export-json <cdl_file> [--output FILE]
    circuit-sim demo
    circuit-sim --help
"""

from __future__ import annotations
import argparse
import logging
import sys
from pathlib import Path

from .core import Signal
from .cdl import parse_cdl
from .simulator import Simulator, Stimulus
from .scope import Oscilloscope
from .analyze import TruthTable, CircuitStats
from .export import circuit_to_dot, circuit_to_json, circuit_to_ascii, circuit_from_json
from .waveform import analyze_trace, format_trace_analysis
from .config import SimConfig

logger = logging.getLogger(__name__)


def _load_cdl(filepath: str):
    """Load a circuit from a CDL file."""
    source = Path(filepath).read_text()
    return parse_cdl(source)


def cmd_run(args):
    """Run a simulation from a CDL file."""
    circuit = _load_cdl(args.cdl_file)
    sim = Simulator(circuit, step_ns=args.step)

    # Trace wires
    if args.trace:
        for wire_name in args.trace.split(","):
            wire_name = wire_name.strip()
            sim.trace(wire_name)
    elif args.trace_all:
        sim.trace_all()

    # Build stimulus from CDL stimuli if present
    duration = args.duration

    # Run simulation
    if hasattr(circuit, '_stimuli') and circuit._stimuli:
        stim = Stimulus()
        for time_ns, wire_name, value in circuit._stimuli:
            stim.set_wire(time_ns, wire_name, value)
        for time_ns, bus_name, value in getattr(circuit, '_bus_stimuli', []):
            stim.set_bus(time_ns, bus_name, value)
        sim.run_with_stimulus(stim, duration)
    else:
        sim.run(duration)

    # Print results
    print(f"Simulation completed: {sim.time_ns}ns")
    print()

    # Show probed values
    if args.trace or args.trace_all:
        traced = args.trace.split(",") if args.trace else []
        if args.trace_all:
            traced = sorted(circuit.wires.keys())
        for name in traced:
            if name in circuit.wires:
                signal = circuit.wires[name].signal
                print(f"  {name:>20s} = {signal.name}")

    # Show oscilloscope
    if args.waveform:
        scope = Oscilloscope()
        for name in sim._traced_wires:
            scope.add_trace(name, sim.get_trace(name))
        print()
        print(scope.render_ascii(width=args.waveform_width))

    # VCD export
    if args.vcd:
        scope = Oscilloscope()
        for name in sim._traced_wires:
            scope.add_trace(name, sim.get_trace(name))
        scope.export_vcd(args.vcd)
        print(f"VCD exported to {args.vcd}")

    # JSON export
    if args.json:
        circuit_to_json(circuit, args.json)
        print(f"Circuit exported to {args.json}")

    # Trace analysis
    if args.analyze:
        for name in sim._traced_wires:
            trace = sim.get_trace(name)
            analysis = analyze_trace(trace, name)
            print()
            print(format_trace_analysis(analysis))


def cmd_truth_table(args):
    """Generate a truth table for a combinational circuit."""
    circuit = _load_cdl(args.cdl_file)
    input_names = [n.strip() for n in args.inputs.split(",")]
    output_names = [n.strip() for n in args.outputs.split(",")]

    tt = TruthTable(circuit, input_names, output_names)
    rows = tt.generate()

    if args.format == "ascii":
        print(tt.to_ascii())
    elif args.format == "csv":
        print(tt.to_csv())
    else:
        # Default: ASCII
        print(tt.to_ascii())


def cmd_stats(args):
    """Print circuit statistics."""
    circuit = _load_cdl(args.cdl_file)
    stats = CircuitStats(circuit)
    print(stats.summary())

    # Additional stats
    print(f"  Buses: {len(circuit.buses)}")
    print(f"  Clocks: {len(circuit.clocks)}")


def cmd_info(args):
    """Print detailed circuit info with ASCII schematic."""
    circuit = _load_cdl(args.cdl_file)
    print(circuit_to_ascii(circuit))

    if args.verbose:
        print()
        print("Wire details:")
        for name, wire in sorted(circuit.wires.items()):
            print(f"  {name:>20s}: {wire.signal.name}")

        print()
        print("Gate details:")
        for gate in circuit.gates:
            inputs = ", ".join(w.name for w in gate._input_wires)
            outputs = ", ".join(w.name for w in gate._output_wires)
            print(f"  {type(gate).__name__:>15s} {gate.name}: {inputs} → {outputs}")

        print()
        print("Sequential elements:")
        for elem in circuit.sequential:
            inputs = ", ".join(w.name for w in elem._input_wires)
            outputs = ", ".join(w.name for w in elem._output_wires)
            print(f"  {type(elem).__name__:>15s} {elem.name}: {inputs} → {outputs}")


def cmd_export_dot(args):
    """Export circuit as Graphviz DOT format."""
    circuit = _load_cdl(args.cdl_file)
    dot = circuit_to_dot(circuit)

    if args.output:
        Path(args.output).write_text(dot)
        print(f"DOT exported to {args.output}")
    else:
        print(dot)


def cmd_export_json(args):
    """Export circuit as JSON."""
    circuit = _load_cdl(args.cdl_file)

    if args.output:
        circuit_to_json(circuit, args.output)
        print(f"Circuit exported to {args.output}")
    else:
        print(circuit_to_json(circuit))


def cmd_demo(args):
    """Run the interactive demo."""
    from . import __version__

    print(f"Circuit Simulator v{__version__} — Interactive Demo")
    print("=" * 50)
    print()

    # Demo 1: Basic AND gate
    print("Demo 1: Basic AND Gate")
    print("-" * 30)
    from .circuit import Circuit
    circ = Circuit("demo_and")
    a = circ.add_wire("a", Signal.LOW)
    b = circ.add_wire("b", Signal.LOW)
    out = circ.add_wire("out")
    circ.add_and("and1", a, b, out)

    sim = Simulator(circ)
    sim.trace("a", "b", "out")

    for a_val in [Signal.LOW, Signal.HIGH]:
        for b_val in [Signal.LOW, Signal.HIGH]:
            sim.reset()
            a.signal = a_val
            b.signal = b_val
            sim.run(10)
            print(f"  a={a_val.name:>9s}  b={b_val.name:>9s}  →  out={out.signal.name}")

    print()

    # Demo 2: Oscilloscope
    print("Demo 2: Oscilloscope Waveforms")
    print("-" * 30)
    circ2 = Circuit("demo_osc")
    clk = circ2.add_wire("clk", Signal.LOW)
    d = circ2.add_wire("d", Signal.HIGH)
    q = circ2.add_wire("q", Signal.LOW)
    qbar = circ2.add_wire("qbar", Signal.HIGH)
    circ2.add_d_flipflop("dff", d, clk, q, qbar)
    circ2.add_clock("sysclk", clk, period_ns=10)

    sim2 = Simulator(circ2)
    sim2.trace("clk", "d", "q")
    sim2.run(80)

    scope = Oscilloscope()
    scope.add_trace("clk", sim2.get_trace("clk"))
    scope.add_trace("d", sim2.get_trace("d"))
    scope.add_trace("q", sim2.get_trace("q"))
    print(scope.render_ascii(width=70))

    # Demo 3: Truth table
    print()
    print("Demo 3: Truth Table for XOR Gate")
    print("-" * 30)
    circ3 = Circuit("xor_tt")
    x = circ3.add_wire("x", Signal.LOW)
    y = circ3.add_wire("y", Signal.LOW)
    z = circ3.add_wire("z")
    circ3.add_xor("xor1", x, y, z)

    tt = TruthTable(circ3, ["x", "y"], ["z"])
    tt.generate()
    print(tt.to_ascii())

    print()
    print("✓ Demo completed!")


def main():
    """Entry point for the circuit-sim CLI."""
    parser = argparse.ArgumentParser(
        prog="circuit-sim",
        description="Digital circuit simulator with CDL, oscilloscope, and analysis tools.",
        epilog="Use 'circuit-sim <command> --help' for more information on a command.",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 2.0.0")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # run command
    run_parser = subparsers.add_parser("run", help="Run a simulation from a CDL file")
    run_parser.add_argument("cdl_file", help="Path to CDL file")
    run_parser.add_argument("--duration", "-d", type=int, default=100, help="Simulation duration in ns (default: 100)")
    run_parser.add_argument("--step", "-s", type=int, default=1, help="Simulation time step in ns (default: 1)")
    run_parser.add_argument("--trace", "-t", help="Comma-separated list of wires to trace")
    run_parser.add_argument("--trace-all", "-T", action="store_true", help="Trace all wires")
    run_parser.add_argument("--waveform", "-w", action="store_true", help="Show ASCII waveform after simulation")
    run_parser.add_argument("--waveform-width", type=int, default=70, help="Width of ASCII waveform (default: 70)")
    run_parser.add_argument("--vcd", help="Export VCD waveform file")
    run_parser.add_argument("--json", help="Export circuit as JSON")
    run_parser.add_argument("--analyze", "-a", action="store_true", help="Analyze traced waveforms")
    run_parser.set_defaults(func=cmd_run)

    # truth-table command
    tt_parser = subparsers.add_parser("truth-table", help="Generate truth table for a combinational circuit")
    tt_parser.add_argument("cdl_file", help="Path to CDL file")
    tt_parser.add_argument("--inputs", "-i", required=True, help="Comma-separated input wire names")
    tt_parser.add_argument("--outputs", "-o", required=True, help="Comma-separated output wire names")
    tt_parser.add_argument("--format", "-f", choices=["ascii", "csv"], default="ascii", help="Output format")
    tt_parser.set_defaults(func=cmd_truth_table)

    # stats command
    stats_parser = subparsers.add_parser("stats", help="Print circuit statistics")
    stats_parser.add_argument("cdl_file", help="Path to CDL file")
    stats_parser.set_defaults(func=cmd_stats)

    # info command
    info_parser = subparsers.add_parser("info", help="Print circuit info and ASCII schematic")
    info_parser.add_argument("cdl_file", help="Path to CDL file")
    info_parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed wire/gate info")
    info_parser.set_defaults(func=cmd_info)

    # export-dot command
    dot_parser = subparsers.add_parser("export-dot", help="Export circuit as Graphviz DOT")
    dot_parser.add_argument("cdl_file", help="Path to CDL file")
    dot_parser.add_argument("--output", "-o", help="Output DOT file path")
    dot_parser.set_defaults(func=cmd_export_dot)

    # export-json command
    json_parser = subparsers.add_parser("export-json", help="Export circuit as JSON")
    json_parser.add_argument("cdl_file", help="Path to CDL file")
    json_parser.add_argument("--output", "-o", help="Output JSON file path")
    json_parser.set_defaults(func=cmd_export_json)

    # demo command
    demo_parser = subparsers.add_parser("demo", help="Run interactive demo")
    demo_parser.set_defaults(func=cmd_demo)

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()