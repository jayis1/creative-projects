# Thermal Lab

A small, deterministic building-thermal simulator for people comparing simple zone insulation and heating scenarios.

Persona: a building-energy learner who wants to estimate how room temperatures evolve without an external simulation package.
Hero path: `python3 thermal_lab.py examples/two-zone.json --outside 5 --hours 1 --step 0.25`.
Input: JSON thermal zones and inter-zone conductances; output: JSON temperature snapshots.
Example: each snapshot shows `living` and `bedroom` temperatures in Celsius; the final sample is at one hour.
Non-goals: detailed HVAC controls, moisture, solar radiation, or calibrated building prediction.

## How it works

Each zone is a lumped thermal mass with heat capacity (Wh/K) and heat loss to outside (W/K). Pairwise links conduct heat between zones. Explicit Euler integration advances the energy balance with a bounded step; the simulator rejects a step larger than a zone's capacity divided by its total conductance, which prevents nonphysical numerical overshoot. Smaller steps generally improve accuracy at increased runtime. See `thermal_lab.py` for the equations.

## Usage

Run the hero command from this directory. Supply `--initial` for uniform initial temperature; `--hours` and `--step` control simulation duration and integration. The JSON model format is illustrated by `examples/two-zone.json`. `--initial-file` accepts per-zone starting temperatures, `--gains-file` adds constant per-zone heater gains in watts, and `--csv` emits a tabular history for spreadsheets. For example, `python3 thermal_lab.py examples/two-zone.json --outside 5 --hours 1 --step 0.25 --csv` emits a header `step,living,bedroom` followed by five rows.

Run tests with `python3 -m unittest discover -s tests -v` (six tests).

All implementation and tests use the Python standard library.

## Known Issues (Resolved)

- Coarse explicit-Euler steps could yield nonphysical overshoot in a high-conductance zone; now reject steps above the per-zone stability bound. Reproduced before the fix and covered by `test_explicit_step_cannot_exceed_thermal_stability_limit`.
