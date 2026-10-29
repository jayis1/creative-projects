# Terrain Erosion

A deterministic, dependency-free height-field erosion lab. The twist is a reproducible cellular slump model that transfers material conservatively to the steepest cardinal neighbor, rather than relying on a stochastic particle rain simulation.

## Run it now

```sh
python3 main.py --output terrain.pgm
python3 -m unittest -v
```

The command writes a compact ASCII PGM image that opens in common image viewers. `--seed 7` controls the initial terrain, and defaults are intentionally small and fast.

## How it works

A seeded sinusoidal surface with slight noise is generated in normalized [0, 1] elevation units. Each erosion pass compares each cell with its four in-bounds neighbors, chooses its steepest downhill neighbor, and transfers `rate * max(0, drop - talus)`. Transfers accumulate in a separate delta grid and apply simultaneously, avoiding iteration-order bias and conserving total height.

## Options and limits

`--width`, `--height` (each 1–512), `--seed`, `--iterations` (0–10,000), `--talus`, `--rate` (0–1), and `--output` configure the simulation. The model represents thermal granular slumping only; it does not simulate water transport, sediment capacity, or real-world units. Runtime is O(width × height × iterations).

## Further ideas

Add hydraulic erosion, boundary conditions, color ramps, and a PPM preview renderer.
