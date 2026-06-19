"""Cluster collapse demo.

A random cloud of bodies under mutual gravity. Watch the cloud collapse and
form transient sub-clumps. Renders a sequence of PPM frames.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nbody.simulation import Simulation
from nbody.renderer import Renderer


def main() -> None:
    out = sys.argv[1] if len(sys.argv) > 1 else "frames"
    sim = Simulation.random_cloud(n=120, seed=7, spread=12.0, max_v=0.3,
                                   dt=0.02, theta=0.6, softening=0.8)
    result = sim.run(400, snapshot_every=10)
    print(f"Cluster collapse: {len(result.snapshots)} snapshots")
    print(f"  dE/E = {abs(result.final_energy - result.initial_energy) / abs(result.initial_energy):.2e}")
    r = Renderer(width=512, height=512, view_size=15.0, trails=True)
    paths = r.render_sequence(result.snapshots, out)
    print(f"Wrote {len(paths)} frames to {out}/")
    print(f"Make a video with:")
    print(f"  ffmpeg -framerate 30 -i {out}/frame_%06d.ppm -c:v libx264 -pix_fmt yuv420p cluster.mp4")


if __name__ == "__main__":
    main()