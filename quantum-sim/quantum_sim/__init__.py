"""
quantum_sim — A from-scratch quantum circuit simulator.

Simulates quantum circuits with state-vector and density-matrix
representations, supporting single- and multi-qubit gates,
measurement, entanglement, and canonical algorithms
(Bell states, teleportation, Deutsch-Jozsa, Grover, QFT).

Pure Python with NumPy as the only dependency.
"""

from .gates import GATES, Gate
from .circuit import QuantumCircuit
from .simulator import Simulator
from .state import StateVector, DensityMatrix
from .qubit import Qubit, entangle
from .bloch import bloch_vector, bloch_sphere_ascii
from .algorithms import (
    bell_state,
    teleportation,
    deutsch_jozsa,
    grovers_search,
    quantum_fourier_transform,
    superdense_coding,
)
from .noise import (
    NoiseChannel,
    depolarizing,
    bit_flip,
    phase_flip,
    amplitude_damping,
    phase_damping,
    pauli_channel,
    apply_channel,
)
from .visualize import draw_circuit
from .advanced import (
    state_tomography,
    bb84_protocol,
    quantum_walk,
    QuantumWalkResult,
)

__version__ = "2.0.0"

__all__ = [
    "GATES",
    "Gate",
    "QuantumCircuit",
    "Simulator",
    "StateVector",
    "DensityMatrix",
    "Qubit",
    "entangle",
    "bloch_vector",
    "bloch_sphere_ascii",
    "bell_state",
    "teleportation",
    "deutsch_jozsa",
    "grovers_search",
    "quantum_fourier_transform",
    "superdense_coding",
    "NoiseChannel",
    "depolarizing",
    "bit_flip",
    "phase_flip",
    "amplitude_damping",
    "phase_damping",
    "pauli_channel",
    "apply_channel",
    "draw_circuit",
    "state_tomography",
    "bb84_protocol",
    "quantum_walk",
    "QuantumWalkResult",
    "__version__",
]