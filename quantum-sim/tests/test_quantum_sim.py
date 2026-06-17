"""Tests for quantum_sim — gates, state, simulator, and algorithms."""

import math
import numpy as np
import pytest

from quantum_sim.gates import GATES, Gate, controlled, rx, ry, rz, phase
from quantum_sim.state import StateVector, DensityMatrix
from quantum_sim.circuit import QuantumCircuit
from quantum_sim.simulator import Simulator
from quantum_sim.qubit import Qubit, ZERO, ONE, PLUS, MINUS, entangle
from quantum_sim.bloch import bloch_vector, bloch_angles, bloch_sphere_ascii
from quantum_sim.algorithms import (
    bell_state,
    deutsch_jozsa,
    grovers_search,
    quantum_fourier_transform,
    superdense_coding,
    teleportation,
)


# ─── Gates ──────────────────────────────────────────────────────────────

class TestGates:
    def test_all_gates_are_unitary(self):
        for name, g in GATES.items():
            if isinstance(g, Gate):
                assert np.allclose(g.matrix @ g.matrix.conj().T, np.eye(g.matrix.shape[0]), atol=1e-9)

    def test_hadamard_matrix(self):
        expected = (1 / math.sqrt(2)) * np.array([[1, 1], [1, -1]])
        assert np.allclose(GATES["H"].matrix, expected)

    def test_x_is_not(self):
        assert np.allclose(GATES["X"].matrix, [[0, 1], [1, 0]])

    def test_z_matrix(self):
        assert np.allclose(GATES["Z"].matrix, np.diag([1, -1]))

    def test_cnot_matrix(self):
        expected = np.array([[1,0,0,0],[0,1,0,0],[0,0,0,1],[0,0,1,0]],dtype=complex)
        assert np.allclose(GATES["CNOT"].matrix, expected)

    def test_toffoli_matrix(self):
        expected = np.eye(8, dtype=complex)
        expected[6,6]=0; expected[7,7]=0
        expected[6,7]=1; expected[7,6]=1
        assert np.allclose(GATES["TOFFOLI"].matrix, expected)

    def test_rx_rotation(self):
        rx0 = rx(0.0)
        assert np.allclose(rx0.matrix, np.eye(2))
        rxpi = rx(math.pi)
        assert np.allclose(rxpi.matrix, np.array([[0,-1j],[-1j,0]]), atol=1e-9)

    def test_ry_rotation(self):
        ry0 = ry(0.0)
        assert np.allclose(ry0.matrix, np.eye(2))
        rypi = ry(math.pi)
        assert np.allclose(rypi.matrix, np.array([[0,-1],[1,0]]), atol=1e-9)

    def test_gate_compose(self):
        h = GATES["H"]
        hh = h.compose(h)
        assert np.allclose(hh.matrix, np.eye(2), atol=1e-9)

    def test_gate_dagger(self):
        t = GATES["T"]
        tdag = t.dagger()
        assert np.allclose(t.compose(tdag).matrix, np.eye(2), atol=1e-9)

    def test_gate_tensor(self):
        # I ⊗ I = 4x4 identity
        ii = GATES["I"].tensor(GATES["I"])
        assert ii.matrix.shape == (4, 4)
        assert np.allclose(ii.matrix, np.eye(4))

    def test_controlled_creates_valid_gate(self):
        cx = controlled(GATES["X"])
        assert cx.matrix.shape == (4, 4)
        assert np.allclose(cx.matrix @ cx.matrix.conj().T, np.eye(4), atol=1e-9)

    def test_non_unitary_raises(self):
        with pytest.raises(ValueError):
            Gate("bad", np.array([[1, 2], [3, 4]], dtype=complex))

    def test_non_square_raises(self):
        with pytest.raises(ValueError):
            Gate("bad", np.array([[1, 0], [0, 1], [0, 0]], dtype=complex))


# ─── StateVector ─────────────────────────────────────────────────────────

