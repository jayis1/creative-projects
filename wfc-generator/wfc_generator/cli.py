"""Command-line interface for the WFC generator."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from typing import List, Optional

from . import __version__
from .config import WFCConfig
from .grid import SelectionStrategy, WFCGrid
from .logging_utils import setup_logging
from .overlap import OverlapModel
from .renderer import Renderer
from .tileset import TileSet
from .presets import (
    create_terrain_tileset,
    create_dungeon_tileset,
    create_city_tileset,
    create_circuit_tileset,
    create_maze_tileset,
    create_village_tileset,
    create_islands_tileset,
)

logger = logging.getLogger("wfc_generator.cli")

PRESET_FACTORIES = {
    "terrain": create_terrain_tileset,
    "dungeon": create_dungeon_tileset,
    "city": create_city_tileset,
    "circuit": create_circuit_tileset,
    "maze": create_maze_tileset,
    "village": create_village_tileset,
    "islands": create_islands_tileset,
}


# --------------------------------------------------------------------------- #
# Argument parsing
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wfc",
        description=(
            "Wave Function Collapse procedural generator — generate maps, "
            "dungeons, cities, circuits, mazes, villages and islands."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_epilog(),
    )
    parser.add_argument("--version", action="version", version=f"wfc {__version__}")
    parser.add_argument(
        "-v", "--verbose", action="count", default=0,
        help="Increase logging verbosity (-v=INFO, -vv=DEBUG).",
    )

    sub = parser.add_subparsers(dest="mode", metavar="<mode>")

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--width", type=int, default=30, help="Grid width (default: 30)")
        p.add_argument("--height", type=int, default=20, help="Grid height (default: 20)")
        p.add_argument("--seed", type=int, default=None, help="Random seed")
        p.add_argument("--periodic", action="store_true", help="Periodic (toroidal) boundaries")
        p.add_argument("--backtrack-limit", type=int, default=10,
                       help="Max full restarts on contradiction (default: 10)")
        p.add_argument(
            "--selection", choices=[s.value for s in SelectionStrategy],
            default=SelectionStrategy.MIN_ENTROPY.value,
            help="Cell selection strategy (default: min_entropy)",
        )
        p.add_argument("--cache-entropy", action="store_true",
                       help="Maintain an entropy cache (faster on large grids)")
        p.add_argument("--output", type=str, default=None,
                       help="Output file (.html/.svg/.png/.txt/.json)")
        p.add_argument("--cell-size", type=int, default=16,
                       help="Cell size in pixels for html/svg/png (default: 16)")
        p.add_argument("--stats", action="store_true", help="Print generation statistics")
        p.add_argument("--config", type=str, default=None,
                       help="Load base config from a JSON/YAML/TOML file")

    for name in PRESET_FACTORIES:
        p = sub.add_parser(name, help=f"Generate a {name} map")
        add_common(p)

    overlap_p = sub.add_parser("overlap", help="Generate from a sample pattern (overlap model)")
    add_common(overlap_p)
    overlap_p.add_argument("--sample", type=str, required=True, help="Sample file (JSON)")
    overlap_p.add_argument("--n", type=int, default=2, help="Pattern size (default: 2)")

    custom_p = sub.add_parser("custom", help="Generate from a custom tile set (JSON)")
    add_common(custom_p)
    custom_p.add_argument("--tileset", type=str, required=True, help="Tile set JSON file")
    custom_p.add_argument("--symmetrize", action="store_true",
                           help="Auto-symmetrize constraints")

    run_p = sub.add_parser("run", help="Run from a config file (auto-detects mode)")
    run_p.add_argument("config", type=str, help="Config file (JSON/YAML/TOML)")
    run_p.add_argument("--output", type=str, default=None, help="Override output file")

    list_p = sub.add_parser("list-presets", help="List available preset tile sets")
    list_p.add_argument("--detail", action="store_true", help="Show tile details")

    val_p = sub.add_parser("validate-tileset", help="Validate a JSON tile set file")
    val_p.add_argument("tileset", type=str, help="Tile set JSON file")
    val_p.add_argument("--symmetrize", action="store_true",
                       help="Symmetrize before validating")

    ser_p = sub.add_parser("serialize", help="Generate and serialize the grid to JSON")
    ser_p.add_argument("--preset", choices=list(PRESET_FACTORIES), required=True,
                       help="Preset tile set to use")
    add_common(ser_p)

    return parser


def _epilog() -> str:
    return """
examples:
  # Generate a 40x25 terrain map with a fixed seed
  wfc terrain --width 40 --height 25 --seed 42

  # Generate a dungeon and write SVG output
  wfc dungeon --width 30 --height 20 --output dungeon.svg

  # Generate a village using the MRV selection strategy
  wfc village --width 25 --height 20 --selection mrv --stats

  # Generate from a sample using the overlap model
  wfc overlap --sample sample.json --width 20 --height 20 --n 3

  # Generate from a custom tile set, auto-symmetrizing constraints
  wfc custom --tileset tiles.json --width 20 --height 12 --symmetrize

  # Run from a config file (mode is read from the config)
  wfc run config.yaml --output out.html

  # List available presets
  wfc list-presets --detail

  # Validate a custom tile set
  wfc validate-tileset tiles.json
