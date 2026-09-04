"""Simulation engine for Particle Life."""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from pathlib import Path
import random
from statistics import fmean
from typing import Any, Iterable

from .io import dump_json, load_mapping
from .models import Particle, SpeciesStyle


@dataclass(slots=True)
class SimulationConfig:
    """Validated simulation configuration.

    The interaction matrix is indexed as `[source_species][target_species]`.
    Positive values attract, negative values repel.
    """

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
    integrator: str = "euler"

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
        integrator = str(data.get("integrator", "euler")).lower()
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
            integrator=integrator,
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
        if self.repulsion_radius >= self.interaction_radius:
            raise ValueError("repulsion_radius must be smaller than interaction_radius")
        if self.max_speed <= 0:
            raise ValueError("max_speed must be positive")
        if self.integrator not in {"euler", "midpoint"}:
            raise ValueError("integrator must be 'euler' or 'midpoint'")
        species_count = len(self.species_styles)
        if species_count == 0:
            raise ValueError("at least one species is required")
        if len(self.species_counts) != species_count:
            raise ValueError("species counts must match species styles")
        if any(count <= 0 for count in self.species_counts):
            raise ValueError("species counts must be positive")
        if len({style.name for style in self.species_styles}) != species_count:
            raise ValueError("species names must be unique")
        if len(self.interactions) != species_count:
            raise ValueError("interaction matrix row count mismatch")
        for row in self.interactions:
            if len(row) != species_count:
                raise ValueError("interaction matrix must be square")
        for style in self.species_styles:
            _validate_hex_color(style.color)

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
            "integrator": self.integrator,
            "species": [
                {"name": style.name, "color": style.color, "count": count}
                for style, count in zip(self.species_styles, self.species_counts)
            ],
            "interactions": self.interactions,
        }


