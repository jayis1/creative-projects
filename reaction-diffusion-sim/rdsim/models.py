"""
Reaction kinetics for various Turing pattern models.

Each model defines:
- react(u, v, params): returns (du_react, dv_react) — the reaction part
- default_state(n, params): returns (u_init, v_init) — default initial concentrations
- default_perturbation(): returns a perturbation config dict
- stability_clamp: (lo, hi) tuple for numerical safety

Models implemented:
- Gray-Scott: classic activator-inhibitor producing spots, labyrinths, mitosis
- FitzHugh-Nagumo: excitable medium producing traveling pulses and spirals
- Gierer-Meinhardt: activator-inhibitor with saturating production
- Brusselator: oscillating chemical reaction network
- Schnakenberg: simpler two-species model with Turing instability
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional, Tuple

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

# Maximum value for clamping concentrations to prevent numerical overflow
MAX_CONCENTRATION = 1e6
MIN_CONCENTRATION = -1e6


def _clamp_field(
    field: NDArray[np.floating],
    lo: float = MIN_CONCENTRATION,
    hi: float = MAX_CONCENTRATION,
) -> NDArray[np.floating]:
    """Clamp field values to prevent overflow in subsequent operations.

    Args:
        field: 2D numpy array of concentration values.
        lo: Minimum allowed value.
        hi: Maximum allowed value.

    Returns:
        Clamped array with same shape.
    """
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

GRAY_SCOTT_DEFAULTS: Dict[str, float] = {
    "Du": 0.16,
    "Dv": 0.08,
    "F": 0.035,
    "k": 0.065,
}


def gray_scott_react(
    u: NDArray[np.floating],
    v: NDArray[np.floating],
    params: Dict[str, float],
) -> Tuple[NDArray[np.floating], NDArray[np.floating]]:
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


def gray_scott_default_state(
    n: int,
    params: Optional[Dict[str, float]] = None,
) -> Tuple[NDArray[np.floating], NDArray[np.floating]]:
    """Default Gray-Scott state: u=1, v=0 (stable homogeneous state)."""
    u = np.ones((n, n), dtype=np.float64)
    v = np.zeros((n, n), dtype=np.float64)
    return u, v


def gray_scott_perturbation() -> Dict[str, Any]:
    return {"type": "center_square", "size": 20, "u_val": 0.0, "v_val": 1.0}


# ──────────────────────────────────────────────────────
# FitzHugh-Nagumo Model
# ∂u/∂t = Du·∇²u + u - u³/3 - v
# ∂v/∂t = Dv·∇²v + ε(u + β - γv)
#
# A 2-variable reduction of the Hodgkin-Huxley neuron model.
# Produces traveling pulses and spiral waves in 2D.
# ──────────────────────────────────────────────────────

FITZHUGH_NAGUMO_DEFAULTS: Dict[str, float] = {
    "Du": 0.001,
    "Dv": 0.004,
    "epsilon": 0.04,
    "beta": 0.5,
    "gamma": 1.0,
}


def fitzhugh_nagumo_react(
    u: NDArray[np.floating],
    v: NDArray[np.floating],
    params: Dict[str, float],
) -> Tuple[NDArray[np.floating], NDArray[np.floating]]:
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


def fitzhugh_nagumo_default_state(
    n: int,
    params: Optional[Dict[str, float]] = None,
) -> Tuple[NDArray[np.floating], NDArray[np.floating]]:
    """Default FHN state: resting near the fixed point.

    The fixed point of u - u³/3 - v = 0 with v = (u + β)/γ is found
    by solving u - u³/3 = (u + β)/γ numerically using bisection.

    Args:
        n: Grid size
        params: Optional dict with 'beta' and 'gamma' keys.
    """
    if params is not None:
        beta = params.get("beta", 0.5)
        gamma = params.get("gamma", 1.0)
    else:
        beta = 0.5
        gamma = 1.0

    def f(u: float) -> float:
        return u - u ** 3 / 3.0 - (u + beta) / gamma

    # Bisection method for robust root-finding
    lo, hi = -3.0, 0.0
    for _ in range(50):
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


def fitzhugh_nagumo_perturbation() -> Dict[str, Any]:
    return {"type": "center_square", "size": 10, "u_val": 1.0, "v_val": 0.5}


# ──────────────────────────────────────────────────────
# Gierer-Meinhardt Model
# ∂u/∂t = Du·∇²u + u²/v - u + ρ
# ∂v/∂t = Dv·∇²v + u² - μv
#
# A classic activator-inhibitor model for biological pattern formation.
# ──────────────────────────────────────────────────────

GIERER_MEINHARDT_DEFAULTS: Dict[str, float] = {
    "Du": 0.02,
    "Dv": 0.4,
    "rho": 0.001,
    "mu": 0.02,
}


def gierer_meinhardt_react(
    u: NDArray[np.floating],
    v: NDArray[np.floating],
    params: Dict[str, float],
) -> Tuple[NDArray[np.floating], NDArray[np.floating]]:
    """Gierer-Meinhardt reaction kinetics.

    The u²/v term provides saturating autocatalysis. Fields are clamped
    to prevent numerical overflow from the u²/v term.
    """
    rho = params.get("rho", 0.001)
    mu = params.get("mu", 0.02)
    u = _clamp_field(u, 0, MAX_CONCENTRATION)
    v_safe = np.maximum(v, 1e-10)
    du = u * u / v_safe - u + rho
    dv = u * u - mu * v
    return du, dv


def gierer_meinhardt_default_state(
    n: int,
    params: Optional[Dict[str, float]] = None,
) -> Tuple[NDArray[np.floating], NDArray[np.floating]]:
    """Default GM state: uniform concentrations with small random perturbations."""
    rng = np.random.default_rng(42)
    u = np.ones((n, n), dtype=np.float64) * 0.5 + rng.normal(0, 0.01, (n, n))
    v = np.ones((n, n), dtype=np.float64) * 1.0 + rng.normal(0, 0.01, (n, n))
    return u, v


def gierer_meinhardt_perturbation() -> Dict[str, Any]:
    return {"type": "random", "noise": 0.01}


# ──────────────────────────────────────────────────────
# Brusselator Model
# ∂u/∂t = Du·∇²u + A - (B+1)u + u²v
# ∂v/∂t = Dv·∇²v + Bu - u²v
#
# The simplest known model that exhibits oscillating chemical patterns.
# ──────────────────────────────────────────────────────

BRUSSELATOR_DEFAULTS: Dict[str, float] = {
    "Du": 0.002,
    "Dv": 0.008,
    "A": 1.0,
    "B": 3.0,
}


def brusselator_react(
    u: NDArray[np.floating],
    v: NDArray[np.floating],
    params: Dict[str, float],
) -> Tuple[NDArray[np.floating], NDArray[np.floating]]:
    """Brusselator reaction kinetics.

    The steady state is (u,v) = (A, B/A). When B > 1+A² and Dv >> Du,
    diffusion-driven instability creates spatial patterns.
    """
    A = params.get("A", 1.0)
    B = params.get("B", 3.0)
    u = _clamp_field(u, -10, 10)
    v = _clamp_field(v, -10, 10)
    du = A - (B + 1) * u + u * u * v
    dv = B * u - u * u * v
    return du, dv


def brusselator_default_state(
    n: int,
    params: Optional[Dict[str, float]] = None,
) -> Tuple[NDArray[np.floating], NDArray[np.floating]]:
    """Default Brusselator state: near steady state (A, B/A)."""
    if params is not None:
        A = params.get("A", 1.0)
        B = params.get("B", 3.0)
    else:
        A = 1.0
        B = 3.0
    u = np.ones((n, n), dtype=np.float64) * A
    v = np.ones((n, n), dtype=np.float64) * (B / A)
    return u, v


def brusselator_perturbation() -> Dict[str, Any]:
    return {"type": "random", "noise": 0.05}


# ──────────────────────────────────────────────────────
# Schnakenberg Model
# ∂u/∂t = Du·∇²u + a - u + u²v
# ∂v/∂t = Dv·∇²v + b - u²v
#
# A simpler two-species model with Turing instability.
# The steady state is (a+b, b/(a+b)²).
# ──────────────────────────────────────────────────────

SCHNAKENBERG_DEFAULTS: Dict[str, float] = {
    "Du": 0.005,
    "Dv": 0.1,
    "a": 0.1,
    "b": 0.9,
}


def schnakenberg_react(
    u: NDArray[np.floating],
    v: NDArray[np.floating],
    params: Dict[str, float],
) -> Tuple[NDArray[np.floating], NDArray[np.floating]]:
    """Schnakenberg reaction kinetics.

    A minimal two-species activator-inhibitor model. The u²v term provides
    autocatalysis, while the b term supplies v at a constant rate.
    """
    a = params.get("a", 0.1)
    b = params.get("b", 0.9)
    u_sq_v = u * u * v
    du = a - u + u_sq_v
    dv = b - u_sq_v
    return du, dv


def schnakenberg_default_state(
    n: int,
    params: Optional[Dict[str, float]] = None,
) -> Tuple[NDArray[np.floating], NDArray[np.floating]]:
    """Default Schnakenberg state: near steady state (a+b, b/(a+b)²)."""
    if params is not None:
        a = params.get("a", 0.1)
        b = params.get("b", 0.9)
    else:
        a = 0.1
        b = 0.9
    u_ss = a + b
    v_ss = b / (u_ss ** 2) if u_ss > 1e-10 else 1.0
    u = np.full((n, n), u_ss, dtype=np.float64)
    v = np.full((n, n), v_ss, dtype=np.float64)
    return u, v


def schnakenberg_perturbation() -> Dict[str, Any]:
    return {"type": "random", "noise": 0.05}


# ──────────────────────────────────────────────────────
# Model Registry
# ──────────────────────────────────────────────────────

MODELS: Dict[str, Dict[str, Any]] = {
    "gray-scott": {
        "react": gray_scott_react,
        "defaults": GRAY_SCOTT_DEFAULTS,
        "default_state": gray_scott_default_state,
        "perturbation": gray_scott_perturbation,
        "param_names": ["Du", "Dv", "F", "k"],
        "description": "Gray-Scott: spots, labyrinths, mitosis patterns",
        "stability_clamp": (0, 1),
    },
    "fhn": {
        "react": fitzhugh_nagumo_react,
        "defaults": FITZHUGH_NAGUMO_DEFAULTS,
        "default_state": fitzhugh_nagumo_default_state,
        "perturbation": fitzhugh_nagumo_perturbation,
        "param_names": ["Du", "Dv", "epsilon", "beta", "gamma"],
        "description": "FitzHugh-Nagumo: traveling pulses and spirals",
        "stability_clamp": (-3, 3),
    },
    "gierer-meinhardt": {
        "react": gierer_meinhardt_react,
        "defaults": GIERER_MEINHARDT_DEFAULTS,
        "default_state": gierer_meinhardt_default_state,
        "perturbation": gierer_meinhardt_perturbation,
        "param_names": ["Du", "Dv", "rho", "mu"],
        "description": "Gierer-Meinhardt: self-amplifying spots",
        "stability_clamp": (0, None),
    },
    "brusselator": {
        "react": brusselator_react,
        "defaults": BRUSSELATOR_DEFAULTS,
        "default_state": brusselator_default_state,
        "perturbation": brusselator_perturbation,
        "param_names": ["Du", "Dv", "A", "B"],
        "description": "Brusselator: oscillating chemical patterns",
        "stability_clamp": (-1, 10),
    },
    "schnakenberg": {
        "react": schnakenberg_react,
        "defaults": SCHNAKENBERG_DEFAULTS,
        "default_state": schnakenberg_default_state,
        "perturbation": schnakenberg_perturbation,
        "param_names": ["Du", "Dv", "a", "b"],
        "description": "Schnakenberg: minimal Turing instability model",
        "stability_clamp": (0, None),
    },
}


def get_model(name: str) -> Dict[str, Any]:
    """Get model config by name. Raises ValueError for unknown models.

    Args:
        name: Model identifier string.

    Returns:
        Model configuration dictionary.

    Raises:
        ValueError: If the model name is not recognized.
    """
    if name not in MODELS:
        available = ", ".join(MODELS.keys())
        raise ValueError(f"Unknown model '{name}'. Available: {available}")
    return MODELS[name]


def register_model(
    name: str,
    react_fn: Callable,
    defaults: Dict[str, float],
    default_state_fn: Callable,
    perturbation_fn: Callable,
    param_names: list,
    description: str,
    stability_clamp: Tuple[Optional[float], Optional[float]] = (None, None),
) -> None:
    """Register a custom model at runtime.

    This allows users to add new reaction kinetics models without
    modifying the library source code.

    Args:
        name: Unique model identifier.
        react_fn: Reaction function with signature (u, v, params) -> (du, dv).
        defaults: Default parameter dict.
        default_state_fn: Function (n, params=None) -> (u, v).
        perturbation_fn: Function () -> perturbation config dict.
        param_names: List of parameter names.
        description: Human-readable model description.
        stability_clamp: (lo, hi) bounds for field clamping.
    """
    if name in MODELS:
        logger.warning(f"Overwriting existing model '{name}'")
    MODELS[name] = {
        "react": react_fn,
        "defaults": defaults,
        "default_state": default_state_fn,
        "perturbation": perturbation_fn,
        "param_names": param_names,
        "description": description,
        "stability_clamp": stability_clamp,
    }
    logger.info(f"Registered model '{name}': {description}")