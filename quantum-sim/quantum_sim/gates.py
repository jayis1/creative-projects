"""
Quantum gate definitions and gate algebra.

Each gate is a complex unitary matrix.  Gates compose via tensor
product (Kronecker product) and matrix multiplication.
"""

from __future__ import annotations

import cmath
import math
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Dict, Iterator, Tuple

import numpy as np

__all__ = ["Gate", "GATES", "controlled", "gate_from_matrix"]


# ---------------------------------------------------------------------------
# Internal helper: exact-ish pretty printing of complex components
# ---------------------------------------------------------------------------

def _fmt_complex(z: complex) -> str:
    """Pretty-print a complex number using fractions for sqrt components."""
    tol = 1e-10
    real, imag = z.real, z.imag
    parts: list[str] = []
    for val, suffix in ((real, ""), (imag, "j")):
        if abs(val) < tol:
            continue
        # try to match to sqrt(fraction) form for common values
        matched = False
        for denom in (1, 2, 3, 4, 6, 8):
            for numer in range(-12, 13):
                if numer == 0:
                    continue
                candidate = math.sqrt(abs(numer) / denom)
                if abs(abs(val) - candidate) < tol and math.copysign(1, numer) == math.copysign(1, val):
                    frac = Fraction(abs(numer), denom).limit_denominator(100)
                    if frac.numerator == 1 and frac.denominator > 1:
                        parts.append(f"sqrt(1/{frac.denominator}){suffix}")
                    elif frac.denominator == 1:
                        parts.append(f"sqrt({frac.numerator}){suffix}")
                    else:
                        parts.append(f"sqrt({frac.numerator}/{frac.denominator}){suffix}")
                    matched = True
                    break
            if matched:
                break
        if not matched:
            parts.append(f"{val:.4g}{suffix}")
    if not parts:
        return "0"
    return "+".join(parts).replace("+-", "-")


# ---------------------------------------------------------------------------
# Gate dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Gate:
    """An immutable quantum gate backed by a unitary matrix."""
    name: str
    matrix: np.ndarray = field(repr=False)

    def __post_init__(self) -> None:
        m = np.asarray(self.matrix, dtype=complex)
        if m.ndim != 2 or m.shape[0] != m.shape[1]:
            raise ValueError(f"Gate {self.name!r}: matrix must be square, got {m.shape}")
        object.__setattr__(self, "matrix", m)
        # verify unitarity (within tolerance)
        identity = np.eye(m.shape[0], dtype=complex)
        prod = m @ m.conj().T
        if not np.allclose(prod, identity, atol=1e-9):
            raise ValueError(f"Gate {self.name!r}: matrix is not unitary")

    @property
    def num_qubits(self) -> int:
        """Number of qubits this gate acts on."""
        n = self.matrix.shape[0]
        if n & (n - 1) != 0:
            raise ValueError(f"Gate {self.name!r}: dimension {n} is not a power of 2")
        return int(math.log2(n))

    def tensor(self, other: "Gate") -> "Gate":
        """Kronecker (tensor) product of two gates."""
        return Gate(
            f"{self.name}⊗{other.name}",
            np.kron(self.matrix, other.matrix),
        )

    def compose(self, other: "Gate") -> "Gate":
        """Matrix product self · other."""
        if self.matrix.shape != other.matrix.shape:
            raise ValueError(
                f"Cannot compose {self.name} ({self.matrix.shape}) with {other.name} ({other.matrix.shape})"
            )
        return Gate(f"{self.name}·{other.name}", self.matrix @ other.matrix)

    def __pow__(self, n: int) -> "Gate":
        """Repeated composition: self composed with itself n times."""
        if n < 0:
            raise ValueError("Negative powers not supported; use .dagger()")
        # Fix: use a proper identity matrix matching this gate's dimension,
        # not the 1-qubit identity GATES['I1'] which fails for multi-qubit gates.
        dim = self.matrix.shape[0]
        result = Gate(f"I{dim}", np.eye(dim, dtype=complex))
        for _ in range(n):
            result = result.compose(self)
        return result

    def dagger(self) -> "Gate":
        """Conjugate transpose (inverse for unitary)."""
        return Gate(f"{self.name}†", self.matrix.conj().T)

    def __str__(self) -> str:
        rows = []
        for row in self.matrix:
            cols = [_fmt_complex(v) for v in row]
            rows.append("  ".join(cols))
        return f"[{self.name}] (d=2^{self.num_qubits})\n" + "\n".join(
            "  [ " + r + " ]" for r in rows
        )

    def __iter__(self) -> Iterator[Tuple[int, int, complex]]:
        """Yield (row, col, value) triples for the matrix entries."""
        rows, cols = self.matrix.shape
        for r in range(rows):
            for c in range(cols):
                yield (r, c, self.matrix[r, c])


