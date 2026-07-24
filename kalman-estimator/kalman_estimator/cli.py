"""Command-line interface for kalman-estimator.

Usage examples::

    # Run a tracking simulation with the linear KF
    kalman-estimator simulate --filter kf --steps 100 --noise 2.0

    # Run with a config file
    kalman-estimator run --config my_config.json --measurements data.json

    # Compare filters on the same data
    kalman-estimator compare --steps 200 --noise 3.0

    # Print diagnostics
    kalman-estimator simulate --filter ukf --steps 100 --diagnostics
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

import numpy as np

from . import (
    KalmanFilter,
    ExtendedKalmanFilter,
    UnscentedKalmanFilter,
    AdaptiveKalmanFilter,
    EnsembleKalmanFilter,
    ParticleFilter,
    smooth,
    FilterDiagnostics,
)
from .config import load_filter_from_config
from .logging_util import get_logger

logger = get_logger("kalman_estimator.cli")


# --------------------------------------------------------------------------- #
#  Data generation
# --------------------------------------------------------------------------- #
def _generate_constant_velocity_data(
    steps: int = 100,
    true_vel: float = 1.0,
    noise_std: float = 2.0,
    seed: int = 42,
):
    """Generate 1-D constant-velocity tracking data."""
    rng = np.random.default_rng(seed)
    true_states = []
    measurements = []
    pos = 0.0
    for _ in range(steps):
        pos += true_vel
        true_states.append([pos, true_vel])
        measurements.append([pos + rng.normal(0, noise_std)])
    return np.array(true_states), np.array(measurements)


# --------------------------------------------------------------------------- #
#  Sub-command: simulate
# --------------------------------------------------------------------------- #
def cmd_simulate(args: argparse.Namespace) -> int:
    """Run a tracking simulation with the specified filter."""
    logger.info("Starting simulation: filter=%s, steps=%d, noise=%.2f",
                args.filter, args.steps, args.noise)

    true_states, measurements = _generate_constant_velocity_data(
        steps=args.steps, noise_std=args.noise, seed=args.seed
    )

    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    Q = np.eye(2) * 0.01
    R = np.array([[args.noise ** 2]])

    diag: Optional[FilterDiagnostics] = None
    if args.diagnostics:
        diag = FilterDiagnostics(state_dim=2, meas_dim=1)

    if args.filter == "kf":
        kf = KalmanFilter(F, H, Q, R, x0=[0.0, 0.0], P0=np.eye(2) * 10)
    elif args.filter == "ekf":
        def f(x, u):
            return F @ x

        def h(x):
            return np.array([x[0]])

        def Fj(x, u):
            return F

        def Hj(x):
            return H

        kf = ExtendedKalmanFilter(f, h, Fj, Hj, Q, R, x0=[0.0, 0.0], P0=np.eye(2) * 10)
    elif args.filter == "ukf":
        def fx(x, dt):
            return F @ x

        def hx(x):
            return np.array([x[0]])

        kf = UnscentedKalmanFilter(fx, hx, 1.0, Q, R, x0=[0.0, 0.0], P0=np.eye(2) * 10)
    elif args.filter == "adaptive":
        kf = AdaptiveKalmanFilter(
            F, H, Q, R, x0=[0.0, 0.0], P0=np.eye(2) * 10,
            alpha=0.95, adapt_Q=True, adapt_R=True,
        )
    elif args.filter == "enkf":
        def fe(x):
            return F @ x

        def he(x):
            return np.array([x[0]])

        kf = EnsembleKalmanFilter(fe, he, Q, R, x0=[0.0, 0.0], P0=np.eye(2) * 10,
                                   N=100, seed=args.seed)
    elif args.filter == "pf":
        def fp(x, u=None):
            return F @ x

        def hp(x):
            return np.array([x[0]])

        kf = ParticleFilter(fp, hp, Q, R, x0=[0.0, 0.0], P0=np.eye(2) * 10,
                            N=500, seed=args.seed)
    else:
        logger.error("Unknown filter type: %s", args.filter)
        return 1

    states = []
    for z in measurements:
        kf.predict()
        kf.update(z)
        states.append(kf.state.copy())
        if diag is not None:
            # compute innovation/S for diagnostics
            y = z - H @ kf.x  # rough post-update (for CLI display only)
            S = H @ kf.P @ H.T + R
            diag.record(y, S, kf.state, kf.covariance,
                        true_state=true_states[len(states) - 1])

    states = np.array(states)
    rmse = np.sqrt(np.mean((states[:, 0] - true_states[:, 0]) ** 2))
    meas_rmse = np.sqrt(np.mean((measurements[:, 0] - true_states[:, 0]) ** 2))

    print(f"\n{'='*50}")
    print(f"  Filter: {args.filter.upper()}")
    print(f"  Steps:  {args.steps}")
    print(f"  Noise:  {args.noise}")
    print(f"{'='*50}")
    print(f"  True final position: {true_states[-1, 0]:.3f}")
    print(f"  Estimated position:  {states[-1, 0]:.3f}")
    print(f"  Measurement RMSE:    {meas_rmse:.4f}")
    print(f"  Filter RMSE:         {rmse:.4f}")
    print(f"  Improvement:         {((meas_rmse - rmse) / meas_rmse * 100):.1f}%")
    print(f"{'='*50}")

    if diag is not None:
        s = diag.summary()
        print(f"\n  Diagnostics:")
        print(f"    NIS mean:          {s.get('nis_mean', 'N/A'):.4f}")
        print(f"    NEES mean:         {s.get('nees_mean', 'N/A'):.4f}")
        print(f"    Log-likelihood:    {s.get('log_likelihood', 'N/A'):.2f}")

    if args.output:
        output_data = {
            "filter": args.filter,
            "steps": args.steps,
            "noise": args.noise,
            "rmse": float(rmse),
            "measurement_rmse": float(meas_rmse),
            "states": states.tolist(),
            "true_states": true_states.tolist(),
        }
        with open(args.output, "w") as outf:
            json.dump(output_data, outf, indent=2)
        logger.info("Results saved to %s", args.output)

    return 0


# --------------------------------------------------------------------------- #
#  Sub-command: compare
# --------------------------------------------------------------------------- #
def cmd_compare(args: argparse.Namespace) -> int:
    """Compare all available filters on the same data."""
    logger.info("Comparing filters: steps=%d, noise=%.2f", args.steps, args.noise)

    true_states, measurements = _generate_constant_velocity_data(
        steps=args.steps, noise_std=args.noise, seed=args.seed
    )

    F = np.array([[1, 1], [0, 1]], dtype=float)
    H = np.array([[1, 0]], dtype=float)
    Q = np.eye(2) * 0.01
    R = np.array([[args.noise ** 2]])

    results = {}
    meas_rmse = np.sqrt(np.mean((measurements[:, 0] - true_states[:, 0]) ** 2))

    # KF
    kf = KalmanFilter(F, H, Q, R, x0=[0.0, 0.0], P0=np.eye(2) * 10)
    s = []
    for z in measurements:
        kf.predict()
        kf.update(z)
        s.append(kf.state.copy())
    results["KF"] = np.array(s)

    # RTS smoother
    kf2 = KalmanFilter(F, H, Q, R, x0=[0.0, 0.0], P0=np.eye(2) * 10)
    _, _, x_sm, _ = smooth(kf2, [z[0] for z in measurements])
    results["RTS"] = np.array(x_sm)

    # UKF
    def fx(x, dt):
        return F @ x

    def hx(x):
        return np.array([x[0]])

    ukf = UnscentedKalmanFilter(fx, hx, 1.0, Q, R, x0=[0.0, 0.0], P0=np.eye(2) * 10)
    s = []
    for z in measurements:
        ukf.predict()
        ukf.update(z)
        s.append(ukf.state.copy())
    results["UKF"] = np.array(s)

    # Adaptive KF
    akf = AdaptiveKalmanFilter(F, H, Q, R, x0=[0.0, 0.0], P0=np.eye(2) * 10)
    s = []
    for z in measurements:
        akf.predict()
        akf.update(z)
        s.append(akf.state.copy())
    results["AdaptiveKF"] = np.array(s)

    # Ensemble KF
    def fe(x):
        return F @ x

    def he(x):
        return np.array([x[0]])

    enkf = EnsembleKalmanFilter(fe, he, Q, R, x0=[0.0, 0.0], P0=np.eye(2) * 10,
                                 N=100, seed=args.seed)
    s = []
    for z in measurements:
        enkf.predict()
        enkf.update(z)
        s.append(enkf.state.copy())
    results["EnKF"] = np.array(s)

    # Particle Filter
    def fp(x, u=None):
        return F @ x

    def hp(x):
        return np.array([x[0]])

    pf = ParticleFilter(fp, hp, Q, R, x0=[0.0, 0.0], P0=np.eye(2) * 10,
                        N=500, seed=args.seed)
    s = []
    for z in measurements:
        pf.predict()
        pf.update(z)
        s.append(pf.state.copy())
    results["PF"] = np.array(s)

    # Print comparison table
    print(f"\n{'='*60}")
    print(f"  Filter Comparison  (steps={args.steps}, noise={args.noise})")
    print(f"{'='*60}")
    print(f"  {'Filter':<15} {'Pos RMSE':>10} {'Vel RMSE':>10} {'Improv %':>10}")
    print(f"  {'-'*45}")
    print(f"  {'Measurements':<15} {meas_rmse:>10.4f} {'--':>10} {'0.0':>10}")
    for name, est in results.items():
        pos_rmse = np.sqrt(np.mean((est[:, 0] - true_states[:, 0]) ** 2))
        vel_rmse = np.sqrt(np.mean((est[:, 1] - true_states[:, 1]) ** 2))
        improv = ((meas_rmse - pos_rmse) / meas_rmse * 100) if meas_rmse > 0 else 0
        print(f"  {name:<15} {pos_rmse:>10.4f} {vel_rmse:>10.4f} {improv:>9.1f}%")
    print(f"{'='*60}")

    return 0


# --------------------------------------------------------------------------- #
#  Sub-command: run (with config file)
# --------------------------------------------------------------------------- #
def cmd_run(args: argparse.Namespace) -> int:
    """Run a filter from a config file with optional measurement data."""
    logger.info("Loading config from %s", args.config)
    kf = load_filter_from_config(args.config)

    if args.measurements:
        with open(args.measurements) as mf:
            data = json.load(mf)
        measurements = data if isinstance(data, list) else data.get("measurements", [])
    else:
        # interactive: read from stdin
        logger.info("Reading measurements from stdin (one per line, comma-separated)")
        measurements = []
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                values = [float(v) for v in line.split(",")]
                measurements.append(values)
            except ValueError:
                logger.warning("Skipping invalid line: %s", line)

    print(f"\nRunning filter with {len(measurements)} measurements...")
    states = []
    for z in measurements:
        kf.predict()
        kf.update(z)
        states.append(kf.state.copy())

    print(f"\nFinal state: {kf.state}")
    print(f"Final covariance:\n{kf.covariance}")

    if args.output:
        with open(args.output, "w") as outf:
            json.dump({"states": [s.tolist() for s in states]}, outf, indent=2)
        logger.info("Results saved to %s", args.output)

    return 0


# --------------------------------------------------------------------------- #
#  Main parser
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="kalman-estimator",
        description="State estimation toolkit: KF, EKF, UKF, EnKF, PF, RTS smoother.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Sub-command")

    # simulate
    sim = subparsers.add_parser("simulate", help="Run a tracking simulation")
    sim.add_argument("--filter", type=str, default="kf",
                     choices=["kf", "ekf", "ukf", "adaptive", "enkf", "pf"],
                     help="Filter type (default: kf)")
    sim.add_argument("--steps", type=int, default=100,
                     help="Number of time steps (default: 100)")
    sim.add_argument("--noise", type=float, default=2.0,
                     help="Measurement noise std-dev (default: 2.0)")
    sim.add_argument("--seed", type=int, default=42,
                     help="Random seed (default: 42)")
    sim.add_argument("--diagnostics", action="store_true",
                     help="Print NIS/NEES/log-likelihood diagnostics")
    sim.add_argument("--output", type=str, default=None,
                     help="Save results to JSON file")
    sim.set_defaults(func=cmd_simulate)

    # compare
    cmp_cmd = subparsers.add_parser("compare", help="Compare all filters on same data")
    cmp_cmd.add_argument("--steps", type=int, default=100,
                         help="Number of time steps (default: 100)")
    cmp_cmd.add_argument("--noise", type=float, default=2.0,
                         help="Measurement noise std-dev (default: 2.0)")
    cmp_cmd.add_argument("--seed", type=int, default=42,
                         help="Random seed (default: 42)")
    cmp_cmd.set_defaults(func=cmd_compare)

    # run
    run = subparsers.add_parser("run", help="Run a filter from a config file")
    run.add_argument("--config", type=str, required=True,
                     help="Path to JSON/TOML config file")
    run.add_argument("--measurements", type=str, default=None,
                     help="Path to JSON file with measurement data")
    run.add_argument("--output", type=str, default=None,
                     help="Save results to JSON file")
    run.set_defaults(func=cmd_run)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())