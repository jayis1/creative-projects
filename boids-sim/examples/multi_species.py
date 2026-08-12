"""Example: Multi-species flocking simulation.

Demonstrates boids of different species that only flock with their own kind.
Three species are created, each with a different color, and they form
separate flocks that move independently.
"""

from boids.simulation import BoidSimulation
from boids.config import SimulationConfig
from boids.renderer import SVGRenderer


def main():
    cfg = SimulationConfig(
        num_boids=150,
        num_species=3,
        width=800, height=600,
        w_sep=1.8, w_ali=1.2, w_coh=1.2,
        use_wrap=True,
        trail_length=15,
    )
    sim = BoidSimulation(cfg)

    # Run 100 steps
    for _ in range(100):
        sim.step()

    # Render
    SVGRenderer().render(sim, "multi_species.svg")
    print(f"Saved multi_species.svg with {sim.config.num_species} species")
    print(f"Stats: {sim.stats()}")


if __name__ == "__main__":
    main()