"""Basic tests for hmm-toolkit Phase 1."""

import math
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hmm import HMM, forward, backward, viterbi, baum_welch, generate_sequence
from hmm import posterior_decode, save_hmm, load_hmm, hmm_to_dict, hmm_from_dict
import random


# --- Fixtures ---

def casino_hmm():
    return HMM(
        states=["F", "L"],
        symbols=["1", "2", "3", "4", "5", "6"],
        A=[[0.95, 0.05], [0.10, 0.90]],
        B=[[1/6]*6, [0.10, 0.10, 0.10, 0.10, 0.10, 0.50]],
        pi=[0.5, 0.5],
    )


# --- HMM construction & validation ---

class TestHMMConstruction:
    def test_valid_construction(self):
        hmm = casino_hmm()
        assert hmm.n_states == 2
        assert hmm.n_symbols == 6
        assert len(hmm.A) == 2 and len(hmm.A[0]) == 2
        assert len(hmm.B) == 2 and len(hmm.B[0]) == 6

    def test_rows_normalised(self):
        hmm = casino_hmm()
        for row in hmm.A:
            assert abs(sum(row) - 1.0) < 1e-9
        for row in hmm.B:
            assert abs(sum(row) - 1.0) < 1e-9
        assert abs(sum(hmm.pi) - 1.0) < 1e-9

    def test_normalisation_applied(self):
        hmm = HMM(["a", "b"], ["x", "y"],
                  A=[[2, 2], [3, 1]], B=[[1, 3], [2, 2]], pi=[3, 1])
        assert abs(hmm.A[0][0] - 0.5) < 1e-9
        assert abs(hmm.B[0][1] - 0.75) < 1e-9
        assert abs(hmm.pi[0] - 0.75) < 1e-9

    def test_invalid_A_shape(self):
        with pytest.raises(ValueError):
            HMM(["a", "b"], ["x"], A=[[0.5, 0.5]], B=[[1.0]], pi=[0.5, 0.5])

    def test_invalid_B_shape(self):
        with pytest.raises(ValueError):
            HMM(["a"], ["x", "y"], A=[[1.0]], B=[[0.5]], pi=[1.0])

    def test_negative_probability(self):
        with pytest.raises(ValueError):
            HMM(["a", "b"], ["x"], A=[[-0.1, 1.1], [0.5, 0.5]],
                B=[[1.0], [1.0]], pi=[0.5, 0.5])

    def test_uniform_factory(self):
        hmm = HMM.uniform(["a", "b", "c"], ["x", "y"])
        assert all(abs(v - 1/3) < 1e-9 for v in hmm.pi)
        assert all(abs(v - 0.5) < 1e-9 for v in hmm.B[0])

    def test_random_factory(self):
        hmm = HMM.random(["a", "b"], ["x", "y", "z"], seed=42)
        assert hmm.n_states == 2 and hmm.n_symbols == 3
        for row in hmm.A:
            assert abs(sum(row) - 1.0) < 1e-9
        for row in hmm.B:
            assert abs(sum(row) - 1.0) < 1e-9


# --- Forward / Backward ---

class TestForwardBackward:
    def test_forward_log_likelihood_positive(self):
        hmm = casino_hmm()
        obs = hmm.observation_sequence(["1", "2", "3", "4", "5", "6"])
        _, _, ll = forward(hmm, obs)
        assert ll != -math.inf
        assert ll < 0  # log-prob is negative

    def test_forward_short_sequence(self):
        hmm = casino_hmm()
        obs = [0]
        _, scales, ll = forward(hmm, obs)
        expected = math.log(0.5 * (1/6) + 0.5 * 0.10)
        assert abs(ll - expected) < 1e-9

    def test_forward_empty(self):
        hmm = casino_hmm()
        _, _, ll = forward(hmm, [])
        assert ll == 0.0

    def test_forward_impossible_observation(self):
        # B with all-zero for one symbol → impossible
        hmm = HMM(["a"], ["x", "y"], A=[[1.0]], B=[[1.0, 0.0]], pi=[1.0])
        _, _, ll = forward(hmm, [1])
        assert ll == -math.inf

    def test_backward_shape(self):
        hmm = casino_hmm()
        obs = [0, 1, 2, 3, 4, 5]
        beta = backward(hmm, obs)
        assert len(beta) == 6
        assert all(len(row) == 2 for row in beta)

    def test_forward_backward_consistency(self):
        """gamma[t] computed from alpha*beta (normalised) should be a valid distribution."""
        hmm = casino_hmm()
        obs = [0, 1, 2, 3, 4, 5, 0, 1, 2, 3]
        alpha, scales, ll = forward(hmm, obs)
        beta = backward(hmm, obs, scales)
        for t in range(len(obs)):
            products = [alpha[t][i] * beta[t][i] for i in range(hmm.n_states)]
            s = sum(products)
            # normalised posteriors should each be in [0, 1] and sum to 1
            posteriors = [p / s for p in products]
            assert abs(sum(posteriors) - 1.0) < 1e-9
            assert all(0.0 <= p <= 1.0 + 1e-9 for p in posteriors)


