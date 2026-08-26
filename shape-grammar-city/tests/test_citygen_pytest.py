from __future__ import annotations

import json
from pathlib import Path

import pytest

from citygen.cli import main
from citygen.config import GenerationConfig, load_config
from citygen.districts import analyze_districts
from citygen.generator import CityMap, Point, Tile, generate_city
from citygen.reports import render_report_html


def test_load_json_config(tmp_path: Path) -> None:
    config_path = tmp_path / "city.json"
    config_path.write_text(
        json.dumps(
            {
                "city": {
                    "width": 23,
                    "height": 17,
                    "mode": "organic",
                    "iterations": 14,
                    "landmarks": 2,
                    "zone_weights": {"commercial": 0.35},
                    "seeds": [3, 5],
                }
            }
        )
    )
    config = load_config(config_path)
    assert config == GenerationConfig(
        width=23,
        height=17,
        seed=None,
        mode="organic",
        iterations=14,
        landmarks=2,
        zone_weights={"commercial": 0.35},
        seeds=[3, 5],
        cell_size=18,
        title="Shape Grammar City Report",
    )


def test_load_toml_config(tmp_path: Path) -> None:
    config_path = tmp_path / "city.toml"
    config_path.write_text(
        """
[city]
width = 25
height = 19
mode = "radial"
iterations = 18
landmarks = 3
cell_size = 12

[city.zone_weights]
park = 0.2
""".strip()
    )
    config = load_config(config_path)
    assert config.mode == "radial"
    assert config.cell_size == 12
    assert config.zone_weights == {"park": 0.2}


def test_district_analysis_finds_named_clusters() -> None:
    city = CityMap(11, 11)
    for x in range(2, 6):
        for y in range(2, 5):
            city.set_tile(Point(x, y), Tile.RESIDENTIAL)
    for x in range(2, 6):
        city.set_tile(Point(x, 5), Tile.ROAD)
    districts = analyze_districts(city, min_size=4)
    assert districts
    assert districts[0].tile == "residential"
    assert "Residential" in districts[0].name


def test_report_contains_svg_and_district_table() -> None:
    city = generate_city(width=21, height=17, seed=4, mode="grid")
    districts = analyze_districts(city)
    html = render_report_html(city, stats={"road_cells": 12}, districts=districts, title="Demo")
    assert "<svg" in html
    assert "Districts" in html
    assert "Demo" in html


def test_cli_batch_writes_summary(tmp_path: Path) -> None:
    output = tmp_path / "batch.json"
    exit_code = main([
        "batch",
        "--width",
        "21",
        "--height",
        "17",
        "--mode",
        "grid",
        "--seeds",
        "1,2",
        "--output",
        str(output),
    ])
    payload = json.loads(output.read_text())
    assert exit_code == 0
    assert payload["best_seed"] in {1, 2}
    assert len(payload["runs"]) == 2


def test_cli_report_with_config(tmp_path: Path) -> None:
    config_path = tmp_path / "city.toml"
    output = tmp_path / "report.html"
    config_path.write_text(
        """
width = 21
height = 17
seed = 5
mode = "grid"
iterations = 16
landmarks = 2
cell_size = 10
title = "Configured Report"
""".strip()
    )
    exit_code = main(["report", "--config", str(config_path), "--output", str(output)])
    assert exit_code == 0
    html = output.read_text()
    assert "Configured Report" in html
    assert "<svg" in html


def test_invalid_config_suffix_raises(tmp_path: Path) -> None:
    config_path = tmp_path / "city.yaml"
    config_path.write_text("width: 21")
    with pytest.raises(ValueError):
        load_config(config_path)
