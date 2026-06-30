"""Tests for Gaussian HMM (continuous emissions)."""

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hmm.gaussian import GaussianHMM, random_gaussian_hmm, _gaussian_log_pdf
from hmm._linalg import det, inv, add_ridge, matmul


class TestLinalg:
    def test_det_2x2(self):
        assert abs(det([[4, 2], [1, 3]]) - 10) < 1e-9

    def test_det_3x3(self):
        m = [[1, 2, 3], [4, 5, 6], [7, 8, 10]]
        # det = -3
        assert abs(det(m) - (-3)) < 1e-9

    def test_det_singular(self):
        assert det([[1, 2], [2, 4]]) == 0.0

    def test_inv_2x2(self):
        m = [[4, 2], [1, 3]]
        result = inv(m)
        # m * inv = I
        prod = matmul(m, result)
        assert abs(prod[0][0] - 1) < 1e-9
        assert abs(prod[1][1] - 1) < 1e-9
        assert abs(prod[0][1]) < 1e-9
        assert abs(prod[1][0]) < 1e-9

    def test_inv_singular_raises(self):
        with pytest.raises(ValueError):
            inv([[1, 2], [2, 4]])

    def test_add_ridge(self):
        m = [[1, 0], [0, 1]]
        r = add_ridge(m, 0.5)
        assert r[0][0] == 1.5
        assert r[1][1] == 1.5
        assert r[0][1] == 0

    def test_matmul_identity(self):
        m = [[1, 2], [3, 4]]
        I = [[1, 0], [0, 1]]
        prod = matmul(m, I)
        assert prod == m


class TestGaussianLogPdf:
    def test_univariate_standard(self):
        # N(0, 1): log pdf at 0 = -0.5 * log(2*pi)
        lp = _gaussian_log_pdf([0.0], [0.0], [[1.0]])
        expected = -0.5 * math.log(2 * math.pi)
        assert abs(lp - expected) < 1e-9

    def test_bivariate(self):
        # 2D standard normal at origin
        lp = _gaussian_log_pdf([0.0, 0.0], [0.0, 0.0], [[1.0, 0.0], [0.0, 1.0]])
        expected = -math.log(2 * math.pi)
        assert abs(lp - expected) < 1e-9

    def test_degenerate_covariance(self):
        # Singular covariance should not crash
        lp = _gaussian_log_pdf([0.0], [0.0], [[0.0]])
        assert lp != -math.inf  # should recover with ridge


class TestGaussianHMMConstruction:
    def test_valid(self):
        ghmm = random_gaussian_hmm(["s0", "s1"], 2, seed=42)
        assert ghmm.n_states == 2
        assert ghmm.n_dim == 2
        assert len(ghmm.means) == 2
        assert len(ghmm.covs) == 2

    def test_empty_states(self):
        with pytest.raises(ValueError, match="at least one state"):
            GaussianHMM([], 1, [], [], [], [])

    def test_duplicate_states(self):
        with pytest.raises(ValueError, match="Duplicate"):
            GaussianHMM(["a", "a"], 1, [[0.5, 0.5], [0.5, 0.5]],
                        [[0.0], [0.0]], [[[1.0]], [[1.0]]], [0.5, 0.5])

    def test_wrong_dim(self):
        with pytest.raises(ValueError, match="n_dim"):
            GaussianHMM(["a"], 0, [[1.0]], [[0.0]], [[[1.0]]], [1.0])

    def test_mean_dim_mismatch(self):
        with pytest.raises(ValueError, match="mean"):
            GaussianHMM(["a"], 2, [[1.0]], [[0.0, 0.0, 0.0]], [[[1.0, 0], [0, 1]]], [1.0])


class TestGaussianForwardViterbi:
    def test_forward_returns_valid(self):
        ghmm = random_gaussian_hmm(["s0", "s1"], 1, seed=42)
        obs = [[0.0], [0.1], [0.2]]
        alpha, scales, ll = ghmm.forward(obs)
        assert len(alpha) == 3
        assert len(scales) == 3
        assert ll != -math.inf

    def test_forward_empty(self):
        ghmm = random_gaussian_hmm(["s0"], 1, seed=42)
        _, _, ll = ghmm.forward([])
        assert ll == 0.0

    def test_viterbi_path_length(self):
        ghmm = random_gaussian_hmm(["s0", "s1"], 2, seed=42)
        obs = [[1.0, 2.0], [1.1, 2.1], [0.9, 1.9]]
        path, logp = ghmm.viterbi(obs)
        assert len(path) == 3
        assert all(0 <= s < 2 for s in path)

    def test_viterbi_empty(self):
        ghmm = random_gaussian_hmm(["s0"], 1, seed=42)
        path, logp = ghmm.viterbi([])
        assert path == []
        assert logp == 0.0

    def test_backward_shape(self):
        ghmm = random_gaussian_hmm(["s0", "s1"], 1, seed=42)
        obs = [[0.0], [1.0], [2.0]]
        beta = ghmm.backward(obs)
        assert len(beta) == 3
        assert all(len(r) == 2 for r in beta)


class TestGaussianBaumWelch:
    def test_baum_welch_improves(self):
        ghmm = random_gaussian_hmm(["s0", "s1"], 1, seed=10)
        obs = [[0.1], [0.2], [0.15], [5.0], [5.1], [4.9], [0.1], [5.0]]
        _, _, ll_before = ghmm.forward(obs)
        final_ll, iters = ghmm.baum_welch(obs, iterations=20)
        assert final_ll >= ll_before
        assert iters >= 1

    def test_baum_welch_too_short(self):
        ghmm = random_gaussian_hmm(["s0"], 1, seed=42)
        with pytest.raises(ValueError, match="at least 2"):
            ghmm.baum_welch([[0.0]])

    def test_baum_welch_separates_means(self):
        """Training on two clusters should separate the means."""
        ghmm = random_gaussian_hmm(["s0", "s1"], 1, seed=10)
        obs = [[0.0], [0.1], [-0.1], [0.05], [10.0], [10.1], [9.9], [10.05]]
        ghmm.baum_welch(obs, iterations=50)
        means = sorted(m[0] for m in ghmm.means)
        # The two means should be well separated
        assert abs(means[1] - means[0]) > 5.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])