"""
Bloch sphere utilities: compute the Bloch vector and render an ASCII
projection of a single-qubit state on the Bloch sphere.
"""

from __future__ import annotations

import math
from typing import Tuple

import numpy as np

from .state import StateVector

__all__ = ["bloch_vector", "bloch_sphere_ascii", "bloch_angles"]


def bloch_vector(state: StateVector) -> np.ndarray:
    """
    Compute the Bloch vector (x, y, z) for a single-qubit pure state.

    x = ⟨σ_x⟩, y = ⟨σ_y⟩, z = ⟨σ_z⟩.
    """
    if state.num_qubits != 1:
        raise ValueError("Bloch vector requires a single-qubit state")
    sx = np.array([[0, 1], [1, 0]], dtype=complex)
    sy = np.array([[0, -1j], [1j, 0]], dtype=complex)
    sz = np.array([[1, 0], [0, -1]], dtype=complex)
    x = float(np.real(state.expectation(sx)))
    y = float(np.real(state.expectation(sy)))
    z = float(np.real(state.expectation(sz)))
    return np.array([x, y, z])


def bloch_angles(state: StateVector) -> Tuple[float, float]:
    """
    Return (theta, phi) Bloch sphere angles for a single-qubit state.

    theta: polar angle from +z (0..π)
    phi:   azimuthal angle from +x in the x-y plane (0..2π)
    """
    v = bloch_vector(state)
    x, y, z = v
    theta = math.acos(np.clip(z, -1.0, 1.0))
    phi = math.atan2(y, x) % (2 * math.pi)
    return theta, phi


def bloch_sphere_ascii(state: StateVector, width: int = 40, height: int = 21) -> str:
    """
    Render an ASCII art representation of a single-qubit state
    on the Bloch sphere (orthographic projection).
    """
    if state.num_qubits != 1:
        raise ValueError("bloch_sphere_ascii requires a single-qubit state")
    v = bloch_vector(state)
    x, y, z = v

    grid = [[" "] * width for _ in range(height)]
    cx, cy = width // 2, height // 2
    radius = min(width, height) // 2 - 1

    # Draw circle outline
    for angle_deg in range(0, 360, 3):
        a = math.radians(angle_deg)
        px = int(cx + radius * math.cos(a))
        py = int(cy - radius * math.sin(a))
        if 0 <= px < width and 0 <= py < height:
            grid[py][px] = "·"

    # Draw axes
    # z-axis (vertical)
    for i in range(-radius, radius + 1):
        py = cy - i
        if 0 <= py < height:
            grid[py][cx] = "|" if i != 0 else "+"
    # x-axis (horizontal)
    for i in range(-radius, radius + 1):
        px = cx + i
        if 0 <= px < width:
            grid[cy][px] = "-" if i != 0 else "+"

    # Plot the state vector
    px = int(cx + radius * x)
    py = int(cy - radius * z)  # project z to vertical, ignore y for 2D
    if 0 <= px < width and 0 <= py < height:
        grid[py][px] = "●"

    lines = ["".join(row) for row in grid]
    header = f"Bloch sphere: ({x:+.3f}, {y:+.3f}, {z:+.3f})"
    return header + "\n" + "\n".join(lines)