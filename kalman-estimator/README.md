# kalman-estimator

A **from-scratch state-estimation library** implementing four core estimators
plus diagnostics, batch, and serialization utilities — in pure Python + NumPy.
No external filtering/estimation packages used.

## Estimators & Utilities

| Class / Function | Description |
|-------------------|-------------|
| `KalmanFilter` | Standard linear-discrete Kalman filter with Joseph-form covariance update |
| `ExtendedKalmanFilter` | Extended Kalman Filter (EKF) for nonlinear models via Jacobians |
| `UnscentedKalmanFilter` | Unscented Kalman Filter (UKF) using the scaled unscented transform |
| `RTSSmoother` / `smooth()` | Rauch-Tung-Striebel fixed-interval backward smoother |
| `FilterDiagnostics` | NIS, NEES, log-likelihood, AIC/BIC model-fit diagnostics |
| `batch_filter()` | Run a KF over multiple independent measurement sequences |
| `monte_carlo_error()` | Average RMSE over multiple Monte Carlo runs |
| `save_filter()` / `load_filter()` | JSON serialization of filter state and history |

## How it works

### Kalman Filter (linear)
Operates on linear models `x_k = F·x_{k-1} + B·u_k + w`, `z_k = H·x_k + v`.
Each step performs:
- **Predict**: `x = F·x + B·u`, `P = F·P·Fᵀ + Q`
- **Update**: innovation `y = z − H·x`, gain `K = P·Hᵀ·(H·P·Hᵀ + R)⁻¹`, then
  Joseph-form `P = (I−K·H)·P·(I−K·H)ᵀ + K·R·Kᵀ` for numerical stability.

Input validation: the `update()` method rejects NaN/Inf measurements and
mismatched dimensions.

### Extended Kalman Filter (EKF)
For nonlinear `f(x,u)` and `h(x)`, the EKF linearises around the current
estimate using user-supplied Jacobians `F_jac(x,u)` and `H_jac(x)`. The
recursion is identical to the linear KF but with the Jacobians replacing
the constant matrices. NaN/Inf measurements are rejected.

### Unscented Kalman Filter (UKF)
Instead of linearising, the UKF propagates a deterministic set of **sigma
points** through the nonlinear functions and recovers the mean/covariance
via the unscented transform. No Jacobians needed. Uses the Merwe scaled
sigma-point parameterisation (α, β, κ). The covariance is regularised with
a tiny jitter before Cholesky decomposition for numerical stability.

### RTS Smoother
Given the forward-pass history (prior/posterior means and covariances at
each step), the RTS smoother runs a backward recursion:

```
C_k   = P_{k-1} · Fᵀ · (P_k⁻)⁻¹
x_s   = x_{k-1} + C_k · (x_s,k − x_k⁻)
P_s   = P_{k-1} + C_k · (P_s,k − P_k⁻) · C_kᵀ
```

producing smoothed estimates that use *all* measurements in the interval.

### FilterDiagnostics
Records innovation sequences and (optionally) ground-truth states to compute:
- **NIS** (Normalized Innovation Squared): `yᵀ S⁻¹ y` — should average to
  `meas_dim` under a correct model. Chi-squared confidence interval computed
  via a pure-Python Wilson-Hilferty approximation (no scipy needed).
- **NEES** (Normalized Estimation Error Squared): `(x̂−x)ᵀ P⁻¹ (x̂−x)` —
  should average to `state_dim` if the filter is consistent.
- **Log-likelihood**: Gaussian log-likelihood of the measurement sequence.
- **AIC / BIC**: model selection criteria for comparing different filter
  parameterisations.

### Batch utilities
`batch_filter()` runs a fresh KF on each measurement sequence in a list
(same model parameters). `monte_carlo_error()` computes average per-dimension
RMSE over multiple runs — useful for Monte-Carlo tuning of Q/R.

### Serialization
`save_filter()` / `load_filter()` serialise the full filter state (F, H, Q,
R, B, x, P) and optionally the forward-pass history to JSON, enabling
checkpoint/resume of estimation runs.

## Installation

```bash
cd kalman-estimator
pip install -e .          # or just add the folder to PYTHONPATH
```

Requires NumPy ≥ 1.20.

## Usage

### Linear Kalman filter

```python
import numpy as np
from kalman_estimator import KalmanFilter

kf = KalmanFilter(
    F=np.array([[1, 1], [0, 1]]),   # constant-velocity model
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
```

### RTS smoothing

```python
from kalman_estimator import smooth
kf = KalmanFilter(...)
x_filt, P_filt, x_smooth, P_smooth = smooth(kf, measurements)
```

### EKF (nonlinear)

```python
from kalman_estimator import ExtendedKalmanFilter

ekf = ExtendedKalmanFilter(
    f=my_transition, h=my_measurement,
    F_jac=jac_f, H_jac=jac_h,
    Q=Q, R=R, x0=x0, P0=P0,
)
```

