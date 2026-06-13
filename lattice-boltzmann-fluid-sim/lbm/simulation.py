"""
LBM Simulation engine.

Orchestrates the collision-stream cycle with boundary conditions
and obstacle interactions. Uses a robust implementation order:
  1. Collision
  2. Streaming  
  3. Obstacle bounce-back
  4. Domain boundary conditions
  5. Macroscopic update
"""

import numpy as np
from typing import List, Optional
from .lattice import D2Q9Lattice
from .boundaries import BoundaryCondition, BounceBackBoundary


class LBMSimulation:
    """
    Lattice Boltzmann Method simulation using D2Q9 lattice and BGK collision.
    
    The simulation follows the standard LBM algorithm:
        1. Collision (BGK relaxation towards equilibrium)
        2. Streaming (propagation along lattice velocities)
        3. Boundary conditions (bounce-back, inlet/outlet)
        4. Macroscopic update (density, velocity)
    
    Parameters
    ----------
    nx, ny : int
        Grid dimensions (width, height).
    viscosity : float
        Kinematic viscosity in lattice units.
        Related to relaxation time: nu = cs^2 * (tau - 0.5)
    lattice : D2Q9Lattice, optional
        Lattice configuration (default: standard D2Q9).
    """
    
    def __init__(self, nx: int, ny: int, viscosity: float = 0.02,
                 lattice: Optional[D2Q9Lattice] = None):
        self.nx = nx
        self.ny = ny
        self.lattice = lattice or D2Q9Lattice()
        self.viscosity = viscosity
        
        # Relaxation time from viscosity: nu = cs^2 * (tau - 0.5)
        self.tau = self.viscosity / self.lattice.cs2 + 0.5
        self.omega = 1.0 / self.tau  # Relaxation frequency
        
        # Validate stability
        if self.tau <= 0.5:
            raise ValueError(
                f"Relaxation time tau={self.tau:.4f} must be > 0.5 for stability. "
                f"Increase viscosity (current: {self.viscosity})"
            )
        
        # Distribution functions: shape (Q, Ny, Nx)
        self.f = np.zeros((self.lattice.Q, ny, nx))
        
        # Macroscopic fields
        self.rho = np.ones((ny, nx))
        self.ux = np.zeros((ny, nx))
        self.uy = np.zeros((ny, nx))
        
        # Obstacle mask
        self.obstacle_mask = np.zeros((ny, nx), dtype=bool)
        
        # Boundary conditions
        self.boundary_conditions: List[BoundaryCondition] = []
        
        # Simulation state
        self.step_count = 0
        self.time = 0.0
        
        # Derived quantities
        self.vorticity = np.zeros((ny, nx))
        self.speed = np.zeros((ny, nx))
        
        # Initialize to equilibrium at rest
        self._init_equilibrium()
    
    def _init_equilibrium(self):
        """Initialize distribution functions to equilibrium at rest."""
        self.f = self.lattice.equilibrium(self.rho, self.ux, self.uy)
    
    def set_velocity(self, ux: np.ndarray, uy: np.ndarray):
        """Set the initial velocity field and reinitialize equilibrium."""
        self.ux = ux.copy()
        self.uy = uy.copy()
        self.rho[:] = 1.0
        self.ux[self.obstacle_mask] = 0.0
        self.uy[self.obstacle_mask] = 0.0
        self._init_equilibrium()
    
    def set_inlet_velocity(self, u0: float):
        """
        Set a uniform inlet velocity in the x-direction.
        
        Parameters
        ----------
        u0 : float
            Inlet velocity (in lattice units, typically < 0.1 for low Mach).
        """
        self.ux[:] = u0
        self.uy[:] = 0.0
        self.rho[:] = 1.0
        self.ux[self.obstacle_mask] = 0.0
        self.uy[self.obstacle_mask] = 0.0
        self._init_equilibrium()
    
    def add_obstacle(self, obstacle):
        """Add an obstacle to the simulation domain."""
        mask = obstacle.mask(self.ny, self.nx)
        self.obstacle_mask |= mask
        self.ux[self.obstacle_mask] = 0.0
        self.uy[self.obstacle_mask] = 0.0
    
    def add_boundary_condition(self, bc: BoundaryCondition):
        """Add a boundary condition to be applied each step."""
        self.boundary_conditions.append(bc)
    
    def compute_vorticity(self):
        """
        Compute vorticity (curl of velocity) for flow visualization.
        
        vorticity_z = duy/dx - dux/dy
        """
        duy_dx = np.roll(self.uy, -1, axis=1) - np.roll(self.uy, 1, axis=1)
        dux_dy = np.roll(self.ux, -1, axis=0) - np.roll(self.ux, 1, axis=0)
        self.vorticity = 0.5 * (duy_dx - dux_dy)
        self.vorticity[self.obstacle_mask] = 0.0
    
    def compute_speed(self):
        """Compute velocity magnitude."""
        self.speed = np.sqrt(self.ux**2 + self.uy**2)
        self.speed[self.obstacle_mask] = 0.0
    
    def step(self, n_steps: int = 1):
        """
        Advance simulation by n_steps.
        
        Each step:
          1. Compute macroscopic quantities
          2. Collision (BGK)
          3. Save obstacle distributions for bounce-back
          4. Streaming
          5. Obstacle bounce-back
          6. Apply boundary conditions
          7. Re-compute macroscopic quantities
        """
        for _ in range(n_steps):
            self._single_step()
    
    def _single_step(self):
        """Execute one complete LBM time step."""
        lat = self.lattice
        
        # 1. Compute macroscopic quantities from current distributions
        self.rho, self.ux, self.uy = lat.macroscopic(self.f)
        self.ux[self.obstacle_mask] = 0.0
        self.uy[self.obstacle_mask] = 0.0
        
        # 2. Collision: BGK relaxation
        feq = lat.equilibrium(self.rho, self.ux, self.uy)
        self.f -= self.omega * (self.f - feq)
        
        # 3. Save distributions at obstacle nodes (pre-streaming for bounce-back)
        f_bounce = self.f[:, self.obstacle_mask].copy()
        
        # 4. Streaming
        self.f = lat.stream(self.f)
        
        # 5. Bounce-back at obstacles: reflect to opposite direction
        for i in range(lat.Q):
            self.f[i, self.obstacle_mask] = f_bounce[lat.opposite[i]]
        
        # 6. Apply boundary conditions
        for bc in self.boundary_conditions:
            bc.apply(self)
        
        # 7. Clip negative distributions for stability
        # (small negative values can appear due to BC conflicts at corners)
        self.f = np.maximum(self.f, 1e-10)
        
        # 8. Final macroscopic update
        self.rho, self.ux, self.uy = lat.macroscopic(self.f)
        self.ux[self.obstacle_mask] = 0.0
        self.uy[self.obstacle_mask] = 0.0
        
        self.step_count += 1
        self.time = self.step_count
    
    def kinetic_energy(self) -> float:
        """Compute total kinetic energy: 0.5 * sum(rho * |u|^2)."""
        return 0.5 * np.sum(self.rho * (self.ux**2 + self.uy**2))
    
    def reynolds_number(self, u_char: float, L_char: float) -> float:
        """Compute Reynolds number: Re = u * L / viscosity."""
        return u_char * L_char / self.viscosity
    
    def mach_number(self) -> float:
        """Compute maximum Mach number (should be << 1 for incompressible regime)."""
        self.compute_speed()
        return np.max(self.speed) / self.lattice.cs
    
    def stability_check(self) -> bool:
        """Check basic stability conditions."""
        if self.tau <= 0.5:
            return False
        if np.any(self.rho <= 0):
            return False
        if np.any(np.isnan(self.rho)) or np.any(np.isnan(self.ux)):
            return False
        if np.any(self.rho > 1.5) or np.any(self.rho < 0.5):
            return False
        return True
    
    def summary(self) -> str:
        """Return a summary string of simulation state."""
        self.compute_speed()
        self.compute_vorticity()
        
        max_speed = np.max(self.speed[~self.obstacle_mask]) if np.any(~self.obstacle_mask) else 0
        Re = self.reynolds_number(max_speed, 1.0)
        Ma = max_speed / self.lattice.cs if max_speed > 0 else 0
        KE = self.kinetic_energy()
        
        return (
            f"LBM Simulation Summary\n"
            f"  Grid:       {self.nx} x {self.ny}\n"
            f"  Step:       {self.step_count}\n"
            f"  tau:        {self.tau:.4f}  (omega={self.omega:.4f})\n"
            f"  viscosity:  {self.viscosity:.6f}\n"
            f"  Re (per LU):{Re:.2f}\n"
            f"  Mach (max): {Ma:.4f}\n"
            f"  KE total:   {KE:.6f}\n"
            f"  rho range:  [{np.min(self.rho[~self.obstacle_mask]):.6f}, "
            f"{np.max(self.rho[~self.obstacle_mask]):.6f}]\n"
            f"  |u| range:  [{np.min(self.speed[~self.obstacle_mask]):.6f}, "
            f"{max_speed:.6f}]\n"
            f"  Obstacles:  {np.sum(self.obstacle_mask)} solid nodes\n"
        )