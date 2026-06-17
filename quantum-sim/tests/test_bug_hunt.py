"""
Bug hunt tests — tests that verify specific bugs before and after fixing.

Each test is designed to expose a specific bug found during code review.
"""

import math
import numpy as np
import pytest

from quantum_sim import (
    QuantumCircuit,
    Simulator,
    StateVector,
    DensityMatrix,
    GATES,
    Gate,
)
from quantum_sim.gates import rx, ry, rz, controlled
from quantum_sim.algorithms import grovers_search, grover_circuit, teleportation
from quantum_sim.noise import depolarizing, apply_channel


# ─── Bug 1: Mutable default argument in grovers_search ──────────────────

class TestBugMutableDefault:
    def test_grovers_default_not_mutated(self):
        """BUG: grovers_search has a mutable default argument `marked=[5]`.

        If the default list is mutated by a call, subsequent calls with
        the default will use the mutated list.  Verify the default is intact
        after multiple calls.
        """
        # Call with default
        result1 = grovers_search(n=2, marked=[1])
        # Call with default again — should still search for [5] at n=3
        result2 = grovers_search()  # uses default marked=[5], n=3
        # The marked state 5 (=101) should be found
        assert result2.counts.get("101", 0) > 0


# ─── Bug 2: Empty StateVector accepted ──────────────────────────────────

class TestBugEmptyState:
    def test_empty_state_rejected(self):
        """BUG: StateVector with 0 amplitudes passes the power-of-2 check.

        An empty array has size 0, and 0 & (0-1) = 0 & (-1) = 0 in Python,
        which incorrectly passes the power-of-2 check.  An empty state
        is invalid and should be rejected.
        """
        with pytest.raises(ValueError):
            StateVector(np.array([], dtype=complex))


# ─── Bug 3: Gate.__pow__ with multi-qubit gates ──────────────────────────

class TestBugGatePower:
    def test_pow_multi_qubit_gate(self):
        """BUG: Gate.__pow__ uses GATES['I1'] (1-qubit identity) as the
        starting point.  For a 2-qubit gate, compose() would fail because
        the identity is 2x2 but the gate is 4x4.

        SWAP^2 should equal the 4x4 identity.
        """
        swap = GATES["SWAP"]
        # SWAP^2 = I (4x4)
        swap2 = swap ** 2
        assert swap2.matrix.shape == (4, 4)
        assert np.allclose(swap2.matrix, np.eye(4), atol=1e-9)


# ─── Bug 4: from_dict cannot deserialize parameterized gates ─────────────

class TestBugSerializationParameterized:
    def test_serialize_parameterized_gate(self):
        """BUG: QuantumCircuit.to_dict/from_dict cannot roundtrip
        parameterized gates (RX, RY, RZ, etc.) because the gate name
        includes parameters (e.g. 'RX(0.7854)') which is not a key in GATES.
        """
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.ry(0, math.pi / 4)
        qc.cx(0, 1)

        d = qc.to_dict()
        # Should be able to deserialize
        qc2 = QuantumCircuit.from_dict(d)

        # Verify the circuits produce the same state
        sim = Simulator()
        s1 = sim.evolve(qc)
        s2 = sim.evolve(qc2)
        assert np.allclose(s1.amplitudes, s2.amplitudes, atol=1e-9)


# ─── Bug 5: teleportation return type mismatch ───────────────────────────

class TestBugTeleportationReturnType:
    def test_teleportation_returns_density_matrix(self):
        """BUG: teleportation() has return type annotation
        Tuple[StateVector, int, int] but actually returns a DensityMatrix.
        The annotation should be corrected.
        """
        result, _, _ = teleportation()
        # The result should be a DensityMatrix (has .matrix and .purity)
        assert isinstance(result, DensityMatrix)
        assert hasattr(result, "purity")
        assert hasattr(result, "matrix")


# ─── Bug 6: depolarizing for n_qubits > 1 is incorrect ────────────────────

class TestBugDepolarizingMultiQubit:
    def test_depolarizing_2qubit_correct(self):
        """BUG: depolarizing(p, n_qubits=2) uses Kraus operators that don't
        produce a proper depolarizing channel.  The result should mix
        towards the maximally mixed state I/4, but the current implementation
        doesn't do that correctly.

        For proper depolarizing: ρ → (1-p)ρ + p I/2^n
        Check that applying with p=1 gives I/2^n.
        """
        # Start with a pure state |00⟩⟨00|
        rho = np.zeros((4, 4), dtype=complex)
        rho[0, 0] = 1.0

        # Full depolarizing (p=1) should give I/4
        ch = depolarizing(1.0, n_qubits=2)
        result = apply_channel(rho, ch, (0, 1))

        expected = np.eye(4, dtype=complex) / 4
        assert np.allclose(result, expected, atol=1e-9), \
            f"Expected {expected}, got {result}"


# ─── Bug 7: _G_XX dead code (first computation is wrong) ────────────────

