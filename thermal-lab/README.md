# Thermal Lab

A small, deterministic building-thermal simulator for people comparing simple zone insulation and heating scenarios.

Persona: a building-energy learner who wants to estimate how room temperatures evolve without an external simulation package.
Hero path: `python3 thermal_lab.py examples/two-zone.json --outside 5 --hours 1 --step 0.25`.
Input: JSON thermal zones and inter-zone conductances; output: JSON temperature snapshots.
Example: each snapshot shows `living` and `bedroom` temperatures in Celsius; the final sample is at one hour.
Non-goals: detailed HVAC controls, moisture, solar radiation, or calibrated building prediction.

## How it works

Each zone is a lumped thermal mass with heat capacity (Wh/K) and heat loss to outside (W/K). Pairwise links conduct heat between zones. Explicit Euler integration advances the energy balance with a bounded step; smaller steps generally improve accuracy at increased runtime. See `thermal_lab.py` for the equations.

## Usage

Run the hero command from this directory. Supply `--initial` for uniform initial temperature; `--hours` and `--step` control simulation duration and integration. The JSON model format is illustrated by `examples/two-zone.json`.

Run tests with `python3 -m unittest discover -s tests -v`.

All implementation and tests use the Python standard library.
