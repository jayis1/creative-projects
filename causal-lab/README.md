# causal-lab

A dependency-free, reproducible linear structural causal model (SCM) workbench. Build a directed acyclic graph of equations, simulate observational data, and apply `do()` interventions that replace a variable's generating equation (cutting its incoming causal edges). This is a transparent teaching/simulation tool, not an estimator from real-world data.

## How it works

Variables are evaluated in topological order. Each value is its intercept plus the weighted parent values plus independent Gaussian noise. A seeded random generator makes runs repeatable. An intervention assigns a fixed value and bypasses that variable's equation; its downstream effects remain active. Cycles and malformed models are rejected.

## Usage

Python 3.10+; standard library only.

```sh
cd causal-lab
python3 causal_lab.py --demo
python3 -m unittest discover -s tests -v
```

The demo compares average outcomes for a small observational model and the intervention `do(study=4)`. To load a model from JSON, use an object mapping variable names to `intercept`, nonnegative `noise` standard deviation, and a `parents` object mapping parent names to coefficients:

```json
{"study":{"intercept":2,"noise":1},"score":{"intercept":10,"noise":1,"parents":{"study":3}}}
```

```sh
python3 causal_lab.py --model model.json --count 1000 --seed 7 --do study=4
```

Output is JSON rows. Sample count is limited to 1..1,000,000. Variables and coefficient values are numeric. No user-provided code is evaluated. Results assume independent Gaussian disturbances and linear additive equations; confounding, hidden variables, nonlinear functions, and parameter learning are outside scope.
