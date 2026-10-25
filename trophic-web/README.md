# Trophic Web

Trophic Web is a small, deterministic generalized Lotka–Volterra simulator for students and curious ecology modelers. Run `PYTHONPATH=trophic-web python3 -m trophic_web --steps 10` to see the built-in meadow as CSV, or load a custom web and export its full trajectory.

## How it works

For each species i, abundance evolves as `dx_i/dt = x_i (r_i + Σ A_ij x_j)`. Positive interaction coefficients represent facilitation; negative values encode competition or consumption. The example is illustrative, not a fitted ecological model.

Each step uses classical fourth-order Runge–Kutta (RK4). This is more accurate than forward Euler at a given step size, but it cannot guarantee stability for arbitrary parameters. Abundances are kept nonnegative; non-finite calculations fail explicitly.

## Usage

From the repository root:

```sh
PYTHONPATH=trophic-web python3 -m trophic_web --help
PYTHONPATH=trophic-web python3 -m trophic_web --steps 10 --dt 0.01
PYTHONPATH=trophic-web python3 -m trophic_web --model trophic-web/examples/pond.json --steps 25 --output /tmp/pond.csv
```

The CLI prints sampled CSV rows for quick inspection. `--output` writes every state to a CSV file with a time column. Model JSON requires `names`, `growth`, square `interactions`, and nonnegative `initial` abundance arrays of matching size; see `examples/pond.json`. `--steps` accepts 0 through 1,000,000, and `--dt` must be positive and finite. Requires Python 3.10+; standard library only.

## Tests

```sh
PYTHONPATH=trophic-web python3 -m unittest discover -s trophic-web -p 'test_*.py' -v
```

## Design notes

Unlike a fixed textbook predator–prey pair, the model accepts an arbitrary interaction matrix, so competition, facilitation, and trophic effects can be combined in one inspectable network. It is deterministic and dependency-free, enabling structural comparisons without requiring specialist scientific packages.

## Enhancements

- Load custom, validated ecosystem models from JSON.
- Export complete trajectories to CSV, while keeping terminal output sampled.
- Include a ready-to-run pond food-web fixture.

## Limitations

The supplied web is pedagogical. There is no parameter fitting, adaptive step sizing, stochastic events, or formal equilibrium/stability analysis. Large steps and strong interactions can be numerically unstable; reduce `--dt`.
