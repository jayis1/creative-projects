# kalman-estimator

[![CI](https://github.com/jayis1/creative-projects/actions/workflows/kalman-estimator-ci.yml/badge.svg)](https://github.com/jayis1/creative-projects/actions/workflows/kalman-estimator-ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)
![Tests: 60](https://img.shields.io/badge/tests-60%20passing-brightgreen.svg)
![NumPy](https://img.shields.io/badge/depends%20on-numpy-orange.svg)

A **from-scratch state-estimation library** implementing eight estimators
plus diagnostics, batch utilities, config support, and a CLI — in pure
Python + NumPy. No external filtering/estimation packages used.

---

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Estimators & Utilities](#estimators--utilities)
- [Architecture](#architecture)
- [Usage](#usage)
  - [Linear Kalman Filter](#linear-kalman-filter)
  - [Extended Kalman Filter (EKF)](#extended-kalman-filter-ekf)
  - [Unscented Kalman Filter (UKF)](#unscented-kalman-filter-ukf)
  - [Information Filter](#information-filter)
  - [Adaptive Kalman Filter](#adaptive-kalman-filter)
  - [Ensemble Kalman Filter (EnKF)](#ensemble-kalman-filter-enkf)
  - [Particle Filter](#particle-filter)
  - [RTS Smoother](#rts-smoother)
  - [Numerical Jacobians](#numerical-jacobians)
  - [Diagnostics](#diagnostics)
  - [Batch / Monte Carlo](#batch--monte-carlo)
  - [Serialization](#serialization)
  - [Configuration Files](#configuration-files)
  - [CLI](#cli)
- [Demos & Examples](#demos--examples)
- [Testing](#testing)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Changelog](#changelog)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

`kalman-estimator` is a pure-Python state-estimation library implementing
every major variant of the Kalman filter from first principles — no
FilterPy, no pykalman, no scipy. Just NumPy. The code is readable and
auditable, making it ideal for learning, research, and production use
where transparency matters.

| Class / Function | Description |
|---|---|
| `KalmanFilter` | Standard linear-discrete Kalman filter (Joseph-form) |
| `ExtendedKalmanFilter` | EKF for nonlinear models via Jacobians |
| `UnscentedKalmanFilter` | UKF using the scaled unscented transform (no Jacobians) |
| `InformationFilter` | Information-form (dual) Kalman filter |
| `AdaptiveKalmanFilter` | Sage-Husa adaptive KF with online Q/R estimation |
| `EnsembleKalmanFilter` | Monte-Carlo ensemble Kalman filter |
| `ParticleFilter` | Bootstrap particle filter (SIR) with systematic resampling |
| `RTSSmoother` / `smooth()` | Rauch-Tung-Striebel fixed-interval backward smoother |
| `NumericalJacobianEKF` | EKF with automatic finite-difference Jacobians |
| `FilterDiagnostics` | NIS, NEES, log-likelihood, AIC/BIC |
| `batch_filter()` | Run a KF over multiple independent sequences |
| `monte_carlo_error()` | Average RMSE over Monte Carlo runs |
| `save_filter()` / `load_filter()` | JSON serialization |
| `load_config()` / `load_filter_from_config()` | JSON/TOML config support |

---

## Installation

```bash
cd kalman-estimator
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
```

**Requires:** Python ≥ 3.9, NumPy ≥ 1.20

---

## Quick Start

```python
import numpy as np
from kalman_estimator import KalmanFilter

# Track a 1-D object moving at constant velocity
kf = KalmanFilter(
    F=np.array([[1, 1], [0, 1]]),      # state transition
    H=np.array([[1, 0]]),              # observation
    Q=np.eye(2) * 0.01,                # process noise
    R=np.array([[2.0]]),              # measurement noise
    x0=[0.0, 0.0],                    # initial state
    P0=np.eye(2) * 10,                # initial covariance
)

for z in measurements:
    kf.predict()
    kf.update(z)
    print(f"Position: {kf.state[0]:.2f}, Velocity: {kf.state[1]:.2f}")
```

---

## Architecture

All estimators inherit from `BaseEstimator` (ABC), which defines the
common interface:

```
BaseEstimator (ABC)
├── predict(u=None)      # time-update
├── update(z)            # measurement-update
├── state (property)     # current mean estimate
├── covariance (property) # current covariance
├── step(z, u=None)      # convenience: predict + update
└── reset(x0, P0)        # reset to initial state
```

```
kalman_estimator/
├── __init__.py            # public API + version
├── __main__.py            # python -m kalman_estimator entry point
├── base.py                # BaseEstimator ABC
├── kf.py                  # KalmanFilter (linear, Joseph-form)
├── ekf.py                 # ExtendedKalmanFilter
├── ukf.py                 # UnscentedKalmanFilter (vectorised)
├── info_filter.py         # InformationFilter (dual form)
├── adaptive.py            # AdaptiveKalmanFilter (Sage-Husa)
├── enkf.py                # EnsembleKalmanFilter
├── particle_filter.py     # ParticleFilter (SIR)
├── smoother.py            # RTSSmoother + smooth()
├── diagnostics.py         # NIS/NEES/log-likelihood/AIC/BIC
├── batch.py               # batch_filter / monte_carlo_error
├── serialization.py       # JSON save/load
├── numerical_jacobian.py  # finite-difference Jacobians + NumericalJacobianEKF
├── config.py              # JSON/TOML config loading
├── cli.py                 # command-line interface
└── logging_util.py        # structured logging
```

### How Each Filter Works

#### Kalman Filter (linear)
Operates on linear models `x_k = F·x_{k-1} + B·u_k + w`, `z_k = H·x_k + v`.
- **Predict**: `x = F·x + B·u`, `P = F·P·Fᵀ + Q`
- **Update**: innovation `y = z − H·x`, gain `K = P·Hᵀ·(H·P·Hᵀ + R)⁻¹`,
  Joseph-form `P = (I−K·H)·P·(I−K·H)ᵀ + K·R·Kᵀ` for numerical stability.

#### Extended Kalman Filter (EKF)
For nonlinear `f(x,u)` and `h(x)`, the EKF linearises around the current
estimate using user-supplied Jacobians `F_jac(x,u)` and `H_jac(x)`.

#### Unscented Kalman Filter (UKF)
Instead of linearising, the UKF propagates a deterministic set of **sigma
points** through the nonlinear functions and recovers mean/covariance via
the unscented transform. Uses the Merwe scaled sigma-point parameterisation
(α, β, κ). Covariance is symmetrized after each update. The unscented
transform and update are **vectorised** with NumPy for performance.

#### Information Filter
The dual of the KF — maintains the information vector `y = P⁻¹x` and
information matrix `Y = P⁻¹` instead of `(x, P)`. Update is trivial
(just add information); prediction requires matrix inversion.

#### Adaptive Kalman Filter (Sage-Husa)
A KF that **learns** Q and R online from the innovation sequence using
exponential moving averages. Useful when noise statistics are unknown or
time-varying. Controlled by a forgetting factor `alpha ∈ (0, 1]`.

#### Ensemble Kalman Filter (EnKF)
Monte-Carlo variant that propagates an ensemble of N state samples.
The mean and covariance are estimated empirically from the ensemble.
Suitable for high-dimensional or nonlinear systems. Uses stochastic
(perturbed-observation) update.

#### Particle Filter (SIR)
A bootstrap particle filter that propagates a cloud of N weighted
particles. At each step: propagate → weight by likelihood → resample
when effective sample size drops. Uses systematic resampling (lower
variance than multinomial). Handles nonlinear, non-Gaussian models.

#### RTS Smoother
Given the forward-pass history, runs a backward recursion:
```
C_k = P_{k-1} · Fᵀ · (P_k⁻)⁻¹
x_s = x_{k-1} + C_k · (x_s,k − x_k⁻)
P_s = P_{k-1} + C_k · (P_s,k − P_k⁻) · C_kᵀ
```

#### FilterDiagnostics
- **NIS** (Normalized Innovation Squared): `yᵀ S⁻¹ y` — averages to
  `meas_dim` under a correct model. Chi-squared CI via Wilson-Hilferty.
- **NEES** (Normalized Estimation Error Squared): averages to `state_dim`.
- **Log-likelihood**, **AIC**, **BIC** for model comparison.

---

## Usage

### Linear Kalman Filter

```python
import numpy as np
from kalman_estimator import KalmanFilter

kf = KalmanFilter(
    F=np.array([[1, 1], [0, 1]]),
    H=np.array([[1, 0]]),
    Q=np.eye(2) * 0.01,
    R=np.array([[2.0]]),
    x0=[0.0, 0.0],
    P0=np.eye(2) * 10,
)
for z in measurements:
    kf.predict()
    kf.update(z)
    print(kf.state)

# Or use step() for convenience:
state = kf.step(np.array([5.0]))
```

### Extended Kalman Filter (EKF)

```python
from kalman_estimator import ExtendedKalmanFilter

ekf = ExtendedKalmanFilter(
    f=my_transition,       # f(x, u) -> x_next
    h=my_measurement,      # h(x) -> z
    F_jac=jac_f,           # F_jac(x, u) -> (n, n)
    H_jac=jac_h,           # H_jac(x) -> (m, n)
    Q=Q, R=R, x0=x0, P0=P0,
)
```

### Unscented Kalman Filter (UKF)

```python
from kalman_estimator import UnscentedKalmanFilter

ukf = UnscentedKalmanFilter(
    fx=lambda x, dt: transition(x, dt),
    hx=lambda x: measure(x),
    dt=0.1, Q=Q, R=R, x0=x0, P0=P0,
    alpha=1e-3, beta=2.0, kappa=0.0,  # sigma-point tuning
)
```

### Information Filter

```python
from kalman_estimator import InformationFilter

P0 = np.eye(2) * 10
Y0 = np.linalg.inv(P0)       # information matrix
y0 = Y0 @ np.array([0, 0])   # information vector

inf = InformationFilter(
    F=F, H=H, Q=Q, R=R,
    y0=y0, Y0=Y0,
)
inf.predict()
inf.update(np.array([5.0]))
print(inf.state)         # recovers x = Y⁻¹ y
print(inf.covariance)    # recovers P = Y⁻¹
```

### Adaptive Kalman Filter

```python
from kalman_estimator import AdaptiveKalmanFilter

akf = AdaptiveKalmanFilter(
    F=F, H=H, Q=Q, R=R, x0=x0, P0=P0,
    alpha=0.95,      # forgetting factor
    adapt_Q=True,    # learn process noise
    adapt_R=True,    # learn measurement noise
)
# After running:
print(akf.estimated_R)  # adapted measurement noise
print(akf.estimated_Q)  # adapted process noise
```

### Ensemble Kalman Filter (EnKF)

```python
from kalman_estimator import EnsembleKalmanFilter

enkf = EnsembleKalmanFilter(
    f=lambda x: F @ x,   # transition (nonlinear OK)
    h=lambda x: np.array([x[0]]),  # measurement
    Q=Q, R=R, x0=x0, P0=P0,
    N=100,               # ensemble size
    seed=42,
)
print(enkf.ensemble_members)  # (N, n) array of particles
```

### Particle Filter

```python
from kalman_estimator import ParticleFilter

pf = ParticleFilter(
    f=lambda x, u=None: F @ x,
    h=lambda x: np.array([x[0]]),
    Q=Q, R=R, x0=x0, P0=P0,
    N=500,
    resample_threshold=0.5,
    seed=42,
)
# After update:
print(pf.effective_sample_size)  # N_eff = 1 / Σw²
```

### RTS Smoother

```python
from kalman_estimator import smooth
kf = KalmanFilter(...)
x_filt, P_filt, x_smooth, P_smooth = smooth(kf, measurements)
```

### Numerical Jacobians

```python
from kalman_estimator import numerical_jacobian, NumericalJacobianEKF

# Standalone Jacobian computation:
J = numerical_jacobian(my_func, x, eps=1e-6)

# EKF with automatic finite-difference Jacobians:
ekf = NumericalJacobianEKF(f, h, Q, R, x0=x0, P0=P0, eps=1e-6)
```

### Diagnostics

```python
from kalman_estimator import FilterDiagnostics
diag = FilterDiagnostics(state_dim=2, meas_dim=1)
# after each filter step:
diag.record(innovation, S, kf.state, kf.covariance, true_state=...)
summary = diag.summary()  # NIS mean, NEES mean, log-lik, etc.
```

### Batch / Monte Carlo

```python
from kalman_estimator import batch_filter, monte_carlo_error
results = batch_filter(meas_list, F, H, Q, R, x0, P0)
rmse = monte_carlo_error(meas_list, true_list, F, H, Q, R, x0, P0)
```

### Serialization

```python
from kalman_estimator import save_filter, load_filter
save_filter(kf, "run.json", include_history=True, history=hist_dict)
kf2, hist = load_filter("run.json")
```

### Configuration Files

JSON config (`config.json`):
```json
{
    "filter": "kalman",
    "F": [[1, 1], [0, 1]],
    "H": [[1, 0]],
    "Q": [[0.01, 0], [0, 0.01]],
    "R": [[2.0]],
    "x0": [0.0, 0.0],
    "P0": [[10, 0], [0, 10]]
}
```

```python
from kalman_estimator import load_filter_from_config
kf = load_filter_from_config("config.json")
```

### CLI

```bash
# Run a simulation with a specific filter
kalman-estimator simulate --filter ukf --steps 100 --noise 2.0 --diagnostics

# Compare all filters on the same data
kalman-estimator compare --steps 200 --noise 3.0

# Run from a config file with measurement data
kalman-estimator run --config my_config.json --measurements data.json

# Save results to JSON
kalman-estimator simulate --filter kf --steps 50 --output results.json

# Available filters: kf, ekf, ukf, adaptive, enkf, pf
```

---

## Demos & Examples

### `demo.py` — Linear constant-velocity tracking
```bash
python demo.py
```
Tracks a 1-D object with KF, EKF, UKF, and RTS smoother.
```
RMS position error:
  Measurements: 1.083
  KF          : 0.576
  EKF         : 0.576
  UKF         : 0.576
  RTS smooth  : 0.255
```

### `demo_nonlinear.py` — Nonlinear falling object with drag
```bash
python demo_nonlinear.py
```
Tracks a falling object with quadratic drag using EKF and UKF.

### `examples/compare_all_filters.py`
Runs all 8 estimators on the same data and prints a comparison table.
```bash
python examples/compare_all_filters.py
```
```
=================================================================
  Filter Comparison on 1-D Constant-Velocity Tracking
=================================================================
  Filter            Pos RMSE   Vel RMSE   Improv %
  -------------------------------------------------
  Measurements        1.5488         --        0.0
  KF                  0.7703     0.1851      50.3%
  EKF                 0.7703     0.1851      50.3%
  UKF                 0.7703     0.1851      50.3%
  InfoFilter          0.7703     0.1851      50.3%
  AdaptiveKF          1.4995     1.8713       3.2%
  EnKF                0.7950     0.1890      48.7%
  PF                  1.1493     0.1697      25.8%
  RTS                 0.4427     0.0503      71.4%
=================================================================
```

### `examples/gps_tracking.py`
2-D GPS-like position tracking with KF + RTS smoother + diagnostics.

### `examples/config_example.py`
Demonstrates JSON config-file usage.

---

## Testing

```bash
pytest tests/ -v
```

**60 tests** covering:
- Filter convergence and covariance symmetry
- EKF/UKF linear equivalence to KF
- Information filter equivalence to KF
- Adaptive KF noise estimation
- EnKF and Particle Filter tracking
- RTS smoothing error reduction
- Diagnostics (NIS/NEES/log-lik/AIC/BIC)
- Batch filtering and Monte Carlo RMSE
- Serialization round-trip
- Numerical Jacobian accuracy
- Config file loading (JSON, info filter, unknown type)
- CLI commands (simulate, compare, run)
- Input validation (NaN rejection, dimension checks)
- Singular covariance handling
- UKF control-input forwarding and vectorisation
- BaseEstimator ABC, inheritance, reset

---

## Known Issues (Resolved)

1. **UKF `predict(u)` silently ignored control input** — fixed: forwards `u` to `fx`.
2. **KF/EKF/UKF crashed on singular innovation covariance** — fixed: descriptive `ValueError`.
3. **RTS smoother crashed on singular predicted covariance** — fixed.
4. **Diagnostics NIS/NEES/log-likelihood crashed on singular matrices** — fixed: uses `pinv`.
5. **UKF covariance could lose symmetry** — fixed: symmetrized after each update.
6. **BIC `log(0)` with zero data** — fixed: returns `NaN` gracefully.
7. **Log-likelihood crashed on singular S** — fixed: fallback logdet.

---

## Changelog

### v3.0.0 (comprehensive improvement)
- **+4 new estimators**: InformationFilter, AdaptiveKalmanFilter (Sage-Husa),
  EnsembleKalmanFilter, ParticleFilter (SIR)
- **BaseEstimator ABC** — all filters inherit from a common interface
- **Numerical Jacobian** computation (central finite differences) +
  NumericalJacobianEKF wrapper
- **CLI** (`kalman-estimator` command) with `simulate`, `compare`, `run` subcommands
- **Config file support** (JSON/TOML) with `load_filter_from_config()`
- **Structured logging** utility
- **`__main__.py`** entry point (`python -m kalman_estimator`)
- **Type hints** on all public methods
- **Vectorised UKF** unscented transform and update (removed Python loops)
- **3 example scripts**: compare_all_filters, gps_tracking, config_example
- **GitHub Actions CI** (Python 3.9–3.12)
- **LICENSE** (MIT) and **CONTRIBUTING.md**
- **32 new tests** (60 total, all passing)
- Updated `pyproject.toml` with entry points, classifiers, keywords

### v2.0.0 (enhance + bug hunt)
- FilterDiagnostics, batch filtering, Monte Carlo RMSE, JSON serialization
- Nonlinear falling-object demo (EKF + UKF)
- Input validation across all filters
- 7 bug fixes (see Known Issues above)

### v1.0.0 (initial)
- KalmanFilter, ExtendedKalmanFilter, UnscentedKalmanFilter, RTSSmoother

---

## Roadmap

- [ ] Square-root Kalman filter (Cholesky-based, never forms P explicitly)
- [ ] Cubature Kalman Filter (CKF)
- [ ] Iterated EKF (IEKF) for stronger nonlinearity handling
- [ ] Constant-turn and constant-acceleration motion models
- [ ] Matplotlib-based visualisation utilities
- [ ] Async/streaming mode for real-time estimation
- [ ] C++ extension for performance-critical loops
- [ ] Kalman smoother for EKF/UKF (not just linear KF)
- [ ] Multi-sensor fusion support
- [ ] Parameter optimisation (grid search / Bayes optimisation for Q/R)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style
guidelines, and PR checklist.

---

## License

MIT — see [LICENSE](LICENSE).