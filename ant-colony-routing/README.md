# Ant Colony Routing

A dependency-free, reproducible ant-colony optimizer for Euclidean traveling-salesperson tours.

- Ants probabilistically construct tours using pheromone strength and inverse distance.
- Pheromone evaporation balances exploration; shorter tours deposit more pheromone.
- A 2-opt local search improves each constructed tour before pheromone update.
- The fixed-seed RNG makes runs reproducible. 2-opt is enabled by default and can be disabled through the Python `solve(..., two_opt=False)` API.

## Usage

Run the built-in demonstration:

    python3 aco.py --seed 7 --ants 32 --iterations 150

Supply coordinates as JSON:

    python3 aco.py cities.json --seed 12

`cities.json` is an array such as `[[0, 0], [4, 0], [5, 3], [2, 5]]`. Output JSON contains a route of point indices, its closed-tour distance, and the best-so-far distance after each iteration. Inputs are bounded to 2–200 finite 2D points; ant count and iteration count are bounded to protect runtime.

## Known Issues (Resolved)

- JSON coordinates containing integers too large for floating-point conversion raised an uncaught `OverflowError`. Reproduced with a 10^400 coordinate; `load_points` now raises a user-facing `ValueError`, covered by a regression test.

## Tests

Run the suite:

    python3 -m unittest -v

The algorithm uses only Python's standard library. A fixed seed and identical parameters produce identical output.