"""


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _log_level(verbose: int) -> str:
    if verbose >= 2:
        return "DEBUG"
    if verbose == 1:
        return "INFO"
    return "WARNING"


def _apply_config_to_args(args: argparse.Namespace) -> argparse.Namespace:
    """Merge a --config file into the parsed args (CLI args take priority)."""
    if not getattr(args, "config", None):
        return args
    cfg = WFCConfig.from_file(args.config)
    # CLI overrides config only when explicitly set; argparse defaults make this
    # tricky, so we override only non-default values via the parser defaults.
    parser = build_parser()
    defaults = vars(parser.parse_args([args.mode] if args.mode else []))
    for key, value in cfg.to_dict().items():
        if key in ("extra",):
            continue
        current = getattr(args, key, None)
        default = defaults.get(key)
        # If the current value equals the parser default, allow config to set it.
        if current == default or current is None:
            setattr(args, key, value)
    return args


def _render_output(result, args) -> None:
    if args.output:
        ext = args.output.rsplit(".", 1)[-1].lower()
        if ext == "json":
            grid_obj = getattr(args, "_grid_obj", None)
            if grid_obj is not None:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(grid_obj.to_json())
            else:
                with open(args.output, "w", encoding="utf-8") as f:
                    json.dump({"grid": result}, f, indent=2)
            print(f"Output written to {args.output}")
            return
        if ext == "html":
            content = Renderer.render_html(result, cell_size=args.cell_size, title=f"WFC {args.mode}")
        elif ext == "svg":
            content = Renderer.render_svg(result, cell_size=args.cell_size, title=f"WFC {args.mode}")
        elif ext == "png":
            png_bytes = Renderer.render_png(result, cell_size=args.cell_size, title=f"WFC {args.mode}")
            if png_bytes is None:
                print("PNG rendering requires Pillow. Install with: pip install Pillow", file=sys.stderr)
                sys.exit(1)
            with open(args.output, "wb") as f:
                f.write(png_bytes)
            print(f"Output written to {args.output}")
            return
        else:
            content = Renderer.render_plain(result)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Output written to {args.output}")
    else:
        print(Renderer.render_colored(result))
        print()
        print(Renderer.render_plain(result))


def _run_preset(args: argparse.Namespace, grid_obj: WFCGrid, result) -> None:
    args._grid_obj = grid_obj
    if args.stats:
        print(f"Stats: {grid_obj.stats}", file=sys.stderr)
    _render_output(result, args)
    if args.stats and not args.output:
        print(f"Stats: {grid_obj.stats}")


# --------------------------------------------------------------------------- #
# Subcommand handlers
# --------------------------------------------------------------------------- #
def cmd_generate_preset(args: argparse.Namespace) -> None:
    args = _apply_config_to_args(args)
    tileset = PRESET_FACTORIES[args.mode]()
    for w in tileset.validate():
        print(f"Warning: {w}", file=sys.stderr)
    grid_obj = WFCGrid(
        tileset,
        args.width,
        args.height,
        periodic=args.periodic,
        seed=args.seed,
        backtrack_limit=args.backtrack_limit,
        selection=SelectionStrategy(args.selection),
        cache_entropy=args.cache_entropy,
    )
    if not grid_obj.run():
        print("Generation failed: contradiction encountered!", file=sys.stderr)
        if args.stats:
            print(f"Stats: {grid_obj.stats}", file=sys.stderr)
        sys.exit(1)
    result = grid_obj.get_result()
    if result is None:
        print("Generation failed!", file=sys.stderr)
        sys.exit(1)
    _run_preset(args, grid_obj, result)


def cmd_overlap(args: argparse.Namespace) -> None:
    args = _apply_config_to_args(args)
    try:
        with open(args.sample, "r", encoding="utf-8") as f:
            sample = json.load(f)
    except Exception as e:
        print(f"Error loading sample file: {e}", file=sys.stderr)
        sys.exit(1)
    model = OverlapModel(sample, n=args.n)
    grid_obj = WFCGrid(
        model.tile_set,
        args.width,
        args.height,
        periodic=args.periodic,
        seed=args.seed,
        backtrack_limit=args.backtrack_limit,
        selection=SelectionStrategy(args.selection),
        cache_entropy=args.cache_entropy,
    )
    if not grid_obj.run():
        print("Generation failed: contradiction encountered!", file=sys.stderr)
        if args.stats:
            print(f"Stats: {grid_obj.stats}", file=sys.stderr)
        sys.exit(1)
    result_grid = grid_obj.get_result()
    if result_grid is None:
        print("Generation failed!", file=sys.stderr)
        sys.exit(1)
    # Convert pattern tiles back to a symbol grid.
    result: List[List[str]] = []
    for y in range(args.height):
        row = []
        for x in range(args.width):
            tile_name = result_grid[y][x]
            if tile_name is None:
                row.append("?")
                continue
            tile = model.tile_set.get_tile(tile_name)
            row.append(model._pattern_at(tile.data, 0, 0))
        result.append(row)
    args._grid_obj = grid_obj
    if args.stats:
        print(f"Stats: {grid_obj.stats}", file=sys.stderr)
    _render_output(result, args)


def cmd_custom(args: argparse.Namespace) -> None:
    args = _apply_config_to_args(args)
    try:
        tileset = TileSet.from_json(args.tileset)
    except Exception as e:
        print(f"Error loading tile set: {e}", file=sys.stderr)
        sys.exit(1)
    if args.symmetrize:
        tileset.make_all_symmetric()
    for w in tileset.validate():
        print(f"Warning: {w}", file=sys.stderr)
    grid_obj = WFCGrid(
        tileset,
        args.width,
        args.height,
        periodic=args.periodic,
        seed=args.seed,
        backtrack_limit=args.backtrack_limit,
        selection=SelectionStrategy(args.selection),
        cache_entropy=args.cache_entropy,
    )
    if not grid_obj.run():
        print("Generation failed: contradiction encountered!", file=sys.stderr)
        if args.stats:
            print(f"Stats: {grid_obj.stats}", file=sys.stderr)
        sys.exit(1)
    result = grid_obj.get_result()
    if result is None:
        print("Generation failed!", file=sys.stderr)
        sys.exit(1)
    _run_preset(args, grid_obj, result)


def cmd_run(args: argparse.Namespace) -> None:
    cfg = WFCConfig.from_file(args.config)
    if args.output:
        cfg.output = args.output
    cfg.validate()
    # Build a synthetic namespace and dispatch.
    ns = argparse.Namespace(
        mode=cfg.mode,
        width=cfg.width,
        height=cfg.height,
        seed=cfg.seed,
        periodic=cfg.periodic,
        backtrack_limit=cfg.backtrack_limit,
        selection=cfg.selection,
        cache_entropy=cfg.cache_entropy,
        output=cfg.output,
        cell_size=cfg.cell_size,
        stats=cfg.stats,
        sample=cfg.sample,
        n=cfg.n,
        tileset=cfg.tileset,
        symmetrize=cfg.symmetrize,
        config=None,
    )
    if cfg.mode == "overlap":
        cmd_overlap(ns)
    elif cfg.mode == "custom":
        cmd_custom(ns)
    elif cfg.mode in PRESET_FACTORIES:
        cmd_generate_preset(ns)
    else:
        print(f"Unknown mode {cfg.mode!r} in config file", file=sys.stderr)
        sys.exit(1)


def cmd_list_presets(args: argparse.Namespace) -> None:
    print("Available preset tile sets:")
    for name, factory in PRESET_FACTORIES.items():
        ts = factory()
        if args.detail:
            print(f"\n  {name} ({len(ts)} tiles):")
            for tile in sorted(ts.tiles.values(), key=lambda t: t.name):
                print(f"    - {tile.name:16s} weight={tile.weight:<5} symbol={tile.data!r}")
        else:
            print(f"  {name:12s}  ({len(ts)} tiles)")


def cmd_validate_tileset(args: argparse.Namespace) -> None:
    try:
        tileset = TileSet.from_json(args.tileset)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    if args.symmetrize:
        tileset.make_all_symmetric()
    warnings = tileset.validate()
    if warnings:
        print(f"{len(warnings)} warning(s):")
        for w in warnings:
            print(f"  - {w}")
        sys.exit(1)
    else:
        print(f"OK: {len(tileset)} tiles, no warnings.")


def cmd_serialize(args: argparse.Namespace) -> None:
    args.mode = args.preset  # preset name
    tileset = PRESET_FACTORIES[args.preset]()
    grid_obj = WFCGrid(
        tileset,
        args.width,
        args.height,
        periodic=args.periodic,
        seed=args.seed,
        backtrack_limit=args.backtrack_limit,
        selection=SelectionStrategy(args.selection),
        cache_entropy=args.cache_entropy,
    )
    if not grid_obj.run():
        print("Generation failed: contradiction encountered!", file=sys.stderr)
        sys.exit(1)
    args._grid_obj = grid_obj
    result = grid_obj.get_result()
    if result is None:
        print("Generation failed!", file=sys.stderr)
        sys.exit(1)
    text = grid_obj.to_json()
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Serialized grid written to {args.output}")
    else:
        print(text)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(level=_log_level(args.verbose))

    if args.mode is None:
        parser.print_help()
        sys.exit(1)

    if args.mode in PRESET_FACTORIES:
        cmd_generate_preset(args)
    elif args.mode == "overlap":
        cmd_overlap(args)
    elif args.mode == "custom":
        cmd_custom(args)
    elif args.mode == "run":
        cmd_run(args)
    elif args.mode == "list-presets":
        cmd_list_presets(args)
    elif args.mode == "validate-tileset":
        cmd_validate_tileset(args)
    elif args.mode == "serialize":
        cmd_serialize(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()