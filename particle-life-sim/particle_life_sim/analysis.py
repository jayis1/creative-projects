"""Higher-level analysis tools for Particle Life runs."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from itertools import product
from math import atan2, cos, hypot, log2, pi, sin
from statistics import fmean, pstdev
from typing import Any, Iterable

from .engine import ParticleLifeSimulation, SimulationConfig
from .models import Particle


def summarize_simulation(simulation: ParticleLifeSimulation, bins: int = 12) -> dict[str, Any]:
    """Return core engine metrics plus higher-level emergent-behavior signals."""

    if bins <= 0:
        raise ValueError("bins must be positive")
    metrics = simulation.metrics()
    particles = simulation.particles
    metrics.update(
        {
            "speed_stddev": pstdev([particle.speed() for particle in particles]) if len(particles) > 1 else 0.0,
            "occupancy_entropy": occupancy_entropy(
                particles,
                simulation.config.width,
                simulation.config.height,
                bins=bins,
            ),
            "pairwise_mean_distance": pairwise_mean_distance(
                particles,
                simulation.config.width,
                simulation.config.height,
            ),
            "momentum": momentum(particles),
            "species_spread": species_spread(
                particles,
                simulation.config.species_styles,
                simulation.config.width,
                simulation.config.height,
            ),
            "microsteps": simulation.microstep_count,
            "integrator": simulation.config.integrator,
        }
    )
    return metrics


def occupancy_entropy(particles: Iterable[Particle], width: float, height: float, bins: int = 12) -> float:
    """Measure how evenly particles occupy a coarse grid."""

    counts = [0 for _ in range(bins * bins)]
    total = 0
    for particle in particles:
        col = min(bins - 1, max(0, int((particle.x / width) * bins)))
        row = min(bins - 1, max(0, int((particle.y / height) * bins)))
        counts[row * bins + col] += 1
        total += 1
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in counts:
        if count == 0:
            continue
        probability = count / total
        entropy -= probability * log2(probability)
    return entropy


def pairwise_mean_distance(particles: list[Particle], width: float, height: float) -> float:
    """Return mean wrapped pairwise distance across all unique pairs."""

    if len(particles) < 2:
        return 0.0
    distances: list[float] = []
    for index, particle in enumerate(particles[:-1]):
        for other in particles[index + 1 :]:
            dx = ParticleLifeSimulation._wrapped_delta(other.x - particle.x, width)
            dy = ParticleLifeSimulation._wrapped_delta(other.y - particle.y, height)
            distances.append(hypot(dx, dy))
    return fmean(distances)


def momentum(particles: Iterable[Particle]) -> dict[str, float]:
    """Return total momentum vector and magnitude."""

    total_vx = 0.0
    total_vy = 0.0
    for particle in particles:
        total_vx += particle.vx
        total_vy += particle.vy
    return {
        "x": total_vx,
        "y": total_vy,
        "magnitude": hypot(total_vx, total_vy),
    }


def species_spread(
    particles: Iterable[Particle],
    styles: list[Any],
    width: float,
    height: float,
) -> dict[str, float]:
    """Return mean radial spread around each species centroid."""

    grouped: dict[int, list[Particle]] = {index: [] for index in range(len(styles))}
    for particle in particles:
        grouped.setdefault(particle.species, []).append(particle)
    result: dict[str, float] = {}
    for index, members in grouped.items():
        if not members:
            result[styles[index].name] = 0.0
            continue
        center_x = _circular_mean([member.x for member in members], width)
        center_y = _circular_mean([member.y for member in members], height)
        spread = fmean(
            hypot(
                ParticleLifeSimulation._wrapped_delta(member.x - center_x, width),
                ParticleLifeSimulation._wrapped_delta(member.y - center_y, height),
            )
            for member in members
        )
        result[styles[index].name] = spread
    return result


def sweep_parameters(
    config: SimulationConfig,
    *,
    steps: int,
    dt: float,
    substeps: int,
    seeds: list[int],
    force_scales: list[float],
    drags: list[float],
    bins: int = 12,
) -> list[dict[str, Any]]:
    """Run a parameter sweep and rank results by structured motion heuristics."""

    if not seeds:
        raise ValueError("at least one seed is required")
    if not force_scales:
        raise ValueError("at least one force_scale is required")
    if not drags:
        raise ValueError("at least one drag value is required")

    results: list[dict[str, Any]] = []
    for seed, force_scale, drag in product(seeds, force_scales, drags):
        sweep_config = replace(config, force_scale=force_scale, drag=drag, seed=seed)
        simulation = ParticleLifeSimulation(sweep_config)
        simulation.run(steps=steps, dt=dt, substeps=substeps)
        summary = summarize_simulation(simulation, bins=bins)
        score = _novelty_score(summary)
        results.append(
            {
                "score": score,
                "seed": seed,
                "force_scale": force_scale,
                "drag": drag,
                "summary": summary,
            }
        )
    return sorted(results, key=lambda row: row["score"], reverse=True)


def config_with_updates(config: SimulationConfig, updates: dict[str, Any]) -> SimulationConfig:
    """Return a validated config copy with selected fields replaced."""

    payload = deepcopy(config.to_dict())
    payload.update(updates)
    return SimulationConfig.from_dict(payload, seed=payload.get("seed"))


def _novelty_score(summary: dict[str, Any]) -> float:
    entropy = float(summary.get("occupancy_entropy", 0.0))
    speed = float(summary.get("mean_speed", 0.0))
    spread = fmean(summary.get("species_spread", {}).values()) if summary.get("species_spread") else 0.0
    neighbor_scale = float(summary.get("neighbor_checks", 0.0)) / max(1, int(summary.get("particles", 1)))
    return entropy * 1.8 + speed * 0.8 + spread * 0.2 - neighbor_scale * 0.01


def _circular_mean(values: list[float], size: float) -> float:
    if not values:
        return 0.0
    angles = [2.0 * pi * (value % size) / size for value in values]
    mean_sin = fmean(sin(angle) for angle in angles)
    mean_cos = fmean(cos(angle) for angle in angles)
    angle = atan2(mean_sin, mean_cos)
    if angle < 0.0:
        angle += 2.0 * pi
    return (angle * size) / (2.0 * pi)
