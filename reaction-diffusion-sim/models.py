"""
Reaction kinetics for various Turing pattern models.

Each model defines:
- params: dict of default parameters
- react(u, v, params): returns (du_react, dv_react) — the reaction part
- default_state(n): returns (u_init, v_init) — default initial concentrations
- default_perturbation(): returns a perturbation config dict
- stability_range(): returns (dt_max, clamp) for numerical safety

Models implemented:
- Gray-Scott: classic activator-inhibitor producing spots, labyrinths, mitosis
- FitzHugh-Nagumo: excitable medium producing traveling pulses and spirals
- Gierer-Meinhardt: activator-inhibitor with saturating production
- Brusselator: oscillating chemical reaction network
"""

import numpy as np

# Maximum value for clamping concentrations to prevent numerical overflow
MAX_CONCENTRATION = 1e6
MIN_CONCENTRATION = -1e6


def _clamp_field(field, lo=MIN_CONCENTRATION, hi=MAX_CONCENTRATION):
    """Clamp field values to prevent overflow in subsequent operations."""
    return np.clip(field, lo, hi)


# ──────────────────────────────────────────────────────
# Gray-Scott Model
# ∂u/∂t = Du·∇²u - u·v² + F·(1-u)
# ∂v/∂t = Dv·∇²v + u·v² - (F+k)·v
#
# The classic Gray-Scott model produces an enormous variety of patterns
# depending on F (feed rate) and k (kill rate). See Pearson (1993) for
# a comprehensive parameter space map.
# ──────────────────────────────────────────────────────

GRAY_SCOTT_DEFAULTS = {
    "Du": 0.16,
    "Dv": 0.08,
    "F": 0.035,   # feed rate: controls how fast u is replenished
    "k": 0.065,   # kill rate: controls how fast v is removed
}


def gray_scott_react(u, v, params):
    """Gray-Scott reaction kinetics.
    
    The autocatalytic reaction u + 2v → 3v is the core mechanism.
    F feeds u and (F+k) removes v, creating the activator-inhibitor dynamic.
    """
    F = params.get("F", 0.035)
    k = params.get("k", 0.065)
    uvv = u * v * v
    du = -uvv + F * (1.0 - u)
    dv = uvv - (F + k) * v
    return du, dv


def gray_scott_default_state(n, params=None):
    """Default Gray-Scott state: u=1, v=0 (stable homogeneous state)."""
    u = np.ones((n, n), dtype=np.float64)
    v = np.zeros((n, n), dtype=np.float64)
    return u, v


def gray_scott_perturbation():
    return {"type": "center_square", "size": 20, "u_val": 0.0, "v_val": 1.0}


# ──────────────────────────────────────────────────────
# FitzHugh-Nagumo Model
# ∂u/∂t = Du·∇²u + u - u³/3 - v
# ∂v/∂t = Dv·∇²v + ε(u + β - γv)
#
# A 2-variable reduction of the Hodgkin-Huxley neuron model.
# Produces traveling pulses and spiral waves in 2D.
# ──────────────────────────────────────────────────────

FITZHUGH_NAGUMO_DEFAULTS = {
    "Du": 0.001,
    "Dv": 0.004,
    "epsilon": 0.04,
    "beta": 0.5,
    "gamma": 1.0,
}


def fitzhugh_nagumo_react(u, v, params):
    """FitzHugh-Nagumo reaction kinetics.
    
    u is the fast activator (cubic nullcline), v is the slow inhibitor (linear nullcline).
    epsilon controls the timescale separation — smaller epsilon = sharper pulses.
    """
    epsilon = params.get("epsilon", 0.04)
    beta = params.get("beta", 0.5)
    gamma = params.get("gamma", 1.0)
    du = u - u ** 3 / 3.0 - v
    dv = epsilon * (u + beta - gamma * v)
    return du, dv


def fitzhugh_nagumo_default_state(n, params=None):
    """Default FHN state: resting near the fixed point.
    
    The fixed point of u - u³/3 - v = 0 with v = (u + β)/γ is found
    by solving u - u³/3 = (u + β)/γ numerically. We use scipy.optimize
    or a bisection-based approach for robustness.
    
    Args:
        n: Grid size
        params: Optional dict with 'beta' and 'gamma' keys. If None, uses defaults.
    """
    if params is not None:
        beta = params.get("beta", 0.5)
        gamma = params.get("gamma", 1.0)
    else:
        beta = 0.5
        gamma = 1.0
    
    # Find fixed point: solve f(u) = u - u³/3 - (u+beta)/gamma = 0
    # Use bisection in [-3, 3] which brackets the leftmost root for typical params
    def f(u):
        return u - u ** 3 / 3.0 - (u + beta) / gamma
    
    # Bisection method for robust root-finding
    lo, hi = -3.0, 0.0
    for _ in range(50):  # 50 iterations gives ~15 digits of accuracy
        mid = (lo + hi) / 2.0
        if f(mid) * f(lo) < 0:
            hi = mid
        else:
            lo = mid
    u_eq = (lo + hi) / 2.0
    v_eq = (u_eq + beta) / gamma
    
    u = np.full((n, n), u_eq, dtype=np.float64)
    v = np.full((n, n), v_eq, dtype=np.float64)
    return u, v


