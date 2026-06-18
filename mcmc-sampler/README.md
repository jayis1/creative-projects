# mcmc-sampler

A from-scratch **Markov Chain Monte Carlo** sampling toolkit implementing five
core algorithms — **Metropolis–Hastings**, **Adaptive Metropolis**,
**Hamiltonian Monte Carlo**, **Slice sampling**, and **Gibbs sampling** — along
with built-in target distributions and convergence diagnostics.

All samplers operate on **unnormalised log-density** functions, so they can be
used directly for Bayesian inference without computing normalising constants.

## Algorithms

| Algorithm | Key idea | Best for |
|-----------|----------|----------|
| **Metropolis–Hastings** | Random-walk Gaussian proposal, symmetric ⇒ q cancels | General-purpose, low-dim |
| **Adaptive Metropolis** | Tunes proposal covariance from chain history (Haario 2001) | Unknown scale, multivariate |
| **Hamiltonian MC** | Leapfrog integration of Hamiltonian dynamics | High-dim, correlated posteriors |
| **Slice sampler** | Coordinate-wise slice with stepping-out + shrinkage (Neal 2003) | Low-dim, no tuning needed |
| **Gibbs sampler** | User-provides full conditionals | Conjugate models, hierarchical |

## Built-in distributions

`Normal`, `MultivariateNormal`, `Beta`, `Exponential`, `Uniform`, `Mixture` —
or wrap any log-density with `Target(lambda x: ..., dim=n)`.

## Diagnostics

- `effective_sample_size` — Geyer initial-positive-sequence ESS
- `gelman_rubin` — R-hat potential scale reduction factor
- `autocorrelation` — empirical ACF
- `monte_carlo_error` — MC standard error (std / √ESS)
- `highest_density_interval` — HDI for posterior summaries

## Installation

```bash
cd mcmc-sampler
pip install -e .[plot,test]
```

## Quick start

```python
import numpy as np
from mcmc_sampler import MetropolisHastings, Normal

target = Normal(mu=2.0, sigma=1.5)
sampler = MetropolisHastings(target, proposal_std=1.0,
                             rng=np.random.default_rng(42))
trace = sampler.sample(x0=[0.0], n_samples=10_000, burn=2_000, thin=2)

print(f"acceptance rate: {sampler.acceptance_rate:.3f}")
print(f"posterior mean:  {trace.mean()}")   # ≈ 2.0
print(f"posterior std:   {trace.std()}")    # ≈ 1.5
```

## Bayesian logistic regression example

```bash
python examples/bayesian_logistic.py
```

Estimates posterior over weights `(w0, w1)` of a 1-D logistic model using
Metropolis–Hastings on the unnormalised log-posterior.

## CLI

```bash
# Sample from N(2, 1) via MH
mcmc-sampler sample --algo mh --dist normal --mu 2 --sigma 1 --n 5000 --out t.json

# Diagnostics on a saved trace
mcmc-sampler diagnostics t.json

# R-hat across multiple chains
mcmc-sampler rhat chain1.json chain2.json chain3.json

# Trace + histogram plot
mcmc-sampler plot t.json --out samples.png
```

## Project layout

```
mcmc-sampler/
├── mcmc_sampler/
│   ├── __init__.py        # public API
│   ├── distributions.py   # Target base + built-in distributions
│   ├── samplers.py        # 5 sampler implementations
│   ├── diagnostics.py     # ESS, R-hat, ACF, MCSE, HDI
│   ├── trace.py           # sample container + summary/export
│   └── cli.py             # argparse CLI
├── examples/
│   └── bayesian_logistic.py
├── tests/
├── pyproject.toml
└── README.md
```