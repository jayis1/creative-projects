"""Example: Benchmarking spatial index implementations.

Compares the uniform-grid spatial hash vs the quadtree for neighbor queries.
The grid is typically faster for uniform distributions; the quadtree excels
for clustered/non-uniform distributions.
"""

import time
from boids.simulation import BoidSimulation
from boids.config import SimulationConfig


def benchmark(index_type: str, num_boids: int, steps: int) -> dict:
    cfg = SimulationConfig(
        num_boids=num_boids,
        spatial_index=index_type,
        use_wrap=True,
        width=800, height=600,
    )
    sim = BoidSimulation(cfg)
    # Warmup
    sim.step()
    start = time.perf_counter()
    for _ in range(steps):
        sim.step()
    elapsed = time.perf_counter() - start
    return {
        "index": index_type,
        "boids": num_boids,
        "steps": steps,
        "elapsed_s": round(elapsed, 4),
        "ms_per_step": round(elapsed / steps * 1000, 2),
        "steps_per_sec": round(steps / elapsed, 0),
    }


def main():
    print("=== Spatial Index Benchmark ===\n")
    for n in [100, 300, 500]:
        for index_type in ("grid", "quadtree"):
            result = benchmark(index_type, n, 50)
            print(f"  {result['index']:10s}  {result['boids']:4d} boids: "
                  f"{result['ms_per_step']:.2f} ms/step  "
                  f"({result['steps_per_sec']:.0f} steps/s)")
        print()


if __name__ == "__main__":
    main()