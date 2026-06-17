"""
State representations for quantum simulation.

StateVector: pure state |ψ⟩, a complex vector of dimension 2^n.
DensityMatrix: mixed state ρ, a 2^n × 2^n complex matrix.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterator, List, Tuple

import numpy as np

__all__ = ["StateVector", "DensityMatrix"]


def _to_qubit_indices(dimension: int) -> int:
    if dimension <= 0 or (dimension & (dimension - 1)) != 0:
        raise ValueError(f"Dimension {dimension} is not a power of 2")
    return int(round(math.log2(dimension)))


def _basis_labels(n: int) -> List[str]:
    return [format(i, f"0{n}b") for i in range(2 ** n)]


@dataclass
class StateVector:
    """A pure quantum state |ψ⟩ of n qubits."""

    amplitudes: np.ndarray

    def __post_init__(self) -> None:
        a = np.asarray(self.amplitudes, dtype=complex).flatten()
        if a.size & (a.size - 1) != 0:
            raise ValueError(f"State dimension {a.size} is not a power of 2")
        self.amplitudes = a

    @property
    def num_qubits(self) -> int:
        return _to_qubit_indices(self.amplitudes.size)

    @property
    def dimension(self) -> int:
        return self.amplitudes.size

    def norm(self) -> float:
        """L2 norm (should be 1 for a properly normalized state)."""
        return float(np.sqrt(np.sum(np.abs(self.amplitudes) ** 2)))

    def normalize(self) -> "StateVector":
        """Return a normalized copy."""
        n = self.norm()
        if n == 0:
            raise ValueError("Cannot normalize a zero state")
        return StateVector(self.amplitudes / n)

    def probabilities(self) -> np.ndarray:
        """Measurement probabilities in the computational basis."""
        return np.abs(self.amplitudes) ** 2

    def expectation(self, observable: np.ndarray) -> complex:
        """⟨ψ|O|ψ⟩ for a hermitian observable."""
        if observable.shape != (self.dimension, self.dimension):
            raise ValueError(
                f"Observable shape {observable.shape} != state dimension {self.dimension}"
            )
        return complex(self.amplitudes.conj() @ observable @ self.amplitudes)

    def apply_unitary(self, u: np.ndarray) -> "StateVector":
        """Apply a unitary matrix and return a new state."""
        if u.shape != (self.dimension, self.dimension):
            raise ValueError(f"Unitary shape {u.shape} != state dimension {self.dimension}")
        return StateVector(u @ self.amplitudes)

    def partial_trace(self, keep: List[int]) -> "DensityMatrix":
        """Trace out all qubits NOT in *keep*, returning a density matrix."""
        keep = sorted(keep)
        return self.to_density_matrix().partial_trace(keep)

    def to_density_matrix(self) -> "DensityMatrix":
        """ρ = |ψ⟩⟨ψ|."""
        return DensityMatrix(np.outer(self.amplitudes, self.amplitudes.conj()))

    def fidelity(self, other: "StateVector") -> float:
        """Fidelity |⟨ψ|φ⟩|² between two pure states."""
        if self.dimension != other.dimension:
            raise ValueError("States have different dimensions")
        return float(np.abs(self.amplitudes.conj() @ other.amplitudes) ** 2)

    def is_entangled(self, tol: float = 1e-9) -> bool:
        """Check whether a bipartite state is entangled (Schmidt test)."""
        if self.num_qubits < 2:
            return False
        # Reshape into a matrix and check rank > 1 via SVD
        half = self.num_qubits // 2
        if half == 0:
            return False
        mat = self.amplitudes.reshape(2 ** half, 2 ** (self.num_qubits - half))
        sv = np.linalg.svd(mat, compute_uv=False)
        return int(np.sum(sv > tol)) > 1

    def measure(self, qubit: int, outcome: int, rng: np.random.Generator | None = None) -> "StateVector":
        """
        Projectively measure a qubit and collapse the state.

        Returns the post-measurement state (not normalized) for outcome 0 or 1.
        Use :meth:`measure_probabilistic` for a sampled outcome.
        """
        n = self.num_qubits
        if not (0 <= qubit < n):
            raise ValueError(f"Qubit {qubit} out of range for {n}-qubit state")
        if outcome not in (0, 1):
            raise ValueError("Measurement outcome must be 0 or 1")

        # The qubit index in our convention: qubit 0 is the least-significant
        # (rightmost) bit.  The amplitude index is computed accordingly.
        new_amp = self.amplitudes.copy()
        dim = 2 ** n
        for i in range(dim):
            # extract bit value at the qubit position
            if (i >> qubit) & 1 != outcome:
                new_amp[i] = 0.0
        return StateVector(new_amp)

    def measure_probabilistic(self, qubit: int, rng: np.random.Generator | None = None) -> Tuple[int, "StateVector"]:
        """
        Sample a measurement outcome for *qubit* and return
        (outcome, collapsed_normalized_state).
        """
        if rng is None:
            rng = np.random.default_rng()
        n = self.num_qubits
        probs = self.probabilities()
        p1 = 0.0
        for i in range(2 ** n):
            if (i >> qubit) & 1:
                p1 += probs[i]
        outcome = 1 if rng.random() < p1 else 0
        collapsed = self.measure(qubit, outcome)
        collapsed = collapsed.normalize()
        return outcome, collapsed

    def __str__(self) -> str:
        lines = []
        labels = _basis_labels(self.num_qubits)
        for label, amp in zip(labels, self.amplitudes):
            r = float(amp.real)
            i = float(amp.imag)
            if abs(r) < 1e-12 and abs(i) < 1e-12:
                continue
            if abs(i) < 1e-12:
                lines.append(f"  {r:+.6g} |{label}⟩")
            elif abs(r) < 1e-12:
                lines.append(f"  {i:+.6g}j |{label}⟩")
            else:
                lines.append(f"  ({r:+.6g}{i:+.6g}j) |{label}⟩")
        return "|ψ⟩ =\n" + "\n".join(lines) if lines else "|ψ⟩ = 0"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, StateVector):
            return NotImplemented
        if self.dimension != other.dimension:
            return False
        return bool(np.allclose(self.amplitudes, other.amplitudes, atol=1e-10))

    def __len__(self) -> int:
        return self.dimension


@dataclass
class DensityMatrix:
    """A (possibly mixed) quantum state ρ of n qubits."""

    matrix: np.ndarray

    def __post_init__(self) -> None:
        m = np.asarray(self.matrix, dtype=complex)
        dim = m.shape[0]
        if m.shape != (dim, dim):
            raise ValueError("Density matrix must be square")
        if dim & (dim - 1) != 0:
            raise ValueError(f"Density matrix dimension {dim} is not a power of 2")
        self.matrix = m

    @property
    def num_qubits(self) -> int:
        return _to_qubit_indices(self.matrix.shape[0])

    @property
    def dimension(self) -> int:
        return self.matrix.shape[0]

    def trace(self) -> complex:
        """Trace of ρ (should be 1 for a valid state)."""
        return complex(np.trace(self.matrix))

    def purity(self) -> float:
        """Tr(ρ²).  Purity = 1 for pure states, < 1 for mixed."""
        return float(np.real(np.trace(self.matrix @ self.matrix)))

    def is_pure(self, tol: float = 1e-9) -> bool:
        return abs(self.purity() - 1.0) < tol

    def probabilities(self) -> np.ndarray:
        """Diagonal elements of ρ = measurement probabilities."""
        return np.real(np.diag(self.matrix))

    def expectation(self, observable: np.ndarray) -> complex:
        return complex(np.trace(observable @ self.matrix))

    def apply_unitary(self, u: np.ndarray) -> "DensityMatrix":
        """ρ → U ρ U†."""
        if u.shape != (self.dimension, self.dimension):
            raise ValueError(f"Unitary shape {u.shape} != dimension {self.dimension}")
        return DensityMatrix(u @ self.matrix @ u.conj().T)

    def partial_trace(self, keep: List[int]) -> "DensityMatrix":
        """
        Trace out all qubits NOT in *keep*, returning the reduced
        density matrix for the kept qubits.

        Qubit convention: qubit *i* corresponds to the bit at position
        *i* in the computational basis index (qubit 0 = LSB).

        Implementation: reshape ρ (a 2^n × 2^n matrix) into a tensor with
        2n axes — axes 0..n-1 are the row index, axes n..2n-1 are the
        column index.  Qubit *i* occupies axes (i, n+i).  Tracing out a
        qubit contracts its row axis with its column axis (sum over the
        diagonal), leaving only the kept qubits.
        """
        n = self.num_qubits
        keep_set = set(keep)
        if not all(0 <= q < n for q in keep):
            raise ValueError(f"keep indices out of range for {n} qubits")
        if not keep_set:
            raise ValueError("keep list cannot be empty")

        # Reshape ρ into a (2, 2, ..., 2) tensor with 2n axes.
        # Due to C-order flattening, the row index varies slowest and the
        # column index varies fastest.  So:
        #   axis 0 = row qubit (n-1)  [MSB of row index]
        #   axis n-1 = row qubit 0    [LSB of row index]
        #   axis n = col qubit (n-1)  [MSB of col index]
        #   axis 2n-1 = col qubit 0   [LSB of col index]
        tensor = self.matrix.reshape([2] * (2 * n))

        # Build einsum subscripts using single-tensor contraction.
        # Each of the 2n axes gets a letter.  For traced-out qubits,
        # the row and column axes get the SAME letter so they contract.
        # For kept qubits, row and column axes get DIFFERENT letters
        # so they survive into the output.
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if 2 * n > len(alphabet):
            raise ValueError(f"Too many qubits ({n}) for einsum label space")

        # axis -> letter mapping
        axis_letters = [alphabet[i] for i in range(2 * n)]

        # For each qubit, map its row axis and col axis.
        # Row axis for qubit q: (n - 1 - q)  [because qubit 0 = LSB = last row axis]
        # Col axis for qubit: (2*n - 1 - q)  [qubit 0 = LSB = last col axis]
        for q in range(n):
            row_axis = n - 1 - q
            col_axis = 2 * n - 1 - q
            if q not in keep_set:
                # Trace out: same letter for row and col
                axis_letters[col_axis] = axis_letters[row_axis]

        # Output: kept qubits' row and col axes, ordered by ascending qubit index.
        # For each kept qubit q: output row axis first, then col axis.
        out_letters = []
        for q in sorted(keep):
            out_letters.append(axis_letters[n - 1 - q])        # row axis
            out_letters.append(axis_letters[2 * n - 1 - q])    # col axis

        subscript = "".join(axis_letters) + "->" + "".join(out_letters)
        result = np.einsum(subscript, tensor, optimize=True)

        new_dim = 2 ** len(keep_set)
        result = result.reshape(new_dim, new_dim)
        return DensityMatrix(result)

    def fidelity(self, other: "DensityMatrix") -> float:
        """Uhlmann fidelity Tr(√(√ρ σ √ρ)).  Simplified for pure states."""
        if self.dimension != other.dimension:
            raise ValueError("Different dimensions")
        s = np.sqrt(self.matrix)
        inner = s @ other.matrix @ s
        sqrt_inner = np.sqrt(np.abs(inner))
        return float(np.real(np.trace(sqrt_inner)) ** 2)

    def von_neumann_entropy(self) -> float:
        """S(ρ) = -Tr(ρ log₂ ρ)."""
        evals = np.linalg.eigvalsh(self.matrix)
        evals = np.clip(evals, 0, None)
        s = 0.0
        for e in evals:
            if e > 1e-15:
                s -= e * math.log2(e)
        return float(s)

    def __str__(self) -> str:
        return f"ρ ({self.dimension}×{self.dimension}), purity={self.purity():.6g}"