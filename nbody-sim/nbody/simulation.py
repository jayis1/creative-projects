"""Core simulation orchestration: :class:`Body` and :class:`Simulation`.

The :class:`Simulation` ties together the Barnes–Hut force evaluator and the
leapfrog integrator, records snapshots / diagnostics, and exposes a simple
``run`` method for batch stepping.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .barnes_hut import BHTree
from .body import Body
from .integrator import LeapfrogIntegrator


@dataclass
class Snapshot:
    """A single point-in-time snapshot of the system."""

    step: int
    t: float
    bodies: List[Body]
    energy: float
    momentum: Tuple[float, float]


@dataclass
class SimulationResult:
    """Aggregate result of a :class:`Simulation.run` call."""

    snapshots: List[Snapshot] = field(default_factory=list)
    initial_energy: float = 0.0
    final_energy: float = 0.0
    initial_momentum: Tuple[float, float] = (0.0, 0.0)
    final_momentum: Tuple[float, float] = (0.0, 0.0)
    n_steps: int = 0
    dt: float = 0.0
    theta: float = 0.0
    softening: float = 0.0
    G: float = 0.0


class Simulation:
    """Orchestrates an N-body gravity simulation.

    Parameters
    ----------
    bodies:
        Initial list of :class:`Body` objects (copied defensively).
    dt:
        Time step used by the integrator.
    theta:
        Barnes–Hut opening angle.
    softening:
        Plummer softening length.
    G:
        Gravitational constant.
    """

    def __init__(
        self,
        bodies: List[Body],
        dt: float = 0.01,
        theta: float = 0.5,
        softening: float = 1.0,
        G: float = 1.0,
    ) -> None:
        # Defensive copy so external mutation doesn't corrupt the run.
        self.bodies: List[Body] = [b.copy() for b in bodies]
        self.dt = dt
        self.theta = theta
        self.softening = softening
        self.G = G
        self.integrator = LeapfrogIntegrator(
            theta=theta, softening=softening, G=G
        )
        self.step_count = 0
        self.t = 0.0

    # -- stepping -------------------------------------------------------

    def step(self) -> None:
        """Advance the simulation by one ``dt``."""
        self.integrator.step(self.bodies, self.dt)
        self.step_count += 1
        self.t += self.dt

    def run(
        self,
        n_steps: int,
        snapshot_every: int = 0,
        on_step: Optional[Callable[["Simulation"], None]] = None,
    ) -> SimulationResult:
        """Run ``n_steps`` steps, optionally recording snapshots.

        Parameters
        ----------
        n_steps:
            Number of integration steps to perform.
        snapshot_every:
            If > 0, record a :class:`Snapshot` every ``snapshot_every`` steps
            (always records step 0 and the final step).
        on_step:
            Optional callback invoked after each step. Useful for rendering.
        """
        result = SimulationResult(
            initial_energy=self.integrator.total_energy(self.bodies),
            initial_momentum=self.integrator.total_momentum(self.bodies),
            n_steps=n_steps,
            dt=self.dt,
            theta=self.theta,
            softening=self.softening,
            G=self.G,
        )

        if snapshot_every > 0:
            result.snapshots.append(self._snapshot(0, 0.0))

        for i in range(n_steps):
            self.step()
            if on_step is not None:
                on_step(self)
            if snapshot_every > 0 and (i + 1) % snapshot_every == 0:
                result.snapshots.append(
                    self._snapshot(i + 1, self.t)
                )

        # Always record a final snapshot if it wasn't already captured.
        if snapshot_every > 0:
            last = result.snapshots[-1] if result.snapshots else None
            if last is None or last.step != self.step_count:
                result.snapshots.append(
                    self._snapshot(self.step_count, self.t)
                )

        result.final_energy = self.integrator.total_energy(self.bodies)
        result.final_momentum = self.integrator.total_momentum(self.bodies)
        return result

    # -- helpers --------------------------------------------------------

    def _snapshot(self, step: int, t: float) -> Snapshot:
        return Snapshot(
            step=step,
            t=t,
            bodies=[b.copy() for b in self.bodies],
            energy=self.integrator.total_energy(self.bodies),
            momentum=self.integrator.total_momentum(self.bodies),
        )

    # -- preset initial conditions -------------------------------------

    @classmethod
    def two_body_orbit(
        cls,
        m1: float = 1.0,
        m2: float = 1.0,
        separation: float = 2.0,
        **kwargs: Any,
    ) -> "Simulation":
        """Two bodies in a circular orbit about their common COM.

        Velocities are chosen for a circular orbit assuming ``G = 1``:
        ``v = sqrt(G * M / r)`` with the reduced-mass split between bodies.
        """
        G = kwargs.get("G", 1.0)
        M = m1 + m2
        # Reduced-mass position split: body1 at -m2/M * r, body2 at m1/M * r.
        r1 = separation * m2 / M
        r2 = separation * m1 / M
        # Circular orbit speed: v_rel = sqrt(G*M/r); split by mass ratio.
        v_rel = math.sqrt(G * M / separation)
        v1 = v_rel * m2 / M
        v2 = v_rel * m1 / M
        bodies = [
            Body(-r1, 0.0, 0.0, v1, m1, "body1"),
            Body(r2, 0.0, 0.0, -v2, m2, "body2"),
        ]
        return cls(bodies, **kwargs)

    @classmethod
    def figure_eight(cls, **kwargs: Any) -> "Simulation":
        """The classic equal-mass figure-eight choreography.

        Three equal masses chase each other along a single figure-eight orbit.
        Initial conditions are the well-known Chenciner–Montgomery solution.
        """
        # Standard figure-eight initial conditions (G=1, m=1 each).
        # Positions:
        #   r1 = (0.97000436, -0.24308753)
        #   r2 = (-0.97000436, 0.24308753)
        #   r3 = (0, 0)
        # Velocities:
        #   v3 = (-0.93240737, -0.86473146)
        #   v1 = -v3/2, v2 = -v3/2
        r1 = (0.97000436, -0.24308753)
        r2 = (-0.97000436, 0.24308753)
        v3 = (-0.93240737, -0.86473146)
        v1 = (-v3[0] / 2.0, -v3[1] / 2.0)
        bodies = [
            Body(r1[0], r1[1], v1[0], v1[1], 1.0, "p1"),
            Body(r2[0], r2[1], v1[0], v1[1], 1.0, "p2"),
            Body(0.0, 0.0, v3[0], v3[1], 1.0, "p3"),
        ]
        return cls(bodies, **kwargs)

    @classmethod
    def plummer_sphere(
        cls,
        n: int = 100,
        seed: int = 0,
        radius: float = 10.0,
        M: float = 1.0,
        **kwargs: Any,
    ) -> "Simulation":
        """Sample ``n`` bodies from a Plummer sphere (projected to 2D).

        The Plummer model has density ``rho ~ (1 + r^2)^(-5/2)``. We sample
        radii via inverse-transform sampling, place each body isotropically,
        and give velocities approximating virial equilibrium.
        """
        import random as _r

        rng = _r.Random(seed)
        G = kwargs.get("G", 1.0)
        m_per = M / n
        bodies: List[Body] = []
        for _ in range(n):
            # Sample radius via inverse CDF of Plummer: r = R * u^(1/3)/sqrt(1-u^(2/3))
            u = rng.random()
            r = radius * (u ** (1.0 / 3.0)) / math.sqrt(max(1e-12, 1.0 - u ** (2.0 / 3.0)))
            # Isotropic angle
            theta = 2.0 * math.pi * rng.random()
            x = r * math.cos(theta)
            y = r * math.sin(theta)
            # Approximate circular velocity for softening ~ Plummer core.
            v_circ = math.sqrt(G * M / math.sqrt(r * r + 1.0))
            # Random tangential direction with some scatter for a relaxed cloud.
            vdir = theta + math.pi / 2.0 + (rng.random() - 0.5) * 0.5
            # Scale down a bit so the cloud is bound (factor ~0.7 virial).
            v = 0.7 * v_circ
            vx = v * math.cos(vdir)
            vy = v * math.sin(vdir)
            bodies.append(Body(x, y, vx, vy, m_per))
        return cls(bodies, **kwargs)

    @classmethod
    def random_cloud(
        cls,
        n: int = 50,
        seed: int = 0,
        spread: float = 10.0,
        max_v: float = 0.5,
        **kwargs: Any,
    ) -> "Simulation":
        """A random scatter of bodies for stress-testing the tree."""
        import random as _r

        rng = _r.Random(seed)
        bodies = [
            Body(
                rng.uniform(-spread, spread),
                rng.uniform(-spread, spread),
                rng.uniform(-max_v, max_v),
                rng.uniform(-max_v, max_v),
                rng.uniform(0.5, 2.0),
            )
            for _ in range(n)
        ]
        return cls(bodies, **kwargs)


__all__ = ["Body", "Snapshot", "SimulationResult", "Simulation"]