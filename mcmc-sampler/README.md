# mcmc-sampler

A from-scratch **Markov Chain Monte Carlo** sampling toolkit implementing six
core algorithms — **Metropolis–Hastings**, **Adaptive Metropolis**,
**Hamiltonian Monte Carlo**, **HMC with dual-averaging step-size adaptation**,
**Slice sampling**, and **Gibbs sampling** — along with built-in target
distributions, convergence diagnostics, multi-chain support, and ASCII
visualization.

All samplers operate on **unnormalised log-density** functions, so they can be
used directly for Bayesian inference without computing normalising constants.

## Algorithms

| Algorithm | Key idea | Best for |
|-----------|----------|----------|
| **Metropolis–Hastings** | Random-walk Gaussian proposal, symmetric ⇒ q cancels | General-purpose, low-dim |
| **Adaptive Metropolis** | Tunes proposal covariance from chain history (Haario 2001) | Unknown scale, multivariate |
| **Hamiltonian MC** | Leapfrog integration of Hamiltonian dynamics | High-dim, correlated posteriors |
| **HMC + Dual Averaging** | Auto-tunes step size to target acceptance (Hoffman & Gelman 2014) | When optimal step size is unknown |
| **Slice sampler** | Coordinate-wise slice with stepping-out + shrinkage (Neal 2003) | Low-dim, no tuning needed |
| **Gibbs sampler** | User-provides full conditionals | Conjugate models, hierarchical |

## Built-in distributions

`Normal`, `MultivariateNormal`, `Beta`, `Exponential`, `Gamma`, `StudentT`,
`Uniform`, `Mixture` — or wrap any log-density with `Target(lambda x: ..., dim=n)`.

## Diagnostics

- `effective_sample_size` — Geyer initial-positive-sequence ESS
- `gelman_rubin` — R-hat potential scale reduction factor
- `autocorrelation` — empirical ACF
- `monte_carlo_error` — MC standard error (std / √ESS)
- `highest_density_interval` — HDI for posterior summaries

## Multi-chain support

```python
from mcmc_sampler import MetropolisHastings, Normal, run_chains

target = Normal(0, 1)
def factory(seed):
    return MetropolisHastings(target, proposal_std=1.0,
                              rng=np.random.default_rng(seed))

result = run_chains(factory, x0_list=[[-5.0], [0.0], [5.0]],
                    n_samples=5000, burn=1000)
print(result.rhat())          # per-dimension R-hat
print(result.ess_total())     # pooled ESS
print(result.summary())       # full summary
```

## ASCII visualization

No matplotlib required — visualize traces directly in the terminal:

```python
from mcmc_sampler import MetropolisHastings, Normal, visualize_trace

target = Normal(0, 1)
sampler = MetropolisHastings(target, rng=np.random.default_rng(42))
trace = sampler.sample([0.0], n_samples=2000, burn=500)
print(visualize_trace(trace))
```

Produces ASCII trace plots, histograms, and autocorrelation charts.

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

## HMC with step-size adaptation

```python
from mcmc_sampler import HMCWithAdaptation, MultivariateNormal

target = MultivariateNormal([1, -2], [[1, 0.5], [0.5, 2]])
sampler = HMCWithAdaptation(target, n_steps=20, target_accept=0.65,
                            rng=np.random.default_rng(42))
trace = sampler.sample([0, 0], n_samples=5000, burn=2000)
print(f"adapted step size: {sampler.step_size:.4f}")
print(f"posterior mean: {trace.mean()}")  # ≈ [1, -2]
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

# HMC with automatic step-size adaptation
mcmc-sampler sample --algo hmc-adapt --dist mvn --dim 2 --n 5000 --out t.json

# Diagnostics on a saved trace
mcmc-sampler diagnostics t.json

# R-hat across multiple chains
mcmc-sampler rhat chain1.json chain2.json chain3.json

# ASCII visualization (no matplotlib needed)
mcmc-sampler visualize t.json --param 0

# Trace + histogram plot (requires matplotlib)
mcmc-sampler plot t.json --out samples.png
```

## Project layout

```
mcmc-sampler/
├── mcmc_sampler/
│   ├── __init__.py        # public API
│   ├── distributions.py   # Target base + 8 built-in distributions
│   ├── samplers.py        # 6 sampler implementations
│   ├── diagnostics.py     # ESS, R-hat, ACF, MCSE, HDI
│   ├── multichain.py      # multi-chain runner + convergence summary
│   ├── visualize.py       # ASCII trace/histogram/ACF
│   ├── trace.py           # sample container + summary/export
│   └── cli.py             # argparse CLI (5 subcommands)
├── examples/
│   └── bayesian_logistic.py
├── tests/
│   ├── test_mcmc.py
│   ├── test_enhancements.py
│   └── test_bug_hunt.py
├── pyproject.toml
└── README.md
```

## Known Issues (Resolved)

### Bug 1: Mixture distribution returns NaN when all components are -inf

**Symptom:** `Mixture.log_pdf(x)` returned `NaN` instead of `-inf` when `x` was
outside the support of all component distributions (e.g., evaluating a mixture
of `Uniform(0, 0.1)` and `Uniform(0.9, 1.0)` at `x=0.5`).

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
chain")` when any chain has fewer than 2 samples, making the failure explicit
and actionable.