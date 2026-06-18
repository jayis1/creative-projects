"""Comprehensive pytest test suite for the wfc_generator package.

Covers: tile/tileset core, grid algorithm, selection strategies, overlap
model, renderer, presets (including the new village & islands), config
system, CLI, serialization, and backward-compat with the legacy wfc module.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile

import pytest

# Ensure the package is importable regardless of cwd.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wfc_generator import (
    Tile,
    TileSet,
    WFCGrid,
    OverlapModel,
    Renderer,
    GenerationStats,
    WFCConfig,
    SelectionStrategy,
    create_terrain_tileset,
    create_dungeon_tileset,
    create_city_tileset,
    create_circuit_tileset,
    create_maze_tileset,
    create_village_tileset,
    create_islands_tileset,
)
from wfc_generator.tile import SIDES, OPPOSITE_SIDE


# --------------------------------------------------------------------------- #
# Tile
# --------------------------------------------------------------------------- #
class TestTile:
    def test_basic(self):
        t = Tile("test", weight=2.0, color="#ff0000", data="X")
        assert t.name == "test"
        assert t.weight == 2.0
        assert t.color == "#ff0000"
        assert t.data == "X"
        for side in SIDES:
            assert len(t.constraints[side]) == 0

    def test_add_constraint_string(self):
        t = Tile("a")
        t.add_constraint("top", "neighbor")
        assert "neighbor" in t.get_constraint("top")

    def test_add_constraint_list(self):
        t = Tile("a")
        t.add_constraint("top", ["a", "b", "c"])
        assert t.get_constraint("top") == {"a", "b", "c"}

    def test_add_constraint_set(self):
        t = Tile("a")
        t.add_constraint("top", {"a", "b"})
        assert t.get_constraint("top") == {"a", "b"}

    def test_remove_constraint(self):
        t = Tile("a")
        t.add_constraint("top", ["a", "b", "c"])
        t.remove_constraint("top", "b")
        assert t.get_constraint("top") == {"a", "c"}

    def test_invalid_side_raises(self):
        t = Tile("a")
        with pytest.raises(ValueError):
            t.add_constraint("diagonal", "x")

    def test_empty_name_rejected(self):
        with pytest.raises(ValueError):
            Tile("")

    def test_has_constraint(self):
        t = Tile("a")
        assert not t.has_constraint("top")
        t.add_constraint("top", "b")
        assert t.has_constraint("top")

    def test_equality_and_hash(self):
        a = Tile("x")
        b = Tile("x")
        assert a == b
        assert hash(a) == hash(b)
        assert a != "x"


# --------------------------------------------------------------------------- #
# TileSet
# --------------------------------------------------------------------------- #
class TestTileSet:
    def test_add_get_remove(self):
        ts = TileSet()
        t = Tile("a")
        ts.add_tile(t)
        assert ts.get_tile("a") is t
        assert "a" in ts
        assert len(ts) == 1
        assert ts.remove_tile("a") is t
        assert ts.get_tile("a") is None
        assert len(ts) == 0

    def test_names_sorted(self):
        ts = TileSet()
        ts.add_tile(Tile("c"))
        ts.add_tile(Tile("a"))
        ts.add_tile(Tile("b"))
        assert ts.names == ["a", "b", "c"]

    def test_make_symmetric(self):
        ts = TileSet()
        a = Tile("a")
        b = Tile("b")
        a.add_constraint("right", "b")
        ts.add_tile(a)
        ts.add_tile(b)
        ts.make_symmetric(direction="horizontal")
        assert "a" in b.get_constraint("left")

    def test_validate_unknown_reference(self):
        ts = TileSet()
        a = Tile("a")
        a.add_constraint("right", "ghost")
        ts.add_tile(a)
        warnings = ts.validate()
        assert any("ghost" in w for w in warnings)

    def test_validate_isolated_tile(self):
        ts = TileSet()
        ts.add_tile(Tile("iso"))
        warnings = ts.validate()
        assert any("isolated" in w for w in warnings)

    def test_json_roundtrip(self):
        ts = create_dungeon_tileset()
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            ts.to_json(path)
            loaded = TileSet.from_json(path)
            assert set(loaded.names) == set(ts.names)
        finally:
            os.unlink(path)

    def test_from_json_negative_weight(self):
        data = {"tiles": [{"name": "x", "weight": -1}]}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            with pytest.raises(ValueError):
                TileSet.from_json(path)
        finally:
            os.unlink(path)

    def test_from_json_missing_name(self):
        data = {"tiles": [{"weight": 1}]}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            with pytest.raises(ValueError):
                TileSet.from_json(path)
        finally:
            os.unlink(path)

    def test_rotated_variants(self):
        ts = TileSet()
        base = Tile("path", data="-")
        base.add_constraint("left", "path")
        base.add_constraint("right", "path")
        ts.add_tile(base)
        ts.add_rotated_variants("path")
        assert "path_r90" in ts
        assert "path_r180" in ts
        assert "path_r270" in ts


# --------------------------------------------------------------------------- #
# WFCGrid core
# --------------------------------------------------------------------------- #
class TestWFCGrid:
    def test_dimensions_validation(self):
        ts = create_terrain_tileset()
        with pytest.raises(ValueError):
            WFCGrid(ts, 0, 10)
        with pytest.raises(ValueError):
            WFCGrid(ts, 10, -1)

    def test_empty_tileset(self):
        with pytest.raises(ValueError):
            WFCGrid(TileSet(), 5, 5)

    def test_negative_weight(self):
        ts = TileSet()
        ts.add_tile(Tile("a", weight=-1))
        with pytest.raises(ValueError):
            WFCGrid(ts, 5, 5)

    def test_single_tile(self):
        ts = TileSet()
        ts.add_tile(Tile("only"))
        grid = WFCGrid(ts, 5, 5, seed=1)
        assert grid.run()
        result = grid.get_result()
        for row in result:
            for cell in row:
                assert cell == "only"

    def test_two_tile_alternating(self):
        ts = TileSet()
        a = Tile("a", weight=1)
        b = Tile("b", weight=1)
        a.add_constraint("right", "b")
        b.add_constraint("right", "a")
        a.add_constraint("left", "b")
        b.add_constraint("left", "a")
        # allow same on top/bottom to keep it solvable
        a.add_constraint("top", ["a", "b"])
        a.add_constraint("bottom", ["a", "b"])
        b.add_constraint("top", ["a", "b"])
        b.add_constraint("bottom", ["a", "b"])
        ts.add_tile(a)
        ts.add_tile(b)
        grid = WFCGrid(ts, 6, 2, seed=2)
        assert grid.run()
        result = grid.get_result()
        # Every horizontal neighbor must differ.
        for y in range(2):
            for x in range(5):
                assert result[y][x] != result[y][x + 1]

    def test_neighbors_non_periodic(self):
        ts = create_terrain_tileset()
        grid = WFCGrid(ts, 3, 3, periodic=False)
        n = grid._neighbors(0, 0)
        sides = {s for _, _, s in n}
        assert "top" not in sides
        assert "left" not in sides
        assert "right" in sides
        assert "bottom" in sides

    def test_neighbors_periodic(self):
        ts = create_terrain_tileset()
        grid = WFCGrid(ts, 3, 3, periodic=True)
        n = grid._neighbors(0, 0)
        sides = {s for _, _, s in n}
        assert "top" in sides
        assert "left" in sides

    def test_opposite_side(self):
        assert WFCGrid._opposite_side("top") == "bottom"
        assert WFCGrid._opposite_side("left") == "right"

    def test_progress_callback(self):
        calls = []
        ts = create_terrain_tileset()
        grid = WFCGrid(ts, 10, 6, seed=3, on_progress=lambda f: calls.append(f))
        assert grid.run()
        assert len(calls) > 0
        assert 0.0 <= calls[-1] <= 1.0

    def test_generation_stats(self):
        ts = create_dungeon_tileset()
        grid = WFCGrid(ts, 12, 8, seed=4)
        assert grid.run()
        s = grid.stats
        assert s.collapse_steps == 96
        assert s.duration >= 0.0
        assert s.contradiction is False

    def test_to_json_serialization(self):
        ts = create_maze_tileset()
        grid = WFCGrid(ts, 6, 4, seed=5)
        assert grid.run()
        text = grid.to_json()
        data = json.loads(text)
        assert data["width"] == 6
        assert data["height"] == 4
        assert len(data["grid"]) == 4
        assert len(data["grid"][0]) == 6
        assert data["selection"] == "min_entropy"


# --------------------------------------------------------------------------- #
# Selection strategies
# --------------------------------------------------------------------------- #
class TestSelectionStrategies:
    @pytest.mark.parametrize("strategy", list(SelectionStrategy))
    def test_all_strategies_complete(self, strategy):
        ts = create_terrain_tileset()
        grid = WFCGrid(ts, 10, 6, seed=9, selection=strategy)
        assert grid.run()
        assert grid.get_result() is not None

    def test_invalid_selection_string(self):
        ts = create_terrain_tileset()
        with pytest.raises(ValueError):
            WFCGrid(ts, 5, 5, selection="bogus")

    def test_lexical_picks_first_uncollapsed(self):
        ts = create_terrain_tileset()
        grid = WFCGrid(ts, 4, 4, seed=1, selection=SelectionStrategy.LEXICAL)
        # Before any step the first cell should be selectable.
        cell = grid._find_lexical()
        assert cell == (0, 0)


# --------------------------------------------------------------------------- #
# Overlap model
# --------------------------------------------------------------------------- #
class TestOverlapModel:
    def test_extract_patterns(self):
        sample = [["a", "b"], ["b", "a"]]
        model = OverlapModel(sample, n=2)
        assert len(model.patterns) > 0

    def test_generate(self):
        sample = [
            ["~", "~", ".", "#"],
            [".", "#", "#", "T"],
            ["#", "T", "T", "^"],
        ]
        model = OverlapModel(sample, n=2)
        result = model.generate(width=10, height=6, seed=1)
        # May be None if it fails; just ensure no exception.
        if result is not None:
            assert len(result) == 6
            assert all(len(r) == 10 for r in result)

    def test_n_validation(self):
        sample = [["a"]]
        with pytest.raises(ValueError):
            OverlapModel(sample, n=2, periodic=False)
        with pytest.raises(ValueError):
            OverlapModel(sample, n=0)

    def test_jagged_sample(self):
        with pytest.raises(ValueError):
            OverlapModel([["a", "b"], ["c"]], n=1)

    def test_empty_sample(self):
        with pytest.raises(ValueError):
            OverlapModel([], n=1)


# --------------------------------------------------------------------------- #
# Renderer
# --------------------------------------------------------------------------- #
class TestRenderer:
    def test_plain(self):
        grid = [["a", "b"], ["c", "d"]]
        out = Renderer.render_plain(grid)
        assert "a" in out

    def test_colored(self):
        grid = [["floor", "wall"]]
        out = Renderer.render_colored(grid)
        assert "\033[" in out  # has ANSI codes

    def test_html(self):
        grid = [["floor", "wall"]]
        out = Renderer.render_html(grid)
        assert "<table>" in out
        assert "</html>" in out

    def test_svg(self):
        grid = [["floor", "wall"]]
        out = Renderer.render_svg(grid)
        assert "<svg" in out
        assert "</svg>" in out

    def test_empty_grid_svg(self):
        out = Renderer.render_svg([])
        assert "<svg" in out

    def test_png_without_pillow(self):
        # Should return None gracefully if Pillow is absent; if present, bytes.
        out = Renderer.render_png([["floor"]], cell_size=10)
        assert out is None or isinstance(out, (bytes, bytearray))

    def test_unknown_symbol_fallback(self):
        assert Renderer._get_symbol("zzz") == "z"
        assert Renderer._get_symbol("") == "?"


# --------------------------------------------------------------------------- #
# Presets
# --------------------------------------------------------------------------- #
class TestPresets:
    @pytest.mark.parametrize(
        "name,factory",
        [
            ("terrain", create_terrain_tileset),
            ("dungeon", create_dungeon_tileset),
            ("city", create_city_tileset),
            ("circuit", create_circuit_tileset),
            ("maze", create_maze_tileset),
            ("village", create_village_tileset),
            ("islands", create_islands_tileset),
        ],
    )
    def test_preset_has_tiles_and_runs(self, name, factory):
        ts = factory()
        assert len(ts) > 0
        # Validate constraints reference real tiles.
        warnings = ts.validate()
        ref_warnings = [w for w in warnings if "unknown tile" in w]
        assert ref_warnings == [], f"{name} has unknown tile refs: {ref_warnings}"
        grid = WFCGrid(ts, 10, 6, seed=42)
        assert grid.run()
        result = grid.get_result()
        assert result is not None

    def test_village_unique_tiles(self):
        ts = create_village_tileset()
        assert "building" in ts
        assert "tree" in ts
        assert "fountain" in ts

    def test_islands_unique_tiles(self):
        ts = create_islands_tileset()
        assert "lava" in ts
        assert "ice" in ts


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
class TestConfig:
    def test_defaults(self):
        cfg = WFCConfig()
        assert cfg.width == 30
        assert cfg.mode == "terrain"

    def test_validate_bad_dims(self):
        cfg = WFCConfig(width=0)
        with pytest.raises(ValueError):
            cfg.validate()

    def test_validate_overlap_requires_sample(self):
        cfg = WFCConfig(mode="overlap")
        with pytest.raises(ValueError):
            cfg.validate()

    def test_validate_custom_requires_tileset(self):
        cfg = WFCConfig(mode="custom")
        with pytest.raises(ValueError):
            cfg.validate()

    def test_json_roundtrip(self):
        cfg = WFCConfig(mode="dungeon", width=12, height=8, seed=7, stats=True)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            cfg.to_json(path)
            loaded = WFCConfig.from_json(path)
            assert loaded.mode == "dungeon"
            assert loaded.width == 12
            assert loaded.seed == 7
        finally:
            os.unlink(path)

    def test_override(self):
        cfg = WFCConfig()
        cfg2 = cfg.override(width=50, seed=99)
        assert cfg2.width == 50
        assert cfg2.seed == 99
        assert cfg.width == 30  # original unchanged

    def test_from_dict_ignores_unknown_keys(self):
        cfg = WFCConfig.from_dict({"width": 5, "bogus": "x"})
        assert cfg.width == 5
        assert cfg.extra == {"bogus": "x"}

    def test_selection_validation(self):
        cfg = WFCConfig(selection="nonsense")
        with pytest.raises(ValueError):
            cfg.validate()


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
class TestCLI:
    def _run(self, argv):
        from wfc_generator.cli import main
        import contextlib

        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                main(argv)
            return 0, buf.getvalue()
        except SystemExit as e:
            return e.code, buf.getvalue()

    def test_terrain_cli(self):
        code, out = self._run(["terrain", "--width", "10", "--height", "5", "--seed", "1"])
        assert code == 0
        assert out.strip() != ""

    def test_village_cli(self):
        code, out = self._run(["village", "--width", "8", "--height", "4", "--seed", "2"])
        assert code == 0

    def test_list_presets(self):
        code, out = self._run(["list-presets"])
        assert code == 0
        assert "terrain" in out
        assert "village" in out
        assert "islands" in out

    def test_serialize_stdout(self):
        code, out = self._run(["serialize", "--preset", "maze", "--width", "5", "--height", "3", "--seed", "1"])
        assert code == 0
        data = json.loads(out)
        assert data["width"] == 5
        assert data["height"] == 3

    def test_custom_cli(self):
        data = {
            "tiles": [
                {"name": "a", "weight": 1, "symbol": "a",
                 "constraints": {"top": ["a"], "right": ["a"], "bottom": ["a"], "left": ["a"]}},
            ]
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            code, out = self._run(["custom", "--tileset", path, "--width", "4", "--height", "3", "--symmetrize"])
            assert code == 0
        finally:
            os.unlink(path)

    def test_validate_tileset_ok(self):
        data = {"tiles": [{"name": "a", "weight": 1, "symbol": "a",
                            "constraints": {"top": ["a"], "right": ["a"], "bottom": ["a"], "left": ["a"]}}]}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            code, out = self._run(["validate-tileset", path])
            assert "OK" in out
        finally:
            os.unlink(path)


# --------------------------------------------------------------------------- #
# Backward compatibility with legacy wfc.py shim
# --------------------------------------------------------------------------- #
class TestBackwardCompat:
    def test_wfc_shim_exports(self):
        import wfc
        assert wfc.Tile is Tile
        assert wfc.TileSet is TileSet
        assert wfc.WFCGrid is WFCGrid
        assert wfc.OverlapModel is OverlapModel
        assert wfc.Renderer is Renderer
        assert wfc.GenerationStats is GenerationStats
        assert wfc.create_terrain_tileset is create_terrain_tileset
        assert hasattr(wfc, "__version__")