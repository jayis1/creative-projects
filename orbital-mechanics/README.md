# Orbital Mechanics Simulator

A pure-Python library for two-body orbital mechanics: Keplerian element
conversions, orbit propagation, Lambert's problem, orbital transfer
maneuvers, perturbations, and ground-track / look-angle computations.

## Features

- **Kepler solvers** — Newton-iteration solvers for elliptic (`M = E - e·sin E`),
  hyperbolic (`M = e·sinh H - H`), and the universal-variable form, with
  step damping for high-eccentricity stability.
- **State-vector ↔ orbital elements** — full conversion between Cartesian
  `(r, v)` and classical Keplerian elements `(a, e, i, Ω, ω, ν)`, handling
  equatorial, circular, and degenerate orbits.
- **Propagation** — analytic Kepler propagation (exact for two-body) and
  fixed-step RK4 numerical integration with optional perturbation
  accelerations (Cowell's method).
- **Maneuvers** — Hohmann transfer, bi-elliptic transfer, and Lambert's
  problem solver using the universal-variable formulation with a corrected
  time-of-flight equation.
- **Perturbations** — J2 oblateness acceleration and exponential-atmosphere
  drag, composable with the Cowell propagator.
- **Ground track & look angles** — ECI↔ECEF frame rotations, geodetic
  latitude/longitude/altitude conversion, sub-satellite point tracking,
  and topocentric elevation/azimuth/range from a ground site.
- **Multiple central bodies** — predefined parameters for Earth, Moon, Sun,
  Mars, and Venus.

## Installation

No external dependencies beyond NumPy. Clone and import:

```bash
cd orbital-mechanics
python3 demo.py          # run all smoke tests
python3 cli.py hohmann 6678 42164   # Hohmann LEO→GEO
```

## Usage Examples

### Hohmann Transfer (LEO to GEO)

```python
from orbital import EARTH, hohmann_transfer
res = hohmann_transfer(EARTH, 6678e3, 42164e3)
print(f"Δv = {res.dv_total:.1f} m/s, TOF = {res.tof/3600:.1f} h")
# Δv = 3881.5 m/s, TOF = 5.3 h
```

### Convert Elements to State Vector

```python
from orbital import EARTH, OrbitalElements, elements_to_rv
elems = OrbitalElements(a=7000e3, e=0.01, i=math.radians(51.6),
                         raan=0, argp=math.radians(30), nu=math.radians(45))
sv = elements_to_rv(elems, EARTH)
print(f"r = {sv.r} m, v = {sv.v} m/s")
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

### Propagate with J2 Perturbation

```python
from orbital import (EARTH, OrbitalElements, elements_to_rv,
                     propagate_cowell, j2_acceleration, rv_to_elements)
elems = OrbitalElements(a=7000e3, e=0.01, i=math.radians(51.6),
                         raan=0, argp=0, nu=0)
sv0 = elements_to_rv(elems, EARTH)
sv = propagate_cowell(sv0, EARTH, 86400, step=60,
                       extra_accel=lambda r,v,t: j2_acceleration(r, EARTH))
elems2 = rv_to_elements(sv, EARTH)
print(f"RAAN after 1 day: {math.degrees(elems2.raan):.4f}°")
```

### Ground Track

```python
from orbital import (EARTH, OrbitalElements, elements_to_rv,
                     propagate_kepler, ground_track)
elems = OrbitalElements(a=7000e3, e=0, i=math.radians(45), raan=0, argp=0, nu=0)
sv0 = elements_to_rv(elems, EARTH)
states = []
for k in range(20):
    s = propagate_kepler(sv0, EARTH, k * 600)
    s.t = k * 600
    states.append(s)
pts = ground_track(states, EARTH, gmst0=0.0)
for lat, lon in pts:
    print(f"  {math.degrees(lat):.2f}°, {math.degrees(lon):.2f}°")
```

## CLI

```
python3 cli.py hohmann 6678 42164           # Hohmann LEO→GEO
python3 cli.py elements 7000 0.01 51.6 0 30 45  # Elements→state vector
python3 cli.py lambert 7000 0 0 0 7000 0 1800   # Lambert's problem
python3 cli.py propagate 7000 0.01 51.6 0 30 45 3600  # Propagate orbit
python3 cli.py groundtrack 7000 51.6 600 10     # Ground track points
python3 cli.py j2 7000 0.01 51.6 86400          # J2 perturbation drift
```

## Architecture

```
orbital/
├── __init__.py       — public API exports
├── bodies.py         — celestial body parameters (Earth, Moon, Sun, Mars, Venus)
├── frames.py         — rotation matrices (rot1/rot2/rot3), ECI↔ECEF
├── kepler.py         — Kepler equation solvers (elliptic, hyperbolic, universal)
├── elements.py       — OrbitalElements/StateVector, rv↔elements conversions
├── twobody.py        — Kepler & RK4/Cowell propagators
├── maneuvers.py      — Hohmann, bi-elliptic, Lambert solver, Δv
├── perturbations.py  — J2 oblateness & atmospheric drag accelerations
└── groundtrack.py    — ECEF conversion, geodetic lat/lon, look angles, ground track
```

## Testing

```bash
python3 demo.py    # 10 smoke tests covering all modules
```

## References

- Vallado, D. A., *Fundamentals of Astrodynamics and Applications*, 4th ed.
- Bate, R. R., Mueller, D. D., & White, J. E., *Fundamentals of Astrodynamics*.
- Curtis, H. D., *Orbital Mechanics for Engineering Students*, 3rd ed.
- Izzo, D. (2015), "Revisiting Lambert's problem," *Acta Astronautica*.