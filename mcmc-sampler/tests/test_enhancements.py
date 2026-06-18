"""Tests for Phase 2 enhancements: new distributions, HMC adaptation,
multi-chain, and ASCII visualization."""

import numpy as np
import pytest

from mcmc_sampler import (
    AdaptiveMetropolis,
    Gamma,
    HMCWithAdaptation,
    MetropolisHastings,
    MultiChainResult,
    Normal,
    StudentT,
    Trace,
    ascii_acf,
    ascii_histogram,
    ascii_trace,
    run_chains,
    visualize_trace,
)


# --- new distributions --- #


def test_gamma_log_pdf():
    d = Gamma(k=2.0, theta=1.0)
    # log_pdf(1) = (2-1)*ln(1) - 1/1 - (lgamma(2) + 2*ln(1)) = 0 - 1 - 0 = -1
    assert d.log_pdf([1.0]) == pytest.approx(-1.0, abs=1e-10)


def test_gamma_outside_support():
    d = Gamma(2, 1)
    assert d.log_pdf([0.0]) == -np.inf
    assert d.log_pdf([-1.0]) == -np.inf


def test_studentt_heavier_tails_than_normal():
    t = StudentT(nu=3, mu=0, sigma=1)
    n = Normal(0, 1)
    # far in the tail, Student-t should have higher density
    assert t.log_pdf([10.0]) > n.log_pdf([10.0])


def test_studentt_converges_to_normal():
    # as nu -> inf, Student-t approaches Normal
    t = StudentT(nu=1000, mu=0, sigma=1)
    n = Normal(0, 1)
    assert t.log_pdf([0.0]) == pytest.approx(n.log_pdf([0.0]), abs=0.01)


# --- HMC with adaptation --- #


def test_hmc_adapt_converges():
    target = Normal(2.0, 1.0)
    s = HMCWithAdaptation(target, n_steps=15, target_accept=0.65,
                          init_step_size=0.5, rng=np.random.default_rng(10))
    t = s.sample([0.0], n_samples=3000, burn=2000)
    assert abs(t.mean()[0] - 2.0) < 0.3
    # step size should have been adapted
    assert s.step_size != 0.5


def test_hmc_adapt_multivariate():
    mu = [1.0, -1.0]
    cov = [[1.0, 0.0], [0.0, 0.5]]
    from mcmc_sampler import MultivariateNormal
    target = MultivariateNormal(mu, cov)
    s = HMCWithAdaptation(target, n_steps=20, rng=np.random.default_rng(11))
    t = s.sample([0.0, 0.0], n_samples=3000, burn=2000)
    assert abs(t.mean()[0] - 1.0) < 0.35
    assert abs(t.mean()[1] + 1.0) < 0.35


# --- multi-chain --- #


def test_run_chains_converged():
    target = Normal(0, 1)

    def factory(seed):
        return MetropolisHastings(target, proposal_std=1.0,
                                  rng=np.random.default_rng(seed))
    x0s = [[-5.0], [0.0], [5.0]]
    result = run_chains(factory, x0s, n_samples=3000, burn=1000)
    assert result.n_chains == 3
    rhats = result.rhat()
    assert all(r < 1.05 for r in rhats)
    summary = result.summary()
    assert summary["all_converged"]


def test_run_chains_not_converged():
    target = Normal(0, 1)

    def factory(seed):
        return MetropolisHastings(target, proposal_std=0.01,
                                  rng=np.random.default_rng(seed))
    x0s = [[-10.0], [0.0], [10.0]]
    result = run_chains(factory, x0s, n_samples=500, burn=100)
    # tiny proposal + far apart starts => chains don't mix
    assert any(r > 1.1 for r in result.rhat())


def test_combined_trace():
    t1 = Trace(np.array([[1.0], [2.0]]), names=["x"])
    t2 = Trace(np.array([[3.0], [4.0]]), names=["x"])
    result = MultiChainResult([t1, t2])
    combined = result.combined_trace()
    assert combined.n_samples == 4
    assert combined.mean()[0] == pytest.approx(2.5)


def test_multichain_needs_two_chains():
    with pytest.raises(ValueError):
        run_chains(lambda seed: None, [[0.0]])


# --- ASCII visualization --- #


def test_ascii_histogram_output():
    rng = np.random.default_rng(0)
    text = ascii_histogram(rng.normal(size=500))
    assert "█" in text or "▄" in text or " " in text
    assert len(text) > 10


def test_ascii_trace_output():
    rng = np.random.default_rng(0)
    text = ascii_trace(rng.normal(size=200))
    assert "●" in text
    assert "iter" in text


def test_ascii_acf_output():
    rng = np.random.default_rng(0)
    text = ascii_acf(rng.normal(size=500), max_lag=10)
    assert "lag" in text
    assert len(text.split("\n")) == 11


def test_visualize_trace_all_params():
    t = Trace(np.random.default_rng(0).normal(size=(100, 2)), names=["a", "b"])
    text = visualize_trace(t)
    assert "=== a ===" in text
    assert "=== b ===" in text


def test_visualize_trace_single_param():
    t = Trace(np.random.default_rng(0).normal(size=(100, 2)), names=["a", "b"])
    text = visualize_trace(t, param=1)
    assert "=== b ===" in text
    assert "=== a ===" not in text