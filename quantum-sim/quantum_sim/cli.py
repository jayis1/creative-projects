"""
Command-line interface for quantum-sim.

Usage examples::

    quantum-sim bell
    quantum-sim grover --n 3 --marked 5 101
    quantum-sim qft --n 4
    quantum-sim deutsch-jozsa --oracle balanced
    quantum-sim teleport
    quantum-sim bloch --state "1/sqrt(2),0,0,1/sqrt(2)"
    quantum-sim circuit --qasm
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from typing import List, Optional

import numpy as np

from . import __version__
from .algorithms import (
    bell_state,
    deutsch_jozsa,
    grovers_search,
    quantum_fourier_transform,
    superdense_coding,
    teleportation,
)
from .bloch import bloch_sphere_ascii, bloch_vector
from .circuit import QuantumCircuit
from .qubit import Qubit
from .simulator import Simulator
from .state import StateVector


def _format_counts(counts: dict, n: int) -> str:
    lines = []
    for key, count in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
        prob = count / sum(counts.values()) if counts else 0
        bar = "█" * int(prob * 40)
        lines.append(f"  |{key}⟩: {count:6d}  {prob:7.2%}  {bar}")
    return "\n".join(lines)


def cmd_bell(args: argparse.Namespace) -> None:
    result = bell_state(args.type)
    print(f"Bell state |{['Φ+','Φ-','Ψ+','Ψ-'][args.type]}⟩:")
    print(result.state)
    if args.shots:
        sim = Simulator(seed=args.seed)
        from .algorithms import bell_state as bs
        # re-run with shots
        from .circuit import QuantumCircuit
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        if args.type == 1:
            qc.z(0)
        elif args.type == 2:
            qc.x(1)
        elif args.type == 3:
            qc.x(1)
            qc.z(0)
        r = sim.run(qc, shots=args.shots)
        print(f"\nMeasurement counts ({args.shots} shots):")
        print(_format_counts(r.counts, 2))


def cmd_grover(args: argparse.Namespace) -> None:
    marked = args.marked
    result = grovers_search(n=args.n, marked=marked, shots=args.shots)
    print(f"Grover's search: n={args.n} qubits, marked={marked}, shots={args.shots}")
    print(f"Optimal iterations: {max(1, int(math.floor(math.pi / 4 * math.sqrt(2 ** args.n))))}")
    print(f"\nMeasurement counts:")
    print(_format_counts(result.counts, args.n))
    # Show the marked states
    for m in marked:
        bits = format(m, f"0{args.n}b")
        print(f"  Marked state |{bits}⟩")


def cmd_qft(args: argparse.Namespace) -> None:
    result = quantum_fourier_transform(n=args.n)
    print(f"Quantum Fourier Transform on {args.n} qubits:")
    print(result.state)
    probs = result.probabilities
    print(f"\nProbabilities (top 8):")
    idx = np.argsort(probs)[::-1][:8]
    for i in idx:
        bits = format(i, f"0{args.n}b")
        print(f"  |{bits}⟩: {probs[i]:.6f}")


def cmd_deutsch_jozsa(args: argparse.Namespace) -> None:
    result = deutsch_jozsa(oracle_type=args.oracle, n=args.n)
    print(f"Deutsch-Jozsa algorithm: oracle={args.oracle}, n={args.n}")
    print(f"\nMeasurement counts ({result.shots} shots):")
    print(_format_counts(result.counts, args.n))
    # Check if all-zeros is dominant (constant) or not (balanced)
    all_zero = "0" * args.n
    p0 = result.counts.get(all_zero, 0) / max(result.shots, 1)
    verdict = "CONSTANT" if p0 > 0.5 else "BALANCED"
    print(f"\nVerdict: {verdict} (P(|{'0'*args.n}⟩) = {p0:.2%})")


def cmd_teleport(args: argparse.Namespace) -> None:
    rho, _, _ = teleportation(seed=args.seed)
    print("Quantum teleportation:")
    print(f"  Bob's reduced density matrix:\n{rho.matrix}")
    print(f"  Purity: {rho.purity():.6f}  (1.0 = pure state teleported successfully)")


def cmd_bloch(args: argparse.Namespace) -> None:
    # Parse state string: "a,b,c,d" or "1/sqrt(2),0,0,1/sqrt(2)"
    raw = args.state.replace(" ", "")
    parts = raw.split(",")
    # Evaluate each part safely (allow math expressions)
    safe_globals = {"sqrt": math.sqrt, "pi": math.pi, "j": 1j}
    amps = [complex(eval(p, {"__builtins__": {}}, safe_globals)) for p in parts]  # noqa: S307
    sv = StateVector(np.array(amps, dtype=complex)).normalize()
    vec = bloch_vector(sv)
    print(f"State: {sv}")
    print(f"Bloch vector: ({vec[0]:+.4f}, {vec[1]:+.4f}, {vec[2]:+.4f})")
    print(f"  r = {np.linalg.norm(vec):.4f}  (should be 1.0)")
    print()
    print(bloch_sphere_ascii(sv))


def cmd_superdense(args: argparse.Namespace) -> None:
    result = superdense_coding(args.message)
    print(f"Superdense coding: message = {args.message} (binary: {args.message:02b})")
    print(f"\nMeasurement counts ({result.shots} shots):")
    print(_format_counts(result.counts, 2))


def cmd_qasm(args: argparse.Namespace) -> None:
    qc = QuantumCircuit(3)
    qc.h(0)
    qc.cx(0, 1)
    qc.h(2)
    qc.toffoli(0, 1, 2)
    print(qc.to_qasm())


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="quantum-sim",
        description="A from-scratch quantum circuit simulator.",
    )
    parser.add_argument("--version", action="version", version=f"quantum-sim {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_bell = sub.add_parser("bell", help="Prepare a Bell state")
    p_bell.add_argument("--type", type=int, default=0, choices=[0, 1, 2, 3])
    p_bell.add_argument("--shots", type=int, default=1024)
    p_bell.add_argument("--seed", type=int, default=42)
    p_bell.set_defaults(func=cmd_bell)

    p_grover = sub.add_parser("grover", help="Run Grover's search")
    p_grover.add_argument("--n", type=int, default=3, help="Number of qubits")
    p_grover.add_argument("--marked", type=int, nargs="+", default=[5], help="Marked state indices")
    p_grover.add_argument("--shots", type=int, default=1024)
    p_grover.set_defaults(func=cmd_grover)

    p_qft = sub.add_parser("qft", help="Run the Quantum Fourier Transform")
    p_qft.add_argument("--n", type=int, default=3)
    p_qft.set_defaults(func=cmd_qft)

    p_dj = sub.add_parser("deutsch-jozsa", help="Run the Deutsch-Jozsa algorithm")
    p_dj.add_argument("--oracle", choices=["constant", "balanced"], default="balanced")
    p_dj.add_argument("--n", type=int, default=3)
    p_dj.set_defaults(func=cmd_deutsch_jozsa)

    p_teleport = sub.add_parser("teleport", help="Run quantum teleportation")
    p_teleport.add_argument("--seed", type=int, default=0)
    p_teleport.set_defaults(func=cmd_teleport)

    p_bloch = sub.add_parser("bloch", help="Show a single-qubit state on the Bloch sphere")
    p_bloch.add_argument("--state", type=str, default="1/sqrt(2),1/sqrt(2)",
                         help="Amplitudes as comma-separated expressions")
    p_bloch.set_defaults(func=cmd_bloch)

    p_sd = sub.add_parser("superdense", help="Run superdense coding")
    p_sd.add_argument("--message", type=int, default=2, choices=[0, 1, 2, 3])
    p_sd.set_defaults(func=cmd_superdense)

    p_qasm = sub.add_parser("qasm", help="Print an example circuit in QASM")
    p_qasm.set_defaults(func=cmd_qasm)

    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())