"""
Boundary conditions for LBM simulations.

Implements:
- BounceBackBoundary: No-slip walls via halfway bounce-back on obstacle nodes
- FullWayBounceBackBoundary: No-slip walls at domain boundaries
- ZouHeVelocityBoundary: Zou-He velocity inlet
- ZouHePressureBoundary: Zou-He pressure outlet
- OpenBoundary: Simple extrapolation open boundary (stable, for outlets)
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .lattice import D2Q9Lattice
    from .simulation import LBMSimulation


class BoundaryCondition(ABC):
    """Abstract base class for boundary conditions."""
    
    @abstractmethod
    def apply(self, sim: 'LBMSimulation') -> None:
        """Apply the boundary condition to the simulation."""
        pass


class BounceBackBoundary(BoundaryCondition):
    """
    No-slip boundary using halfway bounce-back scheme.
    
    Solid nodes reflect all distributions to their opposite directions.
    This enforces zero velocity at the wall (no-slip condition).
    
    Parameters
    ----------
    obstacle_mask : np.ndarray, shape (Ny, Nx), dtype bool
        True where solid obstacles exist.
    """
    
    def __init__(self, obstacle_mask: np.ndarray):
        self.obstacle_mask = obstacle_mask
    
    def apply(self, sim: 'LBMSimulation') -> None:
        """Apply bounce-back on all solid nodes."""
        lattice = sim.lattice
        f_bounce = sim.f[:, self.obstacle_mask].copy()
        for i in range(lattice.Q):
            sim.f[i, self.obstacle_mask] = f_bounce[lattice.opposite[i]]


class FullWayBounceBackBoundary(BoundaryCondition):
    """
    Full-way bounce-back for stationary walls at domain boundaries.
    
    Handles top, bottom, left, right walls of the domain.
    """
    
    def __init__(self, top: bool = True, bottom: bool = True, 
                 left: bool = False, right: bool = False):
        self.top = top
        self.bottom = bottom
        self.left = left
        self.right = right
    
    def apply(self, sim: 'LBMSimulation') -> None:
        """Apply bounce-back on domain walls."""
        f = sim.f
        
        # Bottom wall (y=0): directions pointing down bounce up
        if self.bottom:
            f[2, 0, :] = f[4, 0, :]
            f[5, 0, :] = f[7, 0, :]
            f[6, 0, :] = f[8, 0, :]
        
        # Top wall (y=-1): directions pointing up bounce down
        if self.top:
            f[4, -1, :] = f[2, -1, :]
            f[7, -1, :] = f[5, -1, :]
            f[8, -1, :] = f[6, -1, :]
        
        # Left wall (x=0): directions pointing left bounce right
        if self.left:
            f[1, :, 0] = f[3, :, 0]
            f[5, :, 0] = f[7, :, 0]
            f[8, :, 0] = f[6, :, 0]
        
        # Right wall (x=-1): directions pointing right bounce left
        if self.right:
            f[3, :, -1] = f[1, :, -1]
            f[7, :, -1] = f[5, :, -1]
            f[6, :, -1] = f[8, :, -1]


class ZouHeVelocityBoundary(BoundaryCondition):
    """
    Zou-He velocity boundary condition for inlet.
    
    Imposes a prescribed velocity at the left boundary (x=0),
    then uses the Zou-He method to compute unknown distribution
    functions pointing into the domain.
    
    Parameters
    ----------
    ux_inlet : float or np.ndarray
        X-velocity at the boundary.
    uy_inlet : float or np.ndarray, optional
        Y-velocity at the boundary (default 0).
    side : str
        'left' or 'right'.
    """
    
    def __init__(self, ux_inlet, uy_inlet=0.0, side='left'):
        self.ux_inlet = ux_inlet
        self.uy_inlet = uy_inlet
        self.side = side
    
    def apply(self, sim: 'LBMSimulation') -> None:
        """Apply Zou-He velocity BC."""
        lattice = sim.lattice
        f = sim.f
        
        if self.side == 'left':
            col = 0
            ux_val = self.ux_inlet if np.isscalar(self.ux_inlet) else self.ux_inlet
            uy_val = self.uy_inlet if np.isscalar(self.uy_inlet) else self.uy_inlet
            
            # Known distributions: f0, f2, f4, f3, f6, f7 (after streaming)
            # Unknown: f1, f5, f8 (pointing into domain)
            # Interior rows only (skip top/bottom if they are walls)
            rows = slice(1, -1)  # Exclude corner rows for stability
            
            f_left = f[:, rows, col]
            
            rho_left = (f_left[0] + f_left[2] + f_left[4] +
                        2.0 * (f_left[3] + f_left[6] + f_left[7])) / (1.0 - ux_val)
            
            f[1, rows, col] = f_left[3] + (2.0/3.0) * rho_left * ux_val
            f[5, rows, col] = f_left[7] + (1.0/6.0) * rho_left * ux_val + \
                              0.5 * (f_left[4] - f_left[2]) + \
                              0.5 * rho_left * uy_val
            f[8, rows, col] = f_left[6] + (1.0/6.0) * rho_left * ux_val + \
                              0.5 * (f_left[2] - f_left[4]) - \
                              0.5 * rho_left * uy_val


class ZouHePressureBoundary(BoundaryCondition):
    """
    Zou-He pressure (density) boundary condition for outlet.
    
    Imposes a prescribed density (rho=1.0) at the right boundary,
    which acts as a pressure outlet. Computes unknown distributions
    pointing into the domain.
    
    Parameters
    ----------
    rho_boundary : float
        Density at the boundary (rho=1.0 is reference density).
    side : str
        'left' or 'right'.
    """
    
    def __init__(self, rho_boundary: float = 1.0, side: str = 'right'):
        self.rho_boundary = rho_boundary
        self.side = side
    
    def apply(self, sim: 'LBMSimulation') -> None:
        """Apply Zou-He pressure BC."""
        f = sim.f
        rho0 = self.rho_boundary
        
        if self.side == 'right':
            col = -1
            rows = slice(1, -1)  # Skip corners
            
            f_right = f[:, rows, col]
            
            ux_right = -1.0 + (f_right[0] + f_right[2] + f_right[4] +
                               2.0 * (f_right[1] + f_right[5] + f_right[8])) / rho0
            
            f[3, rows, col] = f_right[1] - (2.0/3.0) * rho0 * ux_right
            f[7, rows, col] = f_right[5] - (1.0/6.0) * rho0 * ux_right - \
                              0.5 * (f_right[2] - f_right[4])
            f[6, rows, col] = f_right[8] - (1.0/6.0) * rho0 * ux_right + \
                              0.5 * (f_right[2] - f_right[4])
        
        elif self.side == 'left':
            col = 0
            rows = slice(1, -1)
            
            f_left = f[:, rows, col]
            
            ux_left = 1.0 - (f_left[0] + f_left[2] + f_left[4] +
                             2.0 * (f_left[3] + f_left[6] + f_left[7])) / rho0
            
            f[1, rows, col] = f_left[3] + (2.0/3.0) * rho0 * ux_left
            f[5, rows, col] = f_left[7] + (1.0/6.0) * rho0 * ux_left + \
                              0.5 * (f_left[4] - f_left[2])
            f[8, rows, col] = f_left[6] + (1.0/6.0) * rho0 * ux_left - \
                              0.5 * (f_left[4] - f_left[2])


class OpenBoundary(BoundaryCondition):
    """
    Simple open (zero-gradient) boundary condition.
    
    Extrapolates distributions from interior to boundary.
    More stable than Zou-He for outlet conditions in some cases.
    
    Parameters
    ----------
    side : str
        'left' or 'right'.
    """
    
    def __init__(self, side: str = 'right'):
        self.side = side
    
    def apply(self, sim: 'LBMSimulation') -> None:
        """Apply zero-gradient extrapolation."""
        f = sim.f
        
        if self.side == 'right':
            f[:, :, -1] = f[:, :, -2]
        elif self.side == 'left':
            f[:, :, 0] = f[:, :, 1]


class PeriodicBoundary(BoundaryCondition):
    """
    Periodic boundary condition.
    
    This is actually handled implicitly by the np.roll-based streaming
    in D2Q9Lattice.stream(). This class exists for explicit declaration
    and documentation, but its apply() is a no-op.
    """
    
    def apply(self, sim: 'LBMSimulation') -> None:
        """Periodic BC is handled by streaming — no additional action needed."""
        pass