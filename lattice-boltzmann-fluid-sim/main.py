#!/usr/bin/env python3
"""
Lattice Boltzmann Method Fluid Dynamics Simulator — Main Demo

This script runs several classic CFD simulations:
  1. Von Kármán vortex street behind a cylinder
  2. Flow over a NACA 0012 airfoil
  3. Flow through a porous medium (cylinder array)
  4. Lid-driven cavity

Usage:
  python3 main.py [scenario] [options]

Scenarios:
  vortex     — Von Kármán vortex street (default)
  airfoil    — Flow over NACA 0012 airfoil
  porous     — Flow through porous medium
  cavity     — Lid-driven cavity flow
  all        — Run all scenarios

Options:
  --steps N      Number of simulation steps (default varies by scenario)
  --viscosity V  Kinematic viscosity in lattice units (default: 0.02)
  --scale S      Image upscale factor (default: 2)
  --output DIR   Output directory (default: ./output)
  --fps FPS      GIF frame rate (default: 30)
  --no-gif       Don't create GIF, only final images
"""

import sys
import os
import math
import argparse

import numpy as np
from PIL import Image

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lbm import (
    LBMSimulation,
    D2Q9Lattice,
    BounceBackBoundary,
    FullWayBounceBackBoundary,
    ZouHeVelocityBoundary,
    ZouHePressureBoundary,
    OpenBoundary,
    CircleObstacle,
    RectangleObstacle,
    AirfoilObstacle,
    MultiObstacle,
    CylinderArrayObstacle,
    FluidVisualizer,
)


