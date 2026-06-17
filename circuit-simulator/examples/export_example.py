"""Example: Export and visualization features.

This example demonstrates JSON export, DOT graph export,
ASCII schematic, and waveform analysis.
"""

from circuit_sim.core import Signal
from circuit_sim.circuit import Circuit
from circuit_sim.simulator import Simulator
from circuit_sim.export import circuit_to_json, circuit_to_dot, circuit_to_ascii
from circuit_sim.waveform import analyze_trace, format_trace_analysis

def main():
    print("Export & Analysis Example")
    print("=" * 40)

    # Build a simple circuit
    circ = Circuit("demo_and")
    a = circ.add_wire("a", Signal.LOW)
    b = circ.add_wire("b", Signal.LOW)
    out = circ.add_wire("out")
    circ.add_and("and1", a, b, out)

    # ASCII schematic
    print("\nASCII Schematic:")
    print(circuit_to_ascii(circ))

    # JSON export
    print("\nJSON Export (first 500 chars):")
    json_str = circuit_to_json(circ)
    print(json_str[:500] + "...")

    # DOT export
    print("\nDOT Graph (first 500 chars):")
    dot_str = circuit_to_dot(circ)
    print(dot_str[:500] + "...")

    # Run simulation and analyze trace
    sim = Simulator(circ)
    sim.trace("a", "b", "out")

    a.signal = Signal.HIGH
    b.signal = Signal.HIGH
    sim.run(20)

    print("\nWaveform Analysis for 'out':")
    trace = sim.get_trace("out")
    analysis = analyze_trace(trace, "out")
    print(format_trace_analysis(analysis))


if __name__ == "__main__":
    main()