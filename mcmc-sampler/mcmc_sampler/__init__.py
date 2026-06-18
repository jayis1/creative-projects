"""
mcmc_sampler — A from-scratch MCMC sampling library.

Provides multiple MCMC algorithms (Metropolis-Hastings, Hamiltonian Monte Carlo,
NUTS, Slice sampling, Gibbs sampling, Adaptive Metropolis) for drawing samples
from arbitrary probability distributions defined in pure Python.

All algorithms work with log-density functions (unnormalised) so they can be
used for Bayesian inference without computing normalising constants.

Quick start
-----------
::

    from mcmc_sampler import NUTS, Normal

    target = Normal(mu=2.0, sigma=1.5)
    sampler = NUTS(target, target_accept=0.8, rng=__import__('numpy').random.default_rng(42))
    trace = sampler.sample([0.0], n_samples=5000, burn=2000)
    print(trace.mean(), trace.std())
"""

from .distributions import (
    Normal,
    MultivariateNormal,
    Mixture,
    Beta,
    Exponential,
    Gamma,
    StudentT,
    Uniform,
    Dirichlet,
    Poisson,
    Bernoulli,
    Categorical,
    TruncatedNormal,
    Logistic,
    Weibull,
    ChiSquared,
    Target,
)
from .samplers import (
    MetropolisHastings,
    HamiltonianMC,
    HMCWithAdaptation,
    SliceSampler,
    GibbsSampler,
    AdaptiveMetropolis,
)
from .nuts import NUTS
from .diagnostics import (
    effective_sample_size,
    gelman_rubin,
    autocorrelation,
    monte_carlo_error,
    highest_density_interval,
)
from .trace import Trace
from .multichain import MultiChainResult, run_chains
from .parallel import ParallelChainResult, run_chains_parallel
from .visualize import visualize_trace, ascii_histogram, ascii_trace, ascii_acf
from .bayesian import BayesianModel
from .analysis import (
    map_estimate,
    laplace_approximation,
    gaussian_kde,
    kde_log_pdf,
    acceptance_rate_diagnostic,
    compare_samplers,
    format_comparison,
)
from .config import MCMCConfig, load_config, ConfigError
from .version import __version__

__all__ = [
    # Distributions
    "Normal",
    "MultivariateNormal",
    "Mixture",
    "Beta",
    "Exponential",
    "Gamma",
    "StudentT",
    "Uniform",
    "Dirichlet",
    "Poisson",
    "Bernoulli",
    "Categorical",
    "TruncatedNormal",
    "Logistic",
    "Weibull",
    "ChiSquared",
    "Target",
    # Samplers
    "MetropolisHastings",
    "HamiltonianMC",
    "HMCWithAdaptation",
    "SliceSampler",
    "GibbsSampler",
    "AdaptiveMetropolis",
    "NUTS",
    # Diagnostics
    "effective_sample_size",
    "gelman_rubin",
    "autocorrelation",
    "monte_carlo_error",
    "highest_density_interval",
    # Containers
    "Trace",
    "MultiChainResult",
    "run_chains",
    "ParallelChainResult",
    "run_chains_parallel",
    # Visualization
    "visualize_trace",
    "ascii_histogram",
    "ascii_trace",
    "ascii_acf",
    # Bayesian
    "BayesianModel",
    # Analysis
    "map_estimate",
    "laplace_approximation",
    "gaussian_kde",
    "kde_log_pdf",
    "acceptance_rate_diagnostic",
    "compare_samplers",
    "format_comparison",
    # Config
    "MCMCConfig",
    "load_config",
    "ConfigError",
    # Version
    "__version__",
]