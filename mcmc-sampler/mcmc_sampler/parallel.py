"""
Parallel multi-chain MCMC runner using multiprocessing.

Run multiple independent chains in parallel across CPU cores, then
combine them for convergence diagnostics.
"""

from __future__ import annotations

import logging
import multiprocessing as mp
from typing import Callable, List, Optional, Sequence

import numpy as np

from .diagnostics import effective_sample_size, gelman_rubin, monte_carlo_error
from .samplers import _BaseSampler
from .trace import Trace

logger = logging.getLogger(__name__)


def _run_single_chain(args: tuple) -> Trace:
    """Worker function: create a sampler and run one chain.

    Parameters
    ----------
    args : (sampler_factory, seed, x0, n_samples, burn, thin)
    """
    sampler_factory, seed, x0, n_samples, burn, thin = args
    sampler = sampler_factory(seed)
    trace = sampler.sample(x0, n_samples=n_samples, burn=burn, thin=thin)
    return trace


def run_chains_parallel(sampler_factory: Callable[[int], _BaseSampler],
                        x0_list: Sequence[Sequence[float]],
                        n_samples: int = 5000, burn: int = 1000,
                        thin: int = 1, n_workers: Optional[int] = None
                        ) -> "ParallelChainResult":
    """Run multiple MCMC chains in parallel using multiprocessing.

    Parameters
    ----------
    sampler_factory : callable
        ``sampler_factory(seed) -> _BaseSampler``
    x0_list : list of initial points
    n_samples, burn, thin : sampling parameters
    n_workers : int, optional
        Number of parallel workers.  Defaults to min(n_chains, cpu_count).

    Returns
    -------
    ParallelChainResult
    """
    n_chains = len(x0_list)
    if n_chains < 2:
        raise ValueError("need at least 2 chains")
    if n_workers is None:
        n_workers = min(n_chains, mp.cpu_count())
    n_workers = min(n_workers, n_chains)

    args_list = [
        (sampler_factory, i, x0, n_samples, burn, thin)
        for i, x0 in enumerate(x0_list)
    ]

    logger.info("Running %d chains on %d workers (n_samples=%d, burn=%d)",
                n_chains, n_workers, n_samples, burn)

    # Use spawn context for safety (especially with numpy)
    ctx = mp.get_context("spawn")
    with ctx.Pool(n_workers) as pool:
        chains = pool.map(_run_single_chain, args_list)

    return ParallelChainResult(chains)


class ParallelChainResult:
    """Results from parallel multi-chain MCMC runs.

    Has the same interface as :class:`mcmc_sampler.multichain.MultiChainResult`
    but chains were run in parallel.
    """

    def __init__(self, chains: List[Trace]):
        self.chains = chains
        self.n_chains = len(chains)
        self.dim = chains[0].dim if chains else 0

    def rhat(self) -> List[float]:
        results = []
        for j in range(self.dim):
            cols = [c.samples[:, j] for c in self.chains]
            results.append(gelman_rubin(cols))
        return results

    def ess_total(self) -> List[float]:
        results = []
        for j in range(self.dim):
            total = sum(effective_sample_size(c.samples[:, j])
                        for c in self.chains)
            results.append(total)
        return results

    def combined_trace(self) -> Trace:
        all_samples = np.vstack([c.samples for c in self.chains])
        names = self.chains[0].names
        log_prob = None
        if all(c.log_prob is not None for c in self.chains):
            log_prob = np.concatenate([c.log_prob for c in self.chains])
        return Trace(all_samples, log_prob=log_prob, names=names)

    def summary(self) -> dict:
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