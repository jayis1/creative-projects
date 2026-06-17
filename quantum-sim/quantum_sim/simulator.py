"""
Simulator: applies a QuantumCircuit to a quantum state.

The simulator supports two modes:
  - state_vector: tracks |ψ⟩ as a 2^n complex vector (fast, pure states).
  - density_matrix: tracks ρ (supports mixed states and noise channels).

Gates are applied by embedding the gate's small unitary into the full
Hilbert space via tensor-product embedding, then multiplying.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import numpy as np

from .circuit import Operation, QuantumCircuit
from .gates import GATES, Gate, controlled
from .state import DensityMatrix, StateVector

__all__ = ["Simulator", "SimulationResult"]


def _embed_gate(
    gate_matrix: np.ndarray,
    targets: Tuple[int, ...],
    controls: Tuple[int, ...],
    n_qubits: int,
) -> np.ndarray:
    """
    Build the full 2^n × 2^n unitary for applying *gate_matrix* to
    *targets* with optional *controls* qubits.

    Qubit convention: qubit 0 is the LSB (rightmost in the binary label).

    Two cases:
      1. The gate matrix already includes the control qubits (e.g. CNOT,
         CZ, Toffoli stored as full matrices).  In this case
         n_gate_qubits == len(targets) + len(controls), and we embed the
         full matrix as a pure gate on (controls + targets).
      2. The gate matrix acts only on the target qubits (e.g. a 2×2 gate
         with an explicit control list).  In this case
         n_gate_qubits == len(targets), and we build the controlled version.
    """
    target_set = set(targets)
    control_set = set(controls)
    all_involved = target_set | control_set
    if len(all_involved) != len(targets) + len(controls):
        raise ValueError("Overlap between targets and controls")

    gate_dim = gate_matrix.shape[0]
    n_gate_qubits = int(round(math.log2(gate_dim)))
    total_qubits = len(targets) + len(controls)

    if n_gate_qubits == total_qubits:
        # Case 1: gate matrix already includes controls (CNOT, CZ, etc.)
        # The qubit ordering is (controls..., targets...) where the first
        # element is the MSB of the gate's local space.
        all_qubits = tuple(controls) + tuple(targets)
        return _embed_pure_gate(gate_matrix, all_qubits, n_qubits)
    elif n_gate_qubits == len(targets) and controls:
        # Case 2: build a controlled version of the target gate
        return _embed_controlled_gate(gate_matrix, targets, controls, n_qubits)
    elif not controls and n_gate_qubits == len(targets):
        return _embed_pure_gate(gate_matrix, targets, n_qubits)
    else:
        raise ValueError(
            f"Gate acts on {n_gate_qubits} qubits but "
            f"{len(targets)} targets + {len(controls)} controls given"
        )


def _embed_pure_gate(gate_matrix: np.ndarray, targets: Tuple[int, ...], n_qubits: int) -> np.ndarray:
    """
    Embed a multi-qubit gate into the full 2^n Hilbert space.

    *targets* specifies which global qubits the gate acts on, in MSB-first
    order: targets[0] is the most-significant qubit of the gate's local
    space, targets[-1] is the least-significant.

    Global qubit convention: qubit 0 is the global LSB.
    """
    n_gate = int(round(math.log2(gate_matrix.shape[0])))
    assert n_gate == len(targets), f"Gate dim mismatch: {n_gate} vs {len(targets)}"
    dim = 2 ** n_qubits
    full = np.zeros((dim, dim), dtype=complex)

    involved = set(targets)
    # For each pair (i, j) of global basis indices, extract the sub-indices
    # for the involved qubits (preserving the original target ordering) and
    # look up the gate matrix entry.
    for i in range(dim):
        sub_i = 0
        for k, q in enumerate(targets):
            if (i >> q) & 1:
                sub_i |= (1 << (n_gate - 1 - k))  # MSB = targets[0]
        for j in range(dim):
            sub_j = 0
            for k, q in enumerate(targets):
                if (j >> q) & 1:
                    sub_j |= (1 << (n_gate - 1 - k))
            # Non-involved qubits must match between i and j
            match = True
            for q in range(n_qubits):
                if q in involved:
                    continue
                if ((i >> q) & 1) != ((j >> q) & 1):
                    match = False
                    break
            if match:
                full[i, j] = gate_matrix[sub_i, sub_j]
    return full


def _embed_controlled_gate(
    gate_matrix: np.ndarray,
    targets: Tuple[int, ...],
    controls: Tuple[int, ...],
    n_qubits: int,
) -> np.ndarray:
    """
    Build a controlled unitary from a gate that acts only on *targets*.
    The gate is applied only when all *controls* qubits are |1⟩.
    """
    dim = 2 ** n_qubits
    # First embed the target gate into the full space (acts only on target qubits)
    pure = _embed_pure_gate(gate_matrix, targets, n_qubits)

    # Build the controlled version: identity everywhere except when all
    # controls are |1⟩, where we apply the pure gate.
    result = np.eye(dim, dtype=complex)
    for i in range(dim):
        controls_all_1 = all((i >> c) & 1 for c in controls)
        if controls_all_1:
            result[i, :] = pure[i, :]
    return result


class SimulationResult:
    """Holds the result of a simulation."""

    def __init__(
        self,
        state: StateVector | DensityMatrix,
        n_qubits: int,
        measurements: Dict[int, int] | None = None,
        shots: int = 0,
        counts: Dict[str, int] | None = None,
    ) -> None:
        self.state = state
        self.n_qubits = n_qubits
        self.measurements: Dict[int, int] = measurements or {}
        self.shots = shots
        self.counts: Dict[str, int] = counts or {}

    @property
    def probabilities(self) -> np.ndarray:
        """Measurement probabilities in the computational basis."""
        return self.state.probabilities()

    def get_counts(self) -> Dict[str, int]:
        """Bitstring measurement counts (from sampling or stored)."""
        return dict(self.counts)

    def __repr__(self) -> str:
        return (
            f"SimulationResult(n_qubits={self.n_qubits}, shots={self.shots}, "
            f"counts={self.counts})"
        )


class Simulator:
    """
    Quantum circuit simulator.

    Parameters
    ----------
    mode : str
        'state_vector' (default) or 'density_matrix'.
    seed : int, optional
        Random seed for measurement sampling.
    noise_channels : list, optional
        List of (NoiseChannel, targets) tuples to apply after each gate.
        Only supported in density_matrix mode.
    """

    def __init__(
        self,
        mode: str = "state_vector",
        seed: Optional[int] = None,
        noise_channels: Optional[list] = None,
    ) -> None:
        if mode not in ("state_vector", "density_matrix"):
            raise ValueError(f"Unknown mode '{mode}'; use 'state_vector' or 'density_matrix'")
        self.mode = mode
        self.rng = np.random.default_rng(seed)
        self.noise_channels = noise_channels or []

    def run(self, circuit: QuantumCircuit, initial_state: StateVector | None = None, shots: int = 1024) -> SimulationResult:
        """Run a circuit and return the result with measurement sampling."""
        if self.mode == "state_vector":
            if self.noise_channels:
                raise ValueError("Noise channels require density_matrix mode")
            return self._run_sv(circuit, initial_state, shots)
        return self._run_dm(circuit, initial_state, shots)

    def _run_sv(self, circuit: QuantumCircuit, initial_state: StateVector | None, shots: int) -> SimulationResult:
        n = circuit.n_qubits
        if initial_state is None:
            amps = np.zeros(2 ** n, dtype=complex)
            amps[0] = 1.0
            state = StateVector(amps)
        else:
            state = initial_state
            if state.num_qubits != n:
                raise ValueError(f"Initial state has {state.num_qubits} qubits, circuit has {n}")

        for op in circuit.operations:
            if op.name in ("barrier", "measure"):
                continue
            U = _embed_gate(op.gate.matrix, op.targets, op.controls, n)
            state = state.apply_unitary(U)

        # Sample measurements
        probs = state.probabilities()
        if shots > 0:
            samples = self.rng.choice(2 ** n, size=shots, p=probs)
            counts: Dict[str, int] = {}
            for s in samples:
                key = format(int(s), f"0{n}b")
                counts[key] = counts.get(key, 0) + 1
        else:
            counts = {}

        return SimulationResult(state=state, n_qubits=n, shots=shots, counts=counts)

    def _run_dm(self, circuit: QuantumCircuit, initial_state: DensityMatrix | StateVector | None, shots: int) -> SimulationResult:
        from .noise import apply_channel

        n = circuit.n_qubits
        if initial_state is None:
            dm = np.zeros((2 ** n, 2 ** n), dtype=complex)
            dm[0, 0] = 1.0
            state = DensityMatrix(dm)
        elif isinstance(initial_state, StateVector):
            state = initial_state.to_density_matrix()
        else:
            state = initial_state
            if state.num_qubits != n:
                raise ValueError(f"Initial state has {state.num_qubits} qubits, circuit has {n}")

        for op in circuit.operations:
            if op.name in ("barrier", "measure"):
                continue
            U = _embed_gate(op.gate.matrix, op.targets, op.controls, n)
            state = state.apply_unitary(U)

            # Apply noise channels after each gate
            for channel, targets in self.noise_channels:
                state = DensityMatrix(apply_channel(state.matrix, channel, targets))

        probs = state.probabilities()
        if shots > 0:
            samples = self.rng.choice(2 ** n, size=shots, p=probs)
            counts: Dict[str, int] = {}
            for s in samples:
                key = format(int(s), f"0{n}b")
                counts[key] = counts.get(key, 0) + 1
        else:
            counts = {}

        return SimulationResult(state=state, n_qubits=n, shots=shots, counts=counts)

    def evolve(self, circuit: QuantumCircuit, initial_state: StateVector | None = None) -> StateVector | DensityMatrix:
        """Run the circuit without sampling; return the final quantum state."""
        result = self.run(circuit, initial_state, shots=0)
        return result.state

    def expectation_value(self, circuit: QuantumCircuit, observable: np.ndarray, initial_state: StateVector | None = None) -> complex:
        """Compute ⟨ψ|O|ψ⟩ after running the circuit."""
        state = self.evolve(circuit, initial_state)
        return state.expectation(observable)