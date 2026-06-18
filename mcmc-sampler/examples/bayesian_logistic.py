"""
Bayesian logistic regression with MCMC.

We estimate the posterior over weights (w0, w1) for a 1-D logistic model
    p(y=1 | x) = sigmoid(w0 + w1 * x)
using a Gaussian prior and Metropolis–Hastings sampling.
"""

import numpy as np

from mcmc_sampler import (
    MetropolisHastings,
    Normal,
    Target,
    effective_sample_size,
    highest_density_interval,
    monte_carlo_error,
)


def sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-z))


def main() -> None:
    rng = np.random.default_rng(42)
    # synthetic data
    true_w = np.array([-1.0, 2.5])
    X = rng.normal(0, 2, size=100)
    p = sigmoid(true_w[0] + true_w[1] * X)
    y = (rng.random(100) < p).astype(int)

    # log posterior  ∝ likelihood + prior
    prior = Normal(0, 5)

    def log_post(w):
        logits = w[0] + w[1] * X
        # numerically stable log-likelihood
        ll = float(np.sum(y * logits - np.logaddexp(0, logits)))
        lp = prior.log_pdf([w[0]]) + prior.log_pdf([w[1]])
        return ll + lp

    target = Target(log_post, dim=2, name="logistic-posterior")

    sampler = MetropolisHastings(target, proposal_std=[0.3, 0.2],
                                 rng=np.random.default_rng(7))
    trace = sampler.sample(x0=[0.0, 0.0], n_samples=8000, burn=2000, thin=2)
    print(f"acceptance rate: {sampler.acceptance_rate:.3f}")
    print(f"true weights:   {true_w}")
    print(f"posterior mean: {trace.mean()}")
    for i, nm in enumerate(trace.names):
        lo, hi = highest_density_interval(trace.samples[:, i])
        ess = effective_sample_size(trace.samples[:, i])
        mcse = monte_carlo_error(trace.samples[:, i])
        print(f"  {nm}: mean={trace.mean()[i]:.3f}  HDI95=[{lo:.3f},{hi:.3f}]  "
              f"ESS={ess:.0f}  MCSE={mcse:.4f}")


if __name__ == "__main__":
    main()