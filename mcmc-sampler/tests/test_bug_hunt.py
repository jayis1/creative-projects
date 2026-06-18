"""Bug hunt tests — verify bugs before and after fixing."""

import math
import numpy as np
import pytest

from mcmc_sampler import (
    Mixture,
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


# --- Bug 1: Mixture with all -inf components returns NaN, should return -inf --- #


def test_mixture_all_inf_components():
    """When all component log_pdfs are -inf, the mixture should return -inf,
    not NaN."""
    # Components that are 0 at x=0.5 but -inf elsewhere
    from mcmc_sampler import Uniform
    u1 = Uniform(0, 0.1)
    u2 = Uniform(0.9, 1.0)
    m = Mixture([u1, u2])
    # x=0.5 is outside both supports
    result = m.log_pdf([0.5])
    assert math.isfinite(result) or result == -math.inf, \
        f"Expected finite or -inf, got {result}"
    # The bug: this returns NaN


# --- Bug 2: Slice sampler infinite loop on pathological target --- #


def test_slice_sampler_max_shrinkage():
    """Slice sampler shrinkage loop should have a max iteration limit to
    prevent infinite loops on pathological targets."""
    # A target with a very sharp peak can cause many shrinkage iterations
    def sharp_logpdf(x):
        v = float(x[0]) if hasattr(x, '__len__') else float(x)
        return -abs(v) * 1000  # very sharp Laplace

    target = Target(sharp_logpdf, dim=1, name="sharp")
    sampler = SliceSampler(target, width=10.0, rng=np.random.default_rng(42))
    # This should terminate in reasonable time, not hang
    trace = sampler.sample([0.0], n_samples=100, burn=50)
    assert len(trace) == 100


# --- Bug 3: ESS returns float('inf') for constant chain --- #


def test_ess_constant_chain():
    """ESS of a constant chain should be n (or close), not crash."""
    x = np.ones(1000)
    ess = effective_sample_size(x)
    assert math.isfinite(ess)
    assert ess > 0


# --- Bug 4: gelman_rubin with single-element chains --- #


def test_rhat_single_element_chains():
    """R-hat with chains of length 1 should raise ValueError (can't compute
    within-chain variance with ddof=1 on a single element)."""
    chains = [[1.0], [2.0], [3.0]]
    with pytest.raises(ValueError, match="at least 2 samples"):
        gelman_rubin(chains)


# --- Bug 5: HDI with prob very close to 1 --- #


def test_hdi_prob_close_to_1():
    """HDI with prob close to 1 should still work."""
    x = np.random.default_rng(0).normal(size=100)
    lo, hi = highest_density_interval(x, prob=0.99)
    assert lo < hi
    assert math.isfinite(lo) and math.isfinite(hi)


# --- Bug 6: autocorrelation with constant input --- #


def test_autocorrelation_constant():
    """ACF of constant input should be all 1.0, not NaN."""
    x = np.ones(100)
    acf = autocorrelation(x, max_lag=5)
    assert np.all(np.isfinite(acf))
    assert acf[0] == pytest.approx(1.0)


# --- Bug 7: MCSE with constant input --- #


def test_mcse_constant():
    """MCSE of constant input should be 0, not NaN."""
    x = np.ones(100)
    result = monte_carlo_error(x)
    assert math.isfinite(result)
    assert result == pytest.approx(0.0)