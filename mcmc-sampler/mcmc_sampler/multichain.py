"""
Multi-chain MCMC runner — run several independent chains in parallel and
compute convergence diagnostics across them.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

import numpy as np

from .diagnostics import effective_sample_size, gelman_rubin, monte_carlo_error
from .samplers import _BaseSampler
from .trace import Trace


class MultiChainResult:
    """Holds results from multiple MCMC chains."""

    def __init__(self, chains: List[Trace]):
        self.chains = chains
        self.n_chains = len(chains)
        self.dim = chains[0].dim if chains else 0

    def rhat(self) -> List[float]:
        """R-hat for each parameter dimension."""
        results = []
        for j in range(self.dim):
            cols = [c.samples[:, j] for c in self.chains]
            results.append(gelman_rubin(cols))
        return results

    def ess_total(self) -> List[float]:
        """Pooled ESS (sum of per-chain ESS) for each dimension."""
        results = []
        for j in range(self.dim):
            total = sum(effective_sample_size(c.samples[:, j]) for c in self.chains)
            results.append(total)
        return results

    def combined_trace(self) -> Trace:
        """Concatenate all chains into a single Trace."""
        all_samples = np.vstack([c.samples for c in self.chains])
        names = self.chains[0].names
        log_prob = None
        if all(c.log_prob is not None for c in self.chains):
            log_prob = np.concatenate([c.log_prob for c in self.chains])
        return Trace(all_samples, log_prob=log_prob, names=names)

    def summary(self) -> dict:
        """Overall convergence summary."""
        rhat = self.rhat()
        ess = self.ess_total()
        combined = self.combined_trace()
        return {
            "n_chains": self.n_chains,
            "dim": self.dim,
            "rhat": rhat,
            "all_converged": all(r < 1.01 for r in rhat),
            "ess_pooled": ess,
            "combined_mean": combined.mean().tolist(),
            "combined_std": combined.std().tolist(),
        }


def run_chains(sampler_factory, x0_list: Sequence[Sequence[float]],
               n_samples: int = 5000, burn: int = 1000, thin: int = 1) -> MultiChainResult:
    """Run multiple independent chains.

    Parameters
    ----------
    sampler_factory : callable
        ``sampler_factory(seed) -> _BaseSampler`` — called once per chain
        with a unique integer seed.
    x0_list : list of initial points (one per chain)
    n_samples, burn, thin : passed to each chain's ``sample()``.
    """
    if len(x0_list) < 2:
        raise ValueError("need at least 2 chains")
    chains = []
    for i, x0 in enumerate(x0_list):
        sampler = sampler_factory(seed=i)
        trace = sampler.sample(x0, n_samples=n_samples, burn=burn, thin=thin)
        chains.append(trace)
    return MultiChainResult(chains)