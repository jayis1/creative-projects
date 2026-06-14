"""
PDE Solver engine for reaction-diffusion systems.

Implements:
- 9-point isotropic Laplacian stencil
- Multiple boundary conditions (periodic, dirichlet, neumann)
- Euler and RK2 time integration
- Perturbation seeding
- Checkpoint save/load
"""

import numpy as np
from scipy.ndimage import convolve

from models import get_model


# 9-point isotropic Laplacian stencil (dx=1)
# More isotropic than the standard 5-point stencil
LAPLACIAN_STENCIL = np.array([
    [1 / 6,  4 / 6,  1 / 6],
    [4 / 6, -20 / 6, 4 / 6],
    [1 / 6,  4 / 6,  1 / 6],
], dtype=np.float64)


class BoundaryCondition:
    PERIODIC = "periodic"
    DIRICHLET = "dirichlet"
    NEUMANN = "neumann"


def apply_laplacian(field, bc="periodic", bc_value=0.0):
    """
    Compute the Laplacian of a 2D field using the 9-point stencil.
    
    Args:
        field: 2D numpy array
        bc: Boundary condition — "periodic", "dirichlet", or "neumann"
        bc_value: For dirichlet, the fixed boundary value
    
    Returns:
        Laplacian of the field (same shape)
    """
    if bc == BoundaryCondition.PERIODIC:
        return convolve(field, LAPLACIAN_STENCIL, mode="wrap")
    elif bc == BoundaryCondition.DIRICHLET:
        # Pad with fixed boundary values
        padded = np.pad(field, 1, mode="constant", constant_values=bc_value)
        return _convolve_padded(padded)
    elif bc == BoundaryCondition.NEUMANN:
        # Pad by reflecting at boundaries (zero-flux)
        padded = np.pad(field, 1, mode="reflect")
        return _convolve_padded(padded)
    else:
        raise ValueError(f"Unknown boundary condition: {bc}")


def _convolve_padded(padded):
    """Apply Laplacian stencil to a pre-padded 2D field."""
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
    
    Supports Gray-Scott, FitzHugh-Nagumo, Gierer-Meinhardt, and Brusselator models.
    Uses explicit Euler or RK2 (midpoint) time integration.
    """

    def __init__(self, model_name="gray-scott", grid_size=128, params=None,
                 bc="periodic", dt=1.0, step_count=0):
        """
        Initialize the solver.
        
        Args:
            model_name: Name of the reaction model (see models.MODELS)
            grid_size: Size of the NxN simulation grid
            params: Override model parameters (dict)
            bc: Boundary condition type
            dt: Time step size
            step_count: Initial step count (for resumed simulations)
        """
        self.model_config = get_model(model_name)
        self.model_name = model_name
        self.n = grid_size
        self.dt = dt
        self.bc = bc
        self.step_count = step_count

        # Merge defaults with user overrides
        self.params = dict(self.model_config["defaults"])
        if params:
            self.params.update(params)

        # Initialize state
        u, v = self.model_config["default_state"](grid_size)
        self.u = u
        self.v = v

    def apply_perturbation(self, pert_config=None):
        """
        Apply a perturbation to the concentration fields.
        
        Args:
            pert_config: Dict with keys:
                - type: "center_square", "ring", "cross", "random", "corner"
                - size: size of perturbation region
                - u_val: u concentration to set in perturbed region
                - v_val: v concentration to set in perturbed region
                - noise: amplitude of random noise (for "random" type)
                - center: (row, col) center (default: grid center)
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
            self.u += np.random.randn(n, n) * amplitude
            self.v += np.random.randn(n, n) * amplitude

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
            for _ in range(count):
                rx = np.random.randint(size, n - size)
                ry = np.random.randint(size, n - size)
                s = size // 2
                self.u[rx - s:rx + s, ry - s:ry + s] = u_val
                self.v[rx - s:rx + s, ry - s:ry + s] = v_val

    def step(self, num_steps=1, method="euler"):
        """
        Advance the simulation by num_steps time steps.
        
        Args:
            num_steps: Number of time steps to advance
            method: "euler" or "rk2" for midpoint method
        """
        dt = self.dt
        react_fn = self.model_config["react"]
        params = self.params
        Du = params.get("Du", 0.16)
        Dv = params.get("Dv", 0.08)

        for _ in range(num_steps):
            if method == "euler":
                lu = apply_laplacian(self.u, self.bc)
                lv = apply_laplacian(self.v, self.bc)
                du_react, dv_react = react_fn(self.u, self.v, params)
                self.u += dt * (Du * lu + du_react)
                self.v += dt * (Dv * lv + dv_react)
            elif method == "rk2":
                # Midpoint method (RK2)
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
                raise ValueError(f"Unknown method: {method}")

            self.step_count += 1

    def step_until(self, target_step, method="euler"):
        """Advance until step_count reaches target_step."""
        remaining = target_step - self.step_count
        if remaining > 0:
            self.step(remaining, method)

    def get_state(self):
        """Return current (u, v) arrays."""
        return self.u.copy(), self.v.copy()

    def set_state(self, u, v, step_count=None):
        """Set the simulation state."""
        self.u = u.copy()
        self.v = v.copy()
        if step_count is not None:
            self.step_count = step_count

    def save_checkpoint(self, filepath):
        """Save current state to a compressed NumPy archive."""
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
        """Load solver state from a checkpoint file."""
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
        solver.u = data["u"]
        solver.v = data["v"]
        return solver