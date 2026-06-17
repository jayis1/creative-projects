"""
Quantum noise channels for density-matrix simulation.

Each channel is a completely positive trace-preserving (CPTP) map
represented as a set of Kraus operators {K_i} such that
    ρ → Σ_i K_i ρ K_i†
with Σ_i K_i†K_i = I.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

__all__ = [
    "NoiseChannel",
    "depolarizing",
    "bit_flip",
    "phase_flip",
    "amplitude_damping",
    "phase_damping",
    "pauli_channel",
    "apply_channel",
]


@dataclass(frozen=True)
class NoiseChannel:
    """A CPTP map defined by Kraus operators."""
    name: str
    kraus: Tuple[np.ndarray, ...]
    n_qubits: int

    def __post_init__(self) -> None:
        # Verify completeness: Σ K†K = I
        dim = 2 ** self.n_qubits
        acc = np.zeros((dim, dim), dtype=complex)
        for k in self.kraus:
            acc += k.conj().T @ k
        if not np.allclose(acc, np.eye(dim), atol=1e-9):
            raise ValueError(f"Channel {self.name!r}: Kraus operators are not CPTP")
        object.__setattr__(self, "kraus", tuple(np.asarray(k, dtype=complex) for k in self.kraus))


def depolarizing(p: float, n_qubits: int = 1) -> NoiseChannel:
    """
    Depolarizing channel:
        ρ → (1−p) ρ + (p / 2^n) I

    Kraus operators (single qubit):
        K_0 = √(1−p) I
        K_1 = √(p/3) X
        K_2 = √(p/3) Y
        K_3 = √(p/3) Z
    """
    if not (0 <= p <= 1):
        raise ValueError("Depolarizing probability must be in [0, 1]")
    dim = 2 ** n_qubits
    I = np.eye(dim, dtype=complex)
    if n_qubits == 1:
        X = np.array([[0, 1], [1, 0]], dtype=complex)
        Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
        Z = np.array([[1, 0], [0, -1]], dtype=complex)
        kraus = (
            np.sqrt(1 - p) * I,
            np.sqrt(p / 3) * X,
            np.sqrt(p / 3) * Y,
            np.sqrt(p / 3) * Z,
        )
    else:
        # General n-qubit depolarizing: ρ → (1-p)ρ + p I/2^n
        kraus = (np.sqrt(1 - p) * I, np.sqrt(p) * I / np.sqrt(dim))
    return NoiseChannel("depolarizing", kraus, n_qubits)


def bit_flip(p: float) -> NoiseChannel:
    """
    Bit-flip channel:
        ρ → (1−p) ρ + p X ρ X
    """
    if not (0 <= p <= 1):
        raise ValueError("Bit-flip probability must be in [0, 1]")
    I = np.eye(2, dtype=complex)
    X = np.array([[0, 1], [1, 0]], dtype=complex)
    return NoiseChannel("bit_flip", (np.sqrt(1 - p) * I, np.sqrt(p) * X), 1)


def phase_flip(p: float) -> NoiseChannel:
    """
    Phase-flip channel:
        ρ → (1−p) ρ + p Z ρ Z
    """
    if not (0 <= p <= 1):
        raise ValueError("Phase-flip probability must be in [0, 1]")
    I = np.eye(2, dtype=complex)
    Z = np.array([[1, 0], [0, -1]], dtype=complex)
    return NoiseChannel("phase_flip", (np.sqrt(1 - p) * I, np.sqrt(p) * Z), 1)


def amplitude_damping(gamma: float) -> NoiseChannel:
    """
    Amplitude damping channel:
        K_0 = [[1, 0], [0, √(1−γ)]]
        K_1 = [[0, √γ], [0, 0]]
    """
    if not (0 <= gamma <= 1):
        raise ValueError("Amplitude damping gamma must be in [0, 1]")
    K0 = np.array([[1, 0], [0, math.sqrt(1 - gamma)]], dtype=complex)
    K1 = np.array([[0, math.sqrt(gamma)], [0, 0]], dtype=complex)
    return NoiseChannel("amplitude_damping", (K0, K1), 1)


def phase_damping(gamma: float) -> NoiseChannel:
    """
    Phase damping channel:
        K_0 = [[1, 0], [0, √(1−γ)]]
        K_1 = [[0, 0], [0, √γ]]
    """
    if not (0 <= gamma <= 1):
        raise ValueError("Phase damping gamma must be in [0, 1]")
    K0 = np.array([[1, 0], [0, math.sqrt(1 - gamma)]], dtype=complex)
    K1 = np.array([[0, 0], [0, math.sqrt(gamma)]], dtype=complex)
    return NoiseChannel("phase_damping", (K0, K1), 1)


def pauli_channel(px: float, py: float, pz: float) -> NoiseChannel:
    """
    General Pauli channel:
        ρ → (1−px−py−pz) ρ + px X ρ X + py Y ρ Y + pz Z ρ Z
    """
    total = px + py + pz
    if not (0 <= total <= 1):
        raise ValueError("px + py + pz must be in [0, 1]")
    I = np.eye(2, dtype=complex)
    X = np.array([[0, 1], [1, 0]], dtype=complex)
    Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    Z = np.array([[1, 0], [0, -1]], dtype=complex)
    kraus = [math.sqrt(1 - total) * I, math.sqrt(px) * X, math.sqrt(py) * Y, math.sqrt(pz) * Z]
    return NoiseChannel("pauli_channel", tuple(kraus), 1)


def apply_channel(rho: np.ndarray, channel: NoiseChannel, targets: Tuple[int, ...]) -> np.ndarray:
    """
    Apply a noise channel to specific qubits of a density matrix.

    Parameters
    ----------
    rho : 2^n × 2^n density matrix
    channel : NoiseChannel acting on n_channel qubits
    targets : which global qubits the channel acts on
    """
    from .simulator import _embed_pure_gate

    n_qubits = int(round(math.log2(rho.shape[0])))
    n_channel = channel.n_qubits
    if len(targets) != n_channel:
        raise ValueError(f"Channel acts on {n_channel} qubits but {len(targets)} targets given")

    result = np.zeros_like(rho)
    for k_op in channel.kraus:
        # Embed Kraus operator into full space
        K_full = _embed_pure_gate(k_op, targets, n_qubits)
        result += K_full @ rho @ K_full.conj().T
    return result