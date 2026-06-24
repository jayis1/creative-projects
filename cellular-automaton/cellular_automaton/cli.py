"""CLI for the cellular automaton simulator.

Usage examples::

    # 1D elementary rule
    cellular-automaton run --rule Rule30 --width 80 --steps 40 --seed center

    # 2D Game of Life with a glider
    cellular-automaton run --rule GameOfLife --width 40 --height 20 \
        --steps 100 --pattern glider --format ascii

    # Render to SVG
    cellular-automaton render --rule Rule110 --width 100 --steps 50 \
        --format svg --output rule110.svg

    # List builtin rules / patterns
    cellular-automaton rules
    cellular-automaton patterns
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional

import numpy as np

from .engine import CellularAutomaton, Boundary
from .rules import RULES, get_rule, parse_bx_sx_notation, Rule
from .patterns import PATTERNS, get_pattern, place_pattern, parse_rle
from .visualizer import render_ascii, render_svg, render_ppm, render_png, render_ansi


def _build_ca(args: argparse.Namespace) -> CellularAutomaton:
    rule = get_rule(args.rule)
    height = args.height if args.height else (None if rule.dimensions == 1 else 20)
    ca = CellularAutomaton(
        rule,
        width=args.width,
        height=height,
        boundary=args.boundary,
    )
    # Initial state
    if args.random is not None:
        ca.randomize(args.random, seed=args.seed)
    elif args.pattern:
        pat = get_pattern(args.pattern)
        place_pattern(ca, pat, x=args.px, y=args.py)
    elif args.rle:
        pat = parse_rle(args.rle)
        place_pattern(ca, pat, x=args.px, y=args.py)
    else:
        if rule.dimensions == 1:
            ca.center_seed()
    return ca


def cmd_run(args: argparse.Namespace) -> None:
    ca = _build_ca(args)
    fmt = args.format
    if fmt == "ansi":
        print(render_ansi(ca.grid))
        print()
    else:
        print(render_ascii(ca.grid))

    for _ in range(args.steps):
        ca.step()
        if fmt == "ansi":
            print(render_ansi(ca.grid))
        else:
            print(render_ascii(ca.grid))
        print()


def cmd_render(args: argparse.Namespace) -> None:
    ca = _build_ca(args)
    ca.step(args.steps)
    fmt = args.format
    if fmt == "svg":
        render_svg(ca.grid, path=args.output)
    elif fmt == "ppm":
        render_ppm(ca.grid, args.output)
    elif fmt == "png":
        render_png(ca.grid, args.output)
    elif fmt == "ascii":
        with open(args.output, "w") as f:
            f.write(render_ascii(ca.grid) + "\n")
    else:
        print(render_ascii(ca.grid))
        return
    print(f"Rendered to {args.output}")


def cmd_rules(args: argparse.Namespace) -> None:
    # Show named (non-RuleN) rules first, then elementary rules.
    named = [k for k in RULES if not k.startswith("Rule")]
    print("Named rules:")
    for k in sorted(named):
        print(f"  {k}")
    print(f"\nElementary rules: Rule0 .. Rule255 (256 total)")
    print(f"\nCustom Bxx/Sxx notation supported, e.g. B36/S23")


def cmd_patterns(args: argparse.Namespace) -> None:
    print("Patterns:")
    for k in sorted(PATTERNS):
        print(f"  {k}: {len(PATTERNS[k])} cells")


def cmd_info(args: argparse.Namespace) -> None:
    rule = get_rule(args.rule)
    print(f"Rule: {rule.name}")
    print(f"Type: {type(rule).__name__}")
    print(f"Dimensions: {rule.dimensions}")
    print(f"Radius: {rule.radius}")
    from .rules import GameOfLifeRule, ElementaryRule
    if isinstance(rule, ElementaryRule):
        print(f"Number: {rule.number}")
        print("Wolfram table:")
        print(rule.wolfram_table())
    elif isinstance(rule, GameOfLifeRule):
        print(f"Rule string: {rule.rule_string()}")


def cmd_simulate(args: argparse.Namespace) -> None:
    """Run a CA with statistics and optional cycle detection."""
    ca = _build_ca(args)
    stats = ca.run(args.steps, detect_cycles=not args.no_cycle_detect)
    print(f"Steps run:    {stats.steps}")
    print(f"Final alive:  {stats.final_alive}")
    print(f"Max alive:    {stats.max_alive}")
    print(f"Min alive:    {stats.min_alive}")
    print(f"Stable:       {stats.stable}")
    print(f"Cycle found:  {stats.cycle_detected}")
    if stats.cycle_detected:
        print(f"Cycle length: {stats.cycle_length}")
    if args.json:
        import json as _json
        print(_json.dumps(stats.to_dict(), indent=2))


def cmd_spacetime(args: argparse.Namespace) -> None:
    """Run a 1D CA and render its spacetime diagram."""
    ca = _build_ca(args)
    ca.step(args.steps)
    st = ca.get_spacetime_array()
    if args.format == "ascii":
        out = render_ascii(st, on_char=args.on_char, off_char=args.off_char)
        if args.output:
            with open(args.output, "w") as f:
                f.write(out + "\n")
        else:
            print(out)
    elif args.format == "svg":
        from .visualizer import render_spacetime_svg
        render_spacetime_svg(st, path=args.output or "spacetime.svg")
        print(f"Rendered to {args.output or 'spacetime.svg'}")
    elif args.format == "ppm":
        from .visualizer import render_spacetime_ppm
        render_spacetime_ppm(st, args.output or "spacetime.ppm")
        print(f"Rendered to {args.output or 'spacetime.ppm'}")


def cmd_animate(args: argparse.Namespace) -> None:
    """Render an animation as a sequence of image frames."""
    ca = _build_ca(args)
    from .visualizer import render_animation_frames
    paths = render_animation_frames(
        ca, args.steps, args.output, fmt=args.format, cell_size=args.cell_size
    )
    print(f"Wrote {len(paths)} frames to {args.output}/")


def cmd_save(args: argparse.Namespace) -> None:
    """Run a CA and save its state to JSON."""
    ca = _build_ca(args)
    ca.step(args.steps)
    ca.save(args.output)
    print(f"Saved state to {args.output} (step {ca.step_count})")


def cmd_load(args: argparse.Namespace) -> None:
    """Load a CA state from JSON and print it."""
    ca = CellularAutomaton.load(args.input)
    print(f"Loaded: {ca}")
    print(render_ascii(ca.grid))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cellular-automaton",
        description="1D & 2D cellular automaton simulator.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    # Common rule/initial args
    def add_common(sp):
        sp.add_argument("--rule", required=True, help="Rule name (e.g. Rule30, GameOfLife, B36/S23)")
        sp.add_argument("--width", type=int, default=80, help="Grid width")
        sp.add_argument("--height", type=int, default=None, help="Grid height (2D only)")
        sp.add_argument("--boundary", default="periodic",
                        choices=[b.value for b in Boundary],
                        help="Boundary condition")
        sp.add_argument("--random", type=float, default=None, metavar="DENSITY",
                        help="Random initial state with given density")
        sp.add_argument("--seed", type=int, default=None, help="Random seed")
        sp.add_argument("--pattern", default=None, help="Named pattern to place")
        sp.add_argument("--rle", default=None, help="RLE pattern string")
        sp.add_argument("--px", type=int, default=5, help="Pattern x offset")
        sp.add_argument("--py", type=int, default=5, help="Pattern y offset")

    sp_run = sub.add_parser("run", help="Run and print each step")
    add_common(sp_run)
    sp_run.add_argument("--steps", type=int, default=20)
    sp_run.add_argument("--format", default="ascii", choices=["ascii", "ansi"])
    sp_run.set_defaults(func=cmd_run)

    sp_render = sub.add_parser("render", help="Render final state to a file")
    add_common(sp_render)
    sp_render.add_argument("--steps", type=int, default=20)
    sp_render.add_argument("--format", default="svg", choices=["svg", "ppm", "png", "ascii"])
    sp_render.add_argument("--output", "-o", default="output.svg")
    sp_render.set_defaults(func=cmd_render)

    sp_rules = sub.add_parser("rules", help="List builtin rules")
    sp_rules.set_defaults(func=cmd_rules)

    sp_patterns = sub.add_parser("patterns", help="List builtin patterns")
    sp_patterns.set_defaults(func=cmd_patterns)

    sp_info = sub.add_parser("info", help="Show details about a rule")
    sp_info.add_argument("--rule", required=True)
    sp_info.set_defaults(func=cmd_info)

    sp_sim = sub.add_parser("simulate", help="Run with statistics & cycle detection")
    add_common(sp_sim)
    sp_sim.add_argument("--steps", type=int, default=100)
    sp_sim.add_argument("--no-cycle-detect", action="store_true")
    sp_sim.add_argument("--json", action="store_true", help="Print stats as JSON")
    sp_sim.set_defaults(func=cmd_simulate)

    sp_st = sub.add_parser("spacetime", help="Render 1D spacetime diagram")
    add_common(sp_st)
    sp_st.add_argument("--steps", type=int, default=40)
    sp_st.add_argument("--format", default="ascii", choices=["ascii", "svg", "ppm"])
    sp_st.add_argument("--output", "-o", default=None)
    sp_st.add_argument("--on-char", default="█")
    sp_st.add_argument("--off-char", default=" ")
    sp_st.set_defaults(func=cmd_spacetime)

    sp_anim = sub.add_parser("animate", help="Render animation frames")
    add_common(sp_anim)
    sp_anim.add_argument("--steps", type=int, default=30)
    sp_anim.add_argument("--format", default="ppm", choices=["ppm", "png"])
    sp_anim.add_argument("--output", default="frames")
    sp_anim.add_argument("--cell-size", type=int, default=4)
    sp_anim.set_defaults(func=cmd_animate)

    sp_save = sub.add_parser("save", help="Save state to JSON")
    add_common(sp_save)
    sp_save.add_argument("--steps", type=int, default=10)
    sp_save.add_argument("--output", "-o", required=True)
    sp_save.set_defaults(func=cmd_save)

    sp_load = sub.add_parser("load", help="Load state from JSON")
    sp_load.add_argument("input")
    sp_load.set_defaults(func=cmd_load)

    return p


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())