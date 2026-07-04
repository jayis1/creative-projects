"""Tests for diagnostics: energy, momentum."""
import pytest
from rigidbody import World, RigidBody, Vec2, Polygon, Circle
from rigidbody.diagnostics import Diagnostics, compute_energy, compute_momentum


class TestEnergyComputation:
    def test_kinetic_energy(self):
        b = RigidBody(Circle(1), Vec2(0, 0), density=1)
        b.linear_velocity = Vec2(2, 0)
        e = compute_energy([b])
        expected_ke = 0.5 * b.mass * 4
        assert abs(e["kinetic"] - expected_ke) < 1e-6

    def test_potential_energy(self):
        b = RigidBody(Circle(1), Vec2(0, 10), density=1)
        e = compute_energy([b])
        expected_pe = b.mass * 9.81 * 10
        assert abs(e["potential"] - expected_pe) < 1e-6

    def test_static_body_excluded(self):
        b = RigidBody(Circle(1), Vec2(0, 10), body_type=RigidBody.STATIC)
        e = compute_energy([b])
        assert e["kinetic"] == 0
        assert e["potential"] == 0


class TestMomentum:
    def test_linear_momentum(self):
        b = RigidBody(Circle(1), Vec2(0, 0), density=1)
        b.linear_velocity = Vec2(3, 4)
        p = compute_momentum([b])
        assert abs(p["px"] - b.mass * 3) < 1e-6
        assert abs(p["py"] - b.mass * 4) < 1e-6

    def test_angular_momentum(self):
        b = RigidBody(Circle(1), Vec2(0, 0), density=1)
        b.angular_velocity = 5.0
        p = compute_momentum([b])
        assert abs(p["angular"] - b.inertia * 5.0) < 1e-6


class TestDiagnostics:
    def test_sample_and_report(self):
        w = World(gravity=Vec2(0, -9.81))
        floor = RigidBody(Polygon.box(20, 1), Vec2(0, -0.5), body_type=RigidBody.STATIC)
        box = RigidBody(Polygon.box(1, 1), Vec2(0, 5), density=1)
        w.add_body(floor)
        w.add_body(box)
        diag = Diagnostics()
        for _ in range(60):
            w.step(1 / 60)
            diag.sample(w.bodies)
        report = diag.report()
        assert "kinetic_min" in report
        assert "total_max" in report
        assert len(diag.history) == 60

    def test_energy_drift_empty(self):
        diag = Diagnostics()
        assert diag.energy_drift() == 0.0

    def test_energy_drift(self):
        diag = Diagnostics()
        diag.history = [{"total": 100.0, "step": 0}, {"total": 105.0, "step": 1}]
        assert diag.energy_drift() == pytest.approx(0.05)