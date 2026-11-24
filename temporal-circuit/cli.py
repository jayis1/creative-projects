"""Runnable half-adder trace demonstration."""
import argparse
import csv
import json
import sys

from temporal_circuit import Circuit


def demo(until: int):
    circuit = Circuit()
    a = circuit.input("a")
    b = circuit.input("b")
    summed = circuit.xor_gate("sum", a, b, delay=1)
    carry = circuit.and_gate("carry", a, b, delay=2)
    circuit.set_input("a", 1, at=1)
    circuit.set_input("b", 1, at=3)
    circuit.set_input("a", 0, at=6)
    circuit.run(until=until)
    return circuit, summed, carry


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("csv", "json"), default="csv")
    parser.add_argument("--until", type=int, default=10)
    args = parser.parse_args(argv)
    if args.until < 0:
        parser.error("--until must be nonnegative")
    circuit, _, _ = demo(args.until)
    if args.format == "json":
        print(circuit.trace_json())
    else:
        writer = csv.writer(sys.stdout, lineterminator="\n")
        writer.writerow(("time", "wire", "old", "new", "cause"))
        writer.writerows((r.time, r.wire, r.old, r.new, r.cause) for r in circuit.trace)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
