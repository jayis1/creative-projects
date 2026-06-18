"""
Compare all samplers on the same target distribution.

Shows how to use compare_samplers() and format_comparison()
to evaluate which sampler works best for a given problem.
"""

import numpy as np

from mcmc_sampler import (
    MultivariateNormal,
    MetropolisHastings,
    AdaptiveMetropolis,
    HMCWithAdaptation,
    NUTS,
    SliceSampler,
    compare_samplers,
    format_comparison,
)


def main() -> None:
    # correlated 3-D Gaussian
    mu = [1.0, -1.0, 0.5]
    cov = [[1.0, 0.7, 0.3],
           [0.7, 2.0, 0.1],
           [0.3, 0.1, 0.5]]
    target = MultivariateNormal(mu, cov)
    x0 = np.zeros(3)

    samplers = {
        "MH": MetropolisHastings(target, proposal_std=0.5,
                                 rng=np.random.default_rng(42)),
        "AdaptiveMH": AdaptiveMetropolis(target, init_std=0.5,
                                         rng=np.random.default_rng(42)),
        "HMC-Adapt": HMCWithAdaptation(target, n_steps=20,
                                       rng=np.random.default_rng(42)),
        "NUTS": NUTS(target, target_accept=0.65,
                     rng=np.random.default_rng(42)),
        "Slice": SliceSampler(target, width=2.0,
                              rng=np.random.default_rng(42)),
    }

    print("Comparing samplers on 3-D correlated Gaussian")
    print(f"True mean: {mu}")
    print()
    results = compare_samplers(target, x0, samplers,
                               n_samples=3000, burn=1000, thin=1)
    print(format_comparison(results))
    print()
    for name, r in results.items():
        print(f"{name}: mean={r['mean']}")


if __name__ == "__main__":
    main()