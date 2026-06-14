"""
Reaction kinetics for various Turing pattern models.

Each model defines:
- params: dict of default parameters
- react(u, v, params): returns (du_react, dv_react) — the reaction part
- default_state(n): returns (u_init, v_init) — default initial concentrations
- default_perturbation(): returns a perturbation config dict
"""

import numpy as np


# ──────────────────────────────────────────────────────
# Gray-Scott Model
# ∂u/∂t = Du·∇²u - u·v² + F·(1-u)
# ∂v/∂t = Dv·∇²v + u·v² - (F+k)·v
# ──────────────────────────────────────────────────────

GRAY_SCOTT_DEFAULTS = {
    "Du": 0.16,
    "Dv": 0.08,
    "F": 0.035,   # feed rate
    "k": 0.065,   # kill rate
}


def gray_scott_react(u, v, params):
    """Gray-Scott reaction kinetics."""
    F = params.get("F", 0.035)
    k = params.get("k", 0.065)
    uvv = u * v * v
    du = -uvv + F * (1.0 - u)
    dv = uvv - (F + k) * v
    return du, dv


def gray_scott_default_state(n):
    """Default Gray-Scott state: u=1, v=0 with central perturbation."""
    u = np.ones((n, n), dtype=np.float64)
    v = np.zeros((n, n), dtype=np.float64)
    return u, v


def gray_scott_perturbation():
    return {"type": "center_square", "size": 20, "u_val": 0.0, "v_val": 1.0}


# ──────────────────────────────────────────────────────
# FitzHugh-Nagumo Model
# ∂u/∂t = Du·∇²u + u - u³/3 - v
# ∂v/∂t = Dv·∇²v + ε(u + β - γv)
# ──────────────────────────────────────────────────────

FITZHUGH_NAGUMO_DEFAULTS = {
    "Du": 0.001,
    "Dv": 0.004,
    "epsilon": 0.04,
    "beta": 0.5,
    "gamma": 1.0,
}


def fitzhugh_nagumo_react(u, v, params):
    """FitzHugh-Nagumo reaction kinetics."""
    epsilon = params.get("epsilon", 0.04)
    beta = params.get("beta", 0.5)
    gamma = params.get("gamma", 1.0)
    du = u - u ** 3 / 3.0 - v
    dv = epsilon * (u + beta - gamma * v)
    return du, dv


def fitzhugh_nagumo_default_state(n):
    """Default FHN state: resting at (u≈-1.2, v≈-0.6)."""
    u = np.full((n, n), -1.0, dtype=np.float64)
    v = np.full((n, n), -0.5, dtype=np.float64)
    return u, v


def fitzhugh_nagumo_perturbation():
    return {"type": "center_square", "size": 10, "u_val": 1.0, "v_val": 0.5}


# ──────────────────────────────────────────────────────
# Gierer-Meinhardt Model
# ∂u/∂t = Du·∇²u + u²/v - u + ρ
# ∂v/∂t = Dv·∇²v + u² - μv
# ──────────────────────────────────────────────────────

GIERER_MEINHARDT_DEFAULTS = {
    "Du": 0.02,
    "Dv": 0.4,
    "rho": 0.001,
    "mu": 0.02,
}


def gierer_meinhardt_react(u, v, params):
    """Gierer-Meinhardt reaction kinetics. v is clamped to avoid division by zero."""
    rho = params.get("rho", 0.001)
    mu = params.get("mu", 0.02)
    v_safe = np.maximum(v, 1e-10)
    du = u * u / v_safe - u + rho
    dv = u * u - mu * v
    return du, dv


def gierer_meinhardt_default_state(n):
    """Default GM state: small random perturbations around uniform state."""
    u = np.ones((n, n), dtype=np.float64) * 0.5
    v = np.ones((n, n), dtype=np.float64) * 1.0
    return u, v


def gierer_meinhardt_perturbation():
    return {"type": "random", "noise": 0.01}


# ──────────────────────────────────────────────────────
# Brusselator Model
# ∂u/∂t = Du·∇²u + A - (B+1)u + u²v
# ∂v/∂t = Dv·∇²v + Bu - u²v
# ──────────────────────────────────────────────────────

BRUSSELATOR_DEFAULTS = {
    "Du": 0.002,
    "Dv": 0.008,
    "A": 1.0,
    "B": 3.0,
}


def brusselator_react(u, v, params):
    """Brusselator reaction kinetics."""
    A = params.get("A", 1.0)
    B = params.get("B", 3.0)
    du = A - (B + 1) * u + u * u * v
    dv = B * u - u * u * v
    return du, dv


def brusselator_default_state(n):
    """Default Brusselator state: near steady state (A, B/A)."""
    A = 1.0
    B = 3.0
    u = np.ones((n, n), dtype=np.float64) * A
    v = np.ones((n, n), dtype=np.float64) * (B / A)
    return u, v


def brusselator_perturbation():
    return {"type": "random", "noise": 0.05}


# ──────────────────────────────────────────────────────
# Model Registry
# ──────────────────────────────────────────────────────

MODELS = {
    "gray-scott": {
        "react": gray_scott_react,
        "defaults": GRAY_SCOTT_DEFAULTS,
        "default_state": gray_scott_default_state,
        "perturbation": gray_scott_perturbation,
        "param_names": ["Du", "Dv", "F", "k"],
        "description": "Gray-Scott: spots, labyrinths, mitosis patterns",
    },
    "fhn": {
        "react": fitzhugh_nagumo_react,
        "defaults": FITZHUGH_NAGUMO_DEFAULTS,
        "default_state": fitzhugh_nagumo_default_state,
        "perturbation": fitzhugh_nagumo_perturbation,
        "param_names": ["Du", "Dv", "epsilon", "beta", "gamma"],
        "description": "FitzHugh-Nagumo: traveling pulses and spirals",
    },
    "gierer-meinhardt": {
        "react": gierer_meinhardt_react,
        "defaults": GIERER_MEINHARDT_DEFAULTS,
        "default_state": gierer_meinhardt_default_state,
        "perturbation": gierer_meinhardt_perturbation,
        "param_names": ["Du", "Dv", "rho", "mu"],
        "description": "Gierer-Meinhardt: self-amplifying spots",
    },
    "brusselator": {
        "react": brusselator_react,
        "defaults": BRUSSELATOR_DEFAULTS,
        "default_state": brusselator_default_state,
        "perturbation": brusselator_perturbation,
        "param_names": ["Du", "Dv", "A", "B"],
        "description": "Brusselator: oscillating chemical patterns",
    },
}


def get_model(name):
    """Get model config by name. Raises ValueError for unknown models."""
    if name not in MODELS:
        available = ", ".join(MODELS.keys())
        raise ValueError(f"Unknown model '{name}'. Available: {available}")
    return MODELS[name]