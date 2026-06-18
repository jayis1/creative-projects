"""
mcmc_sampler — A from-scratch MCMC sampling library.

Provides multiple MCMC algorithms (Metropolis-Hastings, Hamiltonian Monte Carlo,
Slice sampling, Gibbs sampling, Adaptive Metropolis) for drawing samples from
arbitrary probability distributions defined in pure Python.

All algorithms work with log-density functions (unnormalised) so they can be
used for Bayesian inference without computing normalising constants.
"""

from .distributions import (
    Normal,
    MultivariateNormal,
    Mixture,
    Beta,
    Exponential,
    Uniform,
    Target,
)
from .samplers import (
    MetropolisHastings,
    HamiltonianMC,
    SliceSampler,
    GibbsSampler,
    AdaptiveMetropolis,
)
from .diagnostics import (
    effective_sample_size,
    gelman_rubin,
    autocorrelation,
    monte_carlo_error,
    highest_density_interval,
)
from .trace import Trace
from .version import __version__

__all__ = [
    "Normal",
    "MultivariateNormal",
    "Mixture",
    "Beta",
    "Exponential",
    "Uniform",
    "Target",
    "MetropolisHastings",
    "HamiltonianMC",
    "SliceSampler",
    "GibbsSampler",
    "AdaptiveMetropolis",
    "effective_sample_size",
    "gelman_rubin",
    "autocorrelation",
    "monte_carlo_error",
    "highest_density_interval",
    "Trace",
    "__version__",
]