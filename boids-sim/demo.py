#!/usr/bin/env python3
"""Demo script: run the boids simulation and render an SVG frame."""

from boids.simulation import BoidSimulation, SimulationConfig
from boids.renderer import SVGRenderer, ASCIIRenderer, PPMRenderer

def main():
    cfg = SimulationConfig(
        num_boids=120,
        width=800, height=600,
        w_sep=1.5, w_ali=1.0, w_coh=1.0,
    )
    sim = BoidSimulation(cfg)
    sim.add_obstacle(400, 300, 40)
    sim.add_predator(100, 100)

    print("Running 50 simulation steps...")
    for _ in range(50):
        sim.step()

    # ASCII preview
    renderer = ASCIIRenderer(cols=80, rows=24)
    print(renderer.render(sim))

    # SVG export
    svg = SVGRenderer()
    svg.render(sim, "demo_frame.svg")
    print("\nSaved demo_frame.svg")

    # PPM export
    ppm = PPMRenderer()
    ppm.render(sim, "demo_frame.ppm", scale=1.0)
    print("Saved demo_frame.ppm")

    # Stats
    stats = sim.stats()
    print(f"\nStats: {stats['count']} boids, alignment={stats['alignment']:.3f}, avg_speed={stats['avg_speed']:.2f}")


if __name__ == "__main__":
    main()