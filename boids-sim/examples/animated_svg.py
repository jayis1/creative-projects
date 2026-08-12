"""Example: Animated SVG export.

Creates a self-contained animated SVG file that plays in any web browser
without JavaScript. Uses SMIL animations to show the flock in motion.
"""

from boids.simulation import BoidSimulation
from boids.config import get_preset
from boids.renderer import AnimatedSVGRenderer


def main():
    cfg = get_preset("fast-murmuration")
    sim = BoidSimulation(cfg)

    renderer = AnimatedSVGRenderer(fps=15, loop=True)
    renderer.render(sim, "animated_flock.svg", steps=80)
    print("Saved animated_flock.svg — open in a web browser to view!")
    print(f"  80 frames at 15 fps, looping indefinitely")


if __name__ == "__main__":
    main()