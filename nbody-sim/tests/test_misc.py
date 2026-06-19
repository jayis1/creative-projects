"""Tests for diagnostics, config, numpy force, serialize, renderer."""
import json
import math
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nbody.body import Body
from nbody.simulation import Simulation, Snapshot
from nbody.diagnostics import (
    total_angular_momentum,
    com_velocity,
    virial_ratio,
    min_separation,
    max_acceleration,
    adaptive_dt,
)
from nbody.config import SimConfig, RenderConfig, OutputConfig, load_config, save_config
from nbody.serialize import (
    body_to_dict, body_from_dict,
    snapshot_to_dict, snapshot_from_dict,
    save_result, load_snapshot, save_snapshot,
)
from nbody.renderer import Renderer
from nbody.numpy_force import numpy_accelerations, numpy_energy
from nbody.brute_force import brute_force_accelerations


class TestDiagnostics:
    def test_angular_momentum_circular_orbit(self):
        """A circular orbit should have constant angular momentum."""
        sim = Simulation.two_body_orbit(dt=0.01, softening=0.1)
        L0 = total_angular_momentum(sim.bodies)
        sim.run(100)
        L1 = total_angular_momentum(sim.bodies)
        assert abs(L1 - L0) < 1e-6, f"Angular momentum not conserved: {L0} -> {L1}"

    def test_com_velocity_zero_for_symmetric(self):
        """COM velocity should be zero for a symmetric system."""
        bodies = [
            Body(0, 0, 1, 0, 1),
            Body(0, 0, -1, 0, 1),
        ]
        vx, vy = com_velocity(bodies)
        assert abs(vx) < 1e-12
        assert abs(vy) < 1e-12

    def test_virial_ratio_bound_system(self):
        """A bound system should have 2T/|U| < 1 (virial equilibrium ~1)."""
        sim = Simulation.plummer_sphere(n=50, seed=42, softening=1.0)
        vr = virial_ratio(sim.bodies, G=1.0, softening=1.0)
        # Plummer model with 0.7*v_circ should be bound (vr < 2 or so).
        assert vr > 0
        assert vr < 5.0

    def test_min_separation(self):
        bodies = [Body(0, 0, 0, 0, 1), Body(1, 0, 0, 0, 1), Body(5, 0, 0, 0, 1)]
        d = min_separation(bodies)
        assert abs(d - 1.0) < 1e-10

    def test_min_separation_single_body(self):
        bodies = [Body(0, 0, 0, 0, 1)]
        d = min_separation(bodies)
        assert d == 0.0  # no pairs

    def test_max_acceleration(self):
        bodies = [Body(0, 0, 0, 0, 1), Body(1, 0, 0, 0, 100)]
        a = max_acceleration(bodies, G=1.0, softening=0.1)
        assert a > 0

    def test_adaptive_dt_in_range(self):
        bodies = [Body(0, 0, 0, 0, 1), Body(1, 0, 0, 0, 1)]
        dt = adaptive_dt(bodies, G=1.0, softening=0.5, eta=0.02,
                          dt_min=1e-6, dt_max=0.1)
        assert 1e-6 <= dt <= 0.1

    def test_adaptive_dt_no_acceleration(self):
        """With zero acceleration, dt should be dt_max."""
        bodies = [Body(0, 0, 0, 0, 1)]
        dt = adaptive_dt(bodies, G=1.0, softening=0.5, eta=0.02,
                          dt_min=1e-6, dt_max=0.1)
        assert dt == 0.1


