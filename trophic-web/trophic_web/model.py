"""Small, deterministic generalized Lotka–Volterra food-web simulator."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Web:
    """Species names, intrinsic growth rates, and interaction matrix."""
    names: tuple[str, ...]
    growth: tuple[float, ...]
    interactions: tuple[tuple[float, ...], ...]

    def validate(self) -> None:
        n = len(self.names)
        if n == 0 or len(set(self.names)) != n:
            raise ValueError("web needs unique species names")
        if len(self.growth) != n or len(self.interactions) != n:
            raise ValueError("growth and matrix dimensions must match species")
        if any(len(row) != n for row in self.interactions):
            raise ValueError("interaction matrix must be square")
        if any(not _finite(x) for x in self.growth) or any(
            not _finite(x) for row in self.interactions for x in row
        ):
            raise ValueError("model parameters must be finite")


def _finite(x: float) -> bool:
    return x == x and abs(x) != float("inf")


def derivative(web: Web, state: tuple[float, ...]) -> tuple[float, ...]:
    """Return dx_i/dt = x_i (r_i + sum_j A_ij x_j)."""
    web.validate()
    n = len(web.names)
    if len(state) != n or any(not _finite(x) or x < 0 for x in state):
        raise ValueError("state must contain one finite nonnegative abundance per species")
    return tuple(state[i] * (web.growth[i] + sum(a * x for a, x in zip(web.interactions[i], state))) for i in range(n))


def _add(x: tuple[float, ...], y: tuple[float, ...], scale: float) -> tuple[float, ...]:
    return tuple(a + scale * b for a, b in zip(x, y))


def step(web: Web, state: tuple[float, ...], dt: float) -> tuple[float, ...]:
    """One fourth-order Runge–Kutta step; clamp tiny numerical negatives."""
    if not _finite(dt) or dt <= 0:
        raise ValueError("dt must be positive and finite")
    k1 = derivative(web, state)
    k2 = derivative(web, _add(state, k1, dt / 2))
    k3 = derivative(web, _add(state, k2, dt / 2))
    k4 = derivative(web, _add(state, k3, dt))
    result = tuple(max(0.0, x + dt * (a + 2*b + 2*c + d) / 6)
                   for x, a, b, c, d in zip(state, k1, k2, k3, k4))
    if any(not _finite(x) for x in result):
        raise OverflowError("simulation became non-finite; reduce dt or interaction strength")
    return result


def simulate(web: Web, initial: tuple[float, ...], dt: float = 0.01,
             steps: int = 1000) -> list[tuple[float, ...]]:
    """Return initial state plus every bounded integration state."""
    web.validate()
    if not isinstance(steps, int) or isinstance(steps, bool) or not 0 <= steps <= 1_000_000:
        raise ValueError("steps must be an integer from 0 to 1000000")
    derivative(web, initial)
    states = [initial]
    for _ in range(steps):
        states.append(step(web, states[-1], dt))
    return states


def meadow() -> tuple[Web, tuple[float, ...]]:
    """A small illustrative producer–herbivore–predator web."""
    return (Web(("grass", "hare", "fox"), (1.2, -0.35, -0.2),
                ((-0.08, -0.02, 0.0), (0.015, -0.04, -0.03),
                 (0.0, 0.012, -0.02))), (4.0, 1.0, 0.4))
