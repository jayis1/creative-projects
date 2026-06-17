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

__version__ = "1.0.0"

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
    "__version__",
]