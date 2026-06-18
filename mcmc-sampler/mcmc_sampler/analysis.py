"""
Posterior analysis and estimation utilities.

Includes:
    - MAP estimation via gradient ascent
    - Laplace approximation (Gaussian around the MAP)
    - Kernel density estimation from samples
    - Posterior predictive checks
    - Acceptance rate diagnostics with recommendations
    - Sampler comparison
"""

from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

from .distributions import Target, MultivariateNormal
from .trace import Trace
from .diagnostics import effective_sample_size, monte_carlo_error


Array = Union[np.ndarray, Sequence[float]]


# --------------------------------------------------------------------------- #
# MAP estimation
# --------------------------------------------------------------------------- #


def map_estimate(target: Target, x0: Sequence[float],
                 max_iter: int = 1000, lr: float = 0.01,
                 tol: float = 1e-6) -> np.ndarray:
    """Find the Maximum A Posteriori (MAP) estimate via gradient ascent.

    Uses simple gradient ascent with adaptive learning rate.

    Parameters
    ----------
    target : Target
        The log-density to maximise.
    x0 : starting point
    max_iter : int
        Maximum number of gradient steps.
    lr : float
        Initial learning rate.
    tol : float
        Convergence tolerance on log-density change.

    Returns
    -------
    np.ndarray — the MAP estimate.
    """
    x = np.asarray(x0, dtype=float).reshape(-1).copy()
    lp = target.log_pdf(x)
    if not math.isfinite(lp):
        raise ValueError("x0 has log_pdf = -inf")
    cur_lr = lr
    for _ in range(max_iter):
        grad = target.grad_log_pdf(x)
        x_new = x + cur_lr * grad
        lp_new = target.log_pdf(x_new)
        if not math.isfinite(lp_new):
            cur_lr *= 0.5
            continue
        if lp_new < lp:
            cur_lr *= 0.5
        else:
            if abs(lp_new - lp) < tol:
                x = x_new
                break
            x = x_new
            lp = lp_new
            cur_lr = min(cur_lr * 1.1, lr * 10)
    return x


def laplace_approximation(target: Target, x0: Sequence[float],
                          max_iter: int = 1000, lr: float = 0.01,
                          tol: float = 1e-6) -> MultivariateNormal:
    """Laplace approximation: fit a Gaussian at the MAP.

    Finds the MAP via gradient ascent, then approximates the posterior
    as a Gaussian with mean = MAP and covariance = inverse Hessian of
    log_pdf at the MAP.

    Returns
    -------
    MultivariateNormal — the Laplace approximation.
    """
    x_map = map_estimate(target, x0, max_iter=max_iter, lr=lr, tol=tol)
    d = target.dim

    # Numerical Hessian via central differences
    eps = 1e-5
    H = np.zeros((d, d))
    for i in range(d):
        for j in range(d):
            xpp = x_map.copy(); xpp[i] += eps; xpp[j] += eps
            xpm = x_map.copy(); xpm[i] += eps; xpm[j] -= eps
            xmp = x_map.copy(); xmp[i] -= eps; xmp[j] += eps
            xmm = x_map.copy(); xmm[i] -= eps; xmm[j] -= eps
            H[i, j] = (target.log_pdf(xpp) - target.log_pdf(xpm)
                       - target.log_pdf(xmp) + target.log_pdf(xmm)) / (4 * eps ** 2)

    # Covariance = inverse of the negative Hessian (since we maximise log_pdf)
    cov = -np.linalg.inv(H)

    # Ensure positive-definite
    try:
        np.linalg.cholesky(cov)
    except np.linalg.LinAlgError:
        # Add small jitter for numerical stability
        cov += np.eye(d) * 1e-6 * abs(np.trace(cov)) / d

    return MultivariateNormal(x_map, cov)


# --------------------------------------------------------------------------- #
# Kernel Density Estimation
# --------------------------------------------------------------------------- #


def gaussian_kde(samples: np.ndarray, bandwidth: Optional[float] = None) -> Callable:
    """1-D Gaussian kernel density estimator.

    Parameters
    ----------
    samples : 1-D array
    bandwidth : float, optional
        Silverman's rule is used if not specified.

    Returns
    -------
    callable ``density(x) -> float``
    """
    samples = np.asarray(samples, dtype=float).ravel()
    n = samples.shape[0]
    if n == 0:
        raise ValueError("need at least 1 sample")
    std = samples.std()
    if bandwidth is None:
        # Silverman's rule of thumb
        bandwidth = 1.06 * std * n ** (-1.0 / 5.0)
        if bandwidth <= 0:
            bandwidth = 0.1
    bw2 = bandwidth ** 2
    norm = 1.0 / (n * bandwidth * math.sqrt(2 * math.pi))

    def density(x: float) -> float:
        u = (x - samples) / bandwidth
        return float(norm * np.sum(np.exp(-0.5 * u * u)))

    return density


