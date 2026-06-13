"""
Unit tests for LBM simulation components.
"""

import sys
import os
import math
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lbm.lattice import D2Q9Lattice
from lbm.simulation import LBMSimulation
from lbm.boundaries import (
    BounceBackBoundary,
    ZouHeVelocityBoundary,
    ZouHePressureBoundary,
)
from lbm.obstacles import (
    CircleObstacle,
    RectangleObstacle,
    AirfoilObstacle,
    MultiObstacle,
    CylinderArrayObstacle,
)
from lbm.visualization import FluidVisualizer


def test_lattice_constants():
    """Test D2Q9 lattice constants."""
    lat = D2Q9Lattice()
    
    # Weights sum to 1
    assert np.isclose(lat.w.sum(), 1.0), f"Weights sum to {lat.w.sum()}"
    
    # Speed of sound
    assert np.isclose(lat.cs2, 1.0/3.0), f"cs2 = {lat.cs2}"
    
    # Opposite directions
    for i in range(lat.Q):
        j = lat.opposite[i]
        assert lat.ex[i] == -lat.ex[j], f"ex[{i}] != -ex[{j}]"
        assert lat.ey[i] == -lat.ey[j], f"ey[{i}] != -ey[{j}]"
    
    # Validate
    assert lat.validate(), "Lattice validation failed"
    
    print("  ✓ Lattice constants test passed")


def test_equilibrium_conserves_mass():
    """Test that equilibrium distribution conserves mass."""
    lat = D2Q9Lattice()
    
    nx, ny = 50, 50
    rho = np.ones((ny, nx)) * 1.5
    ux = np.ones((ny, nx)) * 0.05
    uy = np.ones((ny, nx)) * 0.03
    
    feq = lat.equilibrium(rho, ux, uy)
    
    # Sum of equilibrium should equal density
    rho_computed = np.sum(feq, axis=0)
    assert np.allclose(rho_computed, rho, rtol=1e-10), \
        f"Mass conservation error: max diff = {np.max(np.abs(rho_computed - rho))}"
    
    print("  ✓ Equilibrium mass conservation test passed")


def test_equilibrium_conserves_momentum():
    """Test that equilibrium distribution conserves momentum."""
    lat = D2Q9Lattice()
    
    nx, ny = 30, 30
    rho = np.ones((ny, nx)) * 1.2
    ux = np.ones((ny, nx)) * 0.04
    uy = np.ones((ny, nx)) * 0.02
    
    feq = lat.equilibrium(rho, ux, uy)
    
    rho_eq = np.sum(feq, axis=0)
    ux_eq = np.sum(feq * lat.ex[:, None, None], axis=0) / rho_eq
    uy_eq = np.sum(feq * lat.ey[:, None, None], axis=0) / rho_eq
    
    assert np.allclose(ux_eq, ux, rtol=1e-10), f"Momentum x error: max = {np.max(np.abs(ux_eq - ux))}"
    assert np.allclose(uy_eq, uy, rtol=1e-10), f"Momentum y error: max = {np.max(np.abs(uy_eq - uy))}"
    
    print("  ✓ Equilibrium momentum conservation test passed")


def test_streaming_periodicity():
    """Test that streaming preserves mass (periodic boundaries)."""
    lat = D2Q9Lattice()
    
    nx, ny = 20, 20
    f = np.random.rand(lat.Q, ny, nx)
    
    # Streaming should preserve total mass
    mass_before = np.sum(f)
    f_streamed = lat.stream(f)
    mass_after = np.sum(f_streamed)
    
    assert np.isclose(mass_before, mass_after, rtol=1e-10), \
        f"Mass not preserved by streaming: before={mass_before}, after={mass_after}"
    
    print("  ✓ Streaming periodicity test passed")


def test_collision_relaxation():
    """Test that BGK collision relaxes towards equilibrium."""
    lat = D2Q9Lattice()
    
    nx, ny = 20, 20
    rho = np.ones((ny, nx))
    ux = np.ones((ny, nx)) * 0.05
    uy = np.zeros((ny, nx))
    
    # Start from equilibrium
    feq = lat.equilibrium(rho, ux, uy)
    
    # Perturb slightly
    f = feq + np.random.randn(*feq.shape) * 0.001
    
    # Collision should bring closer to equilibrium
    omega = 0.5  # tau = 2
    f_collided = f - omega * (f - feq)
    
    # Check that f_collided is closer to feq than f
    dist_before = np.sum((f - feq)**2)
    dist_after = np.sum((f_collided - feq)**2)
    
    assert dist_after < dist_before, \
        f"Collision did not reduce distance to equilibrium: before={dist_before}, after={dist_after}"
    
    print("  ✓ Collision relaxation test passed")


def test_obstacle_masks():
    """Test obstacle mask generation."""
    ny, nx = 100, 200
    
    # Circle
    circle = CircleObstacle(cx=50, cy=50, radius=10)
    mask = circle.mask(ny, nx)
    assert mask.shape == (ny, nx)
    assert np.sum(mask) > 0, "Circle mask is empty"
    # Check center is solid
    assert mask[50, 50], "Circle center should be solid"
    # Check far-away point is not solid
    assert not mask[0, 0], "Point far from circle should be fluid"
    
    # Rectangle
    rect = RectangleObstacle(x0=20, y0=20, width=30, height=15)
    mask = rect.mask(ny, nx)
    assert mask[25, 25], "Rectangle interior should be solid"
    assert not mask[0, 0], "Point outside rectangle should be fluid"
    
    # Airfoil
    airfoil = AirfoilObstacle(cx=60, cy=50, chord=40, thickness=0.12, angle_deg=5)
    mask = airfoil.mask(ny, nx)
    assert np.sum(mask) > 0, "Airfoil mask is empty"
    
    # MultiObstacle
    multi = MultiObstacle([circle, rect])
    mask = multi.mask(ny, nx)
    # Should contain both circle and rectangle
    circle_mask = circle.mask(ny, nx)
    rect_mask = rect.mask(ny, nx)
    assert np.all(mask >= circle_mask), "MultiObstacle should include circle"
    assert np.all(mask >= rect_mask), "MultiObstacle should include rectangle"
    
    print("  ✓ Obstacle mask tests passed")


