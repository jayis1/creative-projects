# Trophic Web

Trophic Web is a small, deterministic generalized Lotka–Volterra simulator for students and curious ecology modelers. Run the built-in meadow in seconds with `PYTHONPATH=trophic-web python3 -m trophic_web --steps 10` to see species abundances as CSV.

## How it works

For each species i, abundance evolves as `dx_i/dt = x_i (r_i + Σ A_ij x_j)`. Positive interaction coefficients represent facilitation; negative values encode competition or consumption. The example is illustrative, not a fitted ecological model.

Each step uses classical fourth-order Runge–Kutta (RK4). This is more accurate than forward Euler at a given step size, but it cannot guarantee stability for arbitrary parameters. Abundances are kept nonnegative; non-finite calculations fail explicitly.

## Usage

From the repository root:

```sh
PYTHONPATH=trophic-web python3 -m trophic_web --help
PYTHONPATH=trophic-web python3 -m trophic_web --steps 10 --dt 0.01
```

The CLI prints CSV rows for initial, sampled, and final states. `--steps` accepts 0 through 1,000,000, and `--dt` must be positive and finite. Requires Python 3.10+; standard library only.

## Tests

```sh
PYTHONPATH=trophic-web python3 -m unittest discover -s trophic-web -p 'test_*.py' -v
```

## Design notes

Unlike a fixed textbook predator–prey pair, the model accepts an arbitrary interaction matrix, so competition, facilitation, and trophic effects can be combined in one inspectable network. It is intentionally deterministic and dependency-free, making it useful for comparing how interaction structure changes trajectories without turning the demo into an opaque scientific package.

## Planned enhancements

- Load and validate user-defined webs from JSON.
- Write complete simulation trajectories to CSV files.
- Offer trajectory summaries including per-species extrema.

## Limitations

The supplied web is pedagogical. There is no parameter fitting, adaptive step sizing, stochastic events, or formal equilibrium/stability analysis. Large steps and strong interactions can be numerically unstable; reduce `--dt`.
