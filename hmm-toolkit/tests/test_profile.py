"""Tests for Profile HMM (biological sequence alignment)."""

import os
import sys
import math

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hmm.profile import ProfileHMM, build_profile_hmm


class TestProfileHMMConstruction:
    def test_basic_construction(self):
        alignment = ["ATGC", "ATGC", "ATGC"]
        ph = build_profile_hmm(alignment, list("ACGT"), threshold=0.5)
        assert ph.n_matches == 4
        assert ph.n_states == 12  # 3 * 4
        assert "M0" in ph.state_labels

    def test_empty_alignment(self):
        with pytest.raises(ValueError):
            build_profile_hmm([], list("ACGT"))

    def test_duplicate_alphabet(self):
        with pytest.raises(ValueError, match="Duplicate"):
            ProfileHMM(["A", "A"], [0])

    def test_match_column_identification(self):
        alignment = [
            "AT-G",
            "A-AG",
            "AT-G",
        ]
        # column 0: all A → match
        # column 1: T, -, T → 2/3 non-gap → match
        # column 2: -, A, - → 1/3 → insert
        # column 3: all G → match
        cols = ProfileHMM.identify_match_columns(alignment, threshold=0.5)
        assert 0 in cols
        assert 1 in cols
        assert 2 not in cols
        assert 3 in cols

    def test_threshold(self):
        alignment = ["AA", "A-"]
        # col 0: all A → match; col 1: 50% → match at threshold=0.5
        cols = ProfileHMM.identify_match_columns(alignment, threshold=0.5)
        assert cols == [0, 1]
        cols_strict = ProfileHMM.identify_match_columns(alignment, threshold=0.6)
        assert cols_strict == [0]


class TestProfileHMMAlgorithms:
    def test_forward_returns_valid(self):
        alignment = ["ATGC", "ATGC", "ATGC"]
        ph = build_profile_hmm(alignment, list("ACGT"))
        ll = ph.log_likelihood("ATGC")
        assert ll != -math.inf
        assert ll < 0

    def test_matching_sequence_scores_higher(self):
        alignment = ["ATGC", "ATGC", "ATGC", "ATGC"]
        ph = build_profile_hmm(alignment, list("ACGT"))
        ll_match = ph.log_likelihood("ATGC")
        ll_mismatch = ph.log_likelihood("TTTT")
        # A matching sequence should have higher log-likelihood
        assert ll_match > ll_mismatch

    def test_log_odds_score(self):
        alignment = ["ATGC", "ATGC", "ATGC"]
        ph = build_profile_hmm(alignment, list("ACGT"))
        score = ph.log_odds_score("ATGC")
        # A sequence matching the profile should have positive log-odds
        assert score > 0

    def test_viterbi_path(self):
        alignment = ["ATGC", "ATGC", "ATGC"]
        ph = build_profile_hmm(alignment, list("ACGT"))
        path, logp = ph.viterbi("ATGC")
        assert len(path) == len("ATGC")
        assert logp != -math.inf

    def test_viterbi_all_match_states(self):
        alignment = ["ATGC", "ATGC", "ATGC"]
        ph = build_profile_hmm(alignment, list("ACGT"))
        path, _ = ph.viterbi("ATGC")
        # All states should be match states (M0, M1, M2, M3)
        for i, state_idx in enumerate(path):
            label = ph.state_labels[state_idx]
            assert label == f"M{i}", f"Expected M{i}, got {label}"

    def test_unknown_symbol_raises(self):
        alignment = ["ATGC", "ATGC"]
        ph = build_profile_hmm(alignment, list("ACGT"))
        with pytest.raises(KeyError):
            ph.log_likelihood("ATGN")


class TestProfileHmmWithGaps:
    def test_alignment_with_gaps(self):
        alignment = [
            "AT-GC",
            "A--GC",
            "AT-GC",
        ]
        ph = build_profile_hmm(alignment, list("ACGT"), threshold=0.5)
        # Should have match states for columns 0, 1, 3, 4 (col 2 mostly gaps)
        assert ph.n_matches >= 3

    def test_different_sequences_different_scores(self):
        alignment = ["ATGCAT", "ATGCAT", "ATGCAT", "ATGCAT"]
        ph = build_profile_hmm(alignment, list("ACGT"))
        s1 = ph.log_odds_score("ATGCAT")
        s2 = ph.log_odds_score("CCCCCC")
        # The matching sequence should score higher
        assert s1 > s2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])