class TestStateVector:
    def test_zero_state(self):
        sv = StateVector(np.array([1.0, 0.0]))
        assert sv.num_qubits == 1
        assert np.isclose(sv.norm(), 1.0)

    def test_normalize(self):
        sv = StateVector(np.array([3.0, 4.0]))
        assert np.isclose(sv.norm(), 5.0)
        normalized = sv.normalize()
        assert np.isclose(normalized.norm(), 1.0)

    def test_normalize_zero_raises(self):
        with pytest.raises(ValueError):
            StateVector(np.array([0.0, 0.0])).normalize()

    def test_probabilities(self):
        sv = StateVector(np.array([0.6, 0.8], dtype=complex))
        sv = sv.normalize()
        probs = sv.probabilities()
        assert np.isclose(probs[0], 0.36, atol=1e-9)
        assert np.isclose(probs[1], 0.64, atol=1e-9)
        assert np.isclose(np.sum(probs), 1.0)

    def test_expectation_sigma_z(self):
        # |0⟩ has ⟨Z⟩ = +1, |1⟩ has ⟨Z⟩ = -1
        sz = np.array([[1, 0], [0, -1]], dtype=complex)
        sv0 = StateVector(np.array([1.0, 0.0], dtype=complex))
        sv1 = StateVector(np.array([0.0, 1.0], dtype=complex))
        assert np.isclose(sv0.expectation(sz), 1.0)
        assert np.isclose(sv1.expectation(sz), -1.0)

    def test_apply_unitary_hadamard(self):
        sv = StateVector(np.array([1.0, 0.0], dtype=complex))
        h_state = sv.apply_unitary(GATES["H"].matrix)
        expected = np.array([1 / math.sqrt(2), 1 / math.sqrt(2)], dtype=complex)
        assert np.allclose(h_state.amplitudes, expected)

    def test_fidelity_same_state(self):
        sv = StateVector(np.array([1.0, 0.0], dtype=complex))
        assert np.isclose(sv.fidelity(sv), 1.0)

    def test_fidelity_orthogonal(self):
        sv0 = StateVector(np.array([1.0, 0.0], dtype=complex))
        sv1 = StateVector(np.array([0.0, 1.0], dtype=complex))
        assert np.isclose(sv0.fidelity(sv1), 0.0)

    def test_is_entangled_bell(self):
        sv = StateVector(np.array([1/math.sqrt(2), 0, 0, 1/math.sqrt(2)], dtype=complex))
        assert sv.is_entangled()

    def test_is_not_entangled_separable(self):
        sv = StateVector(np.array([1.0, 0, 0, 0], dtype=complex))
        assert not sv.is_entangled()

    def test_measure_collapse(self):
        sv = StateVector(np.array([1/math.sqrt(2), 1/math.sqrt(2)], dtype=complex))
        collapsed = sv.measure(0, 0)
        assert np.isclose(collapsed.amplitudes[0], 1/math.sqrt(2))
        assert np.isclose(collapsed.amplitudes[1], 0.0)

    def test_measure_probabilistic(self):
        sv = StateVector(np.array([0.0, 1.0], dtype=complex))
        rng = np.random.default_rng(0)
        outcome, collapsed = sv.measure_probabilistic(0, rng)
        assert outcome == 1
        assert np.isclose(collapsed.amplitudes[1], 1.0)

    def test_to_density_matrix(self):
        sv = StateVector(np.array([1/math.sqrt(2), 1/math.sqrt(2)], dtype=complex))
        rho = sv.to_density_matrix()
        assert rho.matrix.shape == (2, 2)
        assert np.isclose(np.trace(rho.matrix), 1.0)
        assert np.isclose(rho.purity(), 1.0)


# ─── DensityMatrix ────────────────────────────────────────────────────────

