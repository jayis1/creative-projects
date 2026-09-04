from __future__ import annotations

import json

from particle_life_sim.cli import main
from particle_life_sim.engine import ParticleLifeSimulation, SimulationConfig
from particle_life_sim.io import load_mapping
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
    assert metrics["neighbor_checks"] >= 0


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


def test_timeline_contains_initial_and_final_samples() -> None:
    sim = ParticleLifeSimulation(SimulationConfig.from_dict(get_preset("aurora"), seed=2))
    timeline = sim.timeline(steps=5, dt=0.1, sample_every=2)
    assert timeline[0]["step"] == 0
    assert timeline[-1]["step"] == 5


def test_midpoint_integrator_is_supported() -> None:
    preset = get_preset("binary-star")
    preset["integrator"] = "midpoint"
    sim = ParticleLifeSimulation(SimulationConfig.from_dict(preset, seed=1))
    sim.run(steps=4, dt=0.1)
    assert sim.step_count == 4


def test_load_mapping_supports_toml(tmp_path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        """
width = 40
height = 20
drag = 0.05
force_scale = 20
interaction_radius = 8
repulsion_radius = 2
max_speed = 5
integrator = \"euler\"

[[species]]
name = \"a\"
color = \"#112233\"
count = 2

[[species]]
name = \"b\"
color = \"#445566\"
count = 2

interactions = [[0.5, -0.3], [-0.2, 0.4]]
""".strip()
    )
    data = load_mapping(path)
    assert data["width"] == 40
    assert len(data["species"]) == 2


def test_cli_export_preset_writes_json(tmp_path) -> None:
    output = tmp_path / "aurora.json"
    exit_code = main(["export-preset", "aurora", "--output", str(output)])
    data = json.loads(output.read_text())
    assert exit_code == 0
    assert data["width"] > 0


def test_from_snapshot_restores_state() -> None:
    original = ParticleLifeSimulation(SimulationConfig.from_dict(get_preset("petri"), seed=6))
    original.run(steps=3, dt=0.1)
    restored = ParticleLifeSimulation.from_snapshot(original.snapshot())
    assert restored.snapshot() == original.snapshot()


def test_config_validation_rejects_duplicate_species_names() -> None:
    preset = get_preset("aurora")
    preset["species"][1]["name"] = preset["species"][0]["name"]
    try:
        SimulationConfig.from_dict(preset)
    except ValueError as exc:
        assert "unique" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected duplicate species validation error")
