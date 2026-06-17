"""Example: Truth table generation and analysis.

This example shows how to generate truth tables for combinational
circuits and analyze the results.
"""

from circuit_sim.core import Signal
from circuit_sim.circuit import Circuit
from circuit_sim.analyze import TruthTable, CircuitStats

def main():
    print("Truth Table Generation Example")
    print("=" * 40)

    # Build an XOR gate
    circ = Circuit("xor_gate")
    a = circ.add_wire("a", Signal.LOW)
    b = circ.add_wire("b", Signal.LOW)
    out = circ.add_wire("out")
    circ.add_xor("xor1", a, b, out)

    # Generate truth table
    tt = TruthTable(circ, ["a", "b"], ["out"])
    rows = tt.generate()

    print("\nXOR Gate Truth Table:")
    print(tt.to_ascii())

    print("\nCSV Format:")
    print(tt.to_csv())

    # Circuit statistics
    stats = CircuitStats(circ)
    print(f"\nCircuit Statistics:")
    print(stats.summary())

    # Half adder
    print("\n" + "=" * 40)
    print("Half Adder Truth Table")
    print("=" * 40)

    circ2 = Circuit("half_adder")
    a2 = circ2.add_wire("a", Signal.LOW)
    b2 = circ2.add_wire("b", Signal.LOW)
    s2 = circ2.add_wire("sum")
    c2 = circ2.add_wire("carry")
    circ2.build_half_adder("ha", a2, b2, s2, c2)

    tt2 = TruthTable(circ2, ["a", "b"], ["sum", "carry"])
    tt2.generate()
    print(tt2.to_ascii())

    stats2 = CircuitStats(circ2)
    print(f"\nCircuit Statistics:")
    print(stats2.summary())


if __name__ == "__main__":
    main()