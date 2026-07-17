# Orbital Mechanics Simulator

A pure-Python library for two-body orbital mechanics: Keplerian element
conversions, orbit propagation, Lambert's problem, orbital transfer
maneuvers, perturbations, and ground-track / look-angle computations.

## Features

- **Kepler solvers** — Newton-iteration solvers for elliptic (`M = E - e·sin E`),
  hyperbolic (`M = e·sinh H - H`), parabolic (Barker's equation, closed-form
  Cardano solution), and the universal-variable form, with Mikkola starters
  and step damping for high-eccentricity stability.
- **State-vector ↔ orbital elements** — full conversion between Cartesian
  `(r, v)` and classical Keplerian elements `(a, e, i, Ω, ω, ν)`, handling
  equatorial, circular, and degenerate orbits.  Includes `true_to_eccentric`
  and `eccentric_to_true` conversions.
- **Propagation** — four propagators:
  - `propagate_kepler` — analytic (exact for two-body, elliptic + hyperbolic)
  - `propagate_rk4` / `propagate_cowell` — fixed-step RK4 with optional perturbations
  - `propagate_universal` — universal-variable (all conic sections: elliptic, parabolic, hyperbolic)
  - `propagate_j2_secular` — SGP4-like secular J2 drift (RAAN, argp, mean anomaly rates)
  - `multi_step_propagate` — generate a time series of states
- **Maneuvers** — Hohmann transfer, bi-elliptic transfer, Lambert's problem
  solver (universal-variable with corrected tof equation), plane change
  (simple and combined), minimum-energy transfer time, porkchop plot data
  generation.
- **Perturbations** — J2 oblateness acceleration and exponential-atmosphere
  drag, composable with the Cowell propagator.
- **Ground track & look angles** — ECI↔ECEF frame rotations, geodetic
  latitude/longitude/altitude conversion, sub-satellite point tracking,
  and topocentric elevation/azimuth/range from a ground site.
- **Multiple central bodies** — predefined parameters for Earth, Moon, Sun,
  Mars, and Venus.
- **Rich data classes** — `StateVector` and `OrbitalElements` with `__repr__`,
  validation, comparison, and computed properties (period, mean motion,
  perigee/apogee, energy, orbit type, etc.).

## Installation

No external dependencies beyond NumPy. Clone and import:

```bash
cd orbital-mechanics
python3 demo.py          # run all 23 smoke tests
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

### Universal-Variable Propagation (any orbit type)

```python
from orbital import EARTH, OrbitalElements, elements_to_rv, propagate_universal
# Hyperbolic flyby
elems = OrbitalElements(a=-10e6, e=1.5, i=0, raan=0, argp=0, nu=math.radians(30))
sv = elements_to_rv(elems, EARTH)
sv_f = propagate_universal(sv, EARTH, 600.0)  # works for any conic
```

### J2 Secular Propagation

```python
from orbital import (EARTH, OrbitalElements, elements_to_rv,
                     propagate_j2_secular, rv_to_elements)
elems = OrbitalElements(a=7000e3, e=0.01, i=math.radians(51.6),
                         raan=0, argp=0, nu=0)
sv0 = elements_to_rv(elems, EARTH)
sv = propagate_j2_secular(sv0, EARTH, 86400)  # 1 day
elems2 = rv_to_elements(sv, EARTH)
print(f"RAAN drift: {math.degrees(elems2.raan):.4f}°/day")
```

### Plane Change Maneuver

```python
from orbital import plane_change_delta_v, combined_plane_change_delta_v
# Pure 28.5° plane change at 7.5 km/s
dv = plane_change_delta_v(7546.0, math.radians(28.5))  # ~3715 m/s
# Combined speed + plane change
dv = combined_plane_change_delta_v(7546.0, 3070.0, math.radians(28.5))
```

### Porkchop Plot Data

```python
from orbital import EARTH, porkchop_data
import numpy as np
r1 = np.array([7000e3, 0, 0])
r2 = np.array([0, 7000e3, 0])
data = porkchop_data(EARTH, r1, r2, (1000, 3000), n_tof=50)
for tof, v1, v2 in data:
    print(f"tof={tof:.0f}s, |v1|={v1:.1f}, |v2|={v2:.1f}")
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
├── __init__.py       — public API exports (v2.0)
├── bodies.py         — celestial body parameters (Earth, Moon, Sun, Mars, Venus)
├── frames.py         — rotation matrices (rot1/rot2/rot3), ECI↔ECEF
├── kepler.py         — Kepler equation solvers (elliptic, hyperbolic, Barker, universal)
│                       Mikkola starter, Stumpff functions, step damping
├── elements.py       — OrbitalElements/StateVector with validation & repr,
│                       rv↔elements, true↔eccentric↔mean anomaly conversions
├── twobody.py        — 4 propagators: Kepler, RK4/Cowell, universal, J2-secular
│                       + multi_step_propagate for time series
├── maneuvers.py      — Hohmann, bi-elliptic, Lambert, plane change,
│                       minimum-energy tof, porkchop data, Δv
├── perturbations.py  — J2 oblateness & atmospheric drag accelerations
└── groundtrack.py    — ECEF conversion, geodetic lat/lon, look angles, ground track
```

## Testing

```bash
python3 demo.py    # 23 smoke tests covering all modules
```

## References

- Vallado, D. A., *Fundamentals of Astrodynamics and Applications*, 4th ed.
- Bate, R. R., Mueller, D. D., & White, J. E., *Fundamentals of Astrodynamics*.
- Curtis, H. D., *Orbital Mechanics for Engineering Students*, 3rd ed.
- Izzo, D. (2015), "Revisiting Lambert's problem," *Acta Astronautica*.
- Mikkola, A. (1987), "A cubic approximation for Kepler's equation."