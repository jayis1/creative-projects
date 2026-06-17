#!/usr/bin/env python3
"""
Interactive demo of the circuit simulator.
Shows a 4-bit ripple-carry adder, a clock-driven D flip-flop, and CDL usage.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from circuit_sim.core import Signal
from circuit_sim.circuit import Circuit
from circuit_sim.simulator import Simulator
from circuit_sim.scope import Oscilloscope
from circuit_sim.cdl import parse_cdl


def demo_ripple_carry_adder():
    """Demonstrate a 4-bit ripple-carry adder."""
    print("=" * 60)
    print("DEMO 1: 4-bit Ripple-Carry Adder")
    print("=" * 60)

    circ = Circuit("rca_demo")
    a = circ.add_bus("a", 4)
    b = circ.add_bus("b", 4)
    s = circ.add_bus("s", 4)
    cout = circ.build_ripple_carry_adder("rca", a, b, s)

    sim = Simulator(circ)
    sim.trace("a[0]", "a[1]", "a[2]", "a[3]",
              "b[0]", "b[1]", "b[2]", "b[3]",
              "s[0]", "s[1]", "s[2]", "s[3]")

    print(f"\nCircuit: {circ}")
    print(f"\n  a[3:0]  b[3:0]  =  s[3:0]")
    print("  " + "-" * 35)

    test_cases = [
        (0, 0), (1, 1), (3, 5), (7, 7), (15, 1), (8, 8), (10, 6),
    ]

    for a_val, b_val in test_cases:
        a.write_int(a_val)
        b.write_int(b_val)
        sim.run(30)
        s_val = s.read_int()
        cout_val = cout.signal
        total = s_val + (16 if cout_val == Signal.HIGH else 0)
        print(f"  {a_val:2d} ({a_val:04b}) + {b_val:2d} ({b_val:04b}) = {total:2d} (cout={cout_val.name}, s={s_val:04b})")

    print()


def demo_flipflop_counter():
    """Demonstrate D flip-flops with clock — a 2-bit counter."""
    print("=" * 60)
    print("DEMO 2: 2-bit Counter with D Flip-Flops")
    print("=" * 60)

    circ = Circuit("counter")
    clk = circ.add_wire("clk", Signal.LOW)
    
    # D flip-flop 0: toggles on every clock
    d0 = circ.add_wire("d0", Signal.LOW)
    q0 = circ.add_wire("q0", Signal.LOW)
    q0bar = circ.add_wire("q0bar", Signal.HIGH)
    
    # Connect D0 to Q0bar (toggles every clock)
    circ.add_d_flipflop("dff0", d0, clk, q0, q0bar)
    circ.add_not("inv0", q0, d0)
    
    # D flip-flop 1: toggles when Q0 is HIGH
    d1 = circ.add_wire("d1", Signal.LOW)
    q1 = circ.add_wire("q1", Signal.LOW)
    q1bar = circ.add_wire("q1bar", Signal.HIGH)
    circ.add_d_flipflop("dff1", d1, clk, q1, q1bar)
    circ.add_xor("xor1", q0, q1, d1)
    
    circ.add_clock("sysclk", clk, period_ns=20)

    sim = Simulator(circ)
    sim.trace("clk", "q0", "q1")

    print("\n  Running simulation for 200ns...")
    sim.run(200)

    scope = Oscilloscope()
    scope.add_trace("clk", sim.get_trace("clk"))
    scope.add_trace("q0", sim.get_trace("q0"))
    scope.add_trace("q1", sim.get_trace("q1"))

    print("\n  Waveform:")
    print(scope.render_ascii(width=80))
    print()


def demo_cdl():
    """Demonstrate CDL (Circuit Description Language) usage."""
    print("=" * 60)
    print("DEMO 3: Circuit Description Language (CDL)")
    print("=" * 60)

    source = """
    circuit cdl_mux;
    wire a initial=LOW;
    wire b initial=HIGH;
    wire sel initial=LOW;
    wire out;
    mux2 mux1 a b sel -> out;
    """

    print("\n  CDL Source:")
    for line in source.strip().split('\n'):
        print(f"    {line}")

    circ = parse_cdl(source)
    sim = Simulator(circ)

    print(f"\n  Parsed circuit: {circ}")
    print(f"  Wires: {list(circ.wires.keys())}")
    print(f"  Gates: {len(circ.gates)}")

    # Test the MUX
    a = circ.wire("a")
    b = circ.wire("b")
    sel = circ.wire("sel")
    out = circ.wire("out")

    sim.run(5)
    print(f"\n  sel=LOW → out follows a: out={out.signal.name}")

    sel.signal = Signal.HIGH
    sim.run(5)
    print(f"  sel=HIGH → out follows b: out={out.signal.name}")
    print()


def demo_gates_truth_table():
    """Print truth tables for all gate types."""
    print("=" * 60)
    print("DEMO 4: Gate Truth Tables")
    print("=" * 60)

    from circuit_sim.core import Signal, Wire
    from circuit_sim.gates import (
        AndGate, OrGate, NotGate, XorGate, NandGate, NorGate, XnorGate,
    )

    print("\n  2-Input Gates:")
    print(f"  {'A':>5} {'B':>5} │ {'AND':>5} {'OR':>5} {'XOR':>5} {'NAND':>5} {'NOR':>5} {'XNOR':>5}")
    print("  " + "─" * 65)

    for a_val in [Signal.LOW, Signal.HIGH]:
        for b_val in [Signal.LOW, Signal.HIGH]:
            results = []
            for GateClass in [AndGate, OrGate, XorGate, NandGate, NorGate, XnorGate]:
                a_w = Wire("a", a_val)
                b_w = Wire("b", b_val)
                out = Wire("out")
                gate = GateClass("test", a_w, b_w, out)
                gate.evaluate()
                ready = gate.tick(1)
                for w, s in ready:
                    w.signal = s
                results.append(out.signal.name)
            print(f"  {a_val.name:>5} {b_val.name:>5} │ {' '.join(f'{r:>5}' for r in results)}")

    print(f"\n  NOT gate:")
    for a_val in [Signal.LOW, Signal.HIGH]:
        a = Wire("a", a_val)
        out = Wire("out")
        gate = NotGate("test", a, out)
        gate.evaluate()
        ready = gate.tick(1)
        for w, s in ready:
            w.signal = s
        print(f"  {a_val.name:>5} → {out.signal.name:>5}")
    print()


if __name__ == "__main__":
    demo_gates_truth_table()
    demo_ripple_carry_adder()
    demo_flipflop_counter()
    demo_cdl()
    print("✓ All demos completed successfully!")