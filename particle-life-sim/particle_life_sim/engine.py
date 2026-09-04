"""Simulation engine for Particle Life."""

from __future__ import annotations

from dataclasses import dataclass
import json
import random
from math import hypot
from pathlib import Path
from statistics import fmean
from typing import Any

from .models import Particle, SpeciesStyle


@dataclass(slots=True)
class SimulationConfig:
    """Validated simulation configuration."""

    width: float
    height: float
    drag: float
    force_scale: float
    interaction_radius: float
    repulsion_radius: float
    max_speed: float
    species_styles: list[SpeciesStyle]
    species_counts: list[int]
    interactions: list[list[float]]
    seed: int = 0

    @property
    def species_count(self) -> int:
        return len(self.species_styles)

    @property
    def particle_count(self) -> int:
        return sum(self.species_counts)

    @classmethod
    def from_dict(cls, data: dict[str, Any], seed: int | None = None) -> "SimulationConfig":
        width = float(data["width"])
        height = float(data["height"])
        drag = float(data.get("drag", 0.05))
        force_scale = float(data.get("force_scale", 40.0))
        interaction_radius = float(data.get("interaction_radius", 16.0))
        repulsion_radius = float(data.get("repulsion_radius", 3.0))
        max_speed = float(data.get("max_speed", 8.0))
        species_rows = data["species"]
        interactions = [[float(value) for value in row] for row in data["interactions"]]

        styles = [SpeciesStyle(name=str(row["name"]), color=str(row["color"])) for row in species_rows]
        counts = [int(row["count"]) for row in species_rows]
        cfg = cls(
            width=width,
            height=height,
            drag=drag,
            force_scale=force_scale,
            interaction_radius=interaction_radius,
            repulsion_radius=repulsion_radius,
            max_speed=max_speed,
            species_styles=styles,
            species_counts=counts,
            interactions=interactions,
            seed=int(seed if seed is not None else data.get("seed", 0)),
        )
        cfg.validate()
        return cfg

    def validate(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("width and height must be positive")
        if self.drag < 0:
            raise ValueError("drag must be non-negative")
        if self.force_scale < 0:
            raise ValueError("force_scale must be non-negative")
        if self.interaction_radius <= 0:
            raise ValueError("interaction_radius must be positive")
        if self.repulsion_radius <= 0:
            raise ValueError("repulsion_radius must be positive")
        if self.max_speed <= 0:
            raise ValueError("max_speed must be positive")
        species_count = len(self.species_styles)
        if species_count == 0:
            raise ValueError("at least one species is required")
        if len(self.species_counts) != species_count:
            raise ValueError("species counts must match species styles")
        if any(count <= 0 for count in self.species_counts):
            raise ValueError("species counts must be positive")
        if len(self.interactions) != species_count:
            raise ValueError("interaction matrix row count mismatch")
        for row in self.interactions:
            if len(row) != species_count:
                raise ValueError("interaction matrix must be square")
        for style in self.species_styles:
            if not style.color.startswith("#") or len(style.color) != 7:
                raise ValueError(f"invalid color {style.color!r}; expected #RRGGBB")

    def to_dict(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "drag": self.drag,
            "force_scale": self.force_scale,
            "interaction_radius": self.interaction_radius,
            "repulsion_radius": self.repulsion_radius,
            "max_speed": self.max_speed,
            "seed": self.seed,
            "species": [
                {"name": style.name, "color": style.color, "count": count}
                for style, count in zip(self.species_styles, self.species_counts)
            ],
            "interactions": self.interactions,
        }


class ParticleLifeSimulation:
    """Particle Life simulator with toroidal pairwise forces."""

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.random = random.Random(config.seed)
        self.particles = self._spawn_particles()
        self.step_count = 0

    @classmethod
    def from_json(cls, path: str | Path, seed: int | None = None) -> "ParticleLifeSimulation":
        data = json.loads(Path(path).read_text())
        return cls(SimulationConfig.from_dict(data, seed=seed))

    def _spawn_particles(self) -> list[Particle]:
        particles: list[Particle] = []
        for species, count in enumerate(self.config.species_counts):
            for _ in range(count):
                particles.append(
                    Particle(
                        x=self.random.uniform(0.0, self.config.width),
                        y=self.random.uniform(0.0, self.config.height),
                        vx=self.random.uniform(-0.5, 0.5),
                        vy=self.random.uniform(-0.5, 0.5),
                        species=species,
                    )
                )
        return particles

    def step(self, dt: float = 1.0) -> None:
        if dt <= 0:
            raise ValueError("dt must be positive")
        cfg = self.config
        next_particles: list[Particle] = []
        for index, particle in enumerate(self.particles):
            ax = 0.0
            ay = 0.0
            for other_index, other in enumerate(self.particles):
                if index == other_index:
                    continue
                dx = self._wrapped_delta(other.x - particle.x, cfg.width)
                dy = self._wrapped_delta(other.y - particle.y, cfg.height)
                distance = hypot(dx, dy)
                if distance == 0.0 or distance > cfg.interaction_radius:
                    continue
                direction_x = dx / distance
                direction_y = dy / distance
                attraction = cfg.interactions[particle.species][other.species]
                force = attraction * (1.0 - (distance / cfg.interaction_radius))
                if distance < cfg.repulsion_radius:
                    force -= (cfg.repulsion_radius - distance) / cfg.repulsion_radius
                ax += direction_x * force * cfg.force_scale
                ay += direction_y * force * cfg.force_scale
            vx = (particle.vx + ax * dt) * (1.0 - cfg.drag * dt)
            vy = (particle.vy + ay * dt) * (1.0 - cfg.drag * dt)
            speed = hypot(vx, vy)
            if speed > cfg.max_speed:
                scale = cfg.max_speed / speed
                vx *= scale
                vy *= scale
            x = (particle.x + vx * dt) % cfg.width
            y = (particle.y + vy * dt) % cfg.height
            next_particles.append(Particle(x=x, y=y, vx=vx, vy=vy, species=particle.species))
        self.particles = next_particles
        self.step_count += 1

    def run(self, steps: int, dt: float = 1.0) -> None:
        if steps < 0:
            raise ValueError("steps must be non-negative")
        for _ in range(steps):
            self.step(dt=dt)

    def snapshot(self) -> dict[str, Any]:
        return {
            "step": self.step_count,
            "config": self.config.to_dict(),
            "particles": [
                {"x": p.x, "y": p.y, "vx": p.vx, "vy": p.vy, "species": p.species}
                for p in self.particles
            ],
        }

    def metrics(self) -> dict[str, Any]:
        speeds = [particle.speed() for particle in self.particles]
        species_energy: dict[str, float] = {}
        species_centers: dict[str, tuple[float, float]] = {}
        for index, style in enumerate(self.config.species_styles):
            members = [particle for particle in self.particles if particle.species == index]
            species_energy[style.name] = sum(0.5 * particle.speed() ** 2 for particle in members)
            species_centers[style.name] = (
                fmean([particle.x for particle in members]),
                fmean([particle.y for particle in members]),
            )
        return {
            "step": self.step_count,
            "particles": len(self.particles),
            "mean_speed": fmean(speeds) if speeds else 0.0,
            "max_speed": max(speeds, default=0.0),
            "species_energy": species_energy,
            "species_centers": species_centers,
        }

    @staticmethod
    def _wrapped_delta(delta: float, size: float) -> float:
        half = size / 2.0
        if delta > half:
            return delta - size
        if delta < -half:
            return delta + size
        return delta
