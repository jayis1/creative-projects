"""
PDE Solver engine for reaction-diffusion systems.

Implements:
- 9-point isotropic Laplacian stencil for accurate spatial derivatives
- Multiple boundary conditions (periodic, Dirichlet, Neumann)
- Euler and RK2 (midpoint) time integration
- RK4 (4th-order Runge-Kutta) time integration
- Adaptive time stepping based on CFL-like stability criterion
- Field clamping for numerical stability
- Perturbation seeding (center_square, ring, cross, random, corner, multi_spot)
- Checkpoint save/load via compressed NumPy archives
- Step callback system for progress monitoring
- Event system for simulation milestones
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
from numpy.typing import NDArray
from scipy.ndimage import convolve

from rdsim.models import get_model, _clamp_field

logger = logging.getLogger(__name__)

# 9-point isotropic Laplacian stencil (dx=1)
# More isotropic than standard 5-point, reducing directional artifacts.
LAPLACIAN_STENCIL = np.array([
    [1 / 6,  4 / 6,  1 / 6],
    [4 / 6, -20 / 6, 4 / 6],
    [1 / 6,  4 / 6,  1 / 6],
], dtype=np.float64)


class BoundaryCondition:
    """Boundary condition types for the simulation domain."""
    PERIODIC = "periodic"
    DIRICHLET = "dirichlet"
    NEUMANN = "neumann"


def apply_laplacian(
    field: NDArray[np.floating],
    bc: str = "periodic",
    bc_value: float = 0.0,
) -> NDArray[np.floating]:
    """Compute the Laplacian of a 2D field using the 9-point isotropic stencil.

    The 9-point stencil provides better rotational symmetry compared to the
    standard 5-point stencil, reducing grid-induced anisotropy by ~3x.

    Args:
        field: 2D numpy array of concentration values.
        bc: Boundary condition — "periodic", "dirichlet", or "neumann".
        bc_value: For dirichlet BC, the fixed boundary value.

    Returns:
        2D numpy array — Laplacian of the field.

    Raises:
        ValueError: If bc is not a recognized boundary condition type.
    """
    if bc == BoundaryCondition.PERIODIC:
        return convolve(field, LAPLACIAN_STENCIL, mode="wrap")
    elif bc == BoundaryCondition.DIRICHLET:
        padded = np.pad(field, 1, mode="constant", constant_values=bc_value)
        return _convolve_padded(padded)
    elif bc == BoundaryCondition.NEUMANN:
        padded = np.pad(field, 1, mode="reflect")
        return _convolve_padded(padded)
    else:
        raise ValueError(
            f"Unknown boundary condition: {bc}. "
            f"Use 'periodic', 'dirichlet', or 'neumann'."
        )


def _convolve_padded(padded: NDArray[np.floating]) -> NDArray[np.floating]:
    """Apply Laplacian stencil to a pre-padded 2D field.

    Manually applies the 3x3 stencil to avoid scipy.ndimage.convolve's
    boundary handling, since we've already padded the field.
    """
    n, m = padded.shape
    result = np.zeros((n - 2, m - 2), dtype=np.float64)
    stencil = LAPLACIAN_STENCIL
    for di in range(3):
        for dj in range(3):
            result += stencil[di, dj] * padded[di:n - 2 + di, dj:m - 2 + dj]
    return result


class SimulationEvent:
    """Event types emitted during simulation."""

    STEP_COMPLETE = "step_complete"
    PERTURBATION_APPLIED = "perturbation_applied"
    CHECKPOINT_SAVED = "checkpoint_saved"
    STATE_LOADED = "state_loaded"
    SIMULATION_STARTED = "simulation_started"
    SIMULATION_COMPLETE = "simulation_complete"
    ADAPTIVE_DT_CHANGED = "adaptive_dt_changed"


class ReactionDiffusionSolver:
    """Numerical solver for reaction-diffusion PDE systems.

    Supports Gray-Scott, FitzHugh-Nagumo, Gierer-Meinhardt, Brusselator,
    and Schnakenberg models. Uses explicit Euler, RK2 (midpoint), or RK4
    time integration with optional adaptive time stepping and field clamping
    for stability.

    Example:
        >>> solver = ReactionDiffusionSolver("gray-scott", grid_size=128)
        >>> solver.apply_perturbation()
        >>> solver.step(5000)
        >>> u, v = solver.get_state()
        >>> solver.save_checkpoint("state.npz")
    """

    def __init__(
        self,
        model_name: str = "gray-scott",
        grid_size: int = 128,
        params: Optional[Dict[str, float]] = None,
        bc: str = "periodic",
        dt: float = 1.0,
        step_count: int = 0,
        clamp: bool = True,
    ) -> None:
        """Initialize the solver.

        Args:
            model_name: Name of the reaction model (see models.MODELS).
            grid_size: Size of the NxN simulation grid.
            params: Override model parameters (dict).
            bc: Boundary condition type.
            dt: Time step size.
            step_count: Initial step count (for resumed simulations).
            clamp: Whether to clamp concentrations to model-specific ranges.

        Raises:
            ValueError: If model_name is not recognized or grid_size < 4.
        """
        if grid_size < 4:
            raise ValueError(f"grid_size must be >= 4, got {grid_size}")

        self.model_config = get_model(model_name)
        self.model_name = model_name
        self.n = grid_size
        self.dt = dt
        self.bc = bc
        self.step_count = step_count
        self.clamp = clamp

        # Merge defaults with user overrides
        self.params: Dict[str, float] = dict(self.model_config["defaults"])
        if params:
            self.params.update(params)

        # Get stability clamp range from model config
        self._clamp_range = self.model_config.get("stability_clamp", None)

        # Initialize state
        u, v = self.model_config["default_state"](grid_size, params=self.params)
        self.u = u.astype(np.float64)
        self.v = v.astype(np.float64)

        # Callback system
        self._callbacks: List[Tuple[Callable, int]] = []

        # Event system
        self._event_listeners: Dict[str, List[Callable]] = {}

        # Timing
        self._step_timer: float = 0.0
        self._total_sim_time: float = 0.0

        logger.info(
            f"Initialized {model_name} solver: "
            f"{grid_size}x{grid_size}, dt={dt}, bc={bc}, clamp={clamp}"
        )

    # ── Event system ──

    def on(self, event: str, listener: Callable) -> None:
        """Register an event listener.

        Args:
            event: Event type (see SimulationEvent constants).
            listener: Callback function with signature listener(solver, **kwargs).
        """
        if event not in self._event_listeners:
            self._event_listeners[event] = []
        self._event_listeners[event].append(listener)

    def _emit(self, event: str, **kwargs: Any) -> None:
        """Emit an event to all registered listeners."""
        for listener in self._event_listeners.get(event, []):
            try:
                listener(self, **kwargs)
            except Exception as e:
                logger.warning(f"Event listener error for {event}: {e}")

    # ── Callback system ──

    def add_callback(self, callback: Callable, every: int = 100) -> None:
        """Add a callback function called periodically during simulation.

        Args:
            callback: Function with signature callback(solver) -> None.
            every: Call every N steps.
        """
        self._callbacks.append((callback, every))

    # ── Perturbation ──

    def apply_perturbation(self, pert_config: Optional[Dict[str, Any]] = None) -> None:
        """Apply a perturbation to the concentration fields.

        Perturbations break the symmetry of the initial homogeneous state,
        allowing patterns to nucleate and grow.

        Args:
            pert_config: Dict with perturbation parameters.
                - type: "center_square", "ring", "cross", "random",
                        "corner", "multi_spot"
                - size: Size of perturbation region (pixels)
                - u_val, v_val: Concentration values in perturbed region
                - noise: Amplitude for random perturbation
                - center: (row, col) center position
                - count: Number of spots (for "multi_spot")
                - radius, thickness: For "ring" type

        Raises:
            ValueError: If perturbation type is unrecognized.
        """
        if pert_config is None:
            pert_config = self.model_config["perturbation"]()

        ptype = pert_config.get("type", "center_square")
        n = self.n
        cx, cy = pert_config.get("center", (n // 2, n // 2))
        size = pert_config.get("size", min(n // 5, 20))

        if ptype == "center_square":
            s = size // 2
            r0, r1 = max(cx - s, 0), min(cx + s, n)
            c0, c1 = max(cy - s, 0), min(cy + s, n)
            u_val = pert_config.get("u_val", 0.0)
            v_val = pert_config.get("v_val", 1.0)
            self.u[r0:r1, c0:c1] = u_val
            self.v[r0:r1, c0:c1] = v_val

        elif ptype == "ring":
            radius = pert_config.get("radius", size)
            thickness = pert_config.get("thickness", 3)
            u_val = pert_config.get("u_val", 0.5)
            v_val = pert_config.get("v_val", 1.0)
            yy, xx = np.ogrid[:n, :n]
            dist = np.sqrt((yy - cx) ** 2 + (xx - cy) ** 2)
            mask = (dist >= radius - thickness) & (dist <= radius + thickness)
            self.u[mask] = u_val
            self.v[mask] = v_val

        elif ptype == "cross":
            width = pert_config.get("width", max(size // 4, 2))
            u_val = pert_config.get("u_val", 0.0)
            v_val = pert_config.get("v_val", 1.0)
            hw = width // 2
            self.u[cx - hw:cx + hw, :] = u_val
            self.v[cx - hw:cx + hw, :] = v_val
            self.u[:, cy - hw:cy + hw] = u_val
            self.v[:, cy - hw:cy + hw] = v_val

        elif ptype == "random":
            amplitude = pert_config.get("noise", 0.01)
            rng = np.random.default_rng()
            self.u += rng.normal(0, amplitude, (n, n))
            self.v += rng.normal(0, amplitude, (n, n))

        elif ptype == "corner":
            s = size // 2
            u_val = pert_config.get("u_val", 0.0)
            v_val = pert_config.get("v_val", 1.0)
            self.u[:s, :s] = u_val
            self.v[:s, :s] = v_val

        elif ptype == "multi_spot":
            count = pert_config.get("count", 5)
            u_val = pert_config.get("u_val", 0.0)
            v_val = pert_config.get("v_val", 1.0)
            rng = np.random.default_rng()
            for _ in range(count):
                rx = rng.integers(size, n - size)
                ry = rng.integers(size, n - size)
                s = size // 2
                self.u[rx - s:rx + s, ry - s:ry + s] = u_val
                self.v[rx - s:rx + s, ry - s:ry + s] = v_val
        else:
            raise ValueError(f"Unknown perturbation type: {ptype}")

        self._emit(SimulationEvent.PERTURBATION_APPLIED, pert_type=ptype)
        logger.debug(f"Applied {ptype} perturbation")

    # ── Time stepping ──

    def step(self, num_steps: int = 1, method: str = "euler") -> None:
        """Advance the simulation by num_steps time steps.

        Args:
            num_steps: Number of time steps to advance.
            method: "euler", "rk2", or "rk4".

        Raises:
            ValueError: If method is not recognized.
        """
        if num_steps < 1:
            raise ValueError(f"num_steps must be >= 1, got {num_steps}")

        dt = self.dt
        react_fn = self.model_config["react"]
        params = self.params
        Du = params.get("Du", 0.16)
        Dv = params.get("Dv", 0.08)

        t0 = time.perf_counter()

        for step_idx in range(num_steps):
            if method == "euler":
                self._step_euler(dt, react_fn, params, Du, Dv)
            elif method == "rk2":
                self._step_rk2(dt, react_fn, params, Du, Dv)
            elif method == "rk4":
                self._step_rk4(dt, react_fn, params, Du, Dv)
            else:
                raise ValueError(
                    f"Unknown integration method: {method}. "
                    f"Use 'euler', 'rk2', or 'rk4'."
                )

            # Clamp concentrations for numerical stability
            if self.clamp and self._clamp_range is not None:
                lo, hi = self._clamp_range
                self.u = _clamp_field(
                    self.u, lo if lo is not None else -1e6,
                    hi if hi is not None else 1e6
                )
                self.v = _clamp_field(
                    self.v, lo if lo is not None else -1e6,
                    hi if hi is not None else 1e6
                )

            self.step_count += 1

            # Fire callbacks
            for callback, every in self._callbacks:
                if self.step_count % every == 0:
                    callback(self)

        elapsed = time.perf_counter() - t0
        self._total_sim_time += elapsed
        logger.debug(
            f"Completed {num_steps} {method} steps in {elapsed:.3f}s "
            f"({num_steps / max(elapsed, 1e-10):.0f} steps/s)"
        )

    def _step_euler(
        self,
        dt: float,
        react_fn: Callable,
        params: Dict[str, float],
        Du: float,
        Dv: float,
    ) -> None:
        """Forward Euler time step."""
        lu = apply_laplacian(self.u, self.bc)
        lv = apply_laplacian(self.v, self.bc)
        du_react, dv_react = react_fn(self.u, self.v, params)
        self.u += dt * (Du * lu + du_react)
        self.v += dt * (Dv * lv + dv_react)

    def _step_rk2(
        self,
        dt: float,
        react_fn: Callable,
        params: Dict[str, float],
        Du: float,
        Dv: float,
    ) -> None:
        """Midpoint (RK2) time step for second-order accuracy."""
        lu = apply_laplacian(self.u, self.bc)
        lv = apply_laplacian(self.v, self.bc)
        du1, dv1 = react_fn(self.u, self.v, params)

        u_mid = self.u + 0.5 * dt * (Du * lu + du1)
        v_mid = self.v + 0.5 * dt * (Dv * lv + dv1)

        lu_mid = apply_laplacian(u_mid, self.bc)
        lv_mid = apply_laplacian(v_mid, self.bc)
        du2, dv2 = react_fn(u_mid, v_mid, params)

        self.u += dt * (Du * lu_mid + du2)
        self.v += dt * (Dv * lv_mid + dv2)

    def _step_rk4(
        self,
        dt: float,
        react_fn: Callable,
        params: Dict[str, float],
        Du: float,
        Dv: float,
    ) -> None:
        """4th-order Runge-Kutta time step for high accuracy.

        RK4 requires 4 Laplacian evaluations per step but provides
        O(dt⁴) local truncation error.
        """
        # k1
        lu1 = apply_laplacian(self.u, self.bc)
        lv1 = apply_laplacian(self.v, self.bc)
        du1, dv1 = react_fn(self.u, self.v, params)
        k1_u = Du * lu1 + du1
        k1_v = Dv * lv1 + dv1

        # k2
        u2 = self.u + 0.5 * dt * k1_u
        v2 = self.v + 0.5 * dt * k1_v
        lu2 = apply_laplacian(u2, self.bc)
        lv2 = apply_laplacian(v2, self.bc)
        du2, dv2 = react_fn(u2, v2, params)
        k2_u = Du * lu2 + du2
        k2_v = Dv * lv2 + dv2

        # k3
        u3 = self.u + 0.5 * dt * k2_u
        v3 = self.v + 0.5 * dt * k2_v
        lu3 = apply_laplacian(u3, self.bc)
        lv3 = apply_laplacian(v3, self.bc)
        du3, dv3 = react_fn(u3, v3, params)
        k3_u = Du * lu3 + du3
        k3_v = Dv * lv3 + dv3

        # k4
        u4 = self.u + dt * k3_u
        v4 = self.v + dt * k3_v
        lu4 = apply_laplacian(u4, self.bc)
        lv4 = apply_laplacian(v4, self.bc)
        du4, dv4 = react_fn(u4, v4, params)
        k4_u = Du * lu4 + du4
        k4_v = Dv * lv4 + dv4

        # Combine
        self.u += (dt / 6.0) * (k1_u + 2 * k2_u + 2 * k3_u + k4_u)
        self.v += (dt / 6.0) * (k1_v + 2 * k2_v + 2 * k3_v + k4_v)

    def step_until(self, target_step: int, method: str = "euler") -> None:
        """Advance until step_count reaches target_step.

        Args:
            target_step: Target step count.
            method: Integration method.
        """
        remaining = target_step - self.step_count
        if remaining > 0:
            self.step(remaining, method)

    def adaptive_step(
        self,
        num_steps: int,
        method: str = "euler",
        safety: float = 0.5,
        max_dt: Optional[float] = None,
        min_dt: Optional[float] = None,
        target_change: float = 0.1,
    ) -> float:
        """Advance with adaptive time stepping based on concentration change rate.

        The time step is adjusted so that the maximum concentration change
        per step stays near target_change.

        Args:
            num_steps: Approximate number of steps (actual may vary).
            method: Integration method.
            safety: Safety factor for time step (0 < safety < 1).
            max_dt: Maximum allowed time step.
            min_dt: Minimum allowed time step.
            target_change: Target maximum concentration change per step.

        Returns:
            Final time step used.
        """
        original_dt = self.dt
        if max_dt is None:
            max_dt = self.dt * 4
        if min_dt is None:
            min_dt = self.dt * 0.01

        react_fn = self.model_config["react"]
        params = self.params
        Du = params.get("Du", 0.16)
        Dv = params.get("Dv", 0.08)
        dt = self.dt

        steps_taken = 0
        while steps_taken < num_steps:
            lu = apply_laplacian(self.u, self.bc)
            lv = apply_laplacian(self.v, self.bc)
            du_react, dv_react = react_fn(self.u, self.v, params)

            max_rate = max(
                np.max(np.abs(Du * lu + du_react)),
                np.max(np.abs(Dv * lv + dv_react)),
                1e-10,
            )
            dt = np.clip(safety * target_change / max_rate, min_dt, max_dt)

            if method == "euler":
                self.u += dt * (Du * lu + du_react)
                self.v += dt * (Dv * lv + dv_react)
            else:
                self.dt = dt
                self.step(1, method)

            if self.clamp and self._clamp_range is not None:
                lo, hi = self._clamp_range
                self.u = _clamp_field(
                    self.u, lo if lo is not None else -1e6,
                    hi if hi is not None else 1e6
                )
                self.v = _clamp_field(
                    self.v, lo if lo is not None else -1e6,
                    hi if hi is not None else 1e6
                )

            self.step_count += 1
            steps_taken += 1

            self._emit(
                SimulationEvent.ADAPTIVE_DT_CHANGED,
                dt=dt, max_rate=max_rate,
            )

        # Restore original dt
        self.dt = original_dt
        return dt

    # ── State management ──

    def get_state(self) -> Tuple[NDArray[np.floating], NDArray[np.floating]]:
        """Return copies of the current (u, v) arrays."""
        return self.u.copy(), self.v.copy()

    def set_state(
        self,
        u: NDArray[np.floating],
        v: NDArray[np.floating],
        step_count: Optional[int] = None,
    ) -> None:
        """Set the simulation state.

        Args:
            u, v: 2D numpy arrays.
            step_count: Optional step count override.

        Raises:
            ValueError: If array shapes don't match grid size.
        """
        if u.shape != (self.n, self.n) or v.shape != (self.n, self.n):
            raise ValueError(
                f"State shape mismatch: expected ({self.n}, {self.n}), "
                f"got u={u.shape}, v={v.shape}"
            )
        self.u = u.copy().astype(np.float64)
        self.v = v.copy().astype(np.float64)
        if step_count is not None:
            self.step_count = step_count

    # ── Checkpoint ──

    def save_checkpoint(self, filepath: str) -> None:
        """Save current state to a compressed NumPy archive.

        Saves: u, v arrays, step_count, model_name, all parameters,
        dt, grid_size, and boundary condition.
        """
        np.savez_compressed(
            filepath,
            u=self.u,
            v=self.v,
            step_count=np.array([self.step_count]),
            model_name=np.array([self.model_name]),
            params=np.array([list(self.params.values())]),
            param_keys=np.array([list(self.params.keys())]),
            dt=np.array([self.dt]),
            grid_size=np.array([self.n]),
            bc=np.array([self.bc]),
            clamp=np.array([self.clamp]),
        )
        self._emit(SimulationEvent.CHECKPOINT_SAVED, filepath=filepath)
        logger.info(f"Checkpoint saved to {filepath}")

    @classmethod
    def load_checkpoint(cls, filepath: str) -> "ReactionDiffusionSolver":
        """Load solver state from a checkpoint file.

        Returns a fully initialized solver with restored state.
        """
        data = np.load(filepath, allow_pickle=True)
        model_name = str(data["model_name"][0])
        grid_size = int(data["grid_size"][0])
        dt = float(data["dt"][0])
        bc = str(data["bc"][0])
        step_count = int(data["step_count"][0])

        param_keys = list(data["param_keys"][0])
        param_values = list(data["params"][0])
        params = dict(zip(param_keys, param_values))

        clamp_val = True
        if "clamp" in data:
            clamp_val = bool(data["clamp"][0])

        solver = cls(
            model_name=model_name, grid_size=grid_size,
            params=params, bc=bc, dt=dt, step_count=step_count,
            clamp=clamp_val,
        )
        solver.u = data["u"].astype(np.float64)
        solver.v = data["v"].astype(np.float64)

        solver._emit(SimulationEvent.STATE_LOADED, filepath=filepath)
        logger.info(
            f"Loaded checkpoint from {filepath}: "
            f"{model_name}, step={step_count}, grid={grid_size}"
        )
        return solver

    # ── Statistics ──

    def compute_statistics(self) -> Dict[str, Union[float, int]]:
        """Compute summary statistics of the current simulation state.

        Returns:
            dict with keys: u_min, u_max, u_mean, u_std, v_min, v_max,
                           v_mean, v_std, step_count, sim_time
        """
        return {
            "u_min": float(np.min(self.u)),
            "u_max": float(np.max(self.u)),
            "u_mean": float(np.mean(self.u)),
            "u_std": float(np.std(self.u)),
            "v_min": float(np.min(self.v)),
            "v_max": float(np.max(self.v)),
            "v_mean": float(np.mean(self.v)),
            "v_std": float(np.std(self.v)),
            "step_count": self.step_count,
            "sim_time": self._total_sim_time,
        }

    # ── Parameter space exploration ──

    @staticmethod
    def parameter_sweep(
        model_name: str,
        param_name: str,
        values: list,
        grid_size: int = 64,
        steps: int = 1000,
        method: str = "euler",
        metric: str = "v_std",
    ) -> Dict[float, float]:
        """Run a parameter sweep and collect a metric for each value.

        Useful for exploring how a single parameter affects pattern formation.

        Args:
            model_name: Model to use.
            param_name: Parameter to vary.
            values: List of parameter values to try.
            grid_size: Grid size for each run.
            steps: Steps per run.
            method: Integration method.
            metric: Statistic to collect ("v_std", "u_mean", "v_max", etc.)

        Returns:
            Dict mapping parameter value to metric result.
        """
        results = {}
        for val in values:
            solver = ReactionDiffusionSolver(model_name, grid_size=grid_size)
            solver.params[param_name] = val
            solver.apply_perturbation()
            solver.step(steps, method=method)
            stats = solver.compute_statistics()
            results[val] = stats.get(metric, 0.0)
            logger.info(f"  {param_name}={val}: {metric}={results[val]:.6f}")
        return results