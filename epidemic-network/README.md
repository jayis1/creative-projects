# Epidemic Network Lab

A deterministic, dependency-free agent-based SEIR simulator on a randomized contact network.

Why this is interesting: unlike a homogeneous mixing model, its shuffled ring-lattice makes epidemic spread depend on network topology while retaining an exact reproducible seed.

## How it works

Each person occupies one of four states: Susceptible (S), Exposed (E), Infectious (I), or Recovered (R). A fixed undirected ring-lattice defines contacts. Each day infectious people independently expose susceptible neighbors with probability `beta`. State transitions are synchronous: infections acquired on a day cannot transmit until a later day. Incubation and infectious durations are configurable through the Python API.

## Usage

Requires Python 3.10+; no third-party packages.

```sh
cd epidemic-network
python3 main.py --demo
python3 -m unittest -v
```

The CLI emits JSON containing daily counts and a summary. A smaller run can be configured directly:

```sh
python3 main.py --population 20 --contacts 2 --beta 0.3 --seed 4 --days 15
```

Identical parameters and seed produce identical history. For known-answer behavior, `--contacts 0` leaves the initially exposed person as the only infection; they eventually recover.

## API

```python
from main import Epidemic
sim = Epidemic(population=100, contacts_per_person=4, beta=0.25, seed=7)
history = sim.run(max_days=60)
print(sim.summary())
```

Invalid population, degree, transmission probability, stage durations, or negative run limits raise `ValueError`.

## Planned

- Compare alternative contact-network topologies and intervention scenarios.
- Add attack-rate and reproduction summaries with machine-readable exports.
