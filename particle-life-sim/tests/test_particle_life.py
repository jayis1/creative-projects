from __future__ import annotations

import json

from particle_life_sim.cli import main
from particle_life_sim.engine import ParticleLifeSimulation, SimulationConfig
from particle_life_sim.presets import get_preset, preset_names
from particle_life_sim.render import render_ascii, render_ppm, render_svg


def test_preset_names_are_sorted() -> None:
    assert preset_names() == sorted(preset_names())


def test_simulation_is_deterministic_for_same_seed() -> None:
    config = SimulationConfig.from_dict(get_preset("aurora"), seed=123)
    sim_a = ParticleLifeSimulation(config)
    sim_b = ParticleLifeSimulation(SimulationConfig.from_dict(get_preset("aurora"), seed=123))
    sim_a.run(steps=10, dt=0.1)
    sim_b.run(steps=10, dt=0.1)
    assert sim_a.snapshot() == sim_b.snapshot()


def test_metrics_match_particle_count() -> None:
    sim = ParticleLifeSimulation(SimulationConfig.from_dict(get_preset("binary-star"), seed=5))
    sim.run(steps=5, dt=0.1)
    metrics = sim.metrics()
    assert metrics["particles"] == sum(sim.config.species_counts)
    assert set(metrics["species_energy"]) == {"ember", "ice"}


def test_ascii_svg_and_ppm_renderers_emit_expected_headers() -> None:
    sim = ParticleLifeSimulation(SimulationConfig.from_dict(get_preset("petri"), seed=9))
    ascii_art = render_ascii(sim.particles, sim.config.species_styles, sim.config.width, sim.config.height)
    svg = render_svg(sim.particles, sim.config.species_styles, sim.config.width, sim.config.height)
    ppm = render_ppm(sim.particles, sim.config.species_styles, sim.config.width, sim.config.height)
    assert "1=magenta" in ascii_art
    assert svg.startswith("<svg")
    assert ppm.startswith("P3\n")


def test_cli_snapshot_writes_json(tmp_path) -> None:
    output = tmp_path / "snapshot.json"
    exit_code = main([
        "snapshot",
        "--preset",
        "aurora",
        "--steps",
        "3",
        "--dt",
        "0.1",
        "--seed",
        "4",
        "--output",
        str(output),
    ])
    data = json.loads(output.read_text())
    assert exit_code == 0
    assert data["step"] == 3
    assert len(data["particles"]) > 0
