"""Example: Stats time-series tracking and convergence analysis.

Runs a simulation and records statistics at each step, then analyzes
the time-series to find when the flock converged.
"""

from boids.simulation import BoidSimulation
from boids.config import SimulationConfig
from boids.stats_tracker import StatsTracker


def main():
    cfg = SimulationConfig(num_boids=200, use_wrap=True)
    sim = BoidSimulation(cfg)

    # The simulation has a built-in tracker
    for _ in range(500):
        sim.step()

    tracker = sim.tracker
    print(f"Recorded {len(tracker)} stat snapshots\n")

    # Summary statistics
    summary = tracker.summary()
    print("=== Summary ===")
    for key, vals in summary.items():
        print(f"  {key}: mean={vals['mean']:.4f}  min={vals['min']:.4f}  max={vals['max']:.4f}")

    # Trend analysis (last 50 steps)
    for key in ("alignment", "avg_speed", "spread"):
        trend = tracker.trend(key, window=50)
        if trend is not None:
            direction = "↑" if trend > 0 else "↓" if trend < 0 else "→"
            print(f"  {key} trend: {trend:+.6f} {direction}")

    # Find convergence tick (alignment > 0.5 for 20 consecutive steps)
    conv = tracker.convergence_tick("alignment", threshold=0.5, window=20)
    if conv is not None:
        print(f"\nFlock converged at tick {conv} (alignment >= 0.5 for 20 steps)")
    else:
        print("\nFlock did not converge to alignment >= 0.5")


if __name__ == "__main__":
    main()