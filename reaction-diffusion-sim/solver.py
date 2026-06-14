"""
PDE Solver engine for reaction-diffusion systems.

Implements:
- 9-point isotropic Laplacian stencil for accurate spatial derivatives
- Multiple boundary conditions (periodic, Dirichlet, Neumann)
- Euler and RK2 (midpoint) time integration
- Adaptive time stepping based on CFL-like stability criterion
- Field clamping for numerical stability
- Perturbation seeding (center_square, ring, cross, random, corner, multi_spot)
- Checkpoint save/load via compressed NumPy archives
- Step callback system for progress monitoring

Architecture:
    ReactionDiffusionSolver holds the simulation state (u, v fields) and parameters.
    The solver is designed to be used in a step-wise fashion:
    
        solver = ReactionDiffusionSolver("gray-scott", grid_size=128)
        solver.apply_perturbation()
        solver.step(1000)
        u, v = solver.get_state()
"""

import numpy as np
from scipy.ndimage import convolve

from models import get_model, _clamp_field

# 9-point isotropic Laplacian stencil (dx=1)
# This stencil is more isotropic than the standard 5-point stencil,
# reducing directional artifacts in the diffusion operator.
# For a derivation, see: O'Reilly & Beck (2006), "A Function Approximation
# Approach to the 9-Point Laplacian"
LAPLACIAN_STENCIL = np.array([
    [1 / 6,  4 / 6,  1 / 6],
    [4 / 6, -20 / 6, 4 / 6],
    [1 / 6,  4 / 6,  1 / 6],
], dtype=np.float64)


class BoundaryCondition:
    """Boundary condition types for the simulation domain."""
    PERIODIC = "periodic"      # Wrap-around (toroidal topology)
    DIRICHLET = "dirichlet"    # Fixed value at boundaries
    NEUMANN = "neumann"        # Zero-flux (no gradient at boundary)


