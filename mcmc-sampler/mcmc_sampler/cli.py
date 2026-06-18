"""
Command-line interface for the mcmc-sampler package.

Subcommands
-----------
    sample       Run a sampler on a target distribution
    config       Run a sampler from a config file (YAML/JSON/TOML)
    diagnostics  Compute diagnostics for a saved trace
    rhat         Gelman-Rubin R-hat for multiple traces
    plot         Trace + histogram plot (matplotlib)
    visualize    ASCII trace / histogram / ACF
    compare      Compare multiple samplers on the same target
    map          Find the MAP estimate
    run-parallel Run multiple chains in parallel

Examples
--------
    mcmc-sampler sample --algo nuts --dist normal --mu 2 --sigma 1 --n 5000
    mcmc-sampler config run.yaml --out trace.json
    mcmc-sampler diagnostics trace.json
    mcmc-sampler compare --dist normal --mu 3 --sigma 2 --n 3000
    mcmc-sampler map --dist normal --mu 5 --sigma 1
    mcmc-sampler run-parallel --algo mh --dist normal --n 3000 --chains 4
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from typing import Optional

import numpy as np

from .distributions import (
    Beta as BetaDist,
    Categorical,
    ChiSquared,
    Dirichlet,
    Exponential,
    Gamma,
    Logistic,
    Mixture,
    MultivariateNormal,
    Normal,
    Poisson,
    Bernoulli,
    StudentT,
    Target,
    TruncatedNormal,
    Uniform,
    Weibull,
)
from .samplers import (
    AdaptiveMetropolis,
    GibbsSampler,
    HamiltonianMC,
    HMCWithAdaptation,
    MetropolisHastings,
    SliceSampler,
)
from .nuts import NUTS
from .trace import Trace
from .visualize import visualize_trace
from .diagnostics import (
    autocorrelation,
    effective_sample_size,
    gelman_rubin,
    highest_density_interval,
    monte_carlo_error,
)
from .analysis import (
    acceptance_rate_diagnostic,
    compare_samplers,
    format_comparison,
    map_estimate,
)
from .config import MCMCConfig, load_config, ConfigError
from .parallel import run_chains_parallel
from .version import __version__

logger = logging.getLogger("mcmc_sampler")


# --------------------------------------------------------------------------- #
# Target builder
# --------------------------------------------------------------------------- #

def _build_target(args) -> Target:
    """Build a target distribution from CLI args."""
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
    if args.dist == "gamma":
        return Gamma(k=args.alpha, theta=args.theta)
    if args.dist == "studentt":
        return StudentT(nu=args.nu, mu=args.mu, sigma=args.sigma)
    if args.dist == "uniform":
        return Uniform(a=args.a, b=args.b)
    if args.dist == "mixture":
        c1 = Normal(-3, 1)
        c2 = Normal(3, 1)
        return Mixture([c1, c2], weights=[0.5, 0.5])
    if args.dist == "truncnorm":
        return TruncatedNormal(mu=args.mu, sigma=args.sigma, a=args.a, b=args.b)
    if args.dist == "logistic":
        return Logistic(mu=args.mu, s=args.sigma)
    if args.dist == "weibull":
        return Weibull(k=args.alpha, lam=args.theta)
    if args.dist == "chisq":
        return ChiSquared(k=int(args.nu))
    if args.dist == "poisson":
        return Poisson(lam=args.lam)
    raise ValueError(f"unknown dist {args.dist}")


def _build_target_from_config(tcfg) -> Target:
    """Build a target from a TargetConfig."""
    kind = tcfg.kind
    p = tcfg.params
    if kind == "normal":
        return Normal(mu=p.get("mu", 0.0), sigma=p.get("sigma", 1.0))
    if kind == "mvn":
        dim = p.get("dim", 2)
        mu = np.array(p.get("mu", [0.0] * dim))
        cov = np.array(p.get("cov", np.eye(dim).tolist()))
        return MultivariateNormal(mu, cov)
    if kind == "beta":
        return BetaDist(alpha=p.get("alpha", 2.0), beta=p.get("beta", 2.0))
    if kind == "exp":
        return Exponential(lam=p.get("lam", 1.0))
    if kind == "gamma":
        return Gamma(k=p.get("k", 2.0), theta=p.get("theta", 1.0))
    if kind == "studentt":
        return StudentT(nu=p.get("nu", 3.0), mu=p.get("mu", 0.0),
                        sigma=p.get("sigma", 1.0))
    if kind == "uniform":
        return Uniform(a=p.get("a", 0.0), b=p.get("b", 1.0))
    if kind == "mixture":
        comps = []
        for c in p.get("components", [{"kind": "normal", "mu": -3, "sigma": 1},
                                       {"kind": "normal", "mu": 3, "sigma": 1}]):
            ct = type("T", (), {"kind": c["kind"], "params": {k: v for k, v in c.items() if k != "kind"}})()
            comps.append(_build_target_from_config(ct))
        return Mixture(comps, weights=p.get("weights"))
    if kind == "truncated-normal":
        return TruncatedNormal(mu=p.get("mu", 0.0), sigma=p.get("sigma", 1.0),
                               a=p.get("a", 0.0), b=p.get("b", 1.0))
    if kind == "logistic":
        return Logistic(mu=p.get("mu", 0.0), s=p.get("s", 1.0))
    if kind == "weibull":
        return Weibull(k=p.get("k", 1.0), lam=p.get("lam", 1.0))
    if kind == "chisquared":
        return ChiSquared(k=int(p.get("k", 1)))
    if kind == "poisson":
        return Poisson(lam=p.get("lam", 1.0))
    if kind == "custom":
        raise ConfigError("custom targets cannot be loaded from config files")
    raise ValueError(f"unknown target kind: {kind}")


def _build_sampler(args, target):
    """Build a sampler from CLI args."""
    algo = args.algo
    if algo == "mh":
        return MetropolisHastings(target, proposal_std=args.proposal_std)
    if algo == "am":
        return AdaptiveMetropolis(target, init_std=args.proposal_std)
    if algo == "hmc":
        return HamiltonianMC(target, step_size=args.step_size, n_steps=args.n_steps)
    if algo == "hmc-adapt":
        return HMCWithAdaptation(target, n_steps=args.n_steps,
                                 target_accept=args.target_accept,
                                 init_step_size=args.step_size)
    if algo == "nuts":
        return NUTS(target, max_tree_depth=args.max_tree_depth,
                    target_accept=args.target_accept,
                    init_step_size=args.step_size)
    if algo == "slice":
        return SliceSampler(target, width=args.width)
    raise ValueError(f"unknown algo {algo}")


def _build_sampler_from_config(scfg, target, seed: Optional[int] = None):
    """Build a sampler from a SamplerConfig."""
    algo = scfg.algo
    p = scfg.params
    rng = np.random.default_rng(seed) if seed is not None else None
    if algo == "mh":
        return MetropolisHastings(target, proposal_std=p.get("proposal_std", 1.0), rng=rng)
    if algo == "am":
        return AdaptiveMetropolis(target, init_std=p.get("init_std", 1.0), rng=rng)
    if algo == "hmc":
        return HamiltonianMC(target, step_size=p.get("step_size", 0.1),
                             n_steps=p.get("n_steps", 20), rng=rng)
    if algo == "hmc-adapt":
        return HMCWithAdaptation(target, n_steps=p.get("n_steps", 20),
                                 target_accept=p.get("target_accept", 0.65),
                                 init_step_size=p.get("init_step_size", 0.1), rng=rng)
    if algo == "nuts":
        return NUTS(target, max_tree_depth=p.get("max_tree_depth", 10),
                    target_accept=p.get("target_accept", 0.65),
                    init_step_size=p.get("init_step_size", 0.1), rng=rng)
    if algo == "slice":
        return SliceSampler(target, width=p.get("width", 1.0), rng=rng)
    raise ValueError(f"unknown algo: {algo}")


def _print_trace_summary(trace, sampler=None):
    """Print a human-readable summary of a trace."""
    for nm, stats in trace.summary(burn=0).items():
        print(f"  {nm}: mean={stats['mean']:.4f} std={stats['std']:.4f} "
              f"[{stats['2.5%']:.4f}, {stats['97.5%']:.4f}]")
    if sampler is not None and hasattr(sampler, "acceptance_rate"):
        rate = sampler.acceptance_rate
        algo = getattr(sampler, "name", "")
        print(f"# acceptance rate: {rate:.3f}")
        print(f"# {acceptance_rate_diagnostic(rate, algo)}")
    # per-parameter ESS
    for i, nm in enumerate(trace.names):
        col = trace.samples[:, i]
        ess = effective_sample_size(col)
        mcse = monte_carlo_error(col)
        print(f"  {nm}: ESS={ess:.1f}  MCSE={mcse:.4f}")


# --------------------------------------------------------------------------- #
# Subcommands
# --------------------------------------------------------------------------- #

def cmd_sample(args) -> int:
    target = _build_target(args)
    rng = np.random.default_rng(args.seed) if args.seed is not None else None
    if rng is not None:
        # inject rng into sampler
        sampler = _build_sampler(args, target)
        sampler.rng = rng
    else:
        sampler = _build_sampler(args, target)
    x0 = np.zeros(target.dim) if args.x0 is None else np.asarray(args.x0, dtype=float)
    trace = sampler.sample(x0, n_samples=args.n, burn=args.burn, thin=args.thin)
    print(f"# {sampler.name}")
    _print_trace_summary(trace, sampler)
    if args.out:
        trace.to_json(args.out)
        print(f"# saved trace -> {args.out}")
    return 0


def cmd_config(args) -> int:
    """Run a sampler from a config file."""
    try:
        cfg = load_config(args.config)
    except ConfigError as e:
        print(f"Config error: {e}", file=sys.stderr)
        return 1
    # set up logging
    logging.basicConfig(level=getattr(logging, cfg.output.log_level.upper()),
                        format="%(levelname)s: %(message)s")

    target = _build_target_from_config(cfg.target)
    run = cfg.run
    seed = run.seed
    x0 = np.asarray(run.x0, dtype=float) if run.x0 is not None else np.zeros(target.dim)

    if run.n_chains > 1:
        # parallel multi-chain
        def factory(s):
            return _build_sampler_from_config(cfg.sampler, target, seed=s)
        base_seed = seed if seed is not None else 0
        x0_list = [x0 + np.random.default_rng(base_seed + i).normal(size=target.dim) * 2
                   for i in range(run.n_chains)]
        result = run_chains_parallel(factory, x0_list,
                                     n_samples=run.n_samples,
                                     burn=run.burn, thin=run.thin)
        print(f"# Ran {result.n_chains} chains in parallel")
        summary = result.summary()
        print(f"# R-hat: {['%.4f' % r for r in summary['rhat']]}")
        print(f"# Converged: {summary['all_converged']}")
        print(f"# Pooled ESS: {[round(e) for e in summary['ess_pooled']]}")
        combined = result.combined_trace()
        _print_trace_summary(combined)
        if cfg.output.trace_json:
            combined.to_json(cfg.output.trace_json)
            print(f"# saved trace -> {cfg.output.trace_json}")
    else:
        sampler = _build_sampler_from_config(cfg.sampler, target, seed=seed)
        trace = sampler.sample(x0, n_samples=run.n_samples, burn=run.burn, thin=run.thin)
        print(f"# {sampler.name}")
        _print_trace_summary(trace, sampler)
        if cfg.output.trace_json:
            trace.to_json(cfg.output.trace_json)
            print(f"# saved trace -> {cfg.output.trace_json}")

    if cfg.output.visualize:
        trace_v: Trace
        if cfg.output.trace_json:
            trace_v = Trace.from_json(cfg.output.trace_json)
        else:
            trace_v = trace  # type: ignore[possibly-undefined]
        print(visualize_trace(trace_v))
    return 0


def cmd_diagnostics(args) -> int:
    trace = Trace.from_json(args.trace)
    print(f"# Trace: {len(trace)} samples, dim={trace.dim}")
    for i, nm in enumerate(trace.names):
        col = trace.samples[:, i]
        ess = effective_sample_size(col)
        mcse = monte_carlo_error(col)
        hdi_lo, hdi_hi = highest_density_interval(col)
        print(f"  {nm}: ESS={ess:.1f}  MCSE={mcse:.4f}  "
              f"HDI95=[{hdi_lo:.4f}, {hdi_hi:.4f}]")
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


def cmd_visualize(args) -> int:
    trace = Trace.from_json(args.trace)
    print(visualize_trace(trace, param=args.param))
    return 0


def cmd_compare(args) -> int:
    """Compare multiple samplers on the same target."""
    target = _build_target(args)
    x0 = np.zeros(target.dim)
    samplers = {}
    if "mh" in args.algos:
        samplers["MetropolisHastings"] = MetropolisHastings(
            target, proposal_std=args.proposal_std,
            rng=np.random.default_rng(42))
    if "am" in args.algos:
        samplers["AdaptiveMetropolis"] = AdaptiveMetropolis(
            target, init_std=args.proposal_std,
            rng=np.random.default_rng(42))
    if "hmc" in args.algos:
        samplers["HamiltonianMC"] = HamiltonianMC(
            target, step_size=args.step_size, n_steps=args.n_steps,
            rng=np.random.default_rng(42))
    if "hmc-adapt" in args.algos:
        samplers["HMC-Adapt"] = HMCWithAdaptation(
            target, n_steps=args.n_steps, rng=np.random.default_rng(42))
    if "nuts" in args.algos:
        samplers["NUTS"] = NUTS(
            target, target_accept=0.65, rng=np.random.default_rng(42))
    if "slice" in args.algos:
        samplers["SliceSampler"] = SliceSampler(
            target, width=args.width, rng=np.random.default_rng(42))
    if not samplers:
        print("No valid samplers selected", file=sys.stderr)
        return 1
    results = compare_samplers(target, x0, samplers,
                               n_samples=args.n, burn=args.burn, thin=args.thin)
    print(format_comparison(results))
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(results, fh, indent=2, default=str)
        print(f"# saved comparison -> {args.json}")
    return 0


def cmd_map(args) -> int:
    """Find the MAP estimate."""
    target = _build_target(args)
    x0 = np.zeros(target.dim)
    result = map_estimate(target, x0, max_iter=args.max_iter, lr=args.lr)
    lp = target.log_pdf(result)
    print(f"# MAP estimate: {result}")
    print(f"# log_pdf at MAP: {lp:.6f}")
    return 0


def cmd_run_parallel(args) -> int:
    """Run multiple chains in parallel."""
    target = _build_target(args)

    def factory(seed):
        rng = np.random.default_rng(seed)
        sampler = _build_sampler(args, target)
        sampler.rng = rng
        return sampler

    x0_list = [np.zeros(target.dim) + np.random.default_rng(100 + i).normal(size=target.dim) * 2
               for i in range(args.chains)]
    result = run_chains_parallel(factory, x0_list,
                                 n_samples=args.n, burn=args.burn, thin=args.thin)
    summary = result.summary()
    print(f"# Ran {result.n_chains} chains in parallel")
    print(f"# R-hat: {['%.4f' % r for r in summary['rhat']]}")
    print(f"# Converged: {summary['all_converged']}")
    print(f"# Pooled ESS: {[round(e) for e in summary['ess_pooled']]}")
    combined = result.combined_trace()
    _print_trace_summary(combined)
    if args.out:
        combined.to_json(args.out)
        print(f"# saved trace -> {args.out}")
    return 0


# --------------------------------------------------------------------------- #
# Argument parser
# --------------------------------------------------------------------------- #

def _add_common_dist_args(sp):
    """Add distribution-related arguments to a subparser."""
    sp.add_argument("--dist",
                    choices=["normal", "mvn", "beta", "exp", "mixture",
                             "gamma", "studentt", "uniform", "truncnorm",
                             "logistic", "weibull", "chisq", "poisson"],
                    default="normal")
    sp.add_argument("--mu", type=float, default=0.0)
    sp.add_argument("--sigma", type=float, default=1.0)
    sp.add_argument("--alpha", type=float, default=2.0, help="Beta alpha, Gamma k, or Weibull k")
    sp.add_argument("--beta", type=float, default=2.0, help="Beta beta param")
    sp.add_argument("--theta", type=float, default=1.0, help="Gamma/Weibull scale")
    sp.add_argument("--lam", type=float, default=1.0, help="Exponential/Poisson rate")
    sp.add_argument("--nu", type=float, default=3.0, help="StudentT dof or ChiSq dof")
    sp.add_argument("--a", type=float, default=0.0, help="Uniform/TruncNorm lower")
    sp.add_argument("--b", type=float, default=1.0, help="Uniform/TruncNorm upper")
    sp.add_argument("--dim", type=int, default=2)


def _add_common_sampler_args(sp):
    """Add sampler-related arguments to a subparser."""
    sp.add_argument("--algo",
                    choices=["mh", "am", "hmc", "hmc-adapt", "nuts", "slice"],
                    default="mh")
    sp.add_argument("--proposal-std", type=float, default=1.0)
    sp.add_argument("--step-size", type=float, default=0.1)
    sp.add_argument("--n-steps", type=int, default=20)
    sp.add_argument("--target-accept", type=float, default=0.65)
    sp.add_argument("--width", type=float, default=1.0)
    sp.add_argument("--max-tree-depth", type=int, default=10)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mcmc-sampler",
                                description="MCMC sampling toolkit v" + __version__)
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    # sample
    sp = sub.add_parser("sample", help="run a sampler")
    _add_common_dist_args(sp)
    _add_common_sampler_args(sp)
    sp.add_argument("--n", type=int, default=5000)
    sp.add_argument("--burn", type=int, default=1000)
    sp.add_argument("--thin", type=int, default=1)
    sp.add_argument("--seed", type=int, default=None)
    sp.add_argument("--x0", type=float, nargs="*", default=None, help="initial point")
    sp.add_argument("--out", default=None, help="save trace JSON")
    sp.set_defaults(func=cmd_sample)

    # config
    cp = sub.add_parser("config", help="run from a config file (YAML/JSON/TOML)")
    cp.add_argument("config", help="config file path")
    cp.set_defaults(func=cmd_config)

    # diagnostics
    dp = sub.add_parser("diagnostics", help="compute diagnostics for a trace")
    dp.add_argument("trace", help="trace JSON file")
    dp.set_defaults(func=cmd_diagnostics)

    # rhat
    rp = sub.add_parser("rhat", help="Gelman-Rubin R-hat for multiple traces")
    rp.add_argument("traces", nargs="+", help="trace JSON files")
    rp.set_defaults(func=cmd_rhat)

    # plot
    pp = sub.add_parser("plot", help="trace + histogram plot")
    pp.add_argument("trace", help="trace JSON file")
    pp.add_argument("--out", default="trace.png")
    pp.set_defaults(func=cmd_plot)

    # visualize
    vp = sub.add_parser("visualize", help="ASCII trace / histogram / ACF")
    vp.add_argument("trace", help="trace JSON file")
    vp.add_argument("--param", type=int, default=None)
    vp.set_defaults(func=cmd_visualize)

    # compare
    cmp = sub.add_parser("compare", help="compare multiple samplers")
    _add_common_dist_args(cmp)
    _add_common_sampler_args(cmp)
    cmp.add_argument("--algos", nargs="+",
                     default=["mh", "am", "hmc-adapt", "nuts", "slice"],
                     choices=["mh", "am", "hmc", "hmc-adapt", "nuts", "slice"])
    cmp.add_argument("--n", type=int, default=3000)
    cmp.add_argument("--burn", type=int, default=1000)
    cmp.add_argument("--thin", type=int, default=1)
    cmp.add_argument("--json", default=None, help="save comparison as JSON")
    cmp.set_defaults(func=cmd_compare)

    # map
    mp_ = sub.add_parser("map", help="find the MAP estimate via gradient ascent")
    _add_common_dist_args(mp_)
    mp_.add_argument("--max-iter", type=int, default=1000)
    mp_.add_argument("--lr", type=float, default=0.01)
    mp_.set_defaults(func=cmd_map)

    # run-parallel
    rpp = sub.add_parser("run-parallel", help="run multiple chains in parallel")
    _add_common_dist_args(rpp)
    _add_common_sampler_args(rpp)
    rpp.add_argument("--n", type=int, default=3000)
    rpp.add_argument("--burn", type=int, default=1000)
    rpp.add_argument("--thin", type=int, default=1)
    rpp.add_argument("--chains", type=int, default=4)
    rpp.add_argument("--out", default=None)
    rpp.set_defaults(func=cmd_run_parallel)

    return p


def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())