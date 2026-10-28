# causal-lab

A dependency-free, reproducible simulator for linear structural causal models (SCMs). Define a directed acyclic graph, generate observational samples, or intervene with `do()` to replace a variable's equation and cut its incoming edges. It is a teaching and simulation tool—not a causal estimator for real-world data.

## Contents

- [Quick start](#quick-start)
- [Model format and usage](#model-format-and-usage)
- [How it works](#how-it-works)
- [Limitations and roadmap](#limitations-and-roadmap)
- [Contributing](#contributing)

## Quick start

Python 3.10+; standard library only.

```sh
cd causal-lab
python3 causal_lab.py --demo
python3 -m unittest discover -s tests -v
```

Run a deterministic model using the included `example.json`:

```sh
python3 causal_lab.py --model example.json --expected --do study=4
```

Exact output:

```json
{"study": 4.0, "score": 22.0}
```

## Model format and usage

A model is a JSON object mapping variable names to an intercept, a nonnegative Gaussian noise standard deviation, and optional parent coefficients:

```json
{"study":{"intercept":2,"noise":1},"score":{"intercept":10,"noise":1,"parents":{"study":3}}}
```

Estimate means from seeded Monte Carlo samples (one JSON object per row):

```sh
python3 causal_lab.py --model example.json --count 1000 --seed 7 --do study=4
```

For exact expected values, without Monte Carlo noise:

```sh
python3 causal_lab.py --model example.json --expected --do study=4
```

`--expected` uses topological mean propagation under the zero-mean noise assumption. Repeat `--do NAME=VALUE` to set multiple variables. The CLI returns actionable errors for malformed interventions and invalid models. Sample count is limited to 1..1,000,000; model parameters and interventions must be finite.

## How it works

```text
JSON model -> validation + DAG ordering -> seeded sampler or exact mean propagation -> JSON output
```

Each non-intervened variable is its intercept plus weighted parent values plus independent Gaussian noise. Intervened variables are assigned the requested constant, bypassing their equation; their downstream effects remain active. Cycles, unknown parents, and non-finite parameters are rejected. No user-provided code is evaluated.

## Limitations and roadmap

The model assumes linear additive equations and independent Gaussian disturbances. It does not represent hidden confounding, nonlinear functions, or learn parameters from data.

- Add confidence intervals for Monte Carlo estimates.
- Add graph visualization in DOT format.
- Consider richer noise distributions while keeping seeded reproducibility.

## Contributing

Keep the simulator dependency-free where practical. Add regression tests for model validation, intervention semantics, and CLI behavior; run `python3 -m unittest discover -s tests -v` from this directory before submitting changes.

## Recent improvements

- Added `--expected` to expose exact intervention-aware expectations through the CLI.
- Added a runnable example model and regression coverage for the CLI output.
- Improved malformed `--do` argument errors.
- Rejected non-finite model values and intervention assignments to prevent invalid results propagating silently.
