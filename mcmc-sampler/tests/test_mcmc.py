"""Basic smoke tests — verify samplers converge to known distributions."""

import numpy as np
import pytest

from mcmc_sampler import (
    AdaptiveMetropolis,
    Beta as BetaDist,
    Exponential,
    GibbsSampler,
    HamiltonianMC,
    MetropolisHastings,
    Mixture,
    MultivariateNormal,
    Normal,
    SliceSampler,
    Target,
    Trace,
    autocorrelation,
    effective_sample_size,
    gelman_rubin,
    highest_density_interval,
    monte_carlo_error,
)


# ----------------------- distributions ----------------------- #


def test_normal_log_pdf():
    d = Normal(0, 1)
    assert d.log_pdf([0.0]) == pytest.approx(-0.5 * np.log(2 * np.pi))


def test_mvn_log_pdf():
    d = MultivariateNormal([0, 0], [[1, 0], [0, 1]])
    assert d.log_pdf([0, 0]) == pytest.approx(-np.log(2 * np.pi))


def test_beta_outside_support():
    d = BetaDist(2, 2)
    assert d.log_pdf([0.0]) == -np.inf
    assert d.log_pdf([1.0]) == -np.inf


def test_mixture_log_pdf():
    m = Mixture([Normal(-3, 1), Normal(3, 1)])
    # at x=−3 should be dominated by first component
    assert m.log_pdf([-3.0]) > m.log_pdf([0.0])


# ----------------------- samplers ----------------------- #


def test_mh_converges_normal():
    target = Normal(5.0, 2.0)
    s = MetropolisHastings(target, proposal_std=2.0,
                           rng=np.random.default_rng(1))
    t = s.sample([0.0], n_samples=8000, burn=2000)
    assert abs(t.mean()[0] - 5.0) < 0.2
    assert abs(t.std()[0] - 2.0) < 0.3
    assert 0.1 < s.acceptance_rate < 0.8


def test_mh_multivariate():
    mu = [1.0, -2.0]
    cov = [[1.0, 0.8], [0.8, 2.0]]
    target = MultivariateNormal(mu, cov)
    s = MetropolisHastings(target, proposal_std=[0.6, 0.9],
                           rng=np.random.default_rng(2))
    t = s.sample([0.0, 0.0], n_samples=8000, burn=2000)
    assert abs(t.mean()[0] - 1.0) < 0.25
    assert abs(t.mean()[1] + 2.0) < 0.25


def test_adaptive_metropolis():
    target = Normal(3.0, 1.0)
    s = AdaptiveMetropolis(target, init_std=0.5,
                           rng=np.random.default_rng(3))
    t = s.sample([0.0], n_samples=6000, burn=2000)
    assert abs(t.mean()[0] - 3.0) < 0.3


def test_hmc_converges_normal():
    target = Normal(0.0, 1.0)
    s = HamiltonianMC(target, step_size=0.2, n_steps=15,
                      rng=np.random.default_rng(4))
    t = s.sample([0.0], n_samples=4000, burn=1000)
    assert abs(t.mean()[0]) < 0.2
    assert abs(t.std()[0] - 1.0) < 0.3


def test_slice_sampler_converges():
    target = Normal(1.0, 1.0)
    s = SliceSampler(target, width=2.0, rng=np.random.default_rng(5))
    t = s.sample([0.0], n_samples=4000, burn=1000)
    assert abs(t.mean()[0] - 1.0) < 0.2


def test_gibbs_bivariate_normal():
    """Gibbs sampler for bivariate normal with known conditionals."""
    target = MultivariateNormal([0, 0], [[1, 0.5], [0.5, 1]])

    def cond0(x, rng):
        return rng.normal(0.5 * x[1], np.sqrt(0.75))

    def cond1(x, rng):
        return rng.normal(0.5 * x[0], np.sqrt(0.75))

    s = GibbsSampler(target, [cond0, cond1], rng=np.random.default_rng(6))
    t = s.sample([0.0, 0.0], n_samples=5000, burn=1000)
    assert abs(t.mean()[0]) < 0.2
    assert abs(t.mean()[1]) < 0.2


# ----------------------- diagnostics ----------------------- #


def test_autocorrelation_shape():
    x = np.random.default_rng(0).normal(size=200)
    acf = autocorrelation(x, max_lag=10)
    assert acf.shape == (11,)
    assert acf[0] == pytest.approx(1.0)


def test_ess_iid():
    rng = np.random.default_rng(0)
    x = rng.normal(size=2000)
    ess = effective_sample_size(x)
    assert ess > 1500  # near n for iid


def test_rhat_converged():
    rng = np.random.default_rng(0)
    chains = [rng.normal(size=1000) for _ in range(4)]
    r = gelman_rubin(chains)
    assert r < 1.05


def test_rhat_not_converged():
    chains = [[0.0] * 100, [10.0] * 100]
    r = gelman_rubin(chains)
    assert r > 2.0


def test_hdi():
    x = np.linspace(-1, 1, 1000)
    lo, hi = highest_density_interval(x, prob=0.9)
    assert hi - lo == pytest.approx(1.8, abs=0.05)


def test_mcse():
    x = np.random.default_rng(0).normal(size=1000)
    assert monte_carlo_error(x) > 0


# ----------------------- trace ----------------------- #


def test_trace_json_roundtrip(tmp_path):
    t = Trace(np.random.default_rng(0).normal(size=(50, 2)),
              names=["a", "b"])
    p = tmp_path / "t.json"
    t.to_json(str(p))
    t2 = Trace.from_json(str(p))
    assert t2.names == ["a", "b"]
    assert t2.samples.shape == (50, 2)


def test_trace_summary():
    t = Trace(np.array([[1.0], [2.0], [3.0], [4.0]]), names=["x"])
    s = t.summary()
    assert "x" in s
    assert s["x"]["mean"] == pytest.approx(2.5)


# ----------------------- errors ----------------------- #


def test_bad_x0_raises():
    target = Exponential(1.0)
    s = MetropolisHastings(target, proposal_std=1.0)
    with pytest.raises(ValueError):
        s.sample([-1.0], n_samples=100)  # log_pdf = -inf at x0


def test_dim_mismatch_raises():
    target = Normal(0, 1)
    s = MetropolisHastings(target)
    with pytest.raises(ValueError):
        s.sample([0.0, 0.0], n_samples=100)