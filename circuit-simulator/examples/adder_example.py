"""Example: 4-bit ripple-carry adder simulation.

This example demonstrates building and simulating a 4-bit adder
using the circuit simulator's Python API.
"""

from circuit_sim.core import Signal
from circuit_sim.circuit import Circuit
from circuit_sim.simulator import Simulator
from circuit_sim.scope import Oscilloscope

def main():
    print("4-Bit Ripple-Carry Adder Example")
    print("=" * 40)

    # Build the circuit
    circ = Circuit("adder_4bit")
    a = circ.add_bus("a", 4)
    b = circ.add_bus("b", 4)
    s = circ.add_bus("s", 4)
    cout = circ.build_ripple_carry_adder("rca", a, b, s)

    # Create simulator
    sim = Simulator(circ)
    sim.trace("a[0]", "a[1]", "b[0]", "b[1]", "s[0]", "s[1]")

    # Test addition
    test_cases = [
        (0, 0, "0 + 0"),
        (3, 5, "3 + 5"),
        (7, 7, "7 + 7"),
        (15, 1, "15 + 1"),
    ]

    for a_val, b_val, label in test_cases:
        sim.reset()
        a.write_int(a_val)
        b.write_int(b_val)
        sim.run(30)
        s_val = s.read_int()
        carry = cout.signal == Signal.HIGH
        total = s_val + (16 if carry else 0)
        expected = a_val + b_val
        print(f"  {label} = {total} (carry={'1' if carry else '0'}, s={s_val:04b}) "
              f"{'✓' if total == expected else '✗'}")

    # Show waveform
    print("\nWaveform for last addition:")
    scope = Oscilloscope()
    for name in ["a[0]", "a[1]", "b[0]", "b[1]", "s[0]", "s[1]"]:
        scope.add_trace(name, sim.get_trace(name))
    print(scope.render_ascii(width=70))


if __name__ == "__main__":
    main()