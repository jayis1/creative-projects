"""
Obstacle definitions for LBM simulations.

Provides geometric primitives and special shapes that generate
boolean masks for bounce-back boundary conditions.
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import Tuple


class Obstacle(ABC):
    """Abstract base class for obstacles."""
    
    @abstractmethod
    def mask(self, ny: int, nx: int) -> np.ndarray:
        """Generate a boolean mask (True = solid) for the given grid."""
        pass
    
    @abstractmethod
    def describe(self) -> str:
        """Human-readable description of the obstacle."""
        pass


class CircleObstacle(Obstacle):
    """
    Circular obstacle.
    
    Parameters
    ----------
    cx, cy : float
        Center position in lattice units.
    radius : float
        Radius in lattice units.
    """
    
    def __init__(self, cx: float, cy: float, radius: float):
        self.cx = cx
        self.cy = cy
        self.radius = radius
    
    def mask(self, ny: int, nx: int) -> np.ndarray:
        Y, X = np.mgrid[0:ny, 0:nx]
        return (X - self.cx)**2 + (Y - self.cy)**2 <= self.radius**2
    
    def describe(self) -> str:
        return f"Circle(cx={self.cx}, cy={self.cy}, r={self.radius})"


class RectangleObstacle(Obstacle):
    """
    Rectangular obstacle.
    
    Parameters
    ----------
    x0, y0 : float
        Top-left corner.
    width, height : float
        Dimensions in lattice units.
    """
    
    def __init__(self, x0: float, y0: float, width: float, height: float):
        self.x0 = x0
        self.y0 = y0
        self.width = width
        self.height = height
    
    def mask(self, ny: int, nx: int) -> np.ndarray:
        Y, X = np.mgrid[0:ny, 0:nx]
        return ((X >= self.x0) & (X < self.x0 + self.width) &
                (Y >= self.y0) & (Y < self.y0 + self.height))
    
    def describe(self) -> str:
        return f"Rect(x0={self.x0}, y0={self.y0}, w={self.width}, h={self.height})"


class AirfoilObstacle(Obstacle):
    """
    NACA 4-digit airfoil obstacle.
    
    Generates a NACA 00xx symmetric airfoil (e.g., NACA 0012)
    at a given position and angle of attack.
    
    Parameters
    ----------
    cx, cy : float
        Center position of the airfoil leading edge region.
    chord : float
        Chord length in lattice units.
    thickness : float
        Maximum thickness as fraction of chord (e.g., 0.12 for NACA 0012).
    angle_deg : float
        Angle of attack in degrees.
    """
    
    def __init__(self, cx: float, cy: float, chord: float, 
                 thickness: float = 0.12, angle_deg: float = 0.0):
        self.cx = cx
        self.cy = cy
        self.chord = chord
        self.thickness = thickness
        self.angle_deg = angle_deg
    
    def _naca_yt(self, x_norm: np.ndarray) -> np.ndarray:
        """NACA symmetric airfoil half-thickness at normalized x."""
        t = self.thickness
        return 5.0 * t * (
            0.2969 * np.sqrt(x_norm)
            - 0.1260 * x_norm
            - 0.3516 * x_norm**2
            + 0.2843 * x_norm**3
            - 0.1015 * x_norm**4  # Closed trailing edge coefficient
        )
    
    def mask(self, ny: int, nx: int) -> np.ndarray:
        Y, X = np.mgrid[0:ny, 0:nx].astype(float)
        
        # Rotate coordinates to airfoil frame
        angle_rad = np.radians(self.angle_deg)
        dx = X - self.cx
        dy = Y - self.cy
        
        # Rotate so airfoil x-axis aligns with flow + angle
        x_rot = dx * np.cos(angle_rad) + dy * np.sin(angle_rad)
        y_rot = -dx * np.sin(angle_rad) + dy * np.cos(angle_rad)
        
        # Normalized chord position
        x_norm = x_rot / self.chord
        
        # Only consider points within [0, chord] along the chord
        valid = (x_norm >= 0.0) & (x_norm <= 1.0)
        
        # Half-thickness at each chord position
        yt = self._naca_yt(np.clip(x_norm, 0, 1))
        
        # Inside airfoil: |y| <= yt * chord
        inside = valid & (np.abs(y_rot) <= yt * self.chord)
        
        return inside
    
    def describe(self) -> str:
        return (f"NACA 00{int(self.thickness*100):02d} airfoil "
                f"(cx={self.cx}, cy={self.cy}, chord={self.chord}, "
                f"AoA={self.angle_deg}°)")


class MultiObstacle(Obstacle):
    """
    Composite obstacle from multiple sub-obstacles.
    
    Parameters
    ----------
    obstacles : list of Obstacle
        List of obstacles to combine (union).
    """
    
    def __init__(self, obstacles: list):
        self.obstacles = obstacles
    
    def mask(self, ny: int, nx: int) -> np.ndarray:
        combined = np.zeros((ny, nx), dtype=bool)
        for obs in self.obstacles:
            combined |= obs.mask(ny, nx)
        return combined
    
    def describe(self) -> str:
        descs = [o.describe() for o in self.obstacles]
        return "MultiObstacle(" + ", ".join(descs) + ")"


class CylinderArrayObstacle(Obstacle):
    """
    Array of circular cylinders (e.g., for porous media simulations).
    
    Parameters
    ----------
    spacing : float
        Distance between cylinder centers.
    radius : float
        Radius of each cylinder.
    x_offset, y_offset : float
        Offset for the grid of cylinder centers.
    stagger : bool
        If True, offset every other row by half spacing (staggered array).
    """
    
    def __init__(self, spacing: float = 30, radius: float = 5,
                 x_offset: float = 30, y_offset: float = 30,
                 stagger: bool = True):
        self.spacing = spacing
        self.radius = radius
        self.x_offset = x_offset
        self.y_offset = y_offset
        self.stagger = stagger
    
    def mask(self, ny: int, nx: int) -> np.ndarray:
        Y, X = np.mgrid[0:ny, 0:nx].astype(float)
        combined = np.zeros((ny, nx), dtype=bool)
        
        row = 0
        y = self.y_offset
        while y < ny:
            x = self.x_offset + (self.spacing / 2 if (self.stagger and row % 2 == 1) else 0)
            while x < nx:
                combined |= (X - x)**2 + (Y - y)**2 <= self.radius**2
                x += self.spacing
            y += self.spacing
            row += 1
        
        return combined
    
    def describe(self) -> str:
        return (f"CylinderArray(spacing={self.spacing}, r={self.radius}, "
                f"stagger={self.stagger})")