@dataclass(slots=True)
class SpatialHash:
    """Uniform spatial hash used to reduce neighborhood checks."""

    cell_size: float
    width: float
    height: float

    def bucket_key(self, x: float, y: float) -> tuple[int, int]:
        return (int(x // self.cell_size), int(y // self.cell_size))

    def build(self, particles: Iterable[Particle]) -> dict[tuple[int, int], list[int]]:
        buckets: dict[tuple[int, int], list[int]] = {}
        for index, particle in enumerate(particles):
            buckets.setdefault(self.bucket_key(particle.x, particle.y), []).append(index)
        return buckets

    def neighbor_indices(self, particle: Particle, buckets: dict[tuple[int, int], list[int]]) -> list[int]:
        origin_x, origin_y = self.bucket_key(particle.x, particle.y)
        max_x = max(1, int(self.width // self.cell_size) + 1)
        max_y = max(1, int(self.height // self.cell_size) + 1)
        result: list[int] = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                key = ((origin_x + dx) % max_x, (origin_y + dy) % max_y)
                result.extend(buckets.get(key, ()))
        return result


class ParticleLifeSimulation:
    """Particle Life simulator with toroidal forces and optional midpoint integration."""

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.random = random.Random(config.seed)
        self.particles = self._spawn_particles()
        self.step_count = 0
        self._spatial_hash = SpatialHash(config.interaction_radius, config.width, config.height)
        self.last_neighbor_checks = 0

    @classmethod
    def from_path(cls, path: str | Path, seed: int | None = None) -> "ParticleLifeSimulation":
        data = load_mapping(path)
        return cls(SimulationConfig.from_dict(data, seed=seed))

    @classmethod
    def from_snapshot(cls, data: dict[str, Any]) -> "ParticleLifeSimulation":
        sim = cls(SimulationConfig.from_dict(data["config"]))
        sim.particles = [Particle(**row) for row in data["particles"]]
        sim.step_count = int(data.get("step", 0))
        return sim

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

    def step(self, dt: float = 1.0, substeps: int = 1) -> None:
        if dt <= 0:
            raise ValueError("dt must be positive")
        if substeps <= 0:
            raise ValueError("substeps must be positive")
        slice_dt = dt / substeps
        for _ in range(substeps):
            if self.config.integrator == "midpoint":
                self.particles = self._advance_midpoint(self.particles, slice_dt)
            else:
                self.particles = self._advance_euler(self.particles, slice_dt)
            self.step_count += 1

    def run(self, steps: int, dt: float = 1.0, substeps: int = 1) -> None:
        if steps < 0:
            raise ValueError("steps must be non-negative")
        for _ in range(steps):
            self.step(dt=dt, substeps=substeps)

    def timeline(self, steps: int, dt: float = 1.0, substeps: int = 1, sample_every: int = 1) -> list[dict[str, Any]]:
        if sample_every <= 0:
            raise ValueError("sample_every must be positive")
        rows = [self.metrics()]
        for index in range(1, steps + 1):
            self.step(dt=dt, substeps=substeps)
            if index % sample_every == 0 or index == steps:
                rows.append(self.metrics())
        return rows

    def snapshot(self) -> dict[str, Any]:
        return {
            "step": self.step_count,
            "config": self.config.to_dict(),
            "particles": [
                {"x": p.x, "y": p.y, "vx": p.vx, "vy": p.vy, "species": p.species}
                for p in self.particles
            ],
        }

    def save_snapshot(self, path: str | Path) -> None:
        dump_json(path, self.snapshot())

    def metrics(self) -> dict[str, Any]:
        speeds = [particle.speed() for particle in self.particles]
        species_energy: dict[str, float] = {}
        species_centers: dict[str, tuple[float, float]] = {}
        nearest_neighbor: dict[str, float] = {}
        for index, style in enumerate(self.config.species_styles):
            members = [particle for particle in self.particles if particle.species == index]
            species_energy[style.name] = sum(0.5 * particle.speed() ** 2 for particle in members)
            species_centers[style.name] = (
                fmean([particle.x for particle in members]),
                fmean([particle.y for particle in members]),
            )
            nearest_neighbor[style.name] = self._mean_nearest_neighbor(members)
        return {
            "step": self.step_count,
            "particles": len(self.particles),
            "mean_speed": fmean(speeds) if speeds else 0.0,
            "max_speed": max(speeds, default=0.0),
            "mean_radius": fmean(self._distance_from_center(p) for p in self.particles) if self.particles else 0.0,
            "neighbor_checks": self.last_neighbor_checks,
            "species_energy": species_energy,
            "species_centers": species_centers,
            "nearest_neighbor": nearest_neighbor,
        }

    def _advance_euler(self, particles: list[Particle], dt: float) -> list[Particle]:
        forces = self._compute_accelerations(particles)
        return [self._integrate_particle(particle, ax, ay, dt) for particle, (ax, ay) in zip(particles, forces)]

    def _advance_midpoint(self, particles: list[Particle], dt: float) -> list[Particle]:
        initial_forces = self._compute_accelerations(particles)
        midpoint_particles = [
            self._integrate_particle(particle, ax, ay, dt / 2.0, clamp_speed=False)
            for particle, (ax, ay) in zip(particles, initial_forces)
        ]
        midpoint_forces = self._compute_accelerations(midpoint_particles)
        return [self._integrate_particle(particle, ax, ay, dt) for particle, (ax, ay) in zip(particles, midpoint_forces)]

    def _integrate_particle(
        self,
        particle: Particle,
        ax: float,
        ay: float,
        dt: float,
        *,
        clamp_speed: bool = True,
    ) -> Particle:
        cfg = self.config
        vx = (particle.vx + ax * dt) * max(0.0, 1.0 - cfg.drag * dt)
        vy = (particle.vy + ay * dt) * max(0.0, 1.0 - cfg.drag * dt)
        if clamp_speed:
            speed = hypot(vx, vy)
            if speed > cfg.max_speed:
                scale = cfg.max_speed / speed
                vx *= scale
                vy *= scale
        x = (particle.x + vx * dt) % cfg.width
        y = (particle.y + vy * dt) % cfg.height
        return Particle(x=x, y=y, vx=vx, vy=vy, species=particle.species)

    def _compute_accelerations(self, particles: list[Particle]) -> list[tuple[float, float]]:
        cfg = self.config
        buckets = self._spatial_hash.build(particles)
        accelerations: list[tuple[float, float]] = []
        neighbor_checks = 0
        for index, particle in enumerate(particles):
            ax = 0.0
            ay = 0.0
            for other_index in self._spatial_hash.neighbor_indices(particle, buckets):
                if index == other_index:
                    continue
                other = particles[other_index]
                dx = self._wrapped_delta(other.x - particle.x, cfg.width)
                dy = self._wrapped_delta(other.y - particle.y, cfg.height)
                distance = hypot(dx, dy)
                neighbor_checks += 1
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
            accelerations.append((ax, ay))
        self.last_neighbor_checks = neighbor_checks
        return accelerations

    def _mean_nearest_neighbor(self, members: list[Particle]) -> float:
        if len(members) < 2:
            return 0.0
        nearest: list[float] = []
        for index, particle in enumerate(members):
            best = float("inf")
            for other_index, other in enumerate(members):
                if index == other_index:
                    continue
                dx = self._wrapped_delta(other.x - particle.x, self.config.width)
                dy = self._wrapped_delta(other.y - particle.y, self.config.height)
                best = min(best, hypot(dx, dy))
            nearest.append(best)
        return fmean(nearest)

    def _distance_from_center(self, particle: Particle) -> float:
        center_x = self.config.width / 2.0
        center_y = self.config.height / 2.0
        return hypot(particle.x - center_x, particle.y - center_y)

    @staticmethod
    def _wrapped_delta(delta: float, size: float) -> float:
        half = size / 2.0
        if delta > half:
            return delta - size
        if delta < -half:
            return delta + size
        return delta


def _validate_hex_color(color: str) -> None:
    if not color.startswith("#") or len(color) != 7:
        raise ValueError(f"invalid color {color!r}; expected #RRGGBB")
    int(color[1:], 16)