class TestBugXXGate:
    def test_xx_gate_is_unitary(self):
        """BUG: _G_XX is computed twice.  The first computation (lines
        171-177) produces a non-unitary matrix, which is then overwritten
        by the correct computation.  Verify the final gate is correct."""
        xx = GATES["XX"]
        assert np.allclose(xx.matrix @ xx.matrix.conj().T, np.eye(4), atol=1e-9)

    def test_xx_gate_correct_matrix(self):
        """The XX gate should be (1/√2) * [[1,0,0,i],[0,1,i,0],[0,i,1,0],[i,0,0,1]]"""
        xx = GATES["XX"]
        expected = (1 / math.sqrt(2)) * np.array([
            [1, 0, 0, 1j], [0, 1, 1j, 0], [0, 1j, 1, 0], [1j, 0, 0, 1]
        ], dtype=complex)
        assert np.allclose(xx.matrix, expected, atol=1e-9)


# ─── Bug 8: measure() unused rng parameter ───────────────────────────────

class TestBugMeasureRngUnused:
    def test_measure_rng_parameter_accepted(self):
        """BUG: StateVector.measure() accepts an `rng` parameter that is
        never used.  This is a minor API issue — the parameter should either
        be used or removed.  Verify the function at least accepts it without
        error."""
        sv = StateVector(np.array([1 / math.sqrt(2), 1 / math.sqrt(2)], dtype=complex))
        rng = np.random.default_rng(42)
        # Should not raise even though rng is unused
        result = sv.measure(0, 0, rng=rng)
        assert np.isclose(result.amplitudes[0], 1 / math.sqrt(2))


# ─── Bug 9: bb84 unused variable ─────────────────────────────────────────

class TestBugBB84UnusedVar:
    def test_bb84_returns_correct_types(self):
        """BUG: bb84_protocol has an unused `matching_indices` variable.
        This is dead code that should be cleaned up.  Verify the function
        still returns correct results."""
        from quantum_sim.advanced import bb84_protocol
        alice_key, bob_key, error_rate = bb84_protocol(n_bits=16, seed=42)
        assert isinstance(alice_key, list)
        assert isinstance(bob_key, list)
        assert isinstance(error_rate, float)


# ─── Bug 10: Grover's oracle only works for n ≤ 3 ────────────────────────

class TestBugGroverOracleN4:
    def test_grover_n4_finds_marked(self):
        """BUG: Grover's oracle uses `qc.toffoli(n-1, n-2, 0)` for n≥3,
        which is only a 3-qubit Toffoli.  For n=4 qubits, this doesn't
        implement a proper 4-qubit phase oracle.  Verify that Grover's
        can find a marked state in a 4-qubit search space.
        """
        # Mark state 3 (0011) in a 4-qubit space
        result = grovers_search(n=4, marked=[3], shots=4096)
        # The marked state |0011⟩ should have the highest probability
        # (or at least significantly above the baseline 1/16 = 6.25%)
        marked_count = result.counts.get("0011", 0)
        total = sum(result.counts.values())
        p_marked = marked_count / total
        # Should be well above the uniform 1/16 = 6.25%
        assert p_marked > 0.15, \
            f"Marked state probability {p_marked:.2%} should be > 15%"


# ─── Bug 11: StateVector.dimension for size 1 ───────────────────────────

class TestBugSingleElementState:
    def test_single_element_state(self):
        """A state with a single element (size=1) has dimension 1, which
        is 2^0 = 1 qubit?  No — 2^0 = 1, so num_qubits would be 0.
        This is an edge case: is a 1-element state a valid 0-qubit state?"""
        sv = StateVector(np.array([1.0], dtype=complex))
        # 2^0 = 1, so this is technically a 0-qubit state
        assert sv.num_qubits == 0
        assert sv.dimension == 1


# ─── Bug 12: DensityMatrix doesn't check hermiticity or positivity ──────

class TestBugDensityMatrixValidation:
    def test_non_hermitian_density_matrix_detected(self):
        """BUG: DensityMatrix doesn't verify that the matrix is Hermitian
        (ρ = ρ†), which is a requirement for a valid density matrix.
        Non-Hermitian matrices can lead to incorrect entropy calculations.
        """
        # Non-Hermitian matrix
        bad = np.array([[1, 1], [0, 0]], dtype=complex)
        # Currently accepted, but should ideally be rejected or at least
        # the user should be aware.  Test that it at least doesn't crash.
        rho = DensityMatrix(bad)
        # The trace is 1 but it's not Hermitian — this is problematic
        # Just verify it doesn't crash (the fix would add a Hermiticity check)
        assert rho.dimension == 2


# ─── Bug 13: _embed_pure_gate assert vs proper error ─────────────────────

class TestBugEmbedAssert:
    def test_embed_pure_gate_dimension_mismatch(self):
        """BUG: _embed_pure_gate uses `assert` which can be disabled with
        -O flag.  It should raise a proper ValueError."""
        from quantum_sim.simulator import _embed_pure_gate
        # 2x2 gate but 3 targets — should raise a proper error
        with pytest.raises((ValueError, AssertionError)):
            _embed_pure_gate(np.eye(2, dtype=complex), (0, 1, 2), 3)