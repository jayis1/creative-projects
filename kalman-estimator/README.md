# kalman-estimator

A **from-scratch state-estimation library** implementing four core estimators
in pure Python + NumPy — no external filtering/estimation packages used.

## Estimators

| Class | Description |
|-------|-------------|
| `KalmanFilter` | Standard linear-discrete Kalman filter with Joseph-form covariance update |
| `ExtendedKalmanFilter` | Extended Kalman Filter (EKF) for nonlinear models via Jacobians |
| `UnscentedKalmanFilter` | Unscented Kalman Filter (UKF) using the scaled unscented transform |
| `RTSSmoother` / `smooth()` | Rauch-Tung-Striebel fixed-interval backward smoother |

## How it works

### Kalman Filter (linear)
Operates on linear models `x_k = F·x_{k-1} + B·u_k + w`, `z_k = H·x_k + v`.
Each step performs:
- **Predict**: `x = F·x + B·u`, `P = F·P·Fᵀ + Q`
- **Update**: innovation `y = z − H·x`, gain `K = P·Hᵀ·(H·P·Hᵀ + R)⁻¹`, then
  Joseph-form `P = (I−K·H)·P·(I−K·H)ᵀ + K·R·Kᵀ` for numerical stability.

### Extended Kalman Filter (EKF)
For nonlinear `f(x,u)` and `h(x)`, the EKF linearises around the current
estimate using user-supplied Jacobians `F_jac(x,u)` and `H_jac(x)`. The
recursion is identical to the linear KF but with the Jacobians replacing
the constant matrices.

### Unscented Kalman Filter (UKF)
Instead of linearising, the UKF propagates a deterministic set of **sigma
points** through the nonlinear functions and recovers the mean/covariance
via the unscented transform. No Jacobians needed. Uses the Merwe scaled
sigma-point parameterisation (α, β, κ).

### RTS Smoother
Given the forward-pass history (prior/posterior means and covariances at
each step), the RTS smoother runs a backward recursion:

```
C_k   = P_{k-1} · Fᵀ · (P_k⁻)⁻¹
x_s   = x_{k-1} + C_k · (x_s,k − x_k⁻)
P_s   = P_{k-1} + C_k · (P_s,k − P_k⁻) · C_kᵀ
```

producing smoothed estimates that use *all* measurements in the interval.

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

## Demo

```bash
python demo.py
```

Tracks a 1-D constant-velocity object through noisy measurements with all
four estimators and prints RMS errors. Example output:

```
RMS position error:
  Measurements: 1.083
  KF          : 0.576
  EKF         : 0.576
  UKF         : 0.576
  RTS smooth  : 0.255
```

## Tests

```bash
pytest tests/ -v
```

## File layout

```
kalman-estimator/
├── kalman_estimator/
│   ├── __init__.py     # public API
│   ├── kf.py           # linear Kalman filter
│   ├── ekf.py          # Extended Kalman filter
│   ├── ukf.py          # Unscented Kalman filter
│   └── smoother.py     # RTS smoother
├── tests/
│   └── test_basic.py
├── demo.py
├── pyproject.toml
└── README.md
```