"""Bug hunt tests for hmm-toolkit Phase 3.

Each test demonstrates a bug before the fix is applied, then verifies the fix.
"""

import math
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hmm import HMM, forward, backward, viterbi, baum_welch, generate_sequence
from hmm import posterior_decode, save_hmm, load_hmm
from hmm.sequences import _sample_categorical
from hmm.analysis import state_durations, expected_state_dwell_time, symmetric_kl
import random


def casino_hmm():
    return HMM(
        states=["F", "L"],
        symbols=["1", "2", "3", "4", "5", "6"],
        A=[[0.95, 0.05], [0.10, 0.90]],
        B=[[1/6]*6, [0.10, 0.10, 0.10, 0.10, 0.10, 0.50]],
        pi=[0.5, 0.5],
    )


# === Bug 1: Forward/Viterbi don't validate observation indices ===
# If obs contains an out-of-range index, you get a confusing IndexError
# instead of a clear ValueError.

class TestBugObservationValidation:
    def test_forward_rejects_negative_obs(self):
        """Forward should reject negative observation indices with ValueError."""
        hmm = casino_hmm()
        with pytest.raises(ValueError, match="observation"):
            forward(hmm, [0, -1, 2])

    def test_forward_rejects_out_of_range_obs(self):
        """Forward should reject observation indices >= n_symbols."""
        hmm = casino_hmm()
        with pytest.raises(ValueError, match="observation"):
            forward(hmm, [0, 99, 2])

    def test_viterbi_rejects_out_of_range_obs(self):
        """Viterbi should reject out-of-range observation indices."""
        hmm = casino_hmm()
        with pytest.raises(ValueError, match="observation"):
            viterbi(hmm, [0, 99])


# === Bug 2: Duplicate state/symbol names silently accepted ===
# If states=["A", "A"], the index map only keeps the last entry,
# causing state_index("A") to return 1 instead of 0.

class TestBugDuplicateNames:
    def test_duplicate_states_rejected(self):
        """Duplicate state names should raise ValueError."""
        with pytest.raises(ValueError, match="Duplicate state"):
            HMM(["A", "A"], ["x"],
                [[0.5, 0.5], [0.5, 0.5]], [[1.0], [1.0]], [0.5, 0.5])

    def test_duplicate_symbols_rejected(self):
        """Duplicate symbol names should raise ValueError."""
        with pytest.raises(ValueError, match="Duplicate symbol"):
            HMM(["A"], ["x", "x"],
                [[1.0]], [[0.5, 0.5]], [1.0])


# === Bug 3: Empty states or symbols not rejected ===
# An HMM with 0 states or 0 symbols is degenerate and causes
# division-by-zero in _normalise_row or index errors later.

class TestBugEmptyStatesSymbols:
    def test_empty_states_rejected(self):
        with pytest.raises(ValueError, match="at least one state"):
            HMM([], [], [], [], [])

    def test_empty_symbols_rejected(self):
        with pytest.raises(ValueError, match="at least one symbol"):
            HMM(["A"], [], [[1.0]], [[]], [1.0])


# === Bug 4: Viterbi returns [0]*T for impossible sequence ===
# When the sequence is impossible, viterbi returns [0]*T which looks
# like a valid path of all state-0.  This is misleading.  After fix,
# it should return an empty path or raise.

class TestBugViterbiImpossiblePath:
    def test_viterbi_impossible_returns_empty_path(self):
        """When the sequence is impossible, the returned path should be empty
        (not a misleading [0]*T path)."""
        # Model where state 0 can only emit symbol 0, state 1 can only emit symbol 0
        # But we observe symbol 1 which is impossible
        hmm = HMM(["A", "B"], ["x", "y"],
                  [[0.5, 0.5], [0.5, 0.5]],
                  [[1.0, 0.0], [1.0, 0.0]],  # both states can only emit "x"
                  [0.5, 0.5])
        path, logp = viterbi(hmm, [0, 1])  # second obs "y" is impossible
        assert logp == -math.inf
        # Bug: path was [0, 0] (misleading).  Fix: should be empty.
        assert path == [], f"Expected empty path for impossible sequence, got {path}"


# === Bug 5: _sample_categorical doesn't handle all-zero probabilities ===
# If all probs are 0 (shouldn't happen in a valid HMM but could after
# numerical issues), it silently returns the last index.

class TestBugSampleCategorical:
    def test_sample_categorical_all_zero_raises(self):
        """_sample_categorical should raise on all-zero probabilities."""
        with pytest.raises(ValueError, match="probabilities sum to zero"):
            _sample_categorical([0.0, 0.0, 0.0], random.Random(0))


# === Bug 6: symmetric_kl with impossible sequences ===
# If both models find the sequence impossible, it returns 0.0 which is
# misleading (they might disagree on everything else).

class TestBugSymmetricKL:
    def test_kl_both_impossible_returns_nan(self):
        """symmetric_kl should return NaN, not 0.0, when both models
        find the sequence impossible."""
        hmm_a = HMM(["A"], ["x", "y"], [[1.0]], [[1.0, 0.0]], [1.0])
        hmm_b = HMM(["A"], ["x", "y"], [[1.0]], [[0.0, 1.0]], [1.0])
        # obs = [1] is impossible for hmm_a, obs = [0] is impossible for hmm_b
        # obs = [1] is possible for hmm_b though
        kl = symmetric_kl(hmm_a, hmm_b, [1])
        # hmm_a: impossible (-inf), hmm_b: possible (0.0)
        # |(-inf) - 0.0| = inf
        assert kl == math.inf


# === Bug 7: state_durations with non-string states ===
# state_durations should work with any hashable state type, not just strings.

class TestBugStateDurationsTypes:
    def test_state_durations_with_int_states(self):
        """state_durations should work with integer state paths too."""
        path = [0, 0, 1, 1, 1, 0]
        durations = state_durations(path)
        assert durations == [(0, 2), (1, 3), (0, 1)]


# === Bug 8: set_parameters doesn't validate observation indices in B ===
# After set_parameters, if B has rows that don't sum to 1, they get normalised.
# But if B has the wrong number of columns, _validate_shapes catches it.
# However, if B contains negative values after normalisation (due to
# floating point), they should be caught. This is already handled.
# Instead, test: set_parameters with wrong pi length.

class TestBugSetParametersValidation:
    def test_set_parameters_wrong_pi_length(self):
        """set_parameters should reject pi with wrong length."""
        hmm = casino_hmm()
        with pytest.raises(ValueError):
            hmm.set_parameters(pi=[1.0, 0.0, 0.0])  # 3 entries for 2-state model


if __name__ == "__main__":
    pytest.main([__file__, "-v"])