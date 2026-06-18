"""
Command-line interface for the mcmc-sampler package.

Examples
--------
    mcmc-sampler sample --algo mh --dist normal --mu 2 --sigma 1 --n 5000
    mcmc-sampler sample --algo hmc --dist mvn --dim 2 --n 5000
    mcmc-sampler diagnostics trace.json
    mcmc-sampler plot trace.json --out samples.png
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from typing import Optional

import numpy as np

from .distributions import (
    Beta as BetaDist,
    Exponential,
    Mixture,
    MultivariateNormal,
    Normal,
    Target,
)
from .samplers import (
    AdaptiveMetropolis,
    GibbsSampler,
    HamiltonianMC,
    MetropolisHastings,
    SliceSampler,
)
from .trace import Trace
from .diagnostics import (
    autocorrelation,
    effective_sample_size,
    gelman_rubin,
    highest_density_interval,
    monte_carlo_error,
)
from .version import __version__


def _build_target(args) -> Target:
    if args.dist == "normal":
        return Normal(mu=args.mu, sigma=args.sigma)
    if args.dist == "mvn":
        dim = args.dim
        mu = np.zeros(dim)
        cov = np.eye(dim) * (args.sigma ** 2)
        return MultivariateNormal(mu, cov)
    if args.dist == "beta":
        return BetaDist(alpha=args.alpha, beta=args.beta)
    if args.dist == "exp":
        return Exponential(lam=args.lam)
    if args.dist == "mixture":
        c1 = Normal(-3, 1)
        c2 = Normal(3, 1)
        return Mixture([c1, c2], weights=[0.5, 0.5])
    raise ValueError(f"unknown dist {args.dist}")


def _build_sampler(args, target):
    algo = args.algo
    if algo == "mh":
        return MetropolisHastings(target, proposal_std=args.proposal_std)
    if algo == "am":
        return AdaptiveMetropolis(target, init_std=args.proposal_std)
    if algo == "hmc":
        return HamiltonianMC(target, step_size=args.step_size, n_steps=args.n_steps)
    if algo == "slice":
        return SliceSampler(target, width=args.width)
    raise ValueError(f"unknown algo {algo}")


def cmd_sample(args) -> int:
    target = _build_target(args)
    sampler = _build_sampler(args, target)
    x0 = np.zeros(target.dim)
    trace = sampler.sample(x0, n_samples=args.n, burn=args.burn, thin=args.thin)
    print(f"# {sampler.name} — acceptance rate: {sampler.acceptance_rate:.3f}")
    for nm, stats in trace.summary(burn=0).items():
        print(f"{nm}: mean={stats['mean']:.4f} std={stats['std']:.4f} "
              f"[{stats['2.5%']:.4f}, {stats['97.5%']:.4f}]")
    if args.out:
        trace.to_json(args.out)
        print(f"# saved trace -> {args.out}")
    return 0


def cmd_diagnostics(args) -> int:
    trace = Trace.from_json(args.trace)
    print(f"# Trace: {len(trace)} samples, dim={trace.dim}")
    for i, nm in enumerate(trace.names):
        col = trace.samples[:, i]
        ess = effective_sample_size(col)
        mcse = monte_carlo_error(col)
        hdi_lo, hdi_hi = highest_density_interval(col)
        print(f"{nm}: ESS={ess:.1f}  MCSE={mcse:.4f}  HDI95=[{hdi_lo:.4f}, {hdi_hi:.4f}]")
    return 0


def cmd_rhat(args) -> int:
    traces = [Trace.from_json(p) for p in args.traces]
    if any(t.dim != 1 for t in traces):
        print("rhat sub-command currently supports 1-D chains", file=sys.stderr)
        return 1
    chains = [t.samples[:, 0] for t in traces]
    rhat = gelman_rubin(chains)
    print(f"R-hat = {rhat:.4f}  ({'converged' if rhat < 1.01 else 'NOT converged'})")
    return 0


def cmd_plot(args) -> int:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib is required for plotting", file=sys.stderr)
        return 1
    trace = Trace.from_json(args.trace)
    d = trace.dim
    fig, axes = plt.subplots(d, 2, figsize=(12, 3 * d), squeeze=False)
    for i in range(d):
        axes[i, 0].plot(trace.samples[:, i])
        axes[i, 0].set_title(f"Trace — {trace.names[i]}")
        axes[i, 1].hist(trace.samples[:, i], bins=60, density=True)
        axes[i, 1].set_title(f"Histogram — {trace.names[i]}")
    fig.tight_layout()
    fig.savefig(args.out, dpi=120)
    print(f"# plot saved -> {args.out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mcmc-sampler",
                                description="MCMC sampling toolkit")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("sample", help="run a sampler")
    sp.add_argument("--algo", choices=["mh", "am", "hmc", "slice"], default="mh")
    sp.add_argument("--dist", choices=["normal", "mvn", "beta", "exp", "mixture"],
                    default="normal")
    sp.add_argument("--n", type=int, default=5000)
    sp.add_argument("--burn", type=int, default=1000)
    sp.add_argument("--thin", type=int, default=1)
    sp.add_argument("--mu", type=float, default=0.0)
    sp.add_argument("--sigma", type=float, default=1.0)
    sp.add_argument("--alpha", type=float, default=2.0)
    sp.add_argument("--beta", type=float, default=2.0)
    sp.add_argument("--lam", type=float, default=1.0)
    sp.add_argument("--dim", type=int, default=2)
    sp.add_argument("--proposal-std", type=float, default=1.0)
    sp.add_argument("--step-size", type=float, default=0.1)
    sp.add_argument("--n-steps", type=int, default=20)
    sp.add_argument("--width", type=float, default=1.0)
    sp.add_argument("--out", default=None, help="save trace JSON")
    sp.set_defaults(func=cmd_sample)

    dp = sub.add_parser("diagnostics", help="compute diagnostics for a trace")
    dp.add_argument("trace", help="trace JSON file")
    dp.set_defaults(func=cmd_diagnostics)

    rp = sub.add_parser("rhat", help="Gelman-Rubin R-hat for multiple traces")
    rp.add_argument("traces", nargs="+", help="trace JSON files")
    rp.set_defaults(func=cmd_rhat)

    pp = sub.add_parser("plot", help="trace + histogram plot")
    pp.add_argument("trace", help="trace JSON file")
    pp.add_argument("--out", default="trace.png")
    pp.set_defaults(func=cmd_plot)

    return p


def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())