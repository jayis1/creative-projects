"""
Qubit: high-level single-qubit helper class.

Provides convenient construction and manipulation of single-qubit
states, as well as an *entangle* helper for creating multi-qubit
states from individual qubits.
"""

from __future__ import annotations

import math
from typing import List

import numpy as np

from .state import StateVector

__all__ = ["Qubit", "entangle", "ZERO", "ONE", "PLUS", "MINUS"]


ZERO = StateVector(np.array([1.0, 0.0], dtype=complex))
ONE = StateVector(np.array([0.0, 1.0], dtype=complex))
PLUS = StateVector(np.array([1.0 / math.sqrt(2), 1.0 / math.sqrt(2)], dtype=complex))
MINUS = StateVector(np.array([1.0 / math.sqrt(2), -1.0 / math.sqrt(2)], dtype=complex))


class Qubit:
    """A convenience wrapper around a single-qubit StateVector."""

    def __init__(self, alpha: complex = 1.0, beta: complex = 0.0) -> None:
        """|q⟩ = α|0⟩ + β|1⟩."""
        self.state = StateVector(np.array([alpha, beta], dtype=complex))
        if not np.isclose(self.state.norm(), 1.0, atol=1e-9):
            self.state = self.state.normalize()

    @classmethod
    def from_state(cls, sv: StateVector) -> "Qubit":
        if sv.num_qubits != 1:
            raise ValueError("Qubit wraps a single-qubit state only")
        q = cls()
        q.state = sv
        return q

    @classmethod
    def zero(cls) -> "Qubit":
        return cls(1.0, 0.0)

    @classmethod
    def one(cls) -> "Qubit":
        return cls(0.0, 1.0)

    @classmethod
    def plus(cls) -> "Qubit":
        return cls(1 / math.sqrt(2), 1 / math.sqrt(2))

    @classmethod
    def minus(cls) -> "Qubit":
        return cls(1 / math.sqrt(2), -1 / math.sqrt(2))

    @property
    def alpha(self) -> complex:
        return self.state.amplitudes[0]

    @property
    def beta(self) -> complex:
        return self.state.amplitudes[1]

    def measure(self) -> int:
        """Measure in the computational basis (returns 0 or 1)."""
        outcome, _ = self.state.measure_probabilistic(0)
        return outcome

    def __repr__(self) -> str:
        a, b = self.alpha, self.beta
        return f"Qubit({a:.4g} |0⟩ + {b:.4g} |1⟩)"


def entangle(*qubits: Qubit) -> StateVector:
    """
    Tensor-product multiple qubits into a multi-qubit state.

    Note: the result is only genuinely entangled if the qubits have
    been individually transformed before tensoring.  Tensoring two
    *separable* qubits produces a separable state.

    Example::

        q0 = Qubit.plus()
        q1 = Qubit.zero()
        state = entangle(q0, q1)  # (|00⟩ + |10⟩)/√2
    """
    if not qubits:
        raise ValueError("entangle requires at least one qubit")
    result = qubits[0].state.amplitudes
    for q in qubits[1:]:
        result = np.kron(result, q.state.amplitudes)
    return StateVector(result)