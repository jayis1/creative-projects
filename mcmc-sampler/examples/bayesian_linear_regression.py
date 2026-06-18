"""
Bayesian linear regression using the BayesianModel API and NUTS.

Demonstrates:
    - BayesianModel.linear_regression() convenience constructor
    - NUTS sampler with step-size adaptation
    - Posterior diagnostics (ESS, R-hat via parallel chains)
    - MAP estimate comparison
"""

import numpy as np

from mcmc_sampler import (
    BayesianModel,
    NUTS,
    map_estimate,
    effective_sample_size,
    highest_density_interval,
    monte_carlo_error,
    run_chains,
    MetropolisHastings,
)


def main() -> None:
    rng = np.random.default_rng(42)

    # ---- synthetic data ------------------------------------------------ #
    n, d = 80, 3
    true_w = np.array([1.5, -2.0, 0.8])
    X = rng.normal(0, 1, size=(n, d))
    noise = rng.normal(0, 0.5, size=n)
    y = X @ true_w + noise

    # ---- model --------------------------------------------------------- #
    model = BayesianModel.linear_regression(X, y, prior_std=10.0, noise_std=0.5)
    target = model.as_target(name="linreg-posterior")

    # ---- MAP estimate -------------------------------------------------- #
    x_map = map_estimate(target, x0=np.zeros(model.dim), lr=0.01, max_iter=500)
    print(f"True weights: {true_w}")
    print(f"MAP estimate: {x_map}")

    # ---- NUTS sampling ------------------------------------------------- #
    print("\n--- NUTS ---")
    sampler = NUTS(target, target_accept=0.8, init_step_size=0.05,
                   rng=np.random.default_rng(0))
    trace = sampler.sample(x0=x_map, n_samples=4000, burn=2000, thin=2)
    print(f"adapted step size: {sampler.step_size:.4f}")
    print(f"mean tree depth: {sampler.mean_tree_depth:.1f}")
    for i, nm in enumerate(trace.names):
        lo, hi = highest_density_interval(trace.samples[:, i])
        ess = effective_sample_size(trace.samples[:, i])
        mcse = monte_carlo_error(trace.samples[:, i])
        print(f"  {nm}: mean={trace.mean()[i]:.3f}  HDI95=[{lo:.3f},{hi:.3f}]  "
              f"ESS={ess:.0f}  MCSE={mcse:.4f}")

    # ---- convergence check via multi-chain R-hat ----------------------- #
    print("\n--- Convergence (4 chains) ---")
    def factory(seed):
        return NUTS(target, target_accept=0.8, init_step_size=0.05,
                    rng=np.random.default_rng(seed))
    x0s = [x_map + np.random.default_rng(100 + i).normal(size=model.dim) * 2
           for i in range(4)]
    result = run_chains(factory, x0s, n_samples=2000, burn=1000)
    rhats = result.rhat()
    print(f"R-hat: {['%.4f' % r for r in rhats]}")
    print(f"Converged: {all(r < 1.01 for r in rhats)}")


if __name__ == "__main__":
    main()