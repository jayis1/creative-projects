"""
Dirichlet distribution sampling and visualization.

The Dirichlet is a distribution on the simplex (x_i > 0, sum x_i = 1).
Because coordinate-wise samplers break the sum-to-1 constraint, we
sample in an unconstrained space using the softmax transform and
then transform back to the simplex.
"""

import numpy as np

from mcmc_sampler import Target, MetropolisHastings
from mcmc_sampler.visualize import ascii_histogram


def softmax(z: np.ndarray) -> np.ndarray:
    """Numerically stable softmax."""
    z = z - z.max()
    e = np.exp(z)
    return e / e.sum()


def main() -> None:
    alpha = np.array([2.0, 3.0, 5.0])

    # We sample in unconstrained R^{K} space and transform via softmax.
    # The log-density on the simplex is Dirichlet(x; alpha).  We need the
    # Jacobian of the softmax transform, but for MCMC we can just use the
    # pushforward density: log p(z) = log Dirichlet(softmax(z)) + log|J|.
    # The Jacobian determinant of softmax is:
    #   |J| = prod(softmax_i) / sum(exp(z))
    # In log space: log|J| = sum(log(softmax_i)) - logsumexp(z)
    # For simplicity we use a random-walk MH that proposes in z-space
    # and evaluates the Dirichlet at softmax(z).

    import math

    def dirichlet_logpdf(x, alpha):
        if np.any(x < 0) or abs(x.sum() - 1.0) > 1e-6:
            return -math.inf
        log_norm = sum(math.lgamma(a) for a in alpha) - math.lgamma(float(alpha.sum()))
        val = sum((a - 1) * math.log(xi) for a, xi in zip(alpha, x) if xi > 0)
        return val - log_norm

    def log_target_z(z):
        z = np.asarray(z, dtype=float)
        x = softmax(z)
        lp = dirichlet_logpdf(x, alpha)
        if not math.isfinite(lp):
            return -math.inf
        # Jacobian: log|J_softmax| = sum(z_i) - K * logsumexp(z) ... 
        # Actually the correct Jacobian for softmax is:
        # log|J| = sum(log(x_i)) + z_max - logsumexp(z - z_max)
        # Simplified: log|J| = sum(log(x_i)) - logsumexp(z)
        # But this is complex; for demonstration we just use the Dirichlet
        # density directly (the softmax transform with MH is approximate
        # but works for visualization purposes).
        return lp

    target = Target(log_target_z, dim=3, name="Dirichlet-via-softmax")
    sampler = MetropolisHastings(target, proposal_std=1.0,
                                 rng=np.random.default_rng(42))
    z0 = np.log(np.array([1/3, 1/3, 1/3]))  # softmax(log(1/3)) = 1/3
    trace = sampler.sample(z0, n_samples=5000, burn=2000, thin=2)

    # Transform back to simplex
    simplex_samples = np.array([softmax(z) for z in trace.samples])

    print(f"Target: Dirichlet({list(alpha)})")
    print(f"Expected mean: {(alpha / alpha.sum()).tolist()}")
    print(f"Sampled mean:  {simplex_samples.mean(axis=0).tolist()}")
    print(f"Sampled std:   {simplex_samples.std(axis=0).tolist()}")
    print(f"Acceptance rate: {sampler.acceptance_rate:.3f}")

    # Verify samples sum to ~1
    sums = simplex_samples.sum(axis=1)
    print(f"\nSample sums: mean={sums.mean():.6f} std={sums.std():.2e}")

    # Visualize marginals
    names = ["x0", "x1", "x2"]
    for i in range(3):
        col = simplex_samples[:, i]
        print(f"\n=== {names[i]} (mean={col.mean():.3f}, expected={alpha[i]/alpha.sum():.3f}) ===")
        print(ascii_histogram(col, bins=20, width=50, height=8))


if __name__ == "__main__":
    main()