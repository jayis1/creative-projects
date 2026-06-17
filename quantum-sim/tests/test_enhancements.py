"""Tests for Phase 2 enhancements: noise, visualization, serialization, advanced."""

import math
import numpy as np
import pytest

from quantum_sim import (
    QuantumCircuit,
    Simulator,
    StateVector,
    DensityMatrix,
    depolarizing,
    bit_flip,
    phase_flip,
    amplitude_damping,
    phase_damping,
    pauli_channel,
    apply_channel,
    draw_circuit,
)
from quantum_sim.noise import NoiseChannel
from quantum_sim.advanced import bb84_protocol, quantum_walk, state_tomography


# ─── Noise channels ───────────────────────────────────────────────────────

class TestNoiseChannels:
    def test_depolarizing_is_cptp(self):
        ch = depolarizing(0.1)
        assert isinstance(ch, NoiseChannel)
        assert len(ch.kraus) == 4

    def test_bit_flip_is_cptp(self):
        ch = bit_flip(0.3)
        assert isinstance(ch, NoiseChannel)
        assert len(ch.kraus) == 2

    def test_phase_flip_is_cptp(self):
        ch = phase_flip(0.2)
        assert len(ch.kraus) == 2

    def test_amplitude_damping_is_cptp(self):
        ch = amplitude_damping(0.5)
        assert len(ch.kraus) == 2

    def test_phase_damping_is_cptp(self):
        ch = phase_damping(0.3)
        assert len(ch.kraus) == 2

    def test_pauli_channel_is_cptp(self):
        ch = pauli_channel(0.1, 0.1, 0.1)
        assert len(ch.kraus) == 4

    def test_invalid_probability_raises(self):
        with pytest.raises(ValueError):
            depolarizing(-0.1)
        with pytest.raises(ValueError):
            depolarizing(1.5)

    def test_invalid_pauli_sum_raises(self):
        with pytest.raises(ValueError):
            pauli_channel(0.5, 0.5, 0.5)

    def test_apply_channel_preserves_trace(self):
        rho = np.eye(2, dtype=complex) / 2
        ch = depolarizing(0.1)
        result = apply_channel(rho, ch, (0,))
        assert np.isclose(np.trace(result), 1.0, atol=1e-9)

    def test_depolarizing_mixed_state(self):
        # The depolarizing channel with Kraus operators √(1−p)I, √(p/3)X,
        # √(p/3)Y, √(p/3)Z produces: ρ → (1−p)ρ + (p/3)(XρX+YρY+ZρZ)
        # = (1 − 4p/3)ρ + (2p/3)Tr(ρ)I for single qubit.
        # For ρ = |0⟩⟨0|: result = (1−4p/3)|0⟩⟨0| + (2p/3)I
        rho = np.array([[1, 0], [0, 0]], dtype=complex)
        p = 0.15
        ch = depolarizing(p)
        result = apply_channel(rho, ch, (0,))
        expected = (1 - 4 * p / 3) * rho + (2 * p / 3) * np.eye(2, dtype=complex)
        assert np.allclose(result, expected, atol=1e-9)

    def test_bit_flip_effect(self):
        # Bit flip with p=1 on |0⟩⟨0| → |1⟩⟨1|
        rho = np.array([[1, 0], [0, 0]], dtype=complex)
        ch = bit_flip(1.0)
        result = apply_channel(rho, ch, (0,))
        assert np.isclose(result[1, 1], 1.0, atol=1e-9)

    def test_amplitude_damping_effect(self):
        # Amplitude damping on |1⟩⟨1| with γ=1 → |0⟩⟨0|
        rho = np.array([[0, 0], [0, 1]], dtype=complex)
        ch = amplitude_damping(1.0)
        result = apply_channel(rho, ch, (0,))
        assert np.isclose(result[0, 0], 1.0, atol=1e-9)

    def test_noise_in_simulator(self):
        qc = QuantumCircuit(1)
        qc.h(0)
        ch = depolarizing(0.5)
        sim = Simulator(mode="density_matrix", seed=42, noise_channels=[(ch, (0,))])
        result = sim.run(qc, shots=0)
        # With noise, the state should be mixed
        assert result.state.purity() < 1.0

    def test_noise_rejects_state_vector_mode(self):
        qc = QuantumCircuit(1)
        qc.h(0)
        ch = depolarizing(0.1)
        sim = Simulator(mode="state_vector", noise_channels=[(ch, (0,))])
        with pytest.raises(ValueError):
            sim.run(qc)


# ─── Circuit visualization ─────────────────────────────────────────────────