def run_von_karman_vortex(args):
    """
    Classic Von Kármán vortex street simulation.
    
    A uniform flow encounters a cylinder. Above Re ≈ 47, the flow
    develops periodic vortex shedding — the Von Kármán vortex street.
    """
    nx, ny = 420, 120
    u0 = 0.08  # Inlet velocity
    
    sim = LBMSimulation(nx, ny, viscosity=args.viscosity)
    
    # Cylinder obstacle
    cx, cy = nx // 5, ny // 2
    radius = ny // 9
    cylinder = CircleObstacle(cx, cy, radius)
    sim.add_obstacle(cylinder)
    
    # Boundary conditions
    sim.add_boundary_condition(FullWayBounceBackBoundary(top=True, bottom=True))
    sim.add_boundary_condition(ZouHeVelocityBoundary(u0, side='left'))
    sim.add_boundary_condition(OpenBoundary(side='right'))
    
    Re = sim.reynolds_number(u0, 2 * radius)
    print(f"Von Kármán Vortex Street")
    print(f"  Grid: {nx}x{ny}, Re={Re:.1f}, tau={sim.tau:.4f}")
    print(f"  Cylinder: center=({cx},{cy}), radius={radius}")
    
    vis = FluidVisualizer(sim)
    frames = []
    
    n_steps = args.steps or 12000
    save_interval = max(1, n_steps // 80)
    
    for step in range(1, n_steps + 1):
        sim.step()
        
        if step % save_interval == 0:
            pct = 100 * step / n_steps
            print(f"\r  Step {step}/{n_steps} ({pct:.0f}%)", end='', flush=True)
            frames.append(vis.render_vorticity(cmap='coolwarm', vmin=-0.04, vmax=0.04, scale=args.scale))
    
    print()
    print(sim.summary())
    
    # Save final frames
    os.makedirs(args.output, exist_ok=True)
    
    vis.save_frame(os.path.join(args.output, 'vortex_vorticity.png'), 
                   'vorticity', cmap='coolwarm', scale=args.scale, vmin=-0.04, vmax=0.04)
    vis.save_frame(os.path.join(args.output, 'vortex_speed.png'), 
                   'speed', cmap='jet', scale=args.scale)
    vis.save_frame(os.path.join(args.output, 'vortex_pressure.png'), 
                   'pressure', cmap='ocean', scale=args.scale)
    
    if not args.no_gif and frames:
        gif_path = os.path.join(args.output, 'vortex_animation.gif')
        print(f"Saving animation ({len(frames)} frames) to {gif_path}...")
        FluidVisualizer.create_gif(frames, gif_path, duration=1000 // args.fps)
    
    return sim


def run_airfoil(args):
    """
    Flow over a NACA 0012 airfoil at various angles of attack.
    
    Demonstrates flow separation and stall behavior.
    """
    nx, ny = 500, 200
    u0 = 0.05
    
    sim = LBMSimulation(nx, ny, viscosity=args.viscosity)
    
    # NACA 0012 airfoil at 15° angle of attack
    chord = 80
    cx, cy = nx // 4, ny // 2
    airfoil = AirfoilObstacle(cx, cy, chord, thickness=0.12, angle_deg=15)
    sim.add_obstacle(airfoil)
    
    sim.add_boundary_condition(FullWayBounceBackBoundary(top=True, bottom=True))
    sim.add_boundary_condition(ZouHeVelocityBoundary(u0, side='left'))
    sim.add_boundary_condition(OpenBoundary(side='right'))
    
    Re = sim.reynolds_number(u0, chord)
    print(f"Flow Over NACA 0012 Airfoil")
    print(f"  Grid: {nx}x{ny}, Re={Re:.1f}, AoA=15°, tau={sim.tau:.4f}")
    
    vis = FluidVisualizer(sim)
    frames = []
    
    n_steps = args.steps or 10000
    save_interval = max(1, n_steps // 60)
    
    for step in range(1, n_steps + 1):
        sim.step()
        
        if step % save_interval == 0:
            pct = 100 * step / n_steps
            print(f"\r  Step {step}/{n_steps} ({pct:.0f}%)", end='', flush=True)
            frames.append(vis.render_vorticity(cmap='coolwarm', vmin=-0.03, vmax=0.03, scale=args.scale))
    
    print()
    print(sim.summary())
    
    os.makedirs(args.output, exist_ok=True)
    vis.save_frame(os.path.join(args.output, 'airfoil_vorticity.png'), 
                   'vorticity', scale=args.scale, vmin=-0.03, vmax=0.03)
    vis.save_frame(os.path.join(args.output, 'airfoil_speed.png'), 
                   'speed', scale=args.scale)
    
    if not args.no_gif and frames:
        gif_path = os.path.join(args.output, 'airfoil_animation.gif')
        print(f"Saving animation ({len(frames)} frames) to {gif_path}...")
        FluidVisualizer.create_gif(frames, gif_path, duration=1000 // args.fps)
    
    return sim


def run_porous_medium(args):
    """
    Flow through a porous medium (staggered cylinder array).
    
    Demonstrates tortuous flow paths through porous structures.
    """
    nx, ny = 300, 150
    u0 = 0.04
    
    sim = LBMSimulation(nx, ny, viscosity=args.viscosity)
    
    cylinders = CylinderArrayObstacle(spacing=30, radius=5, stagger=True)
    sim.add_obstacle(cylinders)
    
    sim.add_boundary_condition(FullWayBounceBackBoundary(top=True, bottom=True))
    sim.add_boundary_condition(ZouHeVelocityBoundary(u0, side='left'))
    sim.add_boundary_condition(OpenBoundary(side='right'))
    
    print(f"Flow Through Porous Medium")
    print(f"  Grid: {nx}x{ny}, tau={sim.tau:.4f}")
    
    vis = FluidVisualizer(sim)
    frames = []
    
    n_steps = args.steps or 8000
    save_interval = max(1, n_steps // 60)
    
    for step in range(1, n_steps + 1):
        sim.step()
        
        if step % save_interval == 0:
            pct = 100 * step / n_steps
            print(f"\r  Step {step}/{n_steps} ({pct:.0f}%)", end='', flush=True)
            frames.append(vis.render_speed(cmap='ocean', scale=args.scale))
    
    print()
    print(sim.summary())
    
    os.makedirs(args.output, exist_ok=True)
    vis.save_frame(os.path.join(args.output, 'porous_speed.png'), 
                   'speed', cmap='ocean', scale=args.scale)
    vis.save_frame(os.path.join(args.output, 'porous_pressure.png'), 
                   'pressure', cmap='plasma', scale=args.scale)
    
    if not args.no_gif and frames:
        gif_path = os.path.join(args.output, 'porous_animation.gif')
        print(f"Saving animation ({len(frames)} frames) to {gif_path}...")
        FluidVisualizer.create_gif(frames, gif_path, duration=1000 // args.fps)
    
    return sim


def run_lid_driven_cavity(args):
    """
    Lid-driven cavity flow — a classic CFD benchmark.
    
    The top wall moves at constant velocity, driving a recirculating
    flow inside a square cavity. The flow develops a primary vortex
    and corner eddies at higher Re.
    """
    nx, ny = 150, 150
    u_lid = 0.1  # Lid velocity
    
    sim = LBMSimulation(nx, ny, viscosity=args.viscosity)
    
    # All four walls are solid
    sim.add_boundary_condition(FullWayBounceBackBoundary(top=True, bottom=True, left=True, right=True))
    
    Re = sim.reynolds_number(u_lid, ny)
    print(f"Lid-Driven Cavity Flow")
    print(f"  Grid: {nx}x{ny}, Re={Re:.1f}, tau={sim.tau:.4f}")
    
    vis = FluidVisualizer(sim)
    frames = []
    
    n_steps = args.steps or 8000
    save_interval = max(1, n_steps // 60)
    
    for step in range(1, n_steps + 1):
        # Apply moving lid at top wall (y = ny-1)
        # Set distributions at top row to equilibrium with lid velocity
        top_rho = np.ones(nx)
        top_ux = np.full(nx, u_lid)
        top_uy = np.zeros(nx)
        feq_top = sim.lattice.equilibrium(
            top_rho.reshape(1, -1), 
            top_ux.reshape(1, -1), 
            top_uy.reshape(1, -1)
        )
        sim.f[:, -1, :] = feq_top[:, 0, :]
        
        sim.step()
        
        if step % save_interval == 0:
            pct = 100 * step / n_steps
            print(f"\r  Step {step}/{n_steps} ({pct:.0f}%)", end='', flush=True)
            frames.append(vis.render_speed(cmap='plasma', scale=args.scale))
    
    print()
    print(sim.summary())
    
    os.makedirs(args.output, exist_ok=True)
    vis.save_frame(os.path.join(args.output, 'cavity_speed.png'), 
                   'speed', cmap='plasma', scale=args.scale)
    vis.save_frame(os.path.join(args.output, 'cavity_vorticity.png'), 
                   'vorticity', scale=args.scale)
    
    if not args.no_gif and frames:
        gif_path = os.path.join(args.output, 'cavity_animation.gif')
        print(f"Saving animation ({len(frames)} frames) to {gif_path}...")
        FluidVisualizer.create_gif(frames, gif_path, duration=1000 // args.fps)
    
    return sim


def main():
    parser = argparse.ArgumentParser(description='LBM Fluid Dynamics Simulator')
    parser.add_argument('scenario', nargs='?', default='vortex',
                       choices=['vortex', 'airfoil', 'porous', 'cavity', 'all'],
                       help='Simulation scenario to run')
    parser.add_argument('--steps', type=int, default=None,
                       help='Number of simulation steps')
    parser.add_argument('--viscosity', type=float, default=0.02,
                       help='Kinematic viscosity in lattice units')
    parser.add_argument('--scale', type=int, default=2,
                       help='Image upscale factor')
    parser.add_argument('--output', type=str, default='./output',
                       help='Output directory')
    parser.add_argument('--fps', type=int, default=30,
                       help='GIF frame rate')
    parser.add_argument('--no-gif', action='store_true',
                       help='Skip GIF creation')
    
    args = parser.parse_args()
    
    scenarios = {
        'vortex': run_von_karman_vortex,
        'airfoil': run_airfoil,
        'porous': run_porous_medium,
        'cavity': run_lid_driven_cavity,
    }
    
    if args.scenario == 'all':
        for name, func in scenarios.items():
            print(f"\n{'='*60}")
            print(f"Running scenario: {name}")
            print('='*60)
            func(args)
    else:
        scenarios[args.scenario](args)
    
    print(f"\nDone! Output saved to: {os.path.abspath(args.output)}")


if __name__ == '__main__':
    main()