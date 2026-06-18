"""
Laplace approximation demo.

Finds the MAP of a non-Gaussian posterior and approximates it with a
Gaussian, then compares the Laplace approximation to MCMC samples.
"""

import numpy as np

from mcmc_sampler import (
    Mixture,
    Normal,
    NUTS,
    Target,
    map_estimate,
    laplace_approximation,
    gaussian_kde,
    effective_sample_size,
)


def main() -> None:
    # A mildly non-Gaussian target: mixture of two close normals
    target = Mixture([Normal(0, 1), Normal(1, 0.8)], weights=[0.6, 0.4])

    # MAP
    x_map = map_estimate(target, x0=[0.0], lr=0.01, max_iter=500)
    print(f"MAP estimate: {x_map[0]:.4f}")
    print(f"log_pdf at MAP: {target.log_pdf(x_map):.4f}")

    # Laplace approximation
    laplace = laplace_approximation(target, x0=[0.0], lr=0.01, max_iter=500)
    print(f"Laplace mean: {laplace.mu}")
    print(f"Laplace std: {np.sqrt(laplace.cov[0,0]):.4f}")

    # Compare with MCMC
    sampler = NUTS(target, target_accept=0.8, init_step_size=0.3,
                   rng=np.random.default_rng(42))
    trace = sampler.sample([0.0], n_samples=5000, burn=2000, thin=2)
    print(f"\nMCMC posterior mean: {trace.mean()[0]:.4f}")
    print(f"MCMC posterior std:  {trace.std()[0]:.4f}")
    ess = effective_sample_size(trace.samples[:, 0])
    print(f"ESS: {ess:.0f}")

    # KDE from samples
    kde = gaussian_kde(trace.samples[:, 0])
    test_points = [-2, -1, 0, 0.5, 1, 2]
    print("\nDensity comparison (KDE vs Laplace vs True):")
    for x in test_points:
        print(f"  x={x:5.1f}  KDE={kde(x):.4f}  "
              f"Laplace={np.exp(laplace.log_pdf([x])):.4f}  "
              f"True={np.exp(target.log_pdf([x])):.4f}")


if __name__ == "__main__":
    main()