# --- Viterbi ---

class TestViterbi:
    def test_viterbi_returns_path(self):
        hmm = casino_hmm()
        obs = [0, 1, 2, 3, 4, 5, 0, 1, 2, 3]
        path, logp = viterbi(hmm, obs)
        assert len(path) == 10
        assert all(0 <= s < 2 for s in path)
        assert logp < 0

    def test_viterbi_empty(self):
        hmm = casino_hmm()
        path, logp = viterbi(hmm, [])
        assert path == []
        assert logp == 0.0

    def test_viterbi_all_loaded(self):
        """All 6s should prefer loaded state."""
        hmm = casino_hmm()
        obs = [5] * 10  # symbol "6"
        path, _ = viterbi(hmm, obs)
        assert all(s == 1 for s in path)  # state "L"


# --- Baum-Welch ---

class TestBaumWelch:
    def test_baum_welch_improves_likelihood(self):
        hmm_true = casino_hmm()
        rng = random.Random(42)
        _, obs_syms = generate_sequence(hmm_true, length=200, rng=rng)
        obs = hmm_true.observation_sequence(obs_syms)

        fresh = HMM.random(["F", "L"], ["1", "2", "3", "4", "5", "6"], seed=7)
        _, _, ll_before = forward(fresh, obs)
        final_ll, iters = baum_welch(fresh, obs, iterations=100)
        assert final_ll >= ll_before
        assert iters >= 1

    def test_baum_welch_too_short(self):
        hmm = casino_hmm()
        with pytest.raises(ValueError):
            baum_welch(hmm, [0])

    def test_baum_welch_preserves_valid_probabilities(self):
        hmm = casino_hmm()
        obs = [0, 1, 2, 3, 4, 5] * 5
        baum_welch(hmm, obs, iterations=10)
        for row in hmm.A:
            assert abs(sum(row) - 1.0) < 1e-6
        for row in hmm.B:
            assert abs(sum(row) - 1.0) < 1e-6


# --- Sequence generation ---

class TestGeneration:
    def test_generate_correct_length(self):
        hmm = casino_hmm()
        states, obs = generate_sequence(hmm, length=50, seed=1)
        assert len(states) == 50
        assert len(obs) == 50

    def test_generate_zero(self):
        hmm = casino_hmm()
        states, obs = generate_sequence(hmm, length=0)
        assert states == [] and obs == []

    def test_generate_negative_raises(self):
        hmm = casino_hmm()
        with pytest.raises(ValueError):
            generate_sequence(hmm, length=-1)

    def test_generated_symbols_valid(self):
        hmm = casino_hmm()
        _, obs = generate_sequence(hmm, length=20, seed=2)
        assert all(s in hmm.symbols for s in obs)


# --- Serialization ---

class TestSerialization:
    def test_roundtrip(self):
        hmm = casino_hmm()
        d = hmm_to_dict(hmm)
        hmm2 = hmm_from_dict(d)
        assert hmm2.states == hmm.states
        assert hmm2.symbols == hmm.symbols
        assert hmm.parameters_almost_equal(hmm2)

    def test_save_load(self):
        hmm = casino_hmm()
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            path = f.name
        save_hmm(hmm, path)
        loaded = load_hmm(path)
        assert loaded.parameters_almost_equal(hmm)
        os.unlink(path)


# --- Posterior decode ---

class TestPosteriorDecode:
    def test_posterior_path_length(self):
        hmm = casino_hmm()
        obs = [0, 1, 2, 3, 4, 5]
        path, gamma = posterior_decode(hmm, obs)
        assert len(path) == 6
        assert len(gamma) == 6
        assert all(abs(sum(row) - 1.0) < 0.1 for row in gamma)


# --- Analysis utilities (Phase 2) ---

