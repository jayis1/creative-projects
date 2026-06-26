"""Continuous cellular automata — reaction-diffusion models.

This module implements *continuous-state* cellular automata where each cell
holds a floating-point concentration rather than a discrete state.  The
archetype is the **Gray-Scott** reaction-diffusion model, which produces
spectacular self-organising patterns (spots, stripes, mazes, solitons,
gliders) from simple local rules.

The Gray-Scott equations (per cell, per timestep ``dt``)::

    du/dt = D_u * ∇²u  -  u*v²  +  F*(1-u)
    dv/dt = D_v * ∇²v  +  u*v²  -  (F+k)*v

Where ``u`` is the activator (inhibitor of pattern), ``v`` is the inhibitor,
``F`` is the feed rate, ``k`` is the kill rate, and ``D_u``, ``D_v`` are
diffusion rates.  The Laplacian ``∇²`` is discretised using a 3×3 or 5×5
stencil.

Also includes the **FitzHugh-Nagumo** excitable-medium model, a simplified
neuron-firing equation that produces spiral waves.

All models use NumPy vectorised operations for speed.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np


# --------------------------------------------------------------------------- #
# Base class
# --------------------------------------------------------------------------- #


class ContinuousCA:
    """Base class for continuous (floating-point) cellular automata.

    Unlike discrete CAs, each cell holds a float concentration array.  The
    ``step`` method advances the simulation by one timestep using vectorised
    NumPy operations.

    Attributes
    ----------
    width, height : int
        Grid dimensions.
    states : np.ndarray
        Current state array of shape ``(n_species, height, width)``.
    step_count : int
        Number of timesteps executed.
    """

    n_species: int = 2
    dimensions: int = 2

    def __init__(self, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("width and height must be positive")
        self.width = width
        self.height = height
        self.step_count = 0
        self.states = np.zeros((self.n_species, height, width), dtype=np.float64)

    @property
    def name(self) -> str:
        return type(self).__name__

    def step(self, n: int = 1) -> None:
        """Advance by ``n`` timesteps."""
        for _ in range(n):
            self._single_step()
            self.step_count += 1

    def _single_step(self) -> None:
        raise NotImplementedError

    def _laplacian(self, field: np.ndarray, mode: str = "periodic") -> np.ndarray:
        """3×3 Laplacian (discrete) with the standard 9-point stencil.

        Stencil weights (edges 0.20, corners 0.05, centre −1.00)::

            0.05  0.20  0.05
            0.20 -1.00  0.20
            0.05  0.20  0.05

        The weights sum to zero, so a constant field has zero Laplacian.
        """
        if mode == "periodic":
            padded = np.pad(field, 1, mode="wrap")
        elif mode in ("zero", "fixed"):
            padded = np.pad(field, 1, mode="constant", constant_values=0)
        else:  # reflect / edge
            padded = np.pad(field, 1, mode="edge")
        return (
            0.05 * (padded[:-2, :-2] + padded[:-2, 2:] +
                    padded[2:, :-2] + padded[2:, 2:])  # 4 corners
            + 0.20 * (padded[:-2, 1:-1] + padded[1:-1, :-2] +
                      padded[1:-1, 2:] + padded[2:, 1:-1])  # 4 edges
            - 1.00 * padded[1:-1, 1:-1]  # centre
        )

    def randomize(self, seed: Optional[int] = None) -> None:
        """Default randomisation — subclasses override."""
        raise NotImplementedError

    def to_dict(self) -> Dict:
        return {
            "model": self.name,
            "width": self.width,
            "height": self.height,
            "step_count": self.step_count,
            "states": self.states.tolist(),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ContinuousCA":
        ca = cls(data["width"], data["height"])
        ca.states = np.array(data["states"], dtype=np.float64)
        ca.step_count = data.get("step_count", 0)
        return ca


# --------------------------------------------------------------------------- #
# Gray-Scott reaction-diffusion
# --------------------------------------------------------------------------- #


# Well-known parameter presets producing distinct pattern regimes.
GRAY_SCOTT_PRESETS: Dict[str, Dict[str, float]] = {
    "spots":       {"F": 0.025, "k": 0.060, "Du": 0.2097, "Dv": 0.105},
    "stripes":     {"F": 0.022, "k": 0.059, "Du": 0.2097, "Dv": 0.105},
    "maze":        {"F": 0.029, "k": 0.057, "Du": 0.2097, "Dv": 0.105},
    "worms":       {"F": 0.078, "k": 0.061, "Du": 0.2097, "Dv": 0.105},
    "solitons":    {"F": 0.030, "k": 0.062, "Du": 0.2097, "Dv": 0.105},
    "gliders":     {"F": 0.014, "k": 0.045, "Du": 0.2097, "Dv": 0.105},
    "coral":       {"F": 0.0545,"k": 0.062, "Du": 0.2097, "Dv": 0.105},
    "chaos":       {"F": 0.001, "k": 0.055, "Du": 0.2097, "Dv": 0.105},
    "holes":       {"F": 0.039, "k": 0.058, "Du": 0.2097, "Dv": 0.105},
    "pulsating":   {"F": 0.025, "k": 0.060, "Du": 0.2097, "Dv": 0.105},
}


class GrayScott(ContinuousCA):
    """Gray-Scott reaction-diffusion model.

    Two species: ``u`` (activator, states[0]) and ``v`` (inhibitor, states[1]).

    Parameters
    ----------
    width, height : int
        Grid size.
    F : float
        Feed rate of activator.
    k : float
        Kill rate of inhibitor.
    Du, Dv : float
        Diffusion coefficients for u and v.
    dt : float
        Timestep size.
    boundary : str
        Boundary mode (``periodic``, ``zero``, ``reflect``, ``fixed``).

    Examples
    --------
    >>> gs = GrayScott(80, 80, F=0.025, k=0.06)
    >>> gs.seed_square(40, 40, 5)
    >>> gs.step(1000)
    >>> v = gs.states[1]  # inhibitor field — shows the pattern
    """

    n_species = 2

    def __init__(
        self,
        width: int,
        height: int,
        F: float = 0.025,
        k: float = 0.060,
        Du: float = 0.2097,
        Dv: float = 0.105,
        dt: float = 1.0,
        boundary: str = "periodic",
    ) -> None:
        super().__init__(width, height)
        self.F = F
        self.k = k
        self.Du = Du
        self.Dv = Dv
        self.dt = dt
        self.boundary = boundary
        # Default: u=1 everywhere, v=0 everywhere (quiescent).
        self.states[0] = 1.0

    def _single_step(self) -> None:
        u, v = self.states[0], self.states[1]
        lap_u = self._laplacian(u, self.boundary)
        lap_v = self._laplacian(v, self.boundary)
        uvv = u * v * v
        new_u = u + self.dt * (self.Du * lap_u - uvv + self.F * (1 - u))
        new_v = v + self.dt * (self.Dv * lap_v + uvv - (self.F + self.k) * v)
        # Clamp to physical range.
        np.clip(new_u, 0.0, 1.0, out=new_u)
        np.clip(new_v, 0.0, 1.0, out=new_v)
        self.states[0] = new_u
        self.states[1] = new_v

    def seed_square(self, cx: int, cy: int, radius: int = 5) -> None:
        """Seed a square of inhibitor at ``(cx, cy)``."""
        x0 = max(0, cx - radius)
        x1 = min(self.width, cx + radius)
        y0 = max(0, cy - radius)
        y1 = min(self.height, cy + radius)
        self.states[0, y0:y1, x0:x1] = 0.50
        self.states[1, y0:y1, x0:x1] = 0.25
        # Add noise for symmetry breaking.
        rng = np.random.default_rng()
        self.states[0, y0:y1, x0:x1] += rng.uniform(-0.05, 0.05, (y1 - y0, x1 - x0))
        self.states[1, y0:y1, x0:x1] += rng.uniform(-0.05, 0.05, (y1 - y0, x1 - x0))
        np.clip(self.states[0], 0, 1, out=self.states[0])
        np.clip(self.states[1], 0, 1, out=self.states[1])

    def seed_random(self, n_seeds: int = 5, seed: Optional[int] = None) -> None:
        """Place ``n_seeds`` random inhibitor seeds."""
        rng = np.random.default_rng(seed)
        for _ in range(n_seeds):
            cx = rng.integers(5, self.width - 5)
            cy = rng.integers(5, self.height - 5)
            r = rng.integers(3, 8)
            self.seed_square(int(cx), int(cy), int(r))

    def randomize(self, seed: Optional[int] = None) -> None:
        """Randomise with small v noise across the grid."""
        rng = np.random.default_rng(seed)
        self.states[0] = 1.0
        self.states[1] = 0.0
        # Add a few random seeds.
        self.seed_random(n_seeds=8, seed=seed)

    @classmethod
    def from_preset(cls, preset: str, width: int = 80, height: int = 80, **kwargs) -> "GrayScott":
        """Create a Gray-Scott model from a named preset."""
        if preset not in GRAY_SCOTT_PRESETS:
            raise ValueError(
                f"Unknown preset {preset!r}. Available: {list(GRAY_SCOTT_PRESETS)}"
            )
        params = GRAY_SCOTT_PRESETS[preset]
        params = {**params, **kwargs}
        return cls(width, height, **params)


# --------------------------------------------------------------------------- #
# FitzHugh-Nagumo excitable medium
# --------------------------------------------------------------------------- #


class FitzHughNagumo(ContinuousCA):
    """FitzHugh-Nagumo excitable-medium model.

    Two species: ``v`` (voltage / excitation, states[0]) and ``w``
    (recovery, states[1]).

    Equations::

        dv/dt = D_v * ∇²v + v - v³/3 - w + I
        dw/dt = phi * (v + a - b*w)

    Parameters
    ----------
    width, height : int
        Grid size.
    a, b, phi : float
        Model parameters.
    Dv : float
        Diffusion coefficient of the excitation variable.
    dt : float
        Timestep.
    I : float
        External stimulus current.
    boundary : str
        Boundary mode.
    """

    n_species = 2

    def __init__(
        self,
        width: int,
        height: int,
        a: float = 0.1,
        b: float = 0.3,
        phi: float = 0.05,
        Dv: float = 1.0,
        dt: float = 0.1,
        I: float = 0.0,
        boundary: str = "periodic",
    ) -> None:
        super().__init__(width, height)
        self.a = a
        self.b = b
        self.phi = phi
        self.Dv = Dv
        self.dt = dt
        self.I = I
        self.boundary = boundary

    def _single_step(self) -> None:
        v, w = self.states[0], self.states[1]
        lap_v = self._laplacian(v, self.boundary)
        new_v = v + self.dt * (self.Dv * lap_v + v - v**3 / 3 - w + self.I)
        new_w = w + self.dt * (self.phi * (v + self.a - self.b * w))
        # Clamp voltage to reasonable range.
        np.clip(new_v, -2.0, 2.0, out=new_v)
        np.clip(new_w, -2.0, 2.0, out=new_w)
        self.states[0] = new_v
        self.states[1] = new_w

    def seed_spiral(self, cx: Optional[int] = None, cy: Optional[int] = None) -> None:
        """Seed a spiral-wave initial condition."""
        if cx is None:
            cx = self.width // 2
        if cy is None:
            cy = self.height // 2
        yy, xx = np.meshgrid(
            np.arange(self.height, dtype=np.float64),
            np.arange(self.width, dtype=np.float64),
            indexing="ij",
        )
        # Phase that varies with angle — creates a spiral.
        theta = np.arctan2(yy - cy, xx - cx)
        r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        phase = theta + r * 0.1
        self.states[0] = np.cos(phase) * (r < min(self.width, self.height) / 2)
        self.states[1] = 0.0

    def randomize(self, seed: Optional[int] = None) -> None:
        rng = np.random.default_rng(seed)
        self.states[0] = rng.uniform(-1.5, 1.5, (self.height, self.width))
        self.states[1] = rng.uniform(-0.5, 0.5, (self.height, self.width))


# --------------------------------------------------------------------------- #
# Registry & helpers
# --------------------------------------------------------------------------- #


CONTINUOUS_MODELS: Dict[str, type] = {
    "GrayScott": GrayScott,
    "FitzHughNagumo": FitzHughNagumo,
}


def get_continuous_model(name: str, **kwargs) -> ContinuousCA:
    """Look up a continuous CA model by name (case-insensitive)."""
    lower = {k.lower(): k for k in CONTINUOUS_MODELS}
    if name.lower() in lower:
        key = lower[name.lower()]
        return CONTINUOUS_MODELS[key](**kwargs)
    raise KeyError(f"Unknown continuous model: {name!r}")


def is_continuous_model(name: str) -> bool:
    """Check whether *name* refers to a continuous CA model."""
    return name.lower() in {k.lower() for k in CONTINUOUS_MODELS}


def render_continuous_ascii(
    field: np.ndarray,
    chars: str = " .:-=+*#%@",
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
) -> str:
    """Render a continuous field as ASCII art using a character ramp.

    Parameters
    ----------
    field : np.ndarray
        2D float array.
    chars : str
        Character ramp from low to high (default 10 levels).
    vmin, vmax : float, optional
        Value range for mapping.  Defaults to field min/max.
    """
    if field.ndim == 1:
        field = field.reshape(1, -1)
    if vmin is None:
        vmin = float(field.min())
    if vmax is None:
        vmax = float(field.max())
    if vmax <= vmin:
        vmax = vmin + 1e-9
    normalised = (field - vmin) / (vmax - vmin)
    n_chars = len(chars)
    indices = np.clip((normalised * n_chars).astype(int), 0, n_chars - 1)
    lines = []
    for row in indices:
        lines.append("".join(chars[i] for i in row))
    return "\n".join(lines)