# ---------------------------------------------------------------------------
# Gate registry
# ---------------------------------------------------------------------------

def gate_from_matrix(name: str, m: np.ndarray) -> Gate:
    """Create a Gate from an arbitrary unitary matrix."""
    return Gate(name, m)


def _make_gate(name: str, m: np.ndarray) -> Gate:
    return Gate(name, m)


# Single-qubit gates
_G_H = (1.0 / math.sqrt(2.0)) * np.array([[1, 1], [1, -1]], dtype=complex)
_G_X = np.array([[0, 1], [1, 0]], dtype=complex)
_G_Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
_G_Z = np.array([[1, 0], [0, -1]], dtype=complex)
_G_S = np.array([[1, 0], [0, 1j]], dtype=complex)
_G_T = np.array([[1, 0], [0, cmath.exp(1j * math.pi / 4)]], dtype=complex)
_G_I = np.eye(2, dtype=complex)
_G_SX = 0.5 * np.array([[1 + 1j, 1 - 1j], [1 - 1j, 1 + 1j]], dtype=complex)

# Phase gates
_G_P_S2 = np.diag([1.0, cmath.exp(1j * math.pi / 2)])
_G_P_S3 = np.diag([1.0, cmath.exp(1j * 2 * math.pi / 3)])

# Two-qubit gates
_G_CNOT = np.array(
    [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]], dtype=complex
)
_G_CZ = np.diag([1, 1, 1, -1]).astype(complex)
_G_SWAP = np.array(
    [[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], dtype=complex
)
_G_iSWAP = np.array(
    [[1, 0, 0, 0], [0, 0, 1j, 0], [0, 1j, 0, 0], [0, 0, 0, 1]], dtype=complex
)
_G_XX = (1 / math.sqrt(2)) * np.array(
    [[1, 0, 0, 1j], [0, 1, 1j, 0], [0, 1j, 1, 0], [1j, 0, 0, 1]], dtype=complex
)
# Fix: removed dead code — the previous _G_XX computation (a non-unitary
# matrix product) was immediately overwritten by the correct definition above.
# sqrt(SWAP)
_theta = math.pi / 4.0
_G_SQRTSWAP = np.array(
    [
        [1, 0, 0, 0],
        [0, math.cos(_theta), 1j * math.sin(_theta), 0],
        [0, 1j * math.sin(_theta), math.cos(_theta), 0],
        [0, 0, 0, 1],
    ],
    dtype=complex,
)

# Three-qubit Toffoli gate (CCX)
_G_TOFFOLI = np.eye(8, dtype=complex)
_G_TOFFOLI[6, 6] = 0
_G_TOFFOLI[7, 7] = 0
_G_TOFFOLI[6, 7] = 1
_G_TOFFOLI[7, 6] = 1

# Fredkin gate (CSWAP)
_G_FREDKIN = np.eye(8, dtype=complex)
# swap qubits 1 and 2 when control (qubit 0) is 1
_G_FREDKIN[5, 5] = 0
_G_FREDKIN[5, 6] = 1
_G_FREDKIN[6, 5] = 1
_G_FREDKIN[6, 6] = 0

# Deutsch gate (a three-qubit gate)
# not commonly used, but included for completeness
# Using a simplified version


GATES: Dict[str, Gate] = {
    "I1": _make_gate("I", _G_I),
    "I": _make_gate("I", _G_I),
    "X": _make_gate("X", _G_X),
    "Y": _make_gate("Y", _G_Y),
    "Z": _make_gate("Z", _G_Z),
    "H": _make_gate("H", _G_H),
    "S": _make_gate("S", _G_S),
    "T": _make_gate("T", _G_T),
    "SX": _make_gate("SX", _G_SX),
    "CNOT": _make_gate("CNOT", _G_CNOT),
    "CX": _make_gate("CX", _G_CNOT),
    "CZ": _make_gate("CZ", _G_CZ),
    "SWAP": _make_gate("SWAP", _G_SWAP),
    "iSWAP": _make_gate("iSWAP", _G_iSWAP),
    "SQRTSWAP": _make_gate("SQRTSWAP", _G_SQRTSWAP),
    "XX": _make_gate("XX", _G_XX),
    "TOFFOLI": _make_gate("TOFFOLI", _G_TOFFOLI),
    "CCX": _make_gate("CCX", _G_TOFFOLI),
    "FREDKIN": _make_gate("FREDKIN", _G_FREDKIN),
    "CSWAP": _make_gate("CSWAP", _G_FREDKIN),
}


# ---------------------------------------------------------------------------
# Parameterized gate constructors
# ---------------------------------------------------------------------------

def rx(theta: float) -> Gate:
    """Rotation around X axis by angle *theta*."""
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    return Gate(f"RX({theta:.4g})", np.array([[c, -1j * s], [-1j * s, c]], dtype=complex))


def ry(theta: float) -> Gate:
    """Rotation around Y axis by angle *theta*."""
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    return Gate(f"RY({theta:.4g})", np.array([[c, -s], [s, c]], dtype=complex))


def rz(theta: float) -> Gate:
    """Rotation around Z axis by angle *theta*."""
    return Gate(f"RZ({theta:.4g})", np.array(
        [[cmath.exp(-1j * theta / 2), 0], [0, cmath.exp(1j * theta / 2)]], dtype=complex
    ))


def phase(theta: float) -> Gate:
    """Diagonal phase gate diag(1, e^{i*theta})."""
    return Gate(f"P({theta:.4g})", np.array([[1, 0], [0, cmath.exp(1j * theta)]], dtype=complex))


def u1(theta: float) -> Gate:
    """Alias for phase gate (Qiskit naming)."""
    return phase(theta)


def u2(phi: float, lam: float) -> Gate:
    """U2 gate (Qiskit convention)."""
    return Gate(
        f"U2({phi:.4g},{lam:.4g})",
        (1 / math.sqrt(2)) * np.array(
            [
                [1, -cmath.exp(1j * lam)],
                [cmath.exp(1j * phi), cmath.exp(1j * (phi + lam))],
            ],
            dtype=complex,
        ),
    )


def u3(theta: float, phi: float, lam: float) -> Gate:
    """U3 gate (Qiskit convention)."""
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    return Gate(
        f"U3({theta:.4g},{phi:.4g},{lam:.4g})",
        np.array(
            [
                [c, -s * cmath.exp(1j * lam)],
                [s * cmath.exp(1j * phi), c * cmath.exp(1j * (phi + lam))],
            ],
            dtype=complex,
        ),
    )


def controlled(gate: Gate) -> Gate:
    """
    Build a controlled-U from a single-qubit gate U.

    Returns a 2-qubit Gate whose matrix is:
        [[I, 0], [0, U]]
    """
    if gate.num_qubits != 1:
        raise ValueError(f"controlled() expects a 1-qubit gate, got {gate.num_qubits}")
    u = gate.matrix
    cu = np.eye(4, dtype=complex)
    cu[2:, 2:] = u
    return Gate(f"C-{gate.name}", cu)


# Register parameterized constructors for convenience
GATES["RX"] = rx  # type: ignore[assignment]
GATES["RY"] = ry  # type: ignore[assignment]
GATES["RZ"] = rz  # type: ignore[assignment]
GATES["PHASE"] = phase  # type: ignore[assignment]
GATES["U1"] = u1  # type: ignore[assignment]
GATES["U2"] = u2  # type: ignore[assignment]
GATES["U3"] = u3  # type: ignore[assignment]
GATES["CONTROLLED"] = controlled  # type: ignore[assignment]