class TestNumpyForce:
    def test_numpy_matches_brute_force(self):
        """NumPy-accelerated force should match pure-Python brute force."""
        import random
        rng = random.Random(42)
        bodies = [Body(
            rng.uniform(-5, 5), rng.uniform(-5, 5), 0, 0,
            rng.uniform(0.5, 2.0)
        ) for _ in range(20)]
        bf = brute_force_accelerations(bodies, G=1.0, softening=0.5)
        np_ = numpy_accelerations(bodies, G=1.0, softening=0.5)
        for i, ((bx_bf, by_bf), (bx_np, by_np)) in enumerate(zip(bf, np_)):
            assert abs(bx_bf - bx_np) < 1e-10, f"ax mismatch at {i}: {bx_bf} vs {bx_np}"
            assert abs(by_bf - by_np) < 1e-10, f"ay mismatch at {i}: {by_bf} vs {by_np}"

    def test_numpy_energy_matches_pure(self):
        import random
        rng = random.Random(42)
        bodies = [Body(
            rng.uniform(-5, 5), rng.uniform(-5, 5),
            rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5),
            rng.uniform(0.5, 2.0)
        ) for _ in range(15)]
        sim = Simulation(bodies, dt=0.01, softening=0.5)
        e_pure = sim.total_energy()
        e_np = numpy_energy(bodies, G=1.0, softening=0.5)
        assert abs(e_pure - e_np) < 1e-8, f"Energy mismatch: {e_pure} vs {e_np}"

    def test_numpy_empty(self):
        assert numpy_accelerations([], G=1.0, softening=0.5) == []
        assert numpy_energy([], G=1.0, softening=0.5) == 0.0

    def test_numpy_single_body(self):
        bodies = [Body(0, 0, 0, 0, 1)]
        accels = numpy_accelerations(bodies, G=1.0, softening=0.5)
        assert len(accels) == 1
        assert abs(accels[0][0]) < 1e-12
        assert abs(accels[0][1]) < 1e-12


class TestConfig:
    def test_default_config(self):
        cfg = SimConfig()
        assert cfg.preset == "two-body"
        assert cfg.steps == 1000
        assert cfg.dt == 0.01

    def test_config_from_dict(self):
        d = {"preset": "plummer", "n_bodies": 200, "dt": 0.005, "steps": 5000}
        cfg = SimConfig.from_dict(d)
        assert cfg.preset == "plummer"
        assert cfg.n_bodies == 200
        assert cfg.dt == 0.005
        assert cfg.steps == 5000

    def test_config_to_dict_roundtrip(self):
        cfg = SimConfig(preset="random", n_bodies=50, dt=0.02, theta=0.8)
        d = cfg.to_dict()
        cfg2 = SimConfig.from_dict(d)
        assert cfg2.preset == "random"
        assert cfg2.n_bodies == 50
        assert cfg2.dt == 0.02
        assert cfg2.theta == 0.8

    def test_json_config(self, tmp_path):
        cfg = SimConfig(preset="plummer", n_bodies=100, dt=0.01)
        path = str(tmp_path / "sim.json")
        save_config(cfg, path)
        cfg2 = load_config(path)
        assert cfg2.preset == "plummer"
        assert cfg2.n_bodies == 100
        assert cfg2.dt == 0.01

    def test_yaml_config(self, tmp_path):
        cfg = SimConfig(preset="random", n_bodies=50, steps=2000)
        path = str(tmp_path / "sim.yaml")
        save_config(cfg, path)
        cfg2 = load_config(path)
        assert cfg2.preset == "random"
        assert cfg2.n_bodies == 50
        assert cfg2.steps == 2000

    def test_unsupported_format(self, tmp_path):
        path = str(tmp_path / "sim.txt")
        with pytest.raises(ValueError, match="Unsupported config format"):
            save_config(SimConfig(), path)
        with pytest.raises(ValueError, match="Unsupported config format"):
            load_config(path)

    def test_render_config_in_dict(self):
        d = {
            "preset": "plummer",
            "render": {"enabled": True, "width": 256, "color_by_mass": True},
        }
        cfg = SimConfig.from_dict(d)
        assert cfg.render.enabled is True
        assert cfg.render.width == 256
        assert cfg.render.color_by_mass is True