def kde_log_pdf(samples: np.ndarray, bandwidth: Optional[float] = None
                ) -> Callable[[Array], float]:
    """Like :func:`gaussian_kde` but returns log-density, suitable as a Target."""
    samples = np.asarray(samples, dtype=float).ravel()
    n = samples.shape[0]
    if n == 0:
        raise ValueError("need at least 1 sample")
    std = samples.std()
    if bandwidth is None:
        bandwidth = 1.06 * std * n ** (-1.0 / 5.0)
        if bandwidth <= 0:
            bandwidth = 0.1
    bw = bandwidth

    def _log_pdf(x: Array) -> float:
        x = np.asarray(x, dtype=float).reshape(-1)
        v = float(x[0])
        u = (v - samples) / bw
        # log-sum-exp for stability
        log_kernels = -0.5 * u * u - math.log(bw * math.sqrt(2 * math.pi))
        m = float(np.max(log_kernels))
        if not math.isfinite(m):
            return -math.inf
        return float(m + math.log(np.sum(np.exp(log_kernels - m))) - math.log(n))

    return _log_pdf


# --------------------------------------------------------------------------- #
# Acceptance rate diagnostics
# --------------------------------------------------------------------------- #


def acceptance_rate_diagnostic(rate: float, algo: str) -> str:
    """Return a human-readable recommendation for the acceptance rate.

    Parameters
    ----------
    rate : float — observed acceptance rate (0 to 1)
    algo : str — sampler algorithm name

    Returns
    -------
    str — diagnostic message
    """
    algo = algo.lower()
    if algo in ("mh", "metropolis-hastings"):
        optimal = 0.234  # Roberts, Gelman, Gilks 1997
        if rate < 0.1:
            return (f"Acceptance rate {rate:.3f} is very low. "
                    f"Decrease proposal_std to explore more locally.")
        elif rate > 0.5:
            return (f"Acceptance rate {rate:.3f} is high. "
                    f"Increase proposal_std for better mixing. "
                    f"Optimal ≈ {optimal:.3f} for high-dim.")
        elif 0.15 < rate < 0.4:
            return f"Acceptance rate {rate:.3f} is in a good range."
        else:
            return (f"Acceptance rate {rate:.3f}. Optimal ≈ {optimal:.3f}. "
                    f"Consider tuning proposal_std.")
    elif algo in ("hmc", "hamiltonianmc", "hmc-adapt", "nuts"):
        optimal = 0.65
        if rate < 0.2:
            return (f"Acceptance rate {rate:.3f} is low. "
                    f"Decrease step_size or increase n_steps.")
        elif rate > 0.95:
            return (f"Acceptance rate {rate:.3f} is very high. "
                    f"Increase step_size for more efficient exploration.")
        elif 0.55 < rate < 0.85:
            return f"Acceptance rate {rate:.3f} is good (target ≈ {optimal})."
        else:
            return (f"Acceptance rate {rate:.3f}. Target ≈ {optimal}. "
                    f"Consider step_size tuning.")
    elif algo == "slice":
        return ("Slice sampler always 'accepts' — acceptance rate is not a "
                "useful diagnostic. Check ESS instead.")
    elif algo in ("am", "adaptivemetropolis"):
        if rate < 0.1:
            return ("Low acceptance — the adaptive covariance may be too large. "
                    "Try a longer burn-in for adaptation.")
        elif rate > 0.5:
            return ("High acceptance — adaptive covariance may be too small. "
                    "Try a longer burn-in.")
        else:
            return f"Acceptance rate {rate:.3f} is acceptable for adaptive MH."
    else:
        return f"Acceptance rate {rate:.3f} — no specific recommendation."


# --------------------------------------------------------------------------- #
# Sampler comparison
# --------------------------------------------------------------------------- #


def compare_samplers(target: Target, x0: Sequence[float],
                     samplers: Dict[str, "object"],
                     n_samples: int = 5000, burn: int = 1000,
                     thin: int = 1) -> Dict[str, Dict]:
    """Run multiple samplers on the same target and compare.

    Parameters
    ----------
    target : Target
    x0 : starting point
    samplers : dict mapping name -> sampler instance
    n_samples, burn, thin : sampling parameters

    Returns
    -------
    dict mapping sampler name -> results dict with keys:
        ``mean``, ``std``, ``ess``, ``mcse``, ``acceptance_rate``, ``time``
    """
    import time
    results = {}
    for name, sampler in samplers.items():
        t0 = time.time()
        trace = sampler.sample(x0, n_samples=n_samples, burn=burn, thin=thin)
        elapsed = time.time() - t0
        ess_vals = [effective_sample_size(trace.samples[:, j])
                    for j in range(trace.dim)]
        mcse_vals = [monte_carlo_error(trace.samples[:, j])
                     for j in range(trace.dim)]
        results[name] = {
            "mean": trace.mean().tolist(),
            "std": trace.std().tolist(),
            "ess": ess_vals,
            "mcse": mcse_vals,
            "acceptance_rate": getattr(sampler, "acceptance_rate", None),
            "time": elapsed,
            "n_samples": len(trace),
        }
    return results


def format_comparison(results: Dict[str, Dict]) -> str:
    """Format sampler comparison results as a readable table."""
    lines = []
    header = f"{'Sampler':<20} {'Acc Rate':>10} {'ESS':>10} {'MCSE':>10} {'Time (s)':>10}"
    lines.append(header)
    lines.append("-" * len(header))
    for name, r in results.items():
        acc = f"{r['acceptance_rate']:.3f}" if r['acceptance_rate'] is not None else "N/A"
        ess = f"{np.mean(r['ess']):.0f}"
        mcse = f"{np.mean(r['mcse']):.4f}"
        t = f"{r['time']:.2f}"
        lines.append(f"{name:<20} {acc:>10} {ess:>10} {mcse:>10} {t:>10}")
    return "\n".join(lines)