"""Tests for all renderer classes."""

import os
import tempfile
import pytest
from boids.simulation import BoidSimulation
from boids.config import SimulationConfig
from boids.renderer import (
    ASCIIRenderer, SVGRenderer, PPMRenderer, TrailSVGRenderer,
    AnimatedSVGRenderer, JSONRenderer,
)


class TestASCIIRenderer:
    def test_basic_render(self):
        cfg = SimulationConfig(num_boids=10, width=100, height=100)
        sim = BoidSimulation(cfg)
        sim.step()
        r = ASCIIRenderer(cols=20, rows=10)
        frame = r.render(sim)
        assert isinstance(frame, str)
        lines = frame.split("\n")
        assert len(lines) == 10
        assert len(lines[0]) == 20

    def test_arrow_directions(self):
        cfg = SimulationConfig(num_boids=0, width=100, height=100)
        sim = BoidSimulation(cfg)
        from boids.boid import Boid
        # Right
        sim.boids.append(Boid(50, 50, vx=5, vy=0))
        r = ASCIIRenderer(cols=20, rows=10)
        frame = r.render(sim)
        lines = frame.split("\n")
        char = lines[5][10]
        assert char == "→"

    def test_obstacles_rendered(self):
        cfg = SimulationConfig(num_boids=0, width=100, height=100)
        sim = BoidSimulation(cfg)
        sim.add_obstacle(50, 50, 10)
        r = ASCIIRenderer(cols=20, rows=10)
        frame = r.render(sim)
        assert "#" in frame

    def test_goal_rendered(self):
        cfg = SimulationConfig(num_boids=0, width=100, height=100)
        sim = BoidSimulation(cfg)
        sim.set_goal(50, 50)
        r = ASCIIRenderer(cols=20, rows=10)
        frame = r.render(sim)
        assert "*" in frame

    def test_predators_rendered(self):
        cfg = SimulationConfig(num_boids=0, width=100, height=100)
        sim = BoidSimulation(cfg)
        sim.add_predator(50, 50)
        r = ASCIIRenderer(cols=20, rows=10)
        frame = r.render(sim)
        assert "X" in frame


class TestSVGRenderer:
    def test_basic_render(self):
        cfg = SimulationConfig(num_boids=5)
        sim = BoidSimulation(cfg)
        svg = SVGRenderer().render(sim)
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_render_to_file(self):
        cfg = SimulationConfig(num_boids=5)
        sim = BoidSimulation(cfg)
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            path = f.name
        try:
            SVGRenderer().render(sim, path)
            assert os.path.exists(path)
            with open(path) as f:
                content = f.read()
            assert "<svg" in content
        finally:
            os.unlink(path)

    def test_obstacle_in_svg(self):
        cfg = SimulationConfig(num_boids=3)
        sim = BoidSimulation(cfg)
        sim.add_obstacle(100, 100, 30)
        svg = SVGRenderer().render(sim)
        assert "circle" in svg
        assert "sroke=" not in svg  # the fixed typo

    def test_predator_in_svg(self):
        cfg = SimulationConfig(num_boids=3)
        sim = BoidSimulation(cfg)
        sim.add_predator(200, 200)
        svg = SVGRenderer().render(sim)
        assert "#ff4444" in svg  # predator color

    def test_goal_in_svg(self):
        cfg = SimulationConfig(num_boids=3)
        sim = BoidSimulation(cfg)
        sim.set_goal(400, 300)
        svg = SVGRenderer().render(sim)
        assert "ffd700" in svg  # goal color

    def test_no_sroke_typo(self):
        """Verify the 'sroke=' typo is absent."""
        cfg = SimulationConfig(num_boids=3)
        sim = BoidSimulation(cfg)
        sim.add_obstacle(100, 100, 30)
        svg = SVGRenderer().render(sim)
        assert "sroke=" not in svg


class TestTrailSVGRenderer:
    def test_basic_render(self):
        cfg = SimulationConfig(num_boids=5, trail_length=10)
        sim = BoidSimulation(cfg)
        for _ in range(5):
            sim.step()
        svg = TrailSVGRenderer().render(sim)
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_trail_lines_present(self):
        cfg = SimulationConfig(num_boids=5, trail_length=10)
        sim = BoidSimulation(cfg)
        for _ in range(5):
            sim.step()
        svg = TrailSVGRenderer().render(sim)
        assert "line" in svg


class TestPPMRenderer:
    def test_basic_render(self):
        cfg = SimulationConfig(num_boids=5, width=50, height=50)
        sim = BoidSimulation(cfg)
        with tempfile.NamedTemporaryFile(suffix=".ppm", delete=False) as f:
            path = f.name
        try:
            PPMRenderer().render(sim, path, scale=1.0)
            assert os.path.exists(path)
            with open(path, "rb") as f:
                header = f.read(20)
            assert header.startswith(b"P6")
        finally:
            os.unlink(path)

    def test_zero_scale_raises(self):
        cfg = SimulationConfig(num_boids=3, width=50, height=50)
        sim = BoidSimulation(cfg)
        with pytest.raises(ValueError):
            PPMRenderer().render(sim, "/tmp/test.ppm", scale=0)

    def test_negative_scale_raises(self):
        cfg = SimulationConfig(num_boids=3, width=50, height=50)
        sim = BoidSimulation(cfg)
        with pytest.raises(ValueError):
            PPMRenderer().render(sim, "/tmp/test.ppm", scale=-1.0)

    def test_parse_color(self):
        r = PPMRenderer()
        assert r._parse_color("#ff0000") == (255, 0, 0)
        assert r._parse_color("#00ff00") == (0, 255, 0)
        assert r._parse_color("#0000ff") == (0, 0, 255)


class TestAnimatedSVGRenderer:
    def test_basic_render(self):
        cfg = SimulationConfig(num_boids=5, width=100, height=100)
        sim = BoidSimulation(cfg)
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            path = f.name
        try:
            renderer = AnimatedSVGRenderer(fps=10, loop=True)
            renderer.render(sim, path, steps=10)
            assert os.path.exists(path)
            with open(path) as f:
                content = f.read()
            assert "<svg" in content
            assert "animate" in content
        finally:
            os.unlink(path)

    def test_invalid_fps(self):
        with pytest.raises(ValueError):
            AnimatedSVGRenderer(fps=0)
        with pytest.raises(ValueError):
            AnimatedSVGRenderer(fps=-1)

    def test_no_loop(self):
        cfg = SimulationConfig(num_boids=3, width=50, height=50)
        sim = BoidSimulation(cfg)
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            path = f.name
        try:
            renderer = AnimatedSVGRenderer(fps=10, loop=False)
            renderer.render(sim, path, steps=5)
            with open(path) as f:
                content = f.read()
            assert "indefinite" not in content
        finally:
            os.unlink(path)


class TestJSONRenderer:
    def test_basic_render(self):
        cfg = SimulationConfig(num_boids=5)
        sim = BoidSimulation(cfg)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            JSONRenderer().render(sim, path)
            assert os.path.exists(path)
            import json
            with open(path) as f:
                data = json.load(f)
            assert "boids" in data
            assert len(data["boids"]) == 5
        finally:
            os.unlink(path)