def test_simulation_initialization():
    """Test simulation setup and initial state."""
    nx, ny = 50, 30
    sim = LBMSimulation(nx, ny, viscosity=0.02)
    
    assert sim.nx == nx
    assert sim.ny == ny
    assert sim.tau > 0.5, f"tau={sim.tau} must be > 0.5"
    
    # Initial state should be equilibrium at rest
    assert np.allclose(sim.rho, 1.0, rtol=1e-10), "Initial density should be 1"
    assert np.allclose(sim.ux, 0.0, atol=1e-10), "Initial ux should be 0"
    assert np.allclose(sim.uy, 0.0, atol=1e-10), "Initial uy should be 0"
    
    # Distribution functions should sum to density
    rho_check = np.sum(sim.f, axis=0)
    assert np.allclose(rho_check, 1.0, rtol=1e-10)
    
    print("  ✓ Simulation initialization test passed")


def test_simulation_step():
    """Test that a simulation step preserves mass."""
    nx, ny = 50, 30
    sim = LBMSimulation(nx, ny, viscosity=0.05)
    sim.set_inlet_velocity(0.02)
    
    mass_before = np.sum(sim.f)
    
    sim.step(10)
    
    mass_after = np.sum(sim.f)
    
    # Mass should be approximately conserved
    assert np.allclose(mass_before, mass_after, rtol=0.01), \
        f"Mass not conserved: before={mass_before}, after={mass_after}"
    
    # Check stability
    assert sim.stability_check(), "Simulation became unstable"
    
    print("  ✓ Simulation step test passed")


def test_simulation_with_obstacle():
    """Test simulation with a circular obstacle."""
    nx, ny = 100, 50
    sim = LBMSimulation(nx, ny, viscosity=0.02)
    sim.set_inlet_velocity(0.04)
    
    cylinder = CircleObstacle(cx=25, cy=ny//2, radius=5)
    sim.add_obstacle(cylinder)
    
    sim.add_boundary_condition(ZouHeVelocityBoundary(0.04, side='left'))
    sim.add_boundary_condition(ZouHePressureBoundary(rho_boundary=1.0, side='right'))
    
    # Run for a few steps
    sim.step(50)
    
    # Check that velocity is zero inside obstacle
    assert np.allclose(sim.ux[sim.obstacle_mask], 0.0, atol=1e-10)
    assert np.allclose(sim.uy[sim.obstacle_mask], 0.0, atol=1e-10)
    
    # Check stability
    assert sim.stability_check(), "Simulation with obstacle became unstable"
    
    print("  ✓ Simulation with obstacle test passed")


def test_simulation_summary():
    """Test that simulation summary runs without error."""
    sim = LBMSimulation(50, 30, viscosity=0.05)
    sim.set_inlet_velocity(0.03)
    sim.step(5)
    
    summary = sim.summary()
    assert isinstance(summary, str)
    assert "Grid:" in summary
    assert "Step:" in summary
    
    print("  ✓ Simulation summary test passed")


def test_visualization():
    """Test visualization rendering."""
    sim = LBMSimulation(50, 30, viscosity=0.05)
    sim.set_inlet_velocity(0.03)
    sim.step(10)
    
    vis = FluidVisualizer(sim)
    
    # Test vorticity rendering
    img = vis.render_vorticity(cmap='coolwarm', vmin=-0.01, vmax=0.01, scale=1)
    assert isinstance(img, Image.Image)
    assert img.size == (50, 30)
    
    # Test speed rendering
    img = vis.render_speed(cmap='jet', scale=2)
    assert isinstance(img, Image.Image)
    assert img.size == (100, 60)  # Scaled by 2
    
    # Test pressure rendering
    img = vis.render_pressure(cmap='ocean', scale=1)
    assert isinstance(img, Image.Image)
    
    print("  ✓ Visualization rendering test passed")


def test_reynolds_number():
    """Test Reynolds number calculation."""
    sim = LBMSimulation(100, 50, viscosity=0.01)
    
    Re = sim.reynolds_number(u_char=0.1, L_char=50)
    expected = 0.1 * 50 / 0.01  # = 500
    assert np.isclose(Re, expected), f"Re={Re}, expected={expected}"
    
    print("  ✓ Reynolds number test passed")


def run_all_tests():
    print("\n" + "="*60)
    print("LBM Fluid Dynamics Simulator — Test Suite")
    print("="*60)
    
    tests = [
        test_lattice_constants,
        test_equilibrium_conserves_mass,
        test_equilibrium_conserves_momentum,
        test_streaming_periodicity,
        test_collision_relaxation,
        test_obstacle_masks,
        test_simulation_initialization,
        test_simulation_step,
        test_simulation_with_obstacle,
        test_simulation_summary,
        test_visualization,
        test_reynolds_number,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ✗ {test.__name__} FAILED: {e}")
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("="*60)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)