### UKF (nonlinear, no Jacobians)

```python
from kalman_estimator import UnscentedKalmanFilter

ukf = UnscentedKalmanFilter(
    fx=lambda x, dt: transition(x, dt),
    hx=lambda x: measure(x),
    dt=0.1, Q=Q, R=R, x0=x0, P0=P0,
)
```

### Diagnostics

```python
from kalman_estimator import FilterDiagnostics
diag = FilterDiagnostics(state_dim=2, meas_dim=1)
# after each filter step:
diag.record(innovation, S, kf.state, kf.covariance, true_state=...)
summary = diag.summary()  # dict of NIS mean, NEES mean, log-lik, AIC, BIC
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

## Demos

### `demo.py` — Linear constant-velocity tracking

```bash
python demo.py
```

Tracks a 1-D constant-velocity object with KF, EKF, UKF, and RTS smoother.

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

Tracks a falling object with quadratic air drag using EKF and UKF, jointly
estimating position, velocity, and the (unknown) drag coefficient.

```
Final state estimates (true = [-146.56, 31.22, 0.01]):
  EKF: pos=-147.74, vel=32.10, drag=0.0092
  UKF: pos=-147.73, vel=32.10, drag=0.0096

RMS errors:
  EKF position RMSE: 0.655
  UKF position RMSE: 0.652
  EKF drag    RMSE: 0.0391
  UKF drag    RMSE: 0.0792
```

## Tests

```bash
pytest tests/ -v
```

28 tests covering: filter convergence, covariance symmetry, EKF/UKF linear
equivalence, RTS smoothing, diagnostics (NIS/NEES/log-lik/AIC/BIC), batch
filtering, Monte Carlo error, serialization round-trip, nonlinear tracking,
input validation (NaN rejection, dimension checks), singular covariance
handling, UKF control-input forwarding, and BIC edge cases.

## Known Issues (Resolved)

The following bugs were identified during the Phase 3 bug hunt and have been
fixed with targeted patches + regression tests:

1. **UKF `predict(u)` silently ignored control input** — `predict()` accepted
   a `u` parameter but never forwarded it to the transition function `fx`.
   Fixed: `predict()` now inspects `fx`'s signature and passes `u` when
   supported. *(test: `test_ukf_predict_ignores_control_input`)*

2. **KF/EKF/UKF crashed with raw `LinAlgError` on singular innovation
   covariance** — `np.linalg.inv(S)` raised an unhelpful numpy exception when
   S was singular (e.g. zero process + measurement noise). Fixed: all three
   filters now catch `LinAlgError` and raise a descriptive `ValueError` with
   guidance. *(test: `test_kf_singular_innovation_cov`)*

3. **RTS smoother crashed on singular predicted covariance** — same
   `np.linalg.inv` issue in the backward recursion. Fixed with try/except and
   descriptive `ValueError`. *(covered by smoother robustness)*

4. **Diagnostics NIS/NEES/log-likelihood crashed on singular covariance** —
   `np.linalg.inv(P)` and `np.linalg.inv(S)` raised `LinAlgError` when
   matrices were singular. Fixed: switched to `np.linalg.pinv` for robust
   pseudo-inverse computation. *(test: `test_diagnostics_nees_singular_cov`)*

5. **UKF covariance could lose symmetry** — the update formula
   `P = P - K·S·Kᵀ` can accumulate floating-point asymmetry. Fixed: P is
   symmetrized after each update via `P = (P + Pᵀ) / 2`.
   *(test: `test_ukf_covariance_symmetry`)*

6. **BIC computation produced `RuntimeWarning: log(0)` with zero data** —
   `bic()` called `np.log(n)` with `n=0`. Fixed: returns `NaN` gracefully when
   no data has been recorded. *(test: `test_diagnostics_bic_zero_steps`)*

7. **Log-likelihood could crash on singular S** — `slogdet` returns
   `sign=0` for singular matrices. Fixed: detects `sign==0` and uses a
   large negative logdet fallback. *(covered by diagnostics robustness)*

## File layout

```
kalman-estimator/
├── kalman_estimator/
│   ├── __init__.py        # public API
│   ├── kf.py              # linear Kalman filter
│   ├── ekf.py             # Extended Kalman filter
│   ├── ukf.py             # Unscented Kalman filter
│   ├── smoother.py        # RTS smoother
│   ├── diagnostics.py     # NIS/NEES/log-likelihood/AIC/BIC
│   ├── batch.py           # batch & Monte Carlo utilities
│   └── serialization.py   # JSON save/load
├── tests/
│   ├── test_basic.py      # 6 core tests
│   └── test_enhanced.py   # 13 enhanced-feature tests
├── demo.py                # linear tracking demo
├── demo_nonlinear.py      # nonlinear falling-object demo
├── pyproject.toml
└── README.md
```