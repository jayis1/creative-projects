from __future__ import annotations

import json

from particle_life_sim.analysis import pairwise_mean_distance, summarize_simulation, sweep_parameters
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
interactions = [[0.5, -0.3], [-0.2, 0.4]]

[[species]]
name = \"a\"
color = \"#112233\"
count = 2

[[species]]
name = \"b\"
color = \"#445566\"
count = 2
""".strip()
    )
    data = load_mapping(path)
    assert data["width"] == 40
    assert len(data["species"]) == 2
    config = SimulationConfig.from_dict(data)
    assert config.particle_count == 4


def test_load_mapping_supports_yaml(tmp_path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        """
width: 40
height: 20
drag: 0.05
force_scale: 20
interaction_radius: 8
repulsion_radius: 2
max_speed: 5
integrator: midpoint
species:
  - name: a
    color: "#112233"
    count: 2
  - name: b
    color: "#445566"
    count: 2
interactions:
  - [0.5, -0.3]
  - [-0.2, 0.4]
""".strip()
    )
    data = load_mapping(path)
    assert data["integrator"] == "midpoint"
    assert len(data["species"]) == 2


def test_cli_export_preset_writes_yaml(tmp_path) -> None:
    output = tmp_path / "aurora.yaml"
    exit_code = main(["export-preset", "aurora", "--output", str(output)])
    data = load_mapping(output)
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


def test_substeps_do_not_change_reported_step_number() -> None:
    sim = ParticleLifeSimulation(SimulationConfig.from_dict(get_preset("aurora"), seed=8))
    sim.run(steps=3, dt=0.1, substeps=4)
    assert sim.step_count == 3


def test_spatial_hash_does_not_duplicate_neighbors_in_single_bucket_world() -> None:
    config = SimulationConfig.from_dict(
        {
            "width": 5,
            "height": 5,
            "drag": 0.0,
            "force_scale": 1.0,
            "interaction_radius": 10.0,
            "repulsion_radius": 1.0,
            "max_speed": 100.0,
            "species": [{"name": "solo", "color": "#112233", "count": 2}],
            "interactions": [[0.5]],
        },
        seed=0,
    )
    sim = ParticleLifeSimulation(config)
    sim.particles = [
        sim.particles[0].__class__(x=1.0, y=2.5, vx=0.0, vy=0.0, species=0),
        sim.particles[0].__class__(x=4.0, y=2.5, vx=0.0, vy=0.0, species=0),
    ]
    sim.step(dt=1.0)
    assert sim.last_neighbor_checks == 2


def test_cli_render_creates_parent_directories(tmp_path) -> None:
    output = tmp_path / "nested" / "frame.svg"
    exit_code = main([
        "render",
        "--preset",
        "aurora",
        "--steps",
        "1",
        "--dt",
        "0.1",
        "--output",
        str(output),
    ])
    assert exit_code == 0
    assert output.exists()


def test_analyze_adds_advanced_metrics() -> None:
    sim = ParticleLifeSimulation(SimulationConfig.from_dict(get_preset("aurora"), seed=8))
    sim.run(steps=4, dt=0.1)
    summary = summarize_simulation(sim, bins=8)
    assert summary["occupancy_entropy"] > 0
    assert "speed_stddev" in summary
    assert "species_spread" in summary
    assert summary["microsteps"] == sim.microstep_count


def test_pairwise_mean_distance_uses_wrapped_space() -> None:
    config = SimulationConfig.from_dict(get_preset("binary-star"), seed=1)
    sim = ParticleLifeSimulation(config)
    sim.particles = [
        sim.particles[0].__class__(x=1.0, y=1.0, vx=0.0, vy=0.0, species=0),
        sim.particles[0].__class__(x=config.width - 1.0, y=1.0, vx=0.0, vy=0.0, species=1),
    ]
    assert pairwise_mean_distance(sim.particles, config.width, config.height) == 2.0


def test_species_centers_use_wrap_aware_mean() -> None:
    config = SimulationConfig.from_dict(
        {
            "width": 100,
            "height": 100,
            "drag": 0.0,
            "force_scale": 1.0,
            "interaction_radius": 10.0,
            "repulsion_radius": 1.0,
            "max_speed": 10.0,
            "species": [{"name": "solo", "color": "#112233", "count": 2}],
            "interactions": [[0.0]],
        }
    )
    sim = ParticleLifeSimulation(config)
    sim.particles = [
        sim.particles[0].__class__(x=1.0, y=50.0, vx=0.0, vy=0.0, species=0),
        sim.particles[0].__class__(x=99.0, y=50.0, vx=0.0, vy=0.0, species=0),
    ]
    center_x, _ = sim.metrics()["species_centers"]["solo"]
    assert center_x < 5.0 or center_x > 95.0


def test_cli_resume_advances_snapshot(tmp_path) -> None:
    snapshot = tmp_path / "snapshot.json"
    resumed = tmp_path / "resumed.json"
    assert main(["snapshot", "--preset", "aurora", "--steps", "2", "--dt", "0.1", "--output", str(snapshot)]) == 0
    assert main(["resume", str(snapshot), "--steps", "3", "--dt", "0.1", "--save-snapshot", str(resumed)]) == 0
    resumed_data = load_mapping(resumed)
    assert resumed_data["step"] == 5


def test_cli_timeline_can_write_csv(tmp_path) -> None:
    output = tmp_path / "timeline.csv"
    assert main([
        "timeline",
        "--preset",
        "aurora",
        "--steps",
        "4",
        "--dt",
        "0.1",
        "--sample-every",
        "2",
        "--output",
        str(output),
    ]) == 0
    text = output.read_text()
    assert "step" in text
    assert "mean_speed" in text


def test_sweep_parameters_returns_ranked_results() -> None:
    config = SimulationConfig.from_dict(get_preset("aurora"), seed=1)
    results = sweep_parameters(
        config,
        steps=3,
        dt=0.1,
        substeps=1,
        seeds=[1, 2],
        force_scales=[30.0, 40.0],
        drags=[0.03],
    )
    assert len(results) == 4
    assert results[0]["score"] >= results[-1]["score"]


def test_cli_sweep_writes_report(tmp_path) -> None:
    output = tmp_path / "sweep.json"
    assert main([
        "sweep",
        "--preset",
        "aurora",
        "--steps",
        "3",
        "--dt",
        "0.1",
        "--seeds",
        "1",
        "2",
        "--force-scales",
        "30",
        "40",
        "--drags",
        "0.03",
        "0.05",
        "--output",
        str(output),
    ]) == 0
    report = load_mapping(output)
    assert report["tested"] == 8
    assert len(report["top"]) >= 1
