"""
D2Q9 Lattice definition for the Lattice Boltzmann Method.

The D2Q9 model uses 9 velocity directions on a 2D lattice:
    
    6  2  5
     \\ | /
    3 - 0 - 1
     / | \\
    7  4  8

Velocity vectors:
    e0 = (0,0),  e1 = (1,0),  e2 = (0,1),  e3 = (-1,0),  e4 = (0,-1)
    e5 = (1,1),  e6 = (-1,1), e7 = (-1,-1), e8 = (1,-1)

Weights:
    w0 = 4/9 (rest)
    w1..4 = 1/9 (cardinal)
    w5..8 = 1/36 (diagonal)
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class D2Q9Lattice:
    """
    D2Q9 lattice configuration for 2D LBM simulations.
    
    Provides the fundamental constants needed for the lattice:
    velocity vectors, weights, and opposite direction indices.
    """
    
    # Number of velocity directions
    Q: int = 9
    
    # Velocity vectors (Q, 2) — (cx, cy) for each direction
    # Direction layout:
    #   6  2  5
    #    \ | /
    #   3 - 0 - 1
    #    / | \
    #   7  4  8
    ex: np.ndarray = None
    ey: np.ndarray = None
    
    # Weights for equilibrium distribution
    w: np.ndarray = None
    
    # Opposite direction index (for bounce-back)
    opposite: np.ndarray = None
    
    # Speed of sound squared
    cs2: float = 1.0 / 3.0
    
    def __post_init__(self):
        if self.ex is None:
            self.ex = np.array([0, 1, 0, -1, 0, 1, -1, -1, 1])
        if self.ey is None:
            self.ey = np.array([0, 0, 1, 0, -1, 1, 1, -1, -1])
        if self.w is None:
            self.w = np.array([4/9, 1/9, 1/9, 1/9, 1/9, 1/36, 1/36, 1/36, 1/36])
        if self.opposite is None:
            # 0<->0, 1<->3, 2<->4, 5<->7, 6<->8
            self.opposite = np.array([0, 3, 4, 1, 2, 7, 8, 5, 6])
    
    @property
    def cs(self) -> float:
        """Speed of sound."""
        return np.sqrt(self.cs2)
    
    def equilibrium(self, rho: np.ndarray, ux: np.ndarray, uy: np.ndarray) -> np.ndarray:
        """
        Compute the Maxwell-Boltzmann equilibrium distribution.
        
        f_eq_i = w_i * rho * (1 + (e_i . u)/cs2 + (e_i . u)^2/(2*cs4) - u.u/(2*cs2))
        
        Parameters
        ----------
        rho : np.ndarray, shape (Ny, Nx)
            Density field
        ux : np.ndarray, shape (Ny, Nx)
            X-velocity field
        uy : np.ndarray, shape (Ny, Nx)
            Y-velocity field
            
        Returns
        -------
        np.ndarray, shape (Q, Ny, Nx)
            Equilibrium distribution functions
        """
        feq = np.zeros((self.Q, rho.shape[0], rho.shape[1]))
        
        usq = ux**2 + uy**2  # |u|^2
        
        for i in range(self.Q):
            eu = self.ex[i] * ux + self.ey[i] * uy  # e_i . u
            feq[i] = self.w[i] * rho * (
                1.0
                + eu / self.cs2
                + eu**2 / (2.0 * self.cs2**2)
                - usq / (2.0 * self.cs2)
            )
        
        return feq
    
    def macroscopic(self, f: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Compute macroscopic quantities from distribution functions.
        
        Parameters
        ----------
        f : np.ndarray, shape (Q, Ny, Nx)
            Distribution functions
            
        Returns
        -------
        rho, ux, uy : tuple of np.ndarray, each shape (Ny, Nx)
            Density and velocity components
        """
        rho = np.sum(f, axis=0)
        ux = np.sum(f * self.ex[:, None, None], axis=0) / rho
        uy = np.sum(f * self.ey[:, None, None], axis=0) / rho
        return rho, ux, uy
    
    def stream(self, f: np.ndarray) -> np.ndarray:
        """
        Streaming step: propagate distributions along their velocity directions.
        
        Each f_i is shifted by (ex_i, ey_i) lattice units.
        Uses np.roll for periodic boundary conditions at the edges.
        
        Parameters
        ----------
        f : np.ndarray, shape (Q, Ny, Nx)
            Pre-streaming distribution functions
            
        Returns
        -------
        np.ndarray, shape (Q, Ny, Nx)
            Post-streaming distribution functions
        """
        f_new = np.empty_like(f)
        for i in range(self.Q):
            f_new[i] = np.roll(np.roll(f[i], self.ex[i], axis=1), self.ey[i], axis=0)
        return f_new
    
    def validate(self) -> bool:
        """Validate lattice constants."""
        assert self.Q == 9, f"Expected Q=9, got {self.Q}"
        assert np.isclose(self.w.sum(), 1.0), f"Weights must sum to 1, got {self.w.sum()}"
        assert len(self.ex) == len(self.ey) == len(self.w) == 9
        # Check opposite directions
        for i in range(1, 5):
            j = self.opposite[i]
            assert self.ex[i] == -self.ex[j], f"Direction {i} opposite {j} x-velocity mismatch"
            assert self.ey[i] == -self.ey[j], f"Direction {i} opposite {j} y-velocity mismatch"
        return True