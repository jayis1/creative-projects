# 🛰️ Orbital Mechanics Simulator

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests: 156](https://img.shields.io/badge/tests-156%20passed-brightgreen.svg)](#testing)
[![Version: 3.0](https://img.shields.io/badge/version-3.0.0-purple.svg)](#changelog)
[![NumPy](https://img.shields.io/badge/depends%20on-numpy-orange.svg)](https://numpy.org)

A pure-Python library for **two-body orbital mechanics**, **astrodynamics**,
and **mission design** — Keplerian element conversions, orbit propagation
(Kepler, RK4, Cowell, universal-variable, J2-secular, **adaptive RKF45**,
**Bulirsch-Stoer**), Lambert's problem, orbital transfer maneuvers,
perturbations, TLE parsing, ground-station visibility, eclipse modelling,
Lagrange points, repeat-ground-track & frozen orbits, CSV/JSON export,
ASCII visualizations, and a comprehensive argparse CLI.

> **No external dependencies beyond NumPy.**  YAML config is optional
> (`pyyaml`); TOML uses the Python 3.11+ stdlib `tomllib`.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Examples](#usage-examples)
- [CLI Reference](#cli-reference)
- [Configuration Files](#configuration-files)
- [Architecture](#architecture)
- [Testing](#testing)
- [ASCII Visualizations](#ascii-visualizations)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [References](#references)
- [License](#license)

---

## Features

### Core Astrodynamics
- **Kepler solvers** — Newton-iteration solvers for elliptic (`M = E − e·sin E`),
  hyperbolic (`M = e·sinh H − H`), parabolic (Barker's equation, closed-form
  Cardano), and the universal-variable form, with Mikkola starters and step
  damping for high-eccentricity stability.
- **State-vector ↔ orbital elements** — full conversion between Cartesian
  `(r, v)` and classical Keplerian elements `(a, e, i, Ω, ω, ν)`, handling
  equatorial, circular, parabolic, and degenerate orbits.
- **Anomaly conversions** — `true_to_eccentric`, `eccentric_to_true`,
  `true_to_mean`, `mean_to_true` for all conic sections.

### Propagation (6 methods)
- `propagate_kepler` — analytic (exact for two-body, elliptic + hyperbolic)
- `propagate_rk4` / `propagate_cowell` — fixed-step RK4 with optional perturbations
- `propagate_universal` — universal-variable (all conic sections)
- `propagate_j2_secular` — SGP4-like secular J2 drift (RAAN, argp, mean anomaly rates)
- **`propagate_rkf45`** — adaptive Runge-Kutta-Fehlberg 4(5) with step control *(new in v3)*
- **`propagate_bs`** — Bulirsch-Stoer extrapolation (very high accuracy) *(new in v3)*
- `multi_step_propagate` — generate a time series of states

### Maneuvers
- Hohmann transfer, bi-elliptic transfer
- Lambert's problem solver (universal-variable / Izzo formulation)
- Plane change (simple and combined), minimum-energy transfer time
- Porkchop plot data generation

### Perturbations
- J2 oblateness acceleration (Vallado Eq. 8.56)
- Exponential-atmosphere drag
- Composable with the Cowell propagator

### Ground Track & Look Angles
- ECI ↔ ECEF frame rotations, geodetic lat/lon/altitude
- Sub-satellite point tracking, topocentric elevation/azimuth/range

### New in v3.0
- **TLE parsing** — NORAD Two-Line Element sets with checksum validation
- **Visibility analysis** — eclipse/umbra detection, sun position,
  ground-station rise/set windows, pass summaries
- **Mission design** — repeat-ground-track orbits, frozen orbits,
  Lagrange points (CR3BP), station-keeping Δv estimates
- **Adaptive propagators** — RKF45 and Bulirsch-Stoer
- **Configuration files** — YAML / JSON / TOML mission configs
- **CSV / JSON export** — state series and ground tracks
- **ASCII visualizations** — orbit, ground track, and porkchop plots
- **Structured logging** — with timing context manager
- **J3 harmonic** — added to Body dataclass for frozen-orbit calculations

### Multiple Central Bodies
Predefined parameters for **Earth, Moon, Sun, Mars, and Venus**.

### Rich Data Classes
`StateVector` and `OrbitalElements` with `__repr__`, validation, comparison,
and computed properties (period, mean motion, perigee/apogee, energy,
orbit type, semi-latus rectum, angular momentum).

---

## Installation

### From source (recommended)

```bash
cd orbital-mechanics
pip install -e ".[dev]"    # installs numpy, pytest, pyyaml
```

### Without pip

```bash
cd orbital-mechanics
python3 demo.py    # run all smoke tests — no install needed
```

**Requirements:** Python ≥ 3.10, NumPy ≥ 1.20.  Optional: `pyyaml` for YAML
configs, `pytest` for the test suite.

---

## Quick Start

```python
import math
from orbital import EARTH, hohmann_transfer, OrbitalElements, elements_to_rv

# Hohmann transfer: LEO → GEO
res = hohmann_transfer(EARTH, 6678e3, 42164e3)
print(f"Δv = {res.dv_total:.1f} m/s, TOF = {res.tof/3600:.1f} h")
# Δv = 3892.6 m/s, TOF = 5.3 h

# Create an orbit from elements
elems = OrbitalElements(a=7000e3, e=0.01, i=math.radians(51.6),
                         raan=0, argp=math.radians(30), nu=math.radians(45))
sv = elements_to_rv(elems, EARTH)
print(f"Period = {elems.period:.1f} s ({elems.period/60:.1f} min)")
print(f"Orbit type: {elems.orbit_type}")
```

---

## Usage Examples

### Hohmann Transfer (LEO to GEO)

```python
from orbital import EARTH, hohmann_transfer
res = hohmann_transfer(EARTH, 6678e3, 42164e3)
print(f"Δv = {res.dv_total:.1f} m/s, TOF = {res.tof/3600:.1f} h")
# Δv = 3892.6 m/s, TOF = 5.3 h
```

### Convert Elements to State Vector

```python
from orbital import EARTH, OrbitalElements, elements_to_rv
import math
elems = OrbitalElements(a=7000e3, e=0.01, i=math.radians(51.6),
                         raan=0, argp=math.radians(30), nu=math.radians(45))
sv = elements_to_rv(elems, EARTH)
print(f"r = {sv.r} m, v = {sv.v} m/s")
print(f"Period = {elems.period:.1f} s, orbit type: {elems.orbit_type}")
```

### Solve Lambert's Problem

```python
from orbital import EARTH, lambert_izzo
import numpy as np
r1 = np.array([7000e3, 0, 0])
r2 = np.array([0, 7000e3, 0])
v1, v2 = lambert_izzo(r1, r2, 1800.0, EARTH.mu, prograde=True)
print(f"v1 = {v1} m/s, v2 = {v2} m/s")
```

### Adaptive RKF45 Propagation (high accuracy)

```python
from orbital import EARTH, OrbitalElements, elements_to_rv, propagate_rkf45
import math
elems = OrbitalElements(a=7000e3, e=0.1, i=math.radians(20),
                         raan=0, argp=0, nu=0)
sv = elements_to_rv(elems, EARTH)
sv_f = propagate_rkf45(sv, EARTH, 86400, rtol=1e-10)  # 1 day, high precision
```

### Parse a TLE

```python
from orbital import parse_tle
line1 = "1 25544U 98067A   08264.51782528 -.00002182  00000-0 -11606-4 0  2927"
line2 = "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537"
tle = parse_tle(line1, line2)
print(f"ISS: a={tle.semi_major_axis/1000:.1f} km, i={math.degrees(tle.inclination):.2f}°")
elems = tle.to_elements()  # convert to OrbitalElements
```

### Lagrange Points (Earth-Moon system)

```python
from orbital import EARTH, MOON, lagrange_points
pts = lagrange_points(EARTH, MOON)
for lp in pts:
    print(f"{lp.name}: {lp.r/1000} km")
```

### Repeat-Ground-Track Orbit

```python
from orbital import EARTH, repeat_groundtrack_orbit
import math
rgt = repeat_groundtrack_orbit(EARTH, N_rev=14, D_days=1,
                                inclination=math.radians(51.6))
print(f"a = {rgt.a/1000:.1f} km, period = {rgt.period/60:.1f} min")
```

### Ground-Station Visibility Windows

```python
from orbital import (EARTH, OrbitalElements, elements_to_rv,
                     multi_step_propagate, visibility_windows, access_summary)
import math
elems = OrbitalElements(a=7000e3, e=0, i=math.radians(45), raan=0, argp=0, nu=0)
sv = elements_to_rv(elems, EARTH)
states = multi_step_propagate(sv, EARTH, 6000, 60)
passes = visibility_windows(states, math.radians(40), 0,
                            min_elevation=math.radians(5))
for p in passes:
    print(access_summary(p))
```

### Eclipse / Umbra Check

```python
from orbital import sun_position, in_umbra, EARTH
import numpy as np
r_sun = sun_position(2460310.5)  # Julian Date
r_sat = np.array([-7000e3, 0, 0])  # opposite side of Earth
print(f"In umbra: {in_umbra(r_sat, r_sun, EARTH)}")  # True
```

### CSV Export

```python
from orbital import (EARTH, OrbitalElements, elements_to_rv,
                     multi_step_propagate, states_to_csv, ground_track,
                     groundtrack_to_csv)
elems = OrbitalElements(a=7000e3, e=0.01, i=math.radians(45), raan=0, argp=0, nu=0)
sv = elements_to_rv(elems, EARTH)
states = multi_step_propagate(sv, EARTH, 3600, 60)
states_to_csv(states, EARTH, "orbit_states.csv")          # 15 columns
pts = ground_track(states, EARTH)
groundtrack_to_csv(pts, "groundtrack.csv")                # lat, lon
```

---

## CLI Reference

The CLI uses argparse with 16 subcommands:

```
python3 cli.py --help
```

| Command       | Description                                      |
|---------------|--------------------------------------------------|
| `hohmann`     | Hohmann transfer between circular orbits         |
| `elements`    | Convert orbital elements to state vector         |
| `lambert`     | Solve Lambert's problem                          |
| `propagate`   | Propagate an orbit (Kepler + RK4 comparison)     |
| `rkf45`       | Adaptive RKF45 propagation                       |
| `groundtrack` | Generate ground-track lat/lon points             |
| `j2`          | J2 perturbation drift analysis                   |
| `tle`         | Parse a TLE file                                 |
| `lagrange`    | Compute Lagrange point positions                 |
| `rgt`         | Compute repeat-ground-track orbit                |
| `frozen`      | Compute frozen-orbit argument of perigee         |
| `porkchop`    | Generate porkchop plot data (+ ASCII)            |
| `visualize`   | ASCII orbit + ground-track visualization         |
| `visibility`  | Ground-station visibility windows                |
| `config`      | Run a mission from a YAML/JSON/TOML config file  |
| `eclipse`     | Check if a satellite is in Earth's umbra         |

### Examples

```bash
python3 cli.py hohmann 6678 42164                    # Hohmann LEO→GEO
python3 cli.py elements 7000 0.01 51.6 0 30 45       # Elements→state vector
python3 cli.py lambert 7000 0 0 0 7000 0 0 1800      # Lambert's problem
python3 cli.py propagate 7000 0.01 51.6 0 30 45 3600 # Propagate orbit
python3 cli.py rkf45 7000 0.01 51.6 0 30 45 86400    # Adaptive propagation
python3 cli.py groundtrack 7000 51.6 600 10          # Ground track points
python3 cli.py j2 7000 0.01 51.6 86400               # J2 perturbation drift
python3 cli.py tle examples/iss.tle                  # Parse ISS TLE
python3 cli.py lagrange earth moon                   # Earth-Moon Lagrange points
python3 cli.py rgt 14 1 51.6                         # 14:1 repeat-ground-track
python3 cli.py frozen 7000 0.01 51.6                 # Frozen orbit argp
python3 cli.py porkchop 7000 0 0 0 7000 0 0 1000 3000 --ascii
python3 cli.py visualize 7000 0.5 30 --points 60     # ASCII orbit plot
python3 cli.py visibility 7000 45 40 0 6000          # Visibility from 40°N
python3 cli.py config examples/mission.yaml          # Run from config
python3 cli.py eclipse 7000 0.1 51.6 90              # Eclipse check
python3 cli.py --body mars hohmann 3890 17000        # Mars Hohmann
```

---

## Configuration Files

Mission configs can be written in YAML, JSON, or TOML.  See
[`examples/mission.yaml`](examples/mission.yaml) and
[`examples/geo.json`](examples/geo.json).

```yaml
body: earth
satellite:
  a_km: 7000
  e: 0.01
  i_deg: 51.6
  raan_deg: 0
  argp_deg: 30
  nu_deg: 0
propagation:
  method: rkf45          # kepler | rk4 | cowell | rkf45 | universal | j2_secular
  dt_s: 86400
  rtol: 1.0e-9
ground_station:
  lat_deg: 40.0
  lon_deg: 0.0
  min_elevation_deg: 5.0
output:
  states_csv: orbit_states.csv
  groundtrack_csv: groundtrack.csv
  verbose: true
```

```bash
python3 cli.py config examples/mission.yaml
```

---

## Architecture

```
orbital-mechanics/
├── orbital/
│   ├── __init__.py        — public API exports (v3.0, 50+ symbols)
│   ├── bodies.py          — celestial body parameters (Earth, Moon, Sun, Mars, Venus)
│   │                        with J2, J3, omega (sidereal rotation rate)
│   ├── frames.py          — rotation matrices (rot1/rot2/rot3), ECI↔ECEF
│   ├── kepler.py          — Kepler equation solvers (elliptic, hyperbolic, Barker,
│   │                        universal) Mikkola starter, Stumpff functions, step damping
│   ├── elements.py        — OrbitalElements/StateVector with validation & repr,
│   │                        rv↔elements, true↔eccentric↔mean anomaly conversions,
│   │                        parabolic orbit support (periapsis-in-a convention)
│   ├── twobody.py         — 6 propagators: Kepler, RK4/Cowell, universal, J2-secular
│   │                        + multi_step_propagate for time series
│   ├── adaptive.py        — adaptive propagators: RKF45, Bulirsch-Stoer ⭐new
│   ├── maneuvers.py       — Hohmann, bi-elliptic, Lambert (Izzo), plane change,
│   │                        minimum-energy tof, porkchop data, Δv
│   ├── perturbations.py   — J2 oblateness & atmospheric drag accelerations
│   ├── groundtrack.py     — ECEF conversion, geodetic lat/lon, look angles, ground track
│   ├── tle.py             — NORAD TLE parser with checksum validation ⭐new
│   ├── visibility.py      — sun position, umbra/eclipse, visibility windows ⭐new
│   ├── mission.py         — repeat-ground-track, frozen orbits, Lagrange points ⭐new
│   ├── config.py          — YAML/JSON/TOML configuration loading ⭐new
│   ├── io_csv.py          — CSV/JSON export of state series and ground tracks ⭐new
│   ├── viz.py             — ASCII orbit, ground-track, porkchop visualisations ⭐new
│   └── logging_utils.py   — structured logging and timing context manager ⭐new
├── tests/                 — pytest suite (156 tests across 4 files) ⭐new
│   ├── conftest.py
│   ├── test_kepler.py     — Kepler/Barker/Stumpff/universal solver tests
│   ├── test_elements.py   — StateVector, OrbitalElements, conversion tests
│   ├── test_propagation.py— All 6 propagators + adaptive methods
│   └── test_features.py   — Maneuvers, TLE, visibility, mission, config, IO, viz
├── examples/              — Usage demos ⭐new
│   ├── iss.tle            — Sample ISS TLE
│   ├── mission.yaml       — YAML config example
│   ├── geo.json           — JSON config example (GEO satellite)
│   ├── demo_hohmann.py    — Hohmann + porkchop demo
│   └── demo_tle.py        — TLE parsing + ISS visualization demo
├── cli.py                 — argparse CLI with 16 subcommands
├── demo.py                — 23 smoke tests (no pytest needed)
├── pyproject.toml         — PEP 621 packaging metadata ⭐new
├── CONTRIBUTING.md        — Development guide ⭐new
├── LICENSE                — MIT license ⭐new
└── README.md              — This file
```

### Module Dependency Graph

```
bodies ← frames ← kepler ← elements ← twobody ← maneuvers
                          ↳ perturbations ↗      ↳ adaptive
                          ↳ groundtrack          ↳ tle
                          ↳ visibility           ↳ mission
                          ↳ config               ↳ io_csv
                          ↳ viz                  ↳ logging_utils
```

---

## Testing

### Smoke tests (no pytest needed)

```bash
python3 demo.py    # 23 tests covering all v2 modules
```

### Full pytest suite

```bash
pytest tests/ -v    # 156 tests across 4 files
```

```
tests/test_kepler.py       — 25 tests (Kepler E/H/Barker/universal/Stumpff/Mikkola)
tests/test_elements.py     — 35 tests (StateVector, OrbitalElements, conversions)
tests/test_propagation.py  — 22 tests (Kepler, RK4, Cowell, universal, J2, RKF45, BS)
tests/test_features.py     — 74 tests (maneuvers, TLE, visibility, mission, config, IO, viz)
============================== 156 passed in 0.5s ==============================
```

---

## ASCII Visualizations

The library includes terminal-friendly ASCII art plots — no matplotlib needed:

### Orbit Plot (XY plane)

```
python3 cli.py visualize 7000 0.5 30 --points 60
```

```
Orbit XY projection (Earth, e=0.5, i=30.0°)
                      • •  •  •  •  •     │
                 • •                   •  •
             • •                          │  •
            •                             │
         ••                               │     •
        •                                 │
      •                                   │        •
     •                                    │
    ••                                    │           •
   •                                      │
   •                                      │            •
  •                                       │
  •                                       │
──•───────────────────────────────────────│─────────────E───
  •                                       │
   •                                      │            •
    ••                                    │           •
     •                                    │        •
      •                                   │
        •                                 │     •
         ••                               │
            •                             │  •
             • •                          │
                 • •                   •  •
                      • •  •  •  •  •     │
x: [-11200, 4200] km  y: [-5773, 5773] km  (S=start, E=end)
```

### Porkchop Plot

```
python3 cli.py porkchop 7000 0 0 0 7000 0 0 1500 4000 --ascii --n-tof 30
```

---

## Roadmap

- [ ] SGP4 full implementation (with short-period terms)
- [ ] Third-body perturbations (Moon, Sun gravity)
- [ ] Solar radiation pressure
- [ ] Numerical optimization for low-thrust trajectories
- [ ] Matplotlib-based 2D/3D plotting (optional dependency)
- [ ] Convert README ASCII demos to rendered images
- [ ] Earth atmospheric density models (Jacchia-Bowman, NRLMSISE)
- [ ] Ecliptic/equatorial frame conversions with nutation
- [ ] ICRF frame transforms
- [ ] Kalman filter for orbit determination

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style,
and pull-request guidelines.

Contributions are welcome!  Please open an issue first to discuss major
changes.

---

## Changelog

### v3.0.0 (2026-07-17) — Comprehensive Improvement

**New modules (8 added):**
- `adaptive.py` — RKF45 and Bulirsch-Stoer adaptive propagators
- `tle.py` — NORAD Two-Line Element parser with checksums
- `visibility.py` — sun position, umbra/eclipse, visibility windows
- `mission.py` — repeat-ground-track, frozen orbits, Lagrange points
- `config.py` — YAML/JSON/TOML configuration loading
- `io_csv.py` — CSV/JSON export of state series and ground tracks
- `viz.py` — ASCII art orbit, ground-track, porkchop visualizations
- `logging_utils.py` — structured logging and timing

**New features:**
- 10 new CLI subcommands (16 total): `rkf45`, `tle`, `lagrange`, `rgt`,
  `frozen`, `porkchop`, `visualize`, `visibility`, `config`, `eclipse`
- Argparse-based CLI with `--help`, `--body`, `--verbose` flags
- J3 harmonic added to `Body` dataclass
- Parabolic orbit support in `elements_to_rv` (periapsis-in-`a` convention)
- Fixed `perigee` property for parabolic orbits
- 156-test pytest suite (4 test files)
- `pyproject.toml` with PEP 621 metadata, installable via `pip install -e .`
- `LICENSE` (MIT), `CONTRIBUTING.md`
- 5 example files (TLE, YAML/JSON configs, 2 demo scripts)

**Bug fixes:**
- Fixed `SatelliteConfig.from_dict` — `a_km`/`a_m` branching was broken
- Fixed `elements_to_rv` for parabolic orbits (was producing NaN)
- Fixed `perigee` property for parabolic orbits (was NaN)
- Fixed Bulirsch-Stoer Aitken-Neville extrapolation indexing

### v2.0.0 — Enhancement

- Universal-variable propagation, J2 secular drift, plane change, porkchop,
  Barker solver, Mikkola starter, validation, repr, 23 smoke tests

### v1.0.0 — Initial Release

- Two-body orbital mechanics simulator with Kepler solvers, Lambert,
  Hohmann, J2, ground tracks

---

## References

- Vallado, D. A., *Fundamentals of Astrodynamics and Applications*, 4th ed.
- Bate, R. R., Mueller, D. D., & White, J. E., *Fundamentals of Astrodynamics*.
- Curtis, H. D., *Orbital Mechanics for Engineering Students*, 3rd ed.
- Izzo, D. (2015), "Revisiting Lambert's problem," *Acta Astronautica*.
- Mikkola, A. (1987), "A cubic approximation for Kepler's equation."
- Kelso, T. S., "Frequently Asked Questions: Two-Line Element Set Format."
- Olson, D. K. (1996), "Converting Earth-Centered, Earth-Fixed Coordinates
  to Geodetic Coordinates."

---

## License

[MIT](LICENSE) © 2026 creative-projects