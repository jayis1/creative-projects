"""Example: Path-following boids.

Demonstrates boids following a circular path of waypoints. The path-following
behavior steers boids toward each waypoint in sequence, creating a flowing
circular motion.
"""

from boids.simulation import BoidSimulation
from boids.config import SimulationConfig
from boids.renderer import SVGRenderer, TrailSVGRenderer
import math


def main():
    cfg = SimulationConfig(
        num_boids=60,
        width=800, height=600,
        max_speed=3.5,
        w_sep=1.2, w_ali=0.8, w_coh=0.8,
        w_path=2.0,
        path_loop=True,
        path_arrival_radius=30,
        trail_length=20,
    )
    sim = BoidSimulation(cfg)

    # Create a circular path with 8 waypoints
    cx, cy, r = 400, 300, 200
    waypoints = [(cx + r * math.cos(i * math.tau / 8), cy + r * math.sin(i * math.tau / 8))
                 for i in range(8)]
    sim.set_all_paths(waypoints, loop=True)

    # Run 200 steps
    for _ in range(200):
        sim.step()

    # Render with trails
    TrailSVGRenderer().render(sim, "path_following.svg")
    print("Saved path_following.svg with circular path of 8 waypoints")
    print(f"Stats: {sim.stats()}")


if __name__ == "__main__":
    main()