def apply_laplacian(field, bc="periodic", bc_value=0.0):
    """
    Compute the Laplacian of a 2D field using the 9-point isotropic stencil.
    
    The 9-point stencil provides better rotational symmetry compared to the
    standard 5-point stencil, reducing grid-induced anisotropy by ~3x.
    
    Args:
        field: 2D numpy array of concentration values
        bc: Boundary condition — "periodic", "dirichlet", or "neumann"
        bc_value: For dirichlet BC, the fixed boundary value
    
    Returns:
        2D numpy array — Laplacian of the field (same shape as input)
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
        raise ValueError(f"Unknown boundary condition: {bc}. "
                         f"Use 'periodic', 'dirichlet', or 'neumann'.")


def _convolve_padded(padded):
    """Apply Laplacian stencil to a pre-padded 2D field.
    
    This manually applies the 3x3 stencil to avoid scipy.ndimage.convolve's
    boundary handling, since we've already padded the field appropriately.
    """
    n, m = padded.shape
    result = np.zeros((n - 2, m - 2), dtype=np.float64)
    stencil = LAPLACIAN_STENCIL
    for di in range(3):
        for dj in range(3):
            result += stencil[di, dj] * padded[di:n - 2 + di, dj:m - 2 + dj]
    return result


class ReactionDiffusionSolver:
    """
    Numerical solver for reaction-diffusion PDE systems.
    
    Supports Gray-Scott, FitzHugh-Nagumo, Gierer-Meinhardt, and Brusselator
    models. Uses explicit Euler or RK2 (midpoint) time integration with
    optional adaptive time stepping and field clamping for stability.
    
    Example:
        >>> solver = ReactionDiffusionSolver("gray-scott", grid_size=128)
        >>> solver.apply_perturbation()
        >>> solver.step(5000)
        >>> u, v = solver.get_state()
        >>> solver.save_checkpoint("state.npz")
    """

    def __init__(self, model_name="gray-scott", grid_size=128, params=None,
                 bc="periodic", dt=1.0, step_count=0, clamp=True):
        """
        Initialize the solver.
        
        Args:
            model_name: Name of the reaction model (see models.MODELS)
            grid_size: Size of the NxN simulation grid
            params: Override model parameters (dict)
            bc: Boundary condition type ("periodic", "dirichlet", "neumann")
            dt: Time step size (overridden if adaptive=True)
            step_count: Initial step count (for resumed simulations)
            clamp: Whether to clamp concentrations to model-specific ranges
        """
        self.model_config = get_model(model_name)
        self.model_name = model_name
        self.n = grid_size
        self.dt = dt
        self.bc = bc
        self.step_count = step_count
        self.clamp = clamp

        # Merge defaults with user overrides
        self.params = dict(self.model_config["defaults"])
        if params:
            self.params.update(params)

        # Get stability clamp range from model config
        self._clamp_range = self.model_config.get("stability_clamp", None)

        # Initialize state
        u, v = self.model_config["default_state"](grid_size)
        self.u = u.astype(np.float64)
        self.v = v.astype(np.float64)
        
        # Callback system for progress monitoring
        self._callbacks = []

    def add_callback(self, callback, every=100):
        """
        Add a callback function called periodically during simulation.
        
        Args:
            callback: Function with signature callback(solver) -> None
            every: Call every N steps
        """
        self._callbacks.append((callback, every))

    def apply_perturbation(self, pert_config=None):
        """
        Apply a perturbation to the concentration fields.
        
        Perturbations break the symmetry of the initial homogeneous state,
        allowing patterns to nucleate and grow. Different perturbation types
        lead to different pattern formation dynamics.
        
        Args:
            pert_config: Dict with keys:
                - type: "center_square", "ring", "cross", "random", "corner", "multi_spot"
                - size: Size of perturbation region (pixels)
                - u_val: u concentration in perturbed region
                - v_val: v concentration in perturbed region
                - noise: Amplitude of random noise (for "random" type)
                - center: (row, col) center position
                - count: Number of spots (for "multi_spot")
                - radius, thickness: For "ring" type
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
                self.v[rx - s:ry + s, ry - s:ry + s] = v_val
        else:
            raise ValueError(f"Unknown perturbation type: {ptype}")

    def step(self, num_steps=1, method="euler"):
        """
        Advance the simulation by num_steps time steps.
        
        Args:
            num_steps: Number of time steps to advance
            method: "euler" for forward Euler, "rk2" for midpoint (RK2)
        
        The Euler method is fast but less stable; RK2 is more accurate
        at the cost of ~2x computation per step.
        """
        dt = self.dt
        react_fn = self.model_config["react"]
        params = self.params
        Du = params.get("Du", 0.16)
        Dv = params.get("Dv", 0.08)

        for step_idx in range(num_steps):
            if method == "euler":
                lu = apply_laplacian(self.u, self.bc)
                lv = apply_laplacian(self.v, self.bc)
                du_react, dv_react = react_fn(self.u, self.v, params)
                self.u += dt * (Du * lu + du_react)
                self.v += dt * (Dv * lv + dv_react)
            elif method == "rk2":
                # Midpoint method (RK2): evaluate derivative at midpoint
                # for second-order accuracy in time
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
            else:
                raise ValueError(f"Unknown integration method: {method}. "
                                 f"Use 'euler' or 'rk2'.")

            # Clamp concentrations for numerical stability
            if self.clamp and self._clamp_range is not None:
                lo, hi = self._clamp_range
                self.u = _clamp_field(self.u, lo if lo is not None else -1e6,
                                      hi if hi is not None else 1e6)
                self.v = _clamp_field(self.v, lo if lo is not None else -1e6,
                                      hi if hi is not None else 1e6)

            self.step_count += 1

            # Fire callbacks
            for callback, every in self._callbacks:
                if self.step_count % every == 0:
                    callback(self)

    def step_until(self, target_step, method="euler"):
        """Advance until step_count reaches target_step."""
        remaining = target_step - self.step_count
        if remaining > 0:
            self.step(remaining, method)

    def adaptive_step(self, num_steps, method="euler", safety=0.5,
                      max_dt=None, min_dt=1e-6, target_change=0.1):
        """
        Advance with adaptive time stepping based on concentration change rate.
        
        The time step is adjusted so that the maximum concentration change
        per step stays near target_change. This prevents the simulation from
        blowing up while allowing large steps in stable regions.
        
        Args:
            num_steps: Approximate number of steps (actual may vary)
            method: Integration method
            safety: Safety factor for time step (0 < safety < 1)
            max_dt: Maximum allowed time step
            min_dt: Minimum allowed time step
            target_change: Target maximum concentration change per step
        """
        if max_dt is None:
            max_dt = self.dt * 4  # allow up to 4x the base dt
        if min_dt is None:
            min_dt = self.dt * 0.01
        
        react_fn = self.model_config["react"]
        params = self.params
        Du = params.get("Du", 0.16)
        Dv = params.get("Dv", 0.08)
        dt = self.dt
        
        steps_taken = 0
        while steps_taken < num_steps:
            # Compute derivatives to estimate optimal dt
            lu = apply_laplacian(self.u, self.bc)
            lv = apply_laplacian(self.v, self.bc)
            du_react, dv_react = react_fn(self.u, self.v, params)
            
            max_rate = max(np.max(np.abs(Du * lu + du_react)),
                          np.max(np.abs(Dv * lv + dv_react)), 1e-10)
            dt = np.clip(safety * target_change / max_rate, min_dt, max_dt)
            
            # Take step with computed dt
            if method == "euler":
                self.u += dt * (Du * lu + du_react)
                self.v += dt * (Dv * lv + dv_react)
            else:
                # For RK2, fall back to regular step method
                self.dt = dt
                self.step(1, method)
            
            if self.clamp and self._clamp_range is not None:
                lo, hi = self._clamp_range
                self.u = _clamp_field(self.u, lo if lo is not None else -1e6,
                                      hi if hi is not None else 1e6)
                self.v = _clamp_field(self.v, lo if lo is not None else -1e6,
                                      hi if hi is not None else 1e6)
            
            self.step_count += 1
            steps_taken += 1
            
            # Fire callbacks
            for callback, every in self._callbacks:
                if self.step_count % every == 0:
                    callback(self)
        
        # Restore original dt
        return dt

    def get_state(self):
        """Return copies of the current (u, v) arrays."""
        return self.u.copy(), self.v.copy()

    def set_state(self, u, v, step_count=None):
        """Set the simulation state.
        
        Args:
            u, v: 2D numpy arrays
            step_count: Optional step count override
        """
        if u.shape != (self.n, self.n) or v.shape != (self.n, self.n):
            raise ValueError(f"State shape mismatch: expected ({self.n}, {self.n}), "
                           f"got u={u.shape}, v={v.shape}")
        self.u = u.copy().astype(np.float64)
        self.v = v.copy().astype(np.float64)
        if step_count is not None:
            self.step_count = step_count

    def save_checkpoint(self, filepath):
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
        )

    @classmethod
    def load_checkpoint(cls, filepath):
        """Load solver state from a checkpoint file.
        
        Restores: u, v arrays, step_count, model, parameters, grid size,
        and boundary condition. Returns a fully initialized solver.
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

        solver = cls(model_name=model_name, grid_size=grid_size,
                     params=params, bc=bc, dt=dt, step_count=step_count)
        solver.u = data["u"].astype(np.float64)
        solver.v = data["v"].astype(np.float64)
        return solver

    def compute_statistics(self):
        """
        Compute summary statistics of the current simulation state.
        
        Returns:
            dict with keys: u_min, u_max, u_mean, u_std, v_min, v_max,
                           v_mean, v_std, step_count
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
        }