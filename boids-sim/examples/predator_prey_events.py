"""Example: Predator-prey simulation with events.

Demonstrates the event/callback system by logging every time a predator
catches a boid. Predators chase the nearest boid, while boids flee.
"""

from boids.simulation import BoidSimulation
from boids.config import SimulationConfig
from boids.renderer import SVGRenderer


def main():
    cfg = SimulationConfig(
        num_boids=200,
        width=800, height=600,
        w_sep=2.0, w_ali=1.0, w_coh=0.8,
        w_flee=5.0, predator_panic_dist=120,
        use_wrap=True,
    )
    sim = BoidSimulation(cfg)

    # Add 3 predators
    sim.add_predator(100, 100)
    sim.add_predator(700, 500)
    sim.add_predator(400, 300)

    # Track catches
    catches = []
    def on_collision(pred, boid):
        catches.append((sim.tick, pred.id, boid.id))
        print(f"  [tick {sim.tick}] Predator {pred.id} caught boid {boid.id}!")

    sim.events.on("collision", on_collision)

    # Run 150 steps
    for _ in range(150):
        sim.step()

    # Render
    SVGRenderer().render(sim, "predator_prey.svg")
    print(f"\nSaved predator_prey.svg")
    print(f"Total catches: {len(catches)}")
    print(f"Stats: {sim.stats()}")


if __name__ == "__main__":
    main()