class TestDensityMatrix:
    def test_trace_one(self):
        rho = DensityMatrix(np.eye(2, dtype=complex) / 2)
        assert np.isclose(rho.trace(), 1.0)

    def test_purity_mixed(self):
        rho = DensityMatrix(np.eye(2, dtype=complex) / 2)
        assert np.isclose(rho.purity(), 0.5)
        assert not rho.is_pure()

    def test_purity_pure(self):
        rho = DensityMatrix(np.outer(np.array([1,0],dtype=complex), np.array([1,0]).conj()))
        assert np.isclose(rho.purity(), 1.0)
        assert rho.is_pure()

    def test_von_neumann_entropy_maximally_mixed(self):
        rho = DensityMatrix(np.eye(2, dtype=complex) / 2)
        s = rho.von_neumann_entropy()
        assert np.isclose(s, 1.0, atol=1e-9)

    def test_von_neumann_entropy_pure(self):
        rho = DensityMatrix(np.outer(np.array([1,0],dtype=complex), np.array([1,0]).conj()))
        assert np.isclose(rho.von_neumann_entropy(), 0.0, atol=1e-9)

    def test_partial_trace_identity(self):
        # |00⟩⟨00|, trace out qubit 1 → |0⟩⟨0|
        rho = DensityMatrix(np.zeros((4,4), dtype=complex))
        rho.matrix[0, 0] = 1.0
        reduced = rho.partial_trace([0])
        assert reduced.matrix.shape == (2, 2)
        assert np.isclose(reduced.matrix[0, 0], 1.0)
        assert np.isclose(reduced.matrix[1, 1], 0.0)

    def test_partial_trace_bell(self):
        # Bell state |Φ+⟩ = (|00⟩+|11⟩)/√2, reduced state is I/2
        sv = StateVector(np.array([1/math.sqrt(2), 0, 0, 1/math.sqrt(2)], dtype=complex))
        rho = sv.to_density_matrix()
        reduced = rho.partial_trace([0])
        assert np.allclose(reduced.matrix, np.eye(2) / 2, atol=1e-9)


# ─── Simulator & Circuit ─────────────────────────────────────────────────