def fitzhugh_nagumo_perturbation():
    return {"type": "center_square", "size": 10, "u_val": 1.0, "v_val": 0.5}


# ──────────────────────────────────────────────────────
# Gierer-Meinhardt Model
# ∂u/∂t = Du·∇²u + u²/v - u + ρ
# ∂v/∂t = Dv·∇²v + u² - μv
#
# A classic activator-inhibitor model for biological pattern formation.
# Note: requires v > 0 to avoid division by zero; concentrations are
# clamped for numerical stability.
# ──────────────────────────────────────────────────────

GIERER_MEINHARDT_DEFAULTS = {
    "Du": 0.02,
    "Dv": 0.4,
    "rho": 0.001,
    "mu": 0.02,
}


def gierer_meinhardt_react(u, v, params):
    """Gierer-Meinhardt reaction kinetics.
    
    The u²/v term provides saturating autocatalysis (as v grows, the
    activation weakens). The small ρ term ensures u doesn't go to zero.
    Fields are clamped to prevent numerical overflow from the u²/v term.
    """
    rho = params.get("rho", 0.001)
    mu = params.get("mu", 0.02)
    # Clamp to prevent overflow in the u²/v term
    u = _clamp_field(u, 0, MAX_CONCENTRATION)
    v_safe = np.maximum(v, 1e-10)  # prevent division by zero
    du = u * u / v_safe - u + rho
    dv = u * u - mu * v
    return du, dv


def gierer_meinhardt_default_state(n, params=None):
    """Default GM state: uniform concentrations with small random perturbations."""
    rng = np.random.default_rng(42)
    u = np.ones((n, n), dtype=np.float64) * 0.5 + rng.normal(0, 0.01, (n, n))
    v = np.ones((n, n), dtype=np.float64) * 1.0 + rng.normal(0, 0.01, (n, n))
    return u, v


def gierer_meinhardt_perturbation():
    return {"type": "random", "noise": 0.01}


# ──────────────────────────────────────────────────────
# Brusselator Model
# ∂u/∂t = Du·∇²u + A - (B+1)u + u²v
# ∂v/∂t = Dv·∇²v + Bu - u²v
#
# The Brusselator (Prigogine & Lefever, 1968) is the simplest known
# model that exhibits oscillating chemical patterns. When B > 1 + A²,
# the homogeneous steady state becomes unstable (Turing instability).
# ──────────────────────────────────────────────────────

BRUSSELATOR_DEFAULTS = {
    "Du": 0.002,
    "Dv": 0.008,
    "A": 1.0,
    "B": 3.0,
}


def brusselator_react(u, v, params):
    """Brusselator reaction kinetics.
    
    The steady state is (u,v) = (A, B/A). When B > 1+A² and Dv >> Du,
    diffusion-driven instability creates spatial patterns.
    Fields are clamped for numerical stability.
    """
    A = params.get("A", 1.0)
    B = params.get("B", 3.0)
    # Clamp to prevent runaway growth
    u = _clamp_field(u, -10, 10)
    v = _clamp_field(v, -10, 10)
    du = A - (B + 1) * u + u * u * v
    dv = B * u - u * u * v
    return du, dv


def brusselator_default_state(n, params=None):
    """Default Brusselator state: near steady state (A, B/A).
    
    Args:
        n: Grid size
        params: Optional dict with 'A' and 'B' keys. If None, uses defaults.
    """
    if params is not None:
        A = params.get("A", 1.0)
        B = params.get("B", 3.0)
    else:
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
        "stability_clamp": (0, 1),  # u and v stay in [0, 1] for GS
    },
    "fhn": {
        "react": fitzhugh_nagumo_react,
        "defaults": FITZHUGH_NAGUMO_DEFAULTS,
        "default_state": fitzhugh_nagumo_default_state,
        "perturbation": fitzhugh_nagumo_perturbation,
        "param_names": ["Du", "Dv", "epsilon", "beta", "gamma"],
        "description": "FitzHugh-Nagumo: traveling pulses and spirals",
        "stability_clamp": (-3, 3),  # FHN can have negative values
    },
    "gierer-meinhardt": {
        "react": gierer_meinhardt_react,
        "defaults": GIERER_MEINHARDT_DEFAULTS,
        "default_state": gierer_meinhardt_default_state,
        "perturbation": gierer_meinhardt_perturbation,
        "param_names": ["Du", "Dv", "rho", "mu"],
        "description": "Gierer-Meinhardt: self-amplifying spots",
        "stability_clamp": (0, None),  # u,v must be positive
    },
    "brusselator": {
        "react": brusselator_react,
        "defaults": BRUSSELATOR_DEFAULTS,
        "default_state": brusselator_default_state,
        "perturbation": brusselator_perturbation,
        "param_names": ["Du", "Dv", "A", "B"],
        "description": "Brusselator: oscillating chemical patterns",
        "stability_clamp": (-1, 10),  # moderate range
    },
}


def get_model(name):
    """Get model config by name. Raises ValueError for unknown models."""
    if name not in MODELS:
        available = ", ".join(MODELS.keys())
        raise ValueError(f"Unknown model '{name}'. Available: {available}")
    return MODELS[name]