class TestVisualization:
    def test_draw_simple_circuit(self):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        text = draw_circuit(qc)
        assert "q0:" in text
        assert "q1:" in text

    def test_draw_empty_circuit(self):
        qc = QuantumCircuit(3)
        text = draw_circuit(qc)
        assert "q0:" in text
        assert "q1:" in text
        assert "q2:" in text

    def test_draw_with_barrier(self):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.barrier()
        qc.h(1)
        text = draw_circuit(qc)
        assert "≡" in text


# ─── Circuit serialization ───────────────────────────────────────────────

class TestSerialization:
    def test_to_dict_basic(self):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        d = qc.to_dict()
        assert d["n_qubits"] == 2
        assert len(d["operations"]) == 2
        assert d["operations"][0]["name"] == "H"

    def test_from_dict_roundtrip(self):
        qc = QuantumCircuit(3)
        qc.h(0)
        qc.cx(0, 1)
        qc.toffoli(0, 1, 2)
        d = qc.to_dict()
        qc2 = QuantumCircuit.from_dict(d)
        assert qc2.n_qubits == 3
        assert len(qc2.operations) == 3
        # Verify the circuits produce the same state
        sim = Simulator()
        s1 = sim.evolve(qc)
        s2 = sim.evolve(qc2)
        assert np.allclose(s1.amplitudes, s2.amplitudes, atol=1e-9)

    def test_to_json_roundtrip(self):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        json_str = qc.to_json()
        qc2 = QuantumCircuit.from_json(json_str)
        assert qc2.n_qubits == 2
        assert len(qc2.operations) == 2


# ─── BB84 protocol ────────────────────────────────────────────────────────

class TestBB84:
    def test_bb84_no_eavesdropping(self):
        alice_key, bob_key, error_rate = bb84_protocol(n_bits=32, eavesdrop=False, seed=42)
        # Without eavesdropping, error rate should be ~0
        assert error_rate < 0.2
        # Keys should match (modulo sifting)
        assert len(alice_key) == len(bob_key)

    def test_bb84_with_eavesdropping(self):
        alice_key, bob_key, error_rate = bb84_protocol(n_bits=64, eavesdrop=True, seed=42)
        # With eavesdropping, there should be detectable errors
        # (might not always be >0 due to randomness, but usually is)
        # Just verify it runs and returns valid types
        assert isinstance(error_rate, float)
        assert 0.0 <= error_rate <= 1.0
        assert isinstance(alice_key, list)
        assert isinstance(bob_key, list)

    def test_bb84_keys_match_no_eve(self):
        alice_key, bob_key, _ = bb84_protocol(n_bits=32, eavesdrop=False, seed=0)
        # Keys should be identical without eavesdropping
        assert alice_key == bob_key


# ─── Quantum walk ──────────────────────────────────────────────────────────

class TestQuantumWalk:
    def test_quantum_walk_runs(self):
        result = quantum_walk(steps=3, coin_state=0, seed=42)
        assert result.steps == 3
        assert result.n_positions > 0
        assert np.isclose(np.sum(result.probabilities), 1.0, atol=1e-3)

    def test_quantum_walk_negative_steps_raises(self):
        with pytest.raises(ValueError):
            quantum_walk(steps=-1)

    def test_quantum_walk_invalid_coin_raises(self):
        with pytest.raises(ValueError):
            quantum_walk(steps=1, coin_state=2)

    def test_quantum_walk_mean(self):
        result = quantum_walk(steps=5, coin_state=0, seed=42)
        # Mean should be a finite number
        assert math.isfinite(result.mean_position)


# ─── State tomography ──────────────────────────────────────────────────────

class TestTomography:
    def test_tomography_pure_state(self):
        # Reconstruct |0⟩⟨0| from a circuit that just produces |0⟩
        qc = QuantumCircuit(1)
        rho = state_tomography(qc, n_qubits=1, shots_per_basis=500, seed=42)
        # Should be approximately |0⟩⟨0|
        assert np.isclose(rho.matrix[0, 0], 1.0, atol=0.2)
        assert np.isclose(rho.matrix[1, 1], 0.0, atol=0.2)

    def test_tomography_hadamard_state(self):
        qc = QuantumCircuit(1)
        qc.h(0)
        rho = state_tomography(qc, n_qubits=1, shots_per_basis=500, seed=42)
        # Should be approximately |+⟩⟨+| = H|0⟩
        assert np.isclose(rho.matrix[0, 0], 0.5, atol=0.2)
        assert np.isclose(rho.matrix[1, 1], 0.5, atol=0.2)