class TestSimulator:
    def test_hadamard_on_zero(self):
        qc = QuantumCircuit(1)
        qc.h(0)
        sim = Simulator()
        state = sim.evolve(qc)
        expected = np.array([1/math.sqrt(2), 1/math.sqrt(2)], dtype=complex)
        assert np.allclose(state.amplitudes, expected, atol=1e-9)

    def test_bell_state_creation(self):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        sim = Simulator()
        state = sim.evolve(qc)
        expected = np.array([1/math.sqrt(2), 0, 0, 1/math.sqrt(2)], dtype=complex)
        assert np.allclose(state.amplitudes, expected, atol=1e-9)

    def test_x_gate(self):
        qc = QuantumCircuit(1)
        qc.x(0)
        sim = Simulator()
        state = sim.evolve(qc)
        assert np.allclose(state.amplitudes, np.array([0, 1], dtype=complex))

    def test_cnot_control_0(self):
        qc = QuantumCircuit(2)
        # |00⟩ → CNOT → |00⟩
        qc.cx(0, 1)
        sim = Simulator()
        state = sim.evolve(qc)
        assert np.allclose(state.amplitudes, np.array([1, 0, 0, 0], dtype=complex))

    def test_cnot_control_1(self):
        qc = QuantumCircuit(2)
        qc.x(0)  # |10⟩
        qc.cx(0, 1)  # → |11⟩
        sim = Simulator()
        state = sim.evolve(qc)
        assert np.allclose(state.amplitudes, np.array([0, 0, 0, 1], dtype=complex))

    def test_toffoli(self):
        # Toffoli with both controls = 1 flips target
        qc = QuantumCircuit(3)
        qc.x(0)
        qc.x(1)
        qc.toffoli(0, 1, 2)
        sim = Simulator()
        state = sim.evolve(qc)
        # |011⟩ → |111⟩
        assert np.isclose(np.abs(state.amplitudes[7])**2, 1.0)

    def test_toffoli_no_flip(self):
        qc = QuantumCircuit(3)
        qc.x(0)  # only one control
        qc.toffoli(0, 1, 2)
        sim = Simulator()
        state = sim.evolve(qc)
        # |001⟩ unchanged → target still 0
        assert np.isclose(np.abs(state.amplitudes[1])**2, 1.0)

    def test_swap_gate(self):
        qc = QuantumCircuit(2)
        qc.x(0)  # qubit 0 = |1⟩, so state is |01⟩ (global index 1)
        qc.swap(0, 1)  # → |10⟩ (global index 2)
        sim = Simulator()
        state = sim.evolve(qc)
        assert np.isclose(np.abs(state.amplitudes[2])**2, 1.0)

    def test_density_matrix_mode(self):
        qc = QuantumCircuit(1)
        qc.h(0)
        sim = Simulator(mode="density_matrix")
        result = sim.run(qc, shots=100)
        assert result.state.matrix.shape == (2, 2)
        assert np.isclose(result.state.purity(), 1.0, atol=1e-9)

    def test_measurement_sampling(self):
        qc = QuantumCircuit(1)
        qc.h(0)
        sim = Simulator(seed=42)
        result = sim.run(qc, shots=1000)
        assert sum(result.counts.values()) == 1000
        # Should be roughly 50/50
        p0 = result.counts.get("0", 0) / 1000
        assert 0.4 < p0 < 0.6

    def test_rx_gate(self):
        qc = QuantumCircuit(1)
        qc.rx(0, math.pi)
        sim = Simulator()
        state = sim.evolve(qc)
        # RX(π)|0⟩ = -i|1⟩
        assert np.isclose(np.abs(state.amplitudes[1])**2, 1.0, atol=1e-9)

    def test_ry_gate(self):
        qc = QuantumCircuit(1)
        qc.ry(0, math.pi / 2)
        sim = Simulator()
        state = sim.evolve(qc)
        # RY(π/2)|0⟩ = (|0⟩ - |1⟩)/√2
        expected = np.array([math.cos(math.pi/4), math.sin(math.pi/4)], dtype=complex)
        assert np.allclose(state.amplitudes, expected, atol=1e-9)

    def test_invalid_qubit_raises(self):
        qc = QuantumCircuit(2)
        with pytest.raises(ValueError):
            qc.h(5)

    def test_duplicate_qubit_raises(self):
        qc = QuantumCircuit(2)
        with pytest.raises(ValueError):
            qc.cx(0, 0)

    def test_circuit_to_qasm(self):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        qasm = qc.to_qasm()
        assert "OPENQASM 2.0" in qasm
        assert "qreg" in qasm
        assert "h q[0];" in qasm
        assert "cx q[0],q[1];" in qasm

    def test_zero_qubits_raises(self):
        with pytest.raises(ValueError):
            QuantumCircuit(0)

    def test_initial_state_mismatch_raises(self):
        qc = QuantumCircuit(2)
        sv = StateVector(np.array([1.0, 0.0], dtype=complex))  # 1 qubit
        sim = Simulator()
        with pytest.raises(ValueError):
            sim.run(qc, initial_state=sv, shots=0)


# ─── Qubit helpers ────────────────────────────────────────────────────────

class TestQubit:
    def test_qubit_zero(self):
        q = Qubit.zero()
        assert np.isclose(q.alpha, 1.0)
        assert np.isclose(q.beta, 0.0)

    def test_qubit_plus(self):
        q = Qubit.plus()
        assert np.isclose(q.alpha, 1/math.sqrt(2))
        assert np.isclose(q.beta, 1/math.sqrt(2))

    def test_entangle_two_qubits(self):
        q0 = Qubit.zero()
        q1 = Qubit.one()
        state = entangle(q0, q1)
        assert state.num_qubits == 2
        assert np.isclose(state.amplitudes[1], 1.0)  # |01⟩ = index 1

    def test_entangle_single(self):
        q = Qubit.plus()
        state = entangle(q)
        assert state.num_qubits == 1


# ─── Bloch sphere ─────────────────────────────────────────────────────────