class TestAnalysis:
    def test_sequence_log_likelihood(self):
        from hmm import sequence_log_likelihood
        hmm = casino_hmm()
        obs = [0, 1, 2]
        ll = sequence_log_likelihood(hmm, obs)
        assert ll < 0 and ll != -math.inf

    def test_classify_sequence(self):
        from hmm import classify_sequence
        # fair model: starts in fair state, uniform emissions
        hmm_fair = HMM(["F", "L"], ["1", "2", "3", "4", "5", "6"],
                       [[1, 0], [0, 1]], [[1/6]*6, [1/6]*6], [1, 0])
        # loaded model: starts in loaded state, 6-biased emissions
        hmm_loaded = HMM(["F", "L"], ["1", "2", "3", "4", "5", "6"],
                         [[1, 0], [0, 1]], [[0.01]*5 + [0.95], [1/6]*6], [1, 0])
        # all 6s should prefer the loaded model
        obs = [5] * 10
        idx, name, ll = classify_sequence([hmm_fair, hmm_loaded], obs)
        assert idx == 1  # loaded model

    def test_state_entropy(self):
        from hmm import state_entropy
        hmm = casino_hmm()
        obs = [0, 1, 2, 3, 4, 5]
        entropies = state_entropy(hmm, obs)
        assert len(entropies) == 6
        assert all(e >= 0 for e in entropies)

    def test_symmetric_kl(self):
        from hmm import symmetric_kl
        hmm_a = casino_hmm()
        hmm_b = HMM(["F", "L"], ["1", "2", "3", "4", "5", "6"],
                    [[0.5, 0.5], [0.5, 0.5]], [[1/6]*6, [1/6]*6], [0.5, 0.5])
        obs = [0, 1, 2, 3, 4, 5]
        kl = symmetric_kl(hmm_a, hmm_b, obs)
        assert kl >= 0

    def test_symmetric_kl_different_symbols_raises(self):
        from hmm import symmetric_kl
        hmm_a = HMM(["a"], ["x"], [[1.0]], [[1.0]], [1.0])
        hmm_b = HMM(["a"], ["y"], [[1.0]], [[1.0]], [1.0])
        with pytest.raises(ValueError):
            symmetric_kl(hmm_a, hmm_b, [0])

    def test_state_durations(self):
        from hmm import state_durations
        path = ["Sunny", "Sunny", "Rainy", "Rainy", "Rainy", "Cloudy"]
        durations = state_durations(path)
        assert durations == [("Sunny", 2), ("Rainy", 3), ("Cloudy", 1)]

    def test_state_durations_empty(self):
        from hmm import state_durations
        assert state_durations([]) == []

    def test_expected_state_dwell_time(self):
        from hmm import expected_state_dwell_time
        hmm = HMM(["a", "b"], ["x"],
                  [[0.75, 0.25], [0.5, 0.5]], [[1.0], [1.0]], [0.5, 0.5])
        dwell = expected_state_dwell_time(hmm)
        assert abs(dwell[0] - 4.0) < 1e-9  # 1 / (1 - 0.75) = 4
        assert abs(dwell[1] - 2.0) < 1e-9  # 1 / (1 - 0.5) = 2

    def test_expected_state_dwell_time_absorbing(self):
        from hmm import expected_state_dwell_time
        hmm = HMM(["a", "b"], ["x"],
                  [[1.0, 0.0], [0.5, 0.5]], [[1.0], [1.0]], [1.0, 0.0])
        dwell = expected_state_dwell_time(hmm)
        assert dwell[0] == math.inf


# --- Multi-sequence Baum-Welch (Phase 2) ---

class TestBaumWelchMulti:
    def test_multi_improves_likelihood(self):
        from hmm import baum_welch_multi
        hmm_true = casino_hmm()
        rng = random.Random(42)
        obs_list = []
        for _ in range(5):
            _, obs_syms = generate_sequence(hmm_true, length=50, rng=rng)
            obs_list.append(hmm_true.observation_sequence(obs_syms))
        fresh = HMM.random(["F", "L"], ["1", "2", "3", "4", "5", "6"], seed=7)
        _, _, ll_before = forward(fresh, obs_list[0])
        final_ll, iters = baum_welch_multi(fresh, obs_list, iterations=50)
        _, _, ll_after = forward(fresh, obs_list[0])
        assert ll_after >= ll_before

    def test_multi_empty_raises(self):
        from hmm import baum_welch_multi
        hmm = casino_hmm()
        with pytest.raises(ValueError):
            baum_welch_multi(hmm, [])

    def test_multi_short_raises(self):
        from hmm import baum_welch_multi
        hmm = casino_hmm()
        with pytest.raises(ValueError):
            baum_welch_multi(hmm, [[0]])

    def test_multi_preserves_valid_probabilities(self):
        from hmm import baum_welch_multi
        hmm = casino_hmm()
        obs_list = [[0, 1, 2, 3, 4, 5] * 3, [5, 4, 3, 2, 1, 0] * 3]
        baum_welch_multi(hmm, obs_list, iterations=10)
        for row in hmm.A:
            assert abs(sum(row) - 1.0) < 1e-6
        for row in hmm.B:
            assert abs(sum(row) - 1.0) < 1e-6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])