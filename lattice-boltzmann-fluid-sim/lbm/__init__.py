"""
Lattice Boltzmann Method (LBM) Fluid Dynamics Simulator

Implements the D2Q9 model for 2D incompressible fluid simulation
using the BGK (Bhatnagar-Gross-Krook) collision operator.
"""

from .lattice import D2Q9Lattice
from .simulation import LBMSimulation
from .boundaries import (
    BoundaryCondition,
    BounceBackBoundary,
    FullWayBounceBackBoundary,
    ZouHeVelocityBoundary,
    ZouHePressureBoundary,
    OpenBoundary,
    PeriodicBoundary,
)
from .obstacles import (
    Obstacle,
    CircleObstacle,
    RectangleObstacle,
    AirfoilObstacle,
    MultiObstacle,
    CylinderArrayObstacle,
)
from .visualization import FluidVisualizer

__version__ = "1.0.0"
__all__ = [
    "D2Q9Lattice",
    "LBMSimulation",
    "BoundaryCondition",
    "BounceBackBoundary",
    "FullWayBounceBackBoundary",
    "ZouHeVelocityBoundary",
    "ZouHePressureBoundary",
    "OpenBoundary",
    "PeriodicBoundary",
    "Obstacle",
    "CircleObstacle",
    "RectangleObstacle",
    "AirfoilObstacle",
    "MultiObstacle",
    "CylinderArrayObstacle",
    "FluidVisualizer",
]