class TestBloch:
    def test_bloch_zero(self):
        sv = StateVector(np.array([1.0, 0.0], dtype=complex))
        v = bloch_vector(sv)
        assert np.allclose(v, [0, 0, 1], atol=1e-9)

    def test_bloch_one(self):
        sv = StateVector(np.array([0.0, 1.0], dtype=complex))
        v = bloch_vector(sv)
        assert np.allclose(v, [0, 0, -1], atol=1e-9)

    def test_bloch_plus(self):
        sv = StateVector(np.array([1/math.sqrt(2), 1/math.sqrt(2)], dtype=complex))
        v = bloch_vector(sv)
        assert np.allclose(v, [1, 0, 0], atol=1e-9)

    def test_bloch_angles(self):
        sv = StateVector(np.array([1.0, 0.0], dtype=complex))
        theta, phi = bloch_angles(sv)
        assert np.isclose(theta, 0)

    def test_bloch_ascii(self):
        sv = StateVector(np.array([1/math.sqrt(2), 1/math.sqrt(2)], dtype=complex))
        text = bloch_sphere_ascii(sv)
        assert "●" in text

    def test_bloch_multi_qubit_raises(self):
        sv = StateVector(np.array([1, 0, 0, 0], dtype=complex))
        with pytest.raises(ValueError):
            bloch_vector(sv)


# ─── Algorithms ──────────────────────────────────────────────────────────

class TestAlgorithms:
    def test_bell_state_creation(self):
        result = bell_state(0)
        sv = result.state
        assert np.isclose(np.abs(sv.amplitudes[0])**2, 0.5)
        assert np.isclose(np.abs(sv.amplitudes[3])**2, 0.5)
        assert np.isclose(np.abs(sv.amplitudes[1])**2, 0.0)
        assert np.isclose(np.abs(sv.amplitudes[2])**2, 0.0)

    def test_bell_state_entangled(self):
        result = bell_state(0)
        assert result.state.is_entangled()

    def test_bell_state_type_2(self):
        result = bell_state(2)  # |Ψ+⟩ = (|01⟩+|10⟩)/√2
        sv = result.state
        assert np.isclose(np.abs(sv.amplitudes[1])**2, 0.5)
        assert np.isclose(np.abs(sv.amplitudes[2])**2, 0.5)

    def test_bell_invalid_type_raises(self):
        with pytest.raises(ValueError):
            bell_state(99)

    def test_deutsch_jozsa_constant(self):
        result = deutsch_jozsa("constant", n=2)
        # The circuit has n+1=3 qubits.  Bitstrings are MSB-first (qubit n
        # is the leftmost character).  The input register is qubits 0..n-1,
        # which occupy the LAST n characters of the bitstring.
        # For a constant oracle, the input register always measures |0...0⟩.
        # The ancilla (qubit n) is in |−⟩ and measures randomly.
        input_zero_count = 0
        for bitstring, count in result.counts.items():
            input_bits = bitstring[-2:]  # last n=2 chars = qubits 0,1
            if input_bits == "00":
                input_zero_count += count
        p0 = input_zero_count / result.shots
        assert p0 > 0.5

    def test_deutsch_jozsa_balanced(self):
        result = deutsch_jozsa("balanced", n=2)
        # For balanced oracle, input register never measures all-zeros.
        input_zero_count = 0
        for bitstring, count in result.counts.items():
            input_bits = bitstring[-2:]
            if input_bits == "00":
                input_zero_count += count
        p0 = input_zero_count / result.shots
        assert p0 < 0.5

    def test_superdense_coding_all_messages(self):
        for msg in range(4):
            result = superdense_coding(msg)
            bits = format(msg, "02b")
            assert result.counts.get(bits, 0) > 0

    def test_superdense_invalid_message(self):
        with pytest.raises(ValueError):
            superdense_coding(5)

    def test_grovers_finds_marked(self):
        result = grovers_search(n=2, marked=[1], shots=1024)
        assert result.counts.get("01", 0) > result.counts.get("00", 0)

    def test_grovers_invalid_marked_raises(self):
        with pytest.raises(ValueError):
            grovers_search(n=2, marked=[99])

    def test_qft_on_zero(self):
        result = quantum_fourier_transform(n=2)
        # QFT|0...0⟩ = uniform superposition
        probs = result.probabilities
        assert np.allclose(probs, 0.25 * np.ones(4), atol=1e-9)

    def test_teleportation(self):
        rho, _, _ = teleportation()
        # The teleported state should be pure
        assert np.isclose(rho.purity(), 1.0, atol=1e-6)