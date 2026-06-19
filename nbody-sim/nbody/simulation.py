"""Core simulation orchestration: :class:`Body` and :class:`Simulation`.

The :class:`Simulation` ties together a force evaluator and an integrator,
records snapshots / diagnostics, and exposes a simple ``run`` method for
batch stepping.

Supports multiple integrators via the ``integrator`` parameter:
``'leapfrog'`` (default), ``'rk4'``, and ``'forest-ruth'``.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from .body import Body
from .integrators import (
    INTEGRATORS,
    LeapfrogIntegrator,
    make_integrator,
)


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
    integrator_name: str = "leapfrog"


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
    integrator:
        Name of the integrator to use: 'leapfrog' (default), 'rk4',
        or 'forest-ruth'.
    recenter_com:
        Shift positions and velocities to the COM frame at init.
    adaptive_dt:
        Recompute the timestep each step from the acceleration field.
    adaptive_eta:
        Safety factor for adaptive timestep.
    dt_min, dt_max:
        Clamps for adaptive timestep.
    """

    def __init__(
        self,
        bodies: List[Body],
        dt: float = 0.01,
        theta: float = 0.5,
        softening: float = 1.0,
        G: float = 1.0,
        integrator: str = "leapfrog",
        recenter_com: bool = False,
        adaptive_dt: bool = False,
        adaptive_eta: float = 0.02,
        dt_min: float = 1e-6,
        dt_max: float = 0.1,
    ) -> None:
        # Defensive copy so external mutation doesn't corrupt the run.
        self.bodies: List[Body] = [b.copy() for b in bodies]
        # Validate inputs.
        if not self.bodies:
            raise ValueError("Simulation requires at least one body")
        for i, b in enumerate(self.bodies):
            if b.m < 0.0:
                raise ValueError(f"body {i} has negative mass {b.m}")
        if not (0.0 <= theta <= 2.0):
            raise ValueError(f"theta must be in [0, 2], got {theta}")
        if softening < 0.0:
            raise ValueError(f"softening must be non-negative, got {softening}")
        if dt <= 0.0 and not adaptive_dt:
            raise ValueError(f"dt must be positive (or use adaptive_dt), got {dt}")
        self.dt = dt
        self._base_dt = dt
        self.theta = theta
        self.softening = softening
        self.G = G
        self.integrator_name = integrator
        self.recenter_com = recenter_com
        self.adaptive_dt = adaptive_dt
        self.adaptive_eta = adaptive_eta
        self.dt_min = dt_min
        self.dt_max = dt_max
        self.integrator = make_integrator(
            integrator, theta=theta, softening=softening, G=G
        )
        self.step_count = 0
        self.t = 0.0
        if recenter_com:
            self._recenter_to_com_frame()

    def _recenter_to_com_frame(self) -> None:
        """Shift positions so COM is at the origin, and subtract COM velocity
        so the total momentum is zero."""
        from .diagnostics import com_velocity
        M = sum(b.m for b in self.bodies)
        if M == 0.0:
            return
        cx = sum(b.m * b.x for b in self.bodies) / M
        cy = sum(b.m * b.y for b in self.bodies) / M
        vx_com, vy_com = com_velocity(self.bodies)
        for b in self.bodies:
            b.x -= cx
            b.y -= cy
            b.vx -= vx_com
            b.vy -= vy_com

    # -- stepping -------------------------------------------------------

    def step(self) -> None:
        """Advance the simulation by one ``dt`` step.

        If ``adaptive_dt`` is enabled, the timestep is recomputed each step
        from the current acceleration field.
        """
        if self.adaptive_dt:
            from .diagnostics import adaptive_dt
            self.dt = adaptive_dt(
                self.bodies, G=self.G, softening=self.softening,
                eta=self.adaptive_eta, dt_min=self.dt_min, dt_max=self.dt_max,
            )
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
            integrator_name=self.integrator_name,
        )

        if snapshot_every > 0:
            result.snapshots.append(self._snapshot(self.step_count, self.t))

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

    # -- diagnostic shortcuts -------------------------------------------

    def total_energy(self) -> float:
        """Current total energy."""
        return self.integrator.total_energy(self.bodies)

    def total_momentum(self) -> Tuple[float, float]:
        """Current total momentum."""
        return self.integrator.total_momentum(self.bodies)

    def center_of_mass(self) -> Tuple[float, float]:
        """Current center-of-mass position."""
        return self.integrator.center_of_mass(self.bodies)

    # -- preset initial conditions -------------------------------------

    @classmethod
    def two_body_orbit(
        cls,
        m1: float = 1.0,
        m2: float = 1.0,
        separation: float = 2.0,
        **kwargs: Any,
    ) -> "Simulation":
        """Two bodies in a circular orbit about their common COM."""
        G = kwargs.get("G", 1.0)
        M = m1 + m2
        r1 = separation * m2 / M
        r2 = separation * m1 / M
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
        """The classic equal-mass figure-eight choreography."""
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
        """Sample ``n`` bodies from a Plummer sphere (projected to 2D)."""
        import random as _r

        rng = _r.Random(seed)
        G = kwargs.get("G", 1.0)
        m_per = M / n
        bodies: List[Body] = []
        for _ in range(n):
            u = rng.random()
            u = min(u, 0.999)
            r = radius * (u ** (1.0 / 3.0)) / math.sqrt(max(1e-12, 1.0 - u ** (2.0 / 3.0)))
            r = min(r, 10.0 * radius)
            theta = 2.0 * math.pi * rng.random()
            x = r * math.cos(theta)
            y = r * math.sin(theta)
            v_circ = math.sqrt(G * M / math.sqrt(r * r + 1.0))
            vdir = theta + math.pi / 2.0 + (rng.random() - 0.5) * 0.5
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

    @classmethod
    def solar_system(
        cls,
        seed: int = 0,
        **kwargs: Any,
    ) -> "Simulation":
        """A simplified inner solar system: Sun + Mercury, Venus, Earth, Mars.

        Units: G=1, solar mass=1, distances in AU, times in years.
        """
        G = kwargs.get("G", 1.0)
        M_sun = 1.0
        # Semi-major axes (AU) and circular orbital speeds.
        planets = [
            # (name, mass, a, color_hint)
            ("Mercury", 1.66e-7, 0.387),
            ("Venus",   2.45e-6, 0.723),
            ("Earth",   3.00e-6, 1.000),
            ("Mars",    3.23e-7, 1.524),
        ]
        bodies = [Body(0.0, 0.0, 0.0, 0.0, M_sun, "Sun")]
        import random as _r
        rng = _r.Random(seed)
        for name, m, a in planets:
            v_circ = math.sqrt(G * M_sun / a)
            # Random initial angle.
            angle = 2.0 * math.pi * rng.random()
            x = a * math.cos(angle)
            y = a * math.sin(angle)
            # Tangential velocity.
            vx = -v_circ * math.sin(angle)
            vy = v_circ * math.cos(angle)
            bodies.append(Body(x, y, vx, vy, m, name))
        return cls(bodies, **kwargs)

    @classmethod
    def binary_system(
        cls,
        m1: float = 1.0,
        m2: float = 0.5,
        separation: float = 3.0,
        eccentricity: float = 0.3,
        **kwargs: Any,
    ) -> "Simulation":
        """Two bodies in an eccentric orbit.

        ``eccentricity=0`` gives a circular orbit; ``eccentricity`` close to
        1 gives a highly elliptical orbit.
        """
        G = kwargs.get("G", 1.0)
        M = m1 + m2
        # Semi-major axis from separation (at periapsis, r=a(1-e)).
        a = separation / (1.0 - eccentricity) if eccentricity < 1.0 else separation
        # Vis-viva: v^2 = G*M*(2/r - 1/a)
        r = separation
        v_rel_sq = G * M * (2.0 / r - 1.0 / a) if a > 0 else G * M / r
        v_rel = math.sqrt(max(v_rel_sq, 0.0))
        r1 = separation * m2 / M
        r2 = separation * m1 / M
        v1 = v_rel * m2 / M
        v2 = v_rel * m1 / M
        bodies = [
            Body(-r1, 0.0, 0.0, v1, m1, "star1"),
            Body(r2, 0.0, 0.0, -v2, m2, "star2"),
        ]
        return cls(bodies, **kwargs)

    @classmethod
    def kuzmin_disk(
        cls,
        n: int = 100,
        seed: int = 0,
        scale_radius: float = 5.0,
        M_total: float = 1.0,
        **kwargs: Any,
    ) -> "Simulation":
        """N bodies in a Kuzmin thin-disk surface density profile.

        The surface density is ``Σ(r) = M * a / (2π * (r² + a²)^(3/2))``.
        Radii are sampled via inverse CDF; velocities are circular.
        """
        import random as _r

        rng = _r.Random(seed)
        G = kwargs.get("G", 1.0)
        m_per = M_total / n
        bodies: List[Body] = []
        a = scale_radius
        for _ in range(n):
            # Inverse CDF for Kuzmin disk cumulative mass:
            # M(r) = M * (1 - a / sqrt(r² + a²))
            # u = M(r)/M → r = a * sqrt(1/u² - 1) ... rearranging:
            # sqrt(r²+a²) = a / (1-u) → r = a * sqrt((1/(1-u))² - 1)
            u = rng.random()
            u = min(u, 0.999)  # avoid divergence
            r = a * math.sqrt(1.0 / (1.0 - u) ** 2 - 1.0)
            r = min(r, 20.0 * a)
            theta = 2.0 * math.pi * rng.random()
            x = r * math.cos(theta)
            y = r * math.sin(theta)
            # Circular velocity in Kuzmin potential:
            # v_circ² = G*M*r² / (r² + a²)^(3/2)
            v_circ = math.sqrt(G * M_total * r * r / (r * r + a * a) ** 1.5)
            vx = -v_circ * math.sin(theta)
            vy = v_circ * math.cos(theta)
            bodies.append(Body(x, y, vx, vy, m_per))
        return cls(bodies, **kwargs)


__all__ = ["Body", "Snapshot", "SimulationResult", "Simulation"]