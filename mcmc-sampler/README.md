<div align="center">

# mcmc-sampler

**A from-scratch Markov Chain Monte Carlo sampling toolkit**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests: 99](https://img.shields.io/badge/tests-99-brightgreen.svg)](tests/)
[![Version: 2.0.0](https://img.shields.io/badge/version-2.0.0-blue.svg)](#changelog)

</div>

---

A pure-Python, NumPy-only MCMC library implementing **7 sampling algorithms**
(including NUTS), **17 built-in distributions**, a **Bayesian modelling
framework**, **parallel multi-chain runs**, **config files** (YAML/JSON/TOML),
**posterior analysis tools** (MAP, Laplace approximation, KDE), and
**ASCII visualization** — all from scratch, no probabilistic programming
framework required.

All samplers operate on **unnormalised log-density** functions, so they can
be used directly for Bayesian inference without computing normalising constants.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Algorithms](#algorithms)
- [Built-in Distributions](#built-in-distributions)
- [Bayesian Modelling](#bayesian-modelling)
- [Configuration Files](#configuration-files)
- [Parallel Multi-Chain](#parallel-multi-chain)
- [Posterior Analysis](#posterior-analysis)
- [ASCII Visualization](#ascii-visualization)
- [CLI](#cli)
- [Architecture](#architecture)
- [Examples](#examples)
- [Testing](#testing)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [Changelog](#changelog)
- [Known Issues (Resolved)](#known-issues-resolved)
- [License](#license)

## Features

| Category | What's included |
|----------|----------------|
| **Samplers** | Metropolis–Hastings, Adaptive Metropolis, HMC, HMC + Dual Averaging, **NUTS** (No-U-Turn Sampler), Slice sampler, Gibbs sampler |
| **Distributions** | Normal, MVN, Beta, Exponential, Gamma, StudentT, Uniform, Mixture, **Dirichlet, Poisson, Bernoulli, Categorical, TruncatedNormal, Logistic, Weibull, ChiSquared** |
| **Diagnostics** | ESS (Geyer), Gelman–Rubin R-hat, ACF, MCSE, HDI |
| **Bayesian** | `BayesianModel` with `.linear_regression()` and `.logistic_regression()` constructors |
| **Analysis** | MAP estimation, Laplace approximation, Gaussian KDE, sampler comparison, acceptance rate diagnostics |
| **Multi-chain** | Sequential (`run_chains`) and **parallel** (`run_chains_parallel`) with multiprocessing |
| **Config** | YAML / JSON / TOML config files for reproducible runs |
| **Visualization** | ASCII trace plots, histograms, ACF charts — no matplotlib required |
| **CLI** | 9 subcommands: sample, config, diagnostics, rhat, plot, visualize, compare, map, run-parallel |
| **Testing** | 99 tests across 4 test files |
| **CI** | GitHub Actions workflow (Python 3.9–3.12) |

## Installation

```bash
cd mcmc-sampler

# Basic install (numpy only)
pip install -e .

# With plotting, YAML config, and testing support
pip install -e ".[dev]"

# Or install specific extras
pip install -e ".[plot]"      # matplotlib for plotting
pip install -e ".[yaml]"      # PyYAML for YAML config files
pip install -e ".[test]"      # pytest + PyYAML
```

**Requirements:** Python ≥ 3.9, NumPy ≥ 1.21

## Quick Start

```python
import numpy as np
from mcmc_sampler import NUTS, Normal

# Define a target distribution
target = Normal(mu=2.0, sigma=1.5)

# Run NUTS with automatic step-size adaptation
sampler = NUTS(target, target_accept=0.65, rng=np.random.default_rng(42))
trace = sampler.sample(x0=[0.0], n_samples=5000, burn=2000, thin=2)

print(f"adapted step size: {sampler.step_size:.4f}")
print(f"posterior mean:  {trace.mean()}")   # ≈ [2.0]
print(f"posterior std:   {trace.std()}")    # ≈ [1.5]
print(f"ESS:             {effective_sample_size(trace.samples[:, 0]):.0f}")
```

### Custom target

```python
from mcmc_sampler import Target, MetropolisHastings

# Any unnormalised log-density
def log_density(x):
    return -0.5 * sum(xi**2 for xi in x)  # standard normal

target = Target(log_density, dim=3, name="my-target")
sampler = MetropolisHastings(target, proposal_std=1.0, rng=np.random.default_rng(0))
trace = sampler.sample([0, 0, 0], n_samples=5000, burn=1000)
```

## Algorithms

| Algorithm | Key idea | Best for |
|-----------|----------|----------|
| **Metropolis–Hastings** | Random-walk Gaussian proposal, symmetric ⇒ q cancels | General-purpose, low-dim |
| **Adaptive Metropolis** | Tunes proposal covariance from chain history (Haario 2001) | Unknown scale, multivariate |
| **Hamiltonian MC** | Leapfrog integration of Hamiltonian dynamics | High-dim, correlated posteriors |
| **HMC + Dual Averaging** | Auto-tunes step size to target acceptance (Hoffman & Gelman 2014) | When optimal step size is unknown |
| **NUTS** | No-U-Turn Sampler: auto-determines trajectory length via recursive doubling | State-of-the-art, no tuning needed |
| **Slice sampler** | Coordinate-wise slice with stepping-out + shrinkage (Neal 2003) | Low-dim, no tuning needed |
| **Gibbs sampler** | User-provides full conditionals | Conjugate models, hierarchical |

### NUTS — the flagship sampler

NUTS automatically determines how many leapfrog steps to take by building a
binary tree and stopping when the trajectory makes a U-turn. Combined with
dual-averaging step-size adaptation, it requires **no manual tuning**:

```python
from mcmc_sampler import NUTS, MultivariateNormal

target = MultivariateNormal([1, -2, 0.5],
                            [[1, 0.7, 0.3], [0.7, 2, 0.1], [0.3, 0.1, 0.5]])
sampler = NUTS(target, target_accept=0.8, rng=np.random.default_rng(42))
trace = sampler.sample([0, 0, 0], n_samples=3000, burn=2000)

print(f"mean tree depth: {sampler.mean_tree_depth:.1f}")
print(f"posterior mean: {trace.mean()}")  # ≈ [1, -2, 0.5]
```

## Built-in Distributions

| Distribution | Constructor | Support |
|-------------|-------------|---------|
| Normal | `Normal(mu, sigma)` | ℝ |
| MultivariateNormal | `MultivariateNormal(mu, cov)` | ℝᵈ |
| Beta | `Beta(alpha, beta)` | [0, 1] |
| Exponential | `Exponential(lam)` | [0, ∞) |
| Gamma | `Gamma(k, theta)` | (0, ∞) |
| StudentT | `StudentT(nu, mu, sigma)` | ℝ |
| Uniform | `Uniform(a, b)` | [a, b] |
| Mixture | `Mixture(components, weights)` | union of supports |
| Dirichlet | `Dirichlet(alpha)` | simplex |
| Poisson | `Poisson(lam)` | ℕ₀ |
| Bernoulli | `Bernoulli(p)` | {0, 1} |
| Categorical | `Categorical(probs)` | {0, ..., K-1} |
| TruncatedNormal | `TruncatedNormal(mu, sigma, a, b)` | [a, b] |
| Logistic | `Logistic(mu, s)` | ℝ |
| Weibull | `Weibull(k, lam)` | [0, ∞) |
| ChiSquared | `ChiSquared(k)` | (0, ∞) |

Or wrap any log-density with `Target(lambda x: ..., dim=n)`.

## Bayesian Modelling

The `BayesianModel` class makes it easy to define posteriors as
prior × likelihood:

```python
from mcmc_sampler import BayesianModel, NUTS, Normal
import numpy as np

# Custom model
model = BayesianModel(dim=2)
model.set_prior(lambda w: Normal(0, 5).log_pdf([w[0]]) + Normal(0, 5).log_pdf([w[1]]))
model.set_likelihood(lambda w: -0.5 * np.sum((data - w[0] - w[1] * X) ** 2))

target = model.as_target(name="my-posterior")
sampler = NUTS(target, target_accept=0.8, rng=np.random.default_rng(42))
trace = sampler.sample([0, 0], n_samples=5000, burn=2000)
```

### Convenience constructors

```python
# Bayesian linear regression (known or unknown noise)
model = BayesianModel.linear_regression(X, y, prior_std=10.0, noise_std=0.5)

# Bayesian logistic regression (intercept added automatically)
model = BayesianModel.logistic_regression(X, y, prior_std=5.0)
```

## Configuration Files

Define reproducible MCMC runs in YAML, JSON, or TOML:

**YAML** (`run.yaml`):
```yaml
target:
  kind: normal
  params: {mu: 2.0, sigma: 1.5}
sampler:
  algo: nuts
  params: {target_accept: 0.65, init_step_size: 0.25}
run:
  n_samples: 5000
  burn: 2000
  thin: 2
  seed: 42
output:
  diagnostics: true
  visualize: false
```

Run from CLI:
```bash
mcmc-sampler config run.yaml --out trace.json
```

Or from Python:
```python
from mcmc_sampler import load_config
cfg = load_config("run.yaml")
print(cfg.target.kind, cfg.sampler.algo, cfg.run.n_samples)
```

See `examples/config_nuts.yaml`, `examples/config_parallel_mvn.json`,
and `examples/config_mixture.toml` for complete examples.

## Parallel Multi-Chain

Run multiple chains across CPU cores for convergence diagnostics:

```python
from mcmc_sampler import NUTS, Normal, run_chains_parallel

target = Normal(0, 1)

def factory(seed):
    return NUTS(target, rng=np.random.default_rng(seed))

result = run_chains_parallel(factory, x0_list=[[-5], [0], [5]],
                             n_samples=3000, burn=1000)
print(result.rhat())         # R-hat per dimension
print(result.ess_total())    # Pooled ESS
print(result.summary())      # Full summary
```

CLI:
```bash
mcmc-sampler run-parallel --algo nuts --dist normal --n 3000 --chains 4
```

## Posterior Analysis

### MAP estimation

```python
from mcmc_sampler import map_estimate, Normal

target = Normal(5.0, 1.0)
x_map = map_estimate(target, x0=[0.0], lr=0.01, max_iter=500)
print(x_map)  # ≈ [5.0]
```

### Laplace approximation

```python
from mcmc_sampler import laplace_approximation, Normal

target = Normal(2.0, 3.0)
gaussian = laplace_approximation(target, x0=[0.0])
print(gaussian.mu)              # ≈ [2.0]
print(gaussian.cov)             # ≈ [[9.0]]
```

### Kernel density estimation

```python
from mcmc_sampler import gaussian_kde, kde_log_pdf

kde = gaussian_kde(trace.samples[:, 0])
print(kde(0.0))  # density at 0

# Use as a Target for further sampling
log_density = kde_log_pdf(trace.samples[:, 0])
```

### Sampler comparison

```python
from mcmc_sampler import compare_samplers, format_comparison

results = compare_samplers(target, x0, {
    "MH": MetropolisHastings(target, rng=...),
    "NUTS": NUTS(target, rng=...),
    "Slice": SliceSampler(target, rng=...),
}, n_samples=3000, burn=1000)

print(format_comparison(results))
```

Output:
```
Sampler                Acc Rate        ESS       MCSE   Time (s)
----------------------------------------------------------------
MH                        0.620        103     0.1227       0.04
NUTS                      0.757       1596     0.0282       1.31
Slice                     1.000       1724     0.0259       0.34
```

### Acceptance rate diagnostics

```python
from mcmc_sampler import acceptance_rate_diagnostic

msg = acceptance_rate_diagnostic(0.05, "mh")
# "Acceptance rate 0.050 is very low. Decrease proposal_std..."
```

## ASCII Visualization

No matplotlib required — visualize traces directly in the terminal:

```python
from mcmc_sampler import MetropolisHastings, Normal, visualize_trace

target = Normal(0, 1)
sampler = MetropolisHastings(target, rng=np.random.default_rng(42))
trace = sampler.sample([0.0], n_samples=2000, burn=500)
print(visualize_trace(trace))
```

Produces ASCII trace plots, histograms, and autocorrelation charts.

## CLI

```bash
# Sample from N(2, 1.5) via NUTS
mcmc-sampler sample --algo nuts --dist normal --mu 2 --sigma 1.5 --n 5000 --out t.json

# Run from a config file
mcmc-sampler config examples/config_nuts.yaml

# HMC with automatic step-size adaptation
mcmc-sampler sample --algo hmc-adapt --dist mvn --dim 3 --n 5000

# Diagnostics on a saved trace
mcmc-sampler diagnostics t.json

# R-hat across multiple chains
mcmc-sampler rhat chain1.json chain2.json chain3.json

# ASCII visualization
mcmc-sampler visualize t.json --param 0

# Compare all samplers
mcmc-sampler compare --dist normal --mu 3 --sigma 2 --n 3000

# Find the MAP estimate
mcmc-sampler map --dist normal --mu 5 --sigma 1

# Run 4 chains in parallel
mcmc-sampler run-parallel --algo nuts --dist normal --n 3000 --chains 4

# Trace + histogram plot (requires matplotlib)
mcmc-sampler plot t.json --out samples.png
```

## Architecture

```
mcmc-sampler/
├── mcmc_sampler/
│   ├── __init__.py          # Public API — all exports
│   ├── distributions.py     # Target base + 17 built-in distributions
│   ├── samplers.py          # 6 sampler implementations (MH, AM, HMC, HMC-Adapt, Slice, Gibbs)
│   ├── nuts.py              # NUTS — No-U-Turn Sampler with dual-averaging
│   ├── diagnostics.py       # ESS, R-hat, ACF, MCSE, HDI
│   ├── trace.py             # Sample container + summary / JSON export
│   ├── multichain.py        # Sequential multi-chain runner
│   ├── parallel.py          # Parallel multi-chain (multiprocessing)
│   ├── bayesian.py          # BayesianModel framework
│   ├── analysis.py          # MAP, Laplace, KDE, comparison, diagnostics
│   ├── visualize.py         # ASCII trace / histogram / ACF
│   ├── config.py            # YAML/JSON/TOML config system
│   ├── cli.py               # argparse CLI (9 subcommands)
│   └── version.py           # Version info
├── examples/
│   ├── bayesian_logistic.py           # Bayesian logistic regression
│   ├── bayesian_linear_regression.py  # Linear regression with NUTS
│   ├── compare_samplers.py            # Sampler comparison demo
│   ├── laplace_approximation.py       # Laplace approximation demo
│   ├── dirichlet_sampling.py          # Dirichlet on the simplex
│   ├── config_nuts.yaml               # YAML config example
│   ├── config_parallel_mvn.json       # JSON config (parallel MVN)
│   └── config_mixture.toml            # TOML config (bimodal mixture)
├── tests/
│   ├── test_mcmc.py          # 20 core tests
│   ├── test_enhancements.py  # 15 enhancement tests
│   ├── test_bug_hunt.py      # 7 bug-hunt tests
│   └── test_improvements.py  # 57 v2.0 improvement tests
├── .github/workflows/ci.yml  # GitHub Actions CI
├── pyproject.toml            # Package config
├── CONTRIBUTING.md           # Contribution guide
├── LICENSE                   # MIT license
└── README.md
```

### Design principles

1. **Unnormalised log-densities** — all samplers work with `log_pdf(x)`, no
   normalising constants needed.
2. **Uniform sampler interface** — every sampler has `.sample(x0, n_samples,
   burn, thin)` returning a `Trace`.
3. **Composable** — `Target` wraps any callable, `BayesianModel` composes
   prior + likelihood, `Mixture` combines any distributions.
4. **No hard dependencies** — only NumPy. matplotlib, PyYAML, and pytest
   are optional extras.
5. **From scratch** — every algorithm implemented from first principles,
   no PPL framework dependency.

## Examples

Run any example:

```bash
python examples/bayesian_logistic.py           # Logistic regression
python examples/bayesian_linear_regression.py  # Linear regression with NUTS
python examples/compare_samplers.py            # Compare all samplers
python examples/laplace_approximation.py       # MAP + Laplace + KDE
python examples/dirichlet_sampling.py          # Dirichlet on simplex
```

## Testing

```bash
# Run all 99 tests
python -m pytest tests/ -v

# Run a specific test class
python -m pytest tests/test_improvements.py::TestNUTS -v

# Run with coverage (if pytest-cov installed)
python -m pytest tests/ --cov=mcmc_sampler --cov-report=term-missing
```

All 99 tests pass:
- `test_mcmc.py` — 20 core sampler & distribution tests
- `test_enhancements.py` — 15 enhancement tests
- `test_bug_hunt.py` — 7 bug-hunt tests
- `test_improvements.py` — 57 v2.0 improvement tests (NUTS, new distributions, Bayesian model, analysis, config, parallel, CLI)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style,
and how to add new samplers and distributions.

## Roadmap

- [ ] **No-U-Turn Sampler with mass matrix adaptation** (diagonal + dense)
- [ ] **Stan-style warmup phases** (windowed adaptation)
- [ ] **Sequential Monte Carlo** (SMC) sampler
- [ ] **Annealed Importance Sampling** for marginal likelihood estimation
- [ ] **Variational inference** (mean-field and full-rank)
- [ ] **Automatic differentiation** integration (optional JAX/autograd backend)
- [ ] **Nested sampling** for model comparison
- [ ] **HMC with Jacobian-aware transforms** for constrained parameters
- [ ] **ArviZ integration** for InferenceData export
- [ ] **Web-based interactive trace visualization**

## Changelog

### v2.0.0 — Comprehensive Improvement

**New samplers:**
- **NUTS** (No-U-Turn Sampler) with recursive doubling and dual-averaging
  step-size adaptation (Hoffman & Gelman 2014)

**New distributions (9 added):**
- Dirichlet, Poisson, Bernoulli, Categorical, TruncatedNormal, Logistic,
  Weibull, ChiSquared

**Bayesian modelling framework:**
- `BayesianModel` class with `set_prior()`, `set_likelihood()`, `as_target()`
- `BayesianModel.linear_regression()` constructor
- `BayesianModel.logistic_regression()` constructor

**Posterior analysis:**
- `map_estimate()` — MAP via gradient ascent with adaptive learning rate
- `laplace_approximation()` — Gaussian approx at MAP via numerical Hessian
- `gaussian_kde()` / `kde_log_pdf()` — kernel density estimation
- `compare_samplers()` / `format_comparison()` — sampler benchmarking
- `acceptance_rate_diagnostic()` — acceptance rate recommendations

**Parallel multi-chain:**
- `run_chains_parallel()` using multiprocessing with spawn context
- `ParallelChainResult` with R-hat, ESS, and summary

**Configuration system:**
- `MCMCConfig` dataclass with full validation
- YAML, JSON, and TOML config file support
- `load_config()` convenience function
- CLI `config` subcommand

**CLI improvements:**
- 4 new subcommands: `config`, `compare`, `map`, `run-parallel`
- Support for all new distributions and NUTS algorithm
- Acceptance rate diagnostics in output
- ESS and MCSE in sample output

**Infrastructure:**
- GitHub Actions CI (Python 3.9–3.12)
- LICENSE (MIT)
- CONTRIBUTING.md
- 5 new example scripts
- 3 config file examples (YAML, JSON, TOML)
- 57 new tests (99 total, all passing)

### v1.0.0 — Initial Release

- 5 samplers: MH, Adaptive MH, HMC, HMC+Dual Averaging, Slice, Gibbs
- 8 distributions: Normal, MVN, Beta, Exponential, Gamma, StudentT, Uniform, Mixture
- Diagnostics: ESS, R-hat, ACF, MCSE, HDI
- Trace container with JSON I/O
- Multi-chain runner
- ASCII visualization
- CLI (5 subcommands)
- 42 tests

## Known Issues (Resolved)

### Bug 1: Mixture distribution returns NaN when all components are -inf

**Symptom:** `Mixture.log_pdf(x)` returned `NaN` instead of `-inf` when `x` was
outside the support of all component distributions.

**Root cause:** The log-sum-exp trick computed `m = max(log_vals)` which was
`-inf` when all components returned `-inf`. Then `exp(log_vals - m)` became
`exp(NaN)` because `-inf - (-inf) = NaN` in floating-point arithmetic.

**Fix:** Added an explicit check — if `max(log_vals)` is not finite, return
`-inf` immediately before attempting the log-sum-exp computation.

### Bug 2: Gelman-Rubin R-hat returns NaN for chains with < 2 samples

**Symptom:** `gelman_rubin([[1.0], [2.0], [3.0]])` returned `NaN` instead of
raising an error.

**Root cause:** `np.var(ddof=1)` on a single-element array produces `NaN`
(division by zero degrees of freedom). This silently propagated through the
R-hat computation.

**Fix:** Added a guard that raises `ValueError("need at least 2 samples per
chain")` when any chain has fewer than 2 samples.

## License

[MIT](LICENSE)