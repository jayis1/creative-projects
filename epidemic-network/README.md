# Epidemic Network Lab

A deterministic, dependency-free agent-based SEIR simulator with selectable contact graphs, interventions, and attack-rate metrics.

Why this is interesting: compared with homogeneous mixing, the simulator models explicit person-to-person contacts, so topology and intervention timing visibly shape spread while remaining reproducible from a seed.

## How it works

Each person occupies Susceptible (S), Exposed (E), Infectious (I), or Recovered (R). The default shuffled ring-lattice has local contacts; `random` builds a shuffled bounded-degree graph. Every day, infectious people independently expose susceptible neighbors with probability `beta`. A configured intervention multiplies this probability from a specified day onward. State transitions are synchronous: infections acquired today cannot transmit today. Incubation and infectious durations are configurable through the Python API.

## Usage

Requires Python 3.10+; no third-party packages.

```sh
cd epidemic-network
python3 main.py --demo
python3 -m unittest -v
```

The CLI emits JSON with daily counts and summary (`ever_infected`, `attack_rate`, `peak_infectious`). A scenario can select a graph and reduce transmission after day 10:

```sh
python3 main.py --population 80 --contacts 4 --topology random --beta 0.3 --intervention-day 10 --beta-multiplier 0.25 --seed 4 --days 40
```

`--topology` accepts `ring` or `random`. `--intervention-day` is zero-based, and `--beta-multiplier` must be between 0 and 1. Identical parameters and seed reproduce identical output. With `--contacts 0`, only the initial exposed person ever becomes infected.

## API

```python
from main import Epidemic
sim = Epidemic(100, contacts_per_person=4, beta=0.25, topology="random",
               intervention_day=10, beta_multiplier=0.5, seed=7)
history = sim.run(max_days=60)
print(sim.summary())
```

Invalid population, degree, stage durations, intervention day, and run limits must be integers; invalid ranges or unknown topology raise `ValueError` rather than leaking lower-level type errors.

## Known Issues (Resolved)

- Floating-point values for discrete parameters (population, contact degree, stage durations, intervention day, and run-day limit) previously caused inconsistent validation: some produced `TypeError` deeper in graph construction or iteration, while others silently passed. The API now rejects them consistently with `ValueError`. Regression coverage: `test_non_integer_discrete_parameters_raise_value_error` and `test_run_requires_integer_day_limit`.

## Planned

- Add repeated-seed ensemble analysis with uncertainty summaries.