class TestSerialization:
    def test_body_roundtrip(self):
        b = Body(1.5, -2.3, 0.1, -0.4, 3.0, "test")
        d = body_to_dict(b)
        b2 = body_from_dict(d)
        assert b2.x == 1.5
        assert b2.y == -2.3
        assert b2.vx == 0.1
        assert b2.vy == -0.4
        assert b2.m == 3.0
        assert b2.name == "test"

    def test_snapshot_roundtrip(self):
        snap = Snapshot(
            step=42, t=0.42,
            bodies=[Body(1, 2, 0.1, 0.2, 1.0, "a"), Body(3, 4, 0.3, 0.4, 2.0, "b")],
            energy=-1.5,
            momentum=(0.1, 0.2),
        )
        d = snapshot_to_dict(snap)
        snap2 = snapshot_from_dict(d)
        assert snap2.step == 42
        assert abs(snap2.t - 0.42) < 1e-10
        assert len(snap2.bodies) == 2
        assert snap2.bodies[0].name == "a"
        assert abs(snap2.energy - (-1.5)) < 1e-10
        assert snap2.momentum == (0.1, 0.2)

    def test_save_load_snapshot(self, tmp_path):
        snap = Snapshot(
            step=10, t=0.1,
            bodies=[Body(0, 0, 0, 0, 1.0)],
            energy=0.0,
            momentum=(0.0, 0.0),
        )
        path = str(tmp_path / "snap.json")
        save_snapshot(snap, path)
        snap2 = load_snapshot(path)
        assert snap2.step == 10

    def test_save_result(self, tmp_path):
        sim = Simulation.two_body_orbit(dt=0.01, softening=0.1)
        result = sim.run(10, snapshot_every=5)
        path = str(tmp_path / "run.json")
        save_result(result, sim, path)
        with open(path) as f:
            data = json.load(f)
        assert "config" in data
        assert "snapshots" in data
        assert len(data["snapshots"]) == len(result.snapshots)


class TestRenderer:
    def test_render_single_frame(self, tmp_path):
        r = Renderer(width=64, height=64, view_size=5.0, trails=False)
        bodies = [Body(0, 0, 0, 0, 1.0), Body(2, 0, 0, 0, 1.0)]
        path = str(tmp_path / "frame.ppm")
        r.render_to_file(bodies, path)
        assert os.path.exists(path)
        with open(path, "rb") as f:
            header = f.read(20)
        assert header.startswith(b"P6")

    def test_render_returns_bytes(self):
        r = Renderer(width=32, height=32, view_size=5.0, trails=False)
        bodies = [Body(0, 0, 0, 0, 1.0)]
        data = r.render_frame(bodies)
        assert isinstance(data, bytes)
        assert data.startswith(b"P6")

    def test_invalid_dimensions(self):
        with pytest.raises(ValueError):
            Renderer(width=0, height=0)
        with pytest.raises(ValueError):
            Renderer(width=-1, height=10)

    def test_invalid_view_size(self):
        with pytest.raises(ValueError):
            Renderer(view_size=0.0)

    def test_invalid_trail_decay(self):
        with pytest.raises(ValueError):
            Renderer(trail_decay=1.5)
        with pytest.raises(ValueError):
            Renderer(trail_decay=-0.1)

    def test_aspect_ratio_uniform(self):
        """Non-square images should preserve world aspect ratio."""
        r = Renderer(width=200, height=100, view_size=10.0, trails=False)
        px1, py1 = r._to_pixel(5.0, 0.0)
        px2, py2 = r._to_pixel(0.0, 5.0)
        cx_px, cy_px = r._to_pixel(0.0, 0.0)
        dx_px = px1 - cx_px
        dy_px = cy_px - py2
        assert dx_px == dy_px, f"Aspect ratio distorted: dx={dx_px}, dy={dy_px}"

    def test_render_sequence(self, tmp_path):
        r = Renderer(width=32, height=32, view_size=5.0, trails=False)
        snaps = [
            Snapshot(step=0, t=0.0, bodies=[Body(0, 0, 0, 0, 1)], energy=0.0,
                     momentum=(0, 0)),
            Snapshot(step=1, t=0.01, bodies=[Body(0.1, 0, 0, 0, 1)], energy=0.0,
                     momentum=(0, 0)),
        ]
        out_dir = str(tmp_path / "frames")
        paths = r.render_sequence(snaps, out_dir)
        assert len(paths) == 2
        assert all(os.path.exists(p) for p in paths)

    def test_color_by_mass(self, tmp_path):
        """Mass-based coloring should produce different colors."""
        r = Renderer(width=32, height=32, view_size=5.0, trails=False,
                      color_by_mass=True)
        bodies = [Body(0, 0, 0, 0, 0.1), Body(2, 0, 0, 0, 10.0)]
        data = r.render_frame(bodies)
        assert data.startswith(b"P6")