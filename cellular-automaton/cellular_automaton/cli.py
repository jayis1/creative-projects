"""CLI for the cellular automaton simulator.

Full argparse-based CLI with 15 subcommands:

    run        — run and print each step
    render     — render final state to a file
    simulate   — run with statistics & cycle detection
    spacetime  — render 1D spacetime diagram
    animate    — render animation frames
    save       — save state to JSON
    load       — load state from JSON
    rules      — list builtin rules
    patterns   — list builtin patterns
    info       — show details about a rule
    classify   — Wolfram classification of a 1D rule
    entropy    — compute entropy of a CA state
    sweep      — parameter sweep over rule parameters
    config     — run from a config file
    multistate — run a multi-state CA (Wireworld, Brian's Brain, etc.)

Usage examples::

    # 1D elementary rule
    cellular-automaton run --rule Rule30 --width 80 --steps 40 --seed center

    # 2D Game of Life with a glider
    cellular-automaton run --rule GameOfLife --width 40 --height 20 \\
        --steps 100 --pattern glider --format ascii

    # Multi-state CA
    cellular-automaton multistate --rule Wireworld --width 40 --height 20 \\
        --random 0.3 --seed 42 --steps 50

    # Run from config file
    cellular-automaton config simulation.yaml

    # Classify elementary rules
    cellular-automaton classify --rule 30
    cellular-automaton classify --all

    # List builtin rules / patterns
    cellular-automaton rules
    cellular-automaton patterns
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Optional

import numpy as np

from .engine import CellularAutomaton, Boundary
from .rules import RULES, get_rule, parse_bx_sx_notation, Rule
from .patterns import PATTERNS, get_pattern, place_pattern, parse_rle, load_rle_file
from .visualizer import (
    render_ascii, render_svg, render_ppm, render_png, render_ansi,
    render_gif, render_multistate_gif,
)
from .multistate import (
    MULTISTATE_RULES, get_multistate_rule, is_multistate_rule,
    WireworldRule, BriansBrainRule, ForestFireRule,
)
from .ltl import (
    LargerThanLifeRule, parse_ltl_notation, LTL_PRESETS,
)
from .continuous import (
    GrayScott, FitzHughNagumo, GRAY_SCOTT_PRESETS, CONTINUOUS_MODELS,
    get_continuous_model, is_continuous_model, render_continuous_ascii,
)

logger = logging.getLogger("cellular_automaton")


def _build_ca(args: argparse.Namespace) -> CellularAutomaton:
    """Build a CA from CLI arguments."""
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


def _build_multistate_ca(args: argparse.Namespace) -> CellularAutomaton:
    """Build a multi-state CA from CLI arguments."""
    # Parse extra params from --params if provided.
    kwargs = {}
    if args.params:
        for kv in args.params.split(","):
            key, _, val = kv.partition("=")
            key = key.strip()
            val = val.strip()
            try:
                val = float(val)
                if val == int(val):
                    val = int(val)
            except ValueError:
                pass  # keep as string
            kwargs[key] = val

    rule = get_multistate_rule(args.rule, **kwargs)
    height = args.height if args.height else 20
    ca = CellularAutomaton(
        rule,
        width=args.width,
        height=height,
        boundary=args.boundary,
    )
    # Set RNG for stochastic rules.
    ca.set_rng(args.seed)
    # Initial state
    if args.random is not None:
        ca.randomize(args.random, seed=args.seed)
    elif args.pattern:
        # For multi-state, "random" with a pattern doesn't make sense,
        # but we can place a binary pattern.
        pat = get_pattern(args.pattern)
        place_pattern(ca, pat, x=args.px, y=args.py)
    elif args.random_states is not None:
        # Random multi-state: each cell gets a random state in [0, n_states).
        rng = np.random.default_rng(args.seed)
        n = rule.n_states
        ca.grid = rng.integers(0, n, size=ca.grid.shape).astype(np.uint8)
        ca.step_count = 0
        ca.history.clear()
        ca.spacetime.clear()
    return ca


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def cmd_run(args: argparse.Namespace) -> None:
    """Run and print each step."""
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
    """Render final state to a file."""
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
    """List builtin rules."""
    named = [k for k in RULES if not k.startswith("Rule")]
    print("Named 2D rules:")
    for k in sorted(named):
        print(f"  {k}")
    print(f"\nElementary 1D rules: Rule0 .. Rule255 (256 total)")
    print(f"\nCustom Bxx/Sxx notation supported, e.g. B36/S23")

    print(f"\nMulti-state rules:")
    for k in sorted(MULTISTATE_RULES):
        rule = MULTISTATE_RULES[k]
        print(f"  {k}: {rule.n_states} states")

    from .ltl import LTL_PRESETS
    print(f"\nLarger-than-Life (LtL) rules:")
    for k in sorted(LTL_PRESETS):
        rule = LTL_PRESETS[k]
        print(f"  {k}: {rule.rule_string()}")

    from .continuous import CONTINUOUS_MODELS, GRAY_SCOTT_PRESETS
    print(f"\nContinuous CA models:")
    for k in sorted(CONTINUOUS_MODELS):
        print(f"  {k}")
    print(f"\nGray-Scott presets:")
    for k in sorted(GRAY_SCOTT_PRESETS):
        p = GRAY_SCOTT_PRESETS[k]
        print(f"  {k}: F={p['F']}, k={p['k']}")


def cmd_patterns(args: argparse.Namespace) -> None:
    """List builtin patterns."""
    print("Patterns:")
    for k in sorted(PATTERNS):
        print(f"  {k}: {len(PATTERNS[k])} cells")


def cmd_info(args: argparse.Namespace) -> None:
    """Show details about a rule."""
    # Check multi-state first.
    if is_multistate_rule(args.rule):
        rule = get_multistate_rule(args.rule)
        print(f"Rule: {rule.name}")
        print(f"Type: {type(rule).__name__}")
        print(f"States: {rule.n_states}")
        print(f"Dimensions: {rule.dimensions}")
        print(f"Radius: {rule.radius}")
        colors = rule.state_colors()
        if colors:
            print("State colors:")
            for state, (r, g, b) in sorted(colors.items()):
                print(f"  State {state}: RGB({r}, {g}, {b})")
        return

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
        print(json.dumps(stats.to_dict(), indent=2))


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


def cmd_classify(args: argparse.Namespace) -> None:
    """Classify a 1D elementary rule using Wolfram's classification."""
    from .analysis import classify_elementary_rule

    if args.all:
        print(f"{'Rule':>6}  {'Class':>5}  {'Entropy':>8}  {'Density':>8}  {'Period':>6}  Description")
        print("-" * 90)
        for n in range(256):
            try:
                result = classify_elementary_rule(n, width=51, steps=100)
                period_str = str(result.period) if result.period else "-"
                print(f"  {n:>3}   {result.classification:>5}  "
                      f"{result.entropy:>8.4f}  {result.density:>8.4f}  "
                      f"{period_str:>6}  {result.description}")
            except Exception as e:
                print(f"  {n:>3}   ERROR: {e}")
    else:
        n = args.rule if isinstance(args.rule, int) else int(args.rule)
        result = classify_elementary_rule(n, width=args.width or 101, steps=args.steps or 200)
        print(f"Rule:         {result.rule_number}")
        print(f"Classification: {result.classification} — {result.description}")
        print(f"Entropy:      {result.entropy:.4f}")
        print(f"Density:      {result.density:.4f}")
        print(f"Stability:    {result.stability:.4f}")
        if result.period:
            print(f"Period:       {result.period}")


def cmd_entropy(args: argparse.Namespace) -> None:
    """Compute the entropy of a CA state."""
    from .analysis import shannon_entropy, spacetime_entropy

    ca = _build_ca(args)
    ca.step(args.steps)

    if args.spacetime:
        st = ca.get_spacetime_array()
        ent = spacetime_entropy(st)
        print(f"Spacetime entropy: {ent:.6f} bits/row (avg)")
    else:
        ent = shannon_entropy(ca.grid, block_size=args.block_size)
        print(f"Shannon entropy (block_size={args.block_size}): {ent:.6f} bits")


def cmd_sweep(args: argparse.Namespace) -> None:
    """Run a parameter sweep over rule parameters."""
    from .analysis import parameter_sweep

    # Parse parameter grid from JSON string.
    param_grid = json.loads(args.params)

    # Build rule factory.
    if args.rule == "ForestFire":
        rule_factory = lambda p, g: ForestFireRule(p=p, g=g)
    elif args.rule.startswith("B") and "/" in args.rule:
        # Parse Bxx/Sxx for a standard rule.
        from .rules import parse_bx_sx_notation
        parsed = parse_bx_sx_notation(args.rule)
        rule_factory = lambda **kw: parsed
    else:
        # For Life-like rules, sweep over density instead.
        # We'll use GameOfLife with random init at different densities.
        from .rules import get_rule
        base_rule = get_rule(args.rule)
        # If no parameters given, sweep over random density.
        if not param_grid:
            param_grid = {"density": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]}
        rule_factory = lambda **kw: base_rule

    results = parameter_sweep(
        rule_factory,
        param_grid,
        width=args.width,
        height=args.height or 50,
        steps=args.steps,
        seed=args.seed or 42,
    )
    print(f"{'Params':>40}  {'Alive':>6}  {'Density':>8}  {'Stable':>6}  {'Cycle':>5}  {'Entropy':>8}")
    print("-" * 100)
    for r in results:
        print(f"  {str(r.params):>38}  {r.final_alive:>6}  "
              f"{r.mean_density:>8.4f}  {str(r.stable):>6}  "
              f"{str(r.cycle_detected):>5}  {r.entropy:>8.4f}")


def cmd_config(args: argparse.Namespace) -> None:
    """Run from a config file."""
    from .config import CAConfig

    cfg = CAConfig.from_file(args.config_file)
    if args.output:
        cfg.output["path"] = args.output
    if args.format:
        cfg.output["format"] = args.format
    if args.steps is not None:
        cfg.steps = args.steps
    ca, result = cfg.run()
    print(f"Completed {ca.step_count} steps with rule {ca.rule.name}")
    if result and cfg.output.get("format") in ("ascii", "ansi"):
        print(result)


def cmd_multistate(args: argparse.Namespace) -> None:
    """Run a multi-state CA (Wireworld, Brian's Brain, Forest Fire, etc.)."""
    ca = _build_multistate_ca(args)
    fmt = args.format

    # Render initial state.
    _print_multistate(ca, fmt)
    print()

    for _ in range(args.steps):
        ca.step()
        _print_multistate(ca, fmt)
        print()


def _print_multistate(ca: CellularAutomaton, fmt: str) -> None:
    """Print a multi-state CA grid using state-aware rendering."""
    if fmt == "ascii":
        # Use digits for multi-state (0-9, then letters).
        chars = "0123456789ABCDEF"
        grid = ca.grid
        if grid.ndim == 1:
            grid = grid.reshape(1, -1)
        for row in grid:
            print("".join(chars[int(c) % len(chars)] if c else "." for c in row))
    elif fmt == "ansi":
        # Color-code by state.
        colors = ca.rule.state_colors() if hasattr(ca.rule, "state_colors") else {}
        if not colors:
            print(render_ansi(ca.grid))
            return
        grid = ca.grid
        if grid.ndim == 1:
            grid = grid.reshape(1, -1)
        RESET = "\033[0m"
        for row in grid:
            line = ""
            for cell in row:
                c = int(cell)
                if c in colors:
                    r, g, b = colors[c]
                    line += f"\033[48;2;{r};{g};{b}m  {RESET}"
                else:
                    line += "  "
            print(line)
    elif fmt == "ascii":
        print(render_ascii(ca.grid))
    else:
        print(render_ascii(ca.grid))


# --------------------------------------------------------------------------- #
# New commands: gif, rle-file, ltl, continuous
# --------------------------------------------------------------------------- #


def cmd_gif(args: argparse.Namespace) -> None:
    """Render a CA evolution as an animated GIF."""
    if is_multistate_rule(args.rule):
        ca = _build_multistate_ca(args)
        render_multistate_gif(
            ca, path=args.output, steps=args.steps,
            cell_size=args.cell_size, duration=args.duration,
        )
    else:
        ca = _build_ca(args)
        render_gif(
            ca, path=args.output, steps=args.steps,
            cell_size=args.cell_size, duration=args.duration,
        )
    print(f"Animated GIF written to {args.output} ({args.steps} frames)")


def cmd_rle_file(args: argparse.Namespace) -> None:
    """Load a pattern from an RLE file and run it."""
    pat = load_rle_file(args.rle_file)
    rule = get_rule(args.rule)
    height = args.height if args.height else (None if rule.dimensions == 1 else 30)
    ca = CellularAutomaton(
        rule, width=args.width, height=height, boundary=args.boundary,
    )
    place_pattern(ca, pat, x=args.px, y=args.py)
    ca.step(args.steps)
    fmt = args.format
    if fmt == "ansi":
        print(render_ansi(ca.grid))
    elif fmt == "svg":
        render_svg(ca.grid, path=args.output or "output.svg")
        print(f"Rendered to {args.output or 'output.svg'}")
    elif fmt == "png":
        render_png(ca.grid, args.output or "output.png")
        print(f"Rendered to {args.output or 'output.png'}")
    else:
        print(render_ascii(ca.grid))
    print(f"\nLoaded pattern with {len(pat)} cells from {args.rle_file}")


def cmd_ltl(args: argparse.Namespace) -> None:
    """Run a Larger-than-Life CA."""
    # Try preset registry first, then parse B/S/R notation.
    if args.rule in LTL_PRESETS:
        rule = LTL_PRESETS[args.rule]
    else:
        rule = parse_ltl_notation(args.rule)
        if rule is None:
            # Try get_rule in case it's a regular rule.
            try:
                rule = get_rule(args.rule)
            except KeyError:
                print(f"Error: '{args.rule}' is not a valid LtL rule or B/S/R notation")
                return
    height = args.height if args.height else 30
    ca = CellularAutomaton(
        rule, width=args.width, height=height, boundary=args.boundary,
    )
    if args.random is not None:
        ca.randomize(args.random, seed=args.seed)
    elif args.pattern:
        pat = get_pattern(args.pattern)
        place_pattern(ca, pat, x=args.px, y=args.py)
    else:
        ca.randomize(0.3, seed=args.seed or 42)

    fmt = args.format
    print(f"Rule: {rule.rule_string()}")
    print(render_ascii(ca.grid))
    print()
    for _ in range(args.steps):
        ca.step()
        if fmt == "ansi":
            print(render_ansi(ca.grid))
        else:
            print(render_ascii(ca.grid))
        print()


def cmd_continuous(args: argparse.Namespace) -> None:
    """Run a continuous CA (reaction-diffusion model)."""
    model_name = args.model
    if model_name not in CONTINUOUS_MODELS:
        print(f"Error: unknown model '{model_name}'. Available: {list(CONTINUOUS_MODELS)}")
        return

    width = args.width
    height = args.height if args.height else width

    # Build model — handle Gray-Scott presets.
    if model_name == "GrayScott" and args.preset:
        model = GrayScott.from_preset(args.preset, width=width, height=height)
    else:
        model = get_continuous_model(model_name, width=width, height=height)

    # Seed the model.
    if model_name == "GrayScott":
        if args.random:
            model.seed_random(n_seeds=8, seed=args.seed)
        else:
            model.seed_square(width // 2, height // 2, radius=args.seed_radius)
    elif model_name == "FitzHughNagumo":
        if args.random:
            model.randomize(seed=args.seed)
        else:
            model.seed_spiral()

    # Run.
    model.step(args.steps)

    # Render.
    if args.format == "ascii":
        # Show the second species (v / w) which carries the visible pattern.
        field = model.states[1] if model.n_species > 1 else model.states[0]
        print(f"Model: {model.name}, step {model.step_count}")
        print(render_continuous_ascii(field))
    elif args.format == "png":
        try:
            from PIL import Image  # type: ignore
        except ImportError:
            print("PNG output requires Pillow: pip install pillow")
            return
        field = model.states[1] if model.n_species > 1 else model.states[0]
        vmin, vmax = float(field.min()), float(field.max())
        if vmax <= vmin:
            vmax = vmin + 1e-9
        normalised = ((field - vmin) / (vmax - vmin) * 255).astype(np.uint8)
        # Apply a simple colormap (blue → cyan → green → yellow → red).
        img = np.zeros((height, width, 3), dtype=np.uint8)
        for i in range(256):
            mask = normalised == i
            t = i / 255.0
            img[mask] = (
                int(255 * min(1, max(0, 4 * t - 1.5))),
                int(255 * min(1, max(0, -4 * abs(t - 0.5) + 1))),
                int(255 * min(1, max(0, -4 * t + 1.5))),
            )
        Image.fromarray(img, "RGB").save(args.output or "output.png")
        print(f"Rendered to {args.output or 'output.png'}")
    elif args.format == "gif":
        try:
            from PIL import Image  # type: ignore
        except ImportError:
            print("GIF output requires Pillow: pip install pillow")
            return
        # Re-run from scratch to capture frames.
        model2 = get_continuous_model(model_name, width=width, height=height)
        if model_name == "GrayScott":
            model2.seed_square(width // 2, height // 2, radius=args.seed_radius)
        elif model_name == "FitzHughNagumo":
            model2.seed_spiral()
        frames: list = []
        for _ in range(args.steps + 1):
            field = model2.states[1] if model2.n_species > 1 else model2.states[0]
            vmin, vmax = float(field.min()), float(field.max())
            if vmax <= vmin:
                vmax = vmin + 1e-9
            normalised = ((field - vmin) / (vmax - vmin) * 255).astype(np.uint8)
            img = np.zeros((height, width, 3), dtype=np.uint8)
            for i in range(256):
                mask = normalised == i
                t = i / 255.0
                img[mask] = (
                    int(255 * min(1, max(0, 4 * t - 1.5))),
                    int(255 * min(1, max(0, -4 * abs(t - 0.5) + 1))),
                    int(255 * min(1, max(0, -4 * t + 1.5))),
                )
            frames.append(Image.fromarray(img, "RGB"))
            model2.step()
        frames[0].save(
            args.output or "output.gif",
            save_all=True, append_images=frames[1:],
            duration=args.duration, loop=0, optimize=True,
        )
        print(f"Animated GIF written to {args.output or 'output.gif'}")


# ---------------------------------------------------------------------------
# Parser construction
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the CLI."""
    p = argparse.ArgumentParser(
        prog="cellular-automaton",
        description="1D & 2D cellular automaton simulator with multi-state support, "
                    "analysis tools, and config files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version", version="%(prog)s 4.0.0")
    sub = p.add_subparsers(dest="command", required=True)

    # Common rule/initial args
    def add_common(sp):
        sp.add_argument("--rule", required=True,
                        help="Rule name (e.g. Rule30, GameOfLife, B36/S23)")
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

    # run
    sp_run = sub.add_parser("run", help="Run and print each step")
    add_common(sp_run)
    sp_run.add_argument("--steps", type=int, default=20)
    sp_run.add_argument("--format", default="ascii", choices=["ascii", "ansi"])
    sp_run.set_defaults(func=cmd_run)

    # render
    sp_render = sub.add_parser("render", help="Render final state to a file")
    add_common(sp_render)
    sp_render.add_argument("--steps", type=int, default=20)
    sp_render.add_argument("--format", default="svg", choices=["svg", "ppm", "png", "ascii"])
    sp_render.add_argument("--output", "-o", default="output.svg")
    sp_render.set_defaults(func=cmd_render)

    # rules
    sp_rules = sub.add_parser("rules", help="List builtin rules")
    sp_rules.set_defaults(func=cmd_rules)

    # patterns
    sp_patterns = sub.add_parser("patterns", help="List builtin patterns")
    sp_patterns.set_defaults(func=cmd_patterns)

    # info
    sp_info = sub.add_parser("info", help="Show details about a rule")
    sp_info.add_argument("--rule", required=True)
    sp_info.set_defaults(func=cmd_info)

    # simulate
    sp_sim = sub.add_parser("simulate", help="Run with statistics & cycle detection")
    add_common(sp_sim)
    sp_sim.add_argument("--steps", type=int, default=100)
    sp_sim.add_argument("--no-cycle-detect", action="store_true")
    sp_sim.add_argument("--json", action="store_true", help="Print stats as JSON")
    sp_sim.set_defaults(func=cmd_simulate)

    # spacetime
    sp_st = sub.add_parser("spacetime", help="Render 1D spacetime diagram")
    add_common(sp_st)
    sp_st.add_argument("--steps", type=int, default=40)
    sp_st.add_argument("--format", default="ascii", choices=["ascii", "svg", "ppm"])
    sp_st.add_argument("--output", "-o", default=None)
    sp_st.add_argument("--on-char", default="█")
    sp_st.add_argument("--off-char", default=" ")
    sp_st.set_defaults(func=cmd_spacetime)

    # animate
    sp_anim = sub.add_parser("animate", help="Render animation frames")
    add_common(sp_anim)
    sp_anim.add_argument("--steps", type=int, default=30)
    sp_anim.add_argument("--format", default="ppm", choices=["ppm", "png"])
    sp_anim.add_argument("--output", default="frames")
    sp_anim.add_argument("--cell-size", type=int, default=4)
    sp_anim.set_defaults(func=cmd_animate)

    # save
    sp_save = sub.add_parser("save", help="Save state to JSON")
    add_common(sp_save)
    sp_save.add_argument("--steps", type=int, default=10)
    sp_save.add_argument("--output", "-o", required=True)
    sp_save.set_defaults(func=cmd_save)

    # load
    sp_load = sub.add_parser("load", help="Load state from JSON")
    sp_load.add_argument("input")
    sp_load.set_defaults(func=cmd_load)

    # classify
    sp_classify = sub.add_parser("classify", help="Wolfram classification of 1D rules")
    sp_classify.add_argument("--rule", default=None, help="Rule number (0-255)")
    sp_classify.add_argument("--all", action="store_true", help="Classify all 256 rules")
    sp_classify.add_argument("--width", type=int, default=101, help="Grid width for classification")
    sp_classify.add_argument("--steps", type=int, default=200, help="Steps for classification")
    sp_classify.set_defaults(func=cmd_classify)

    # entropy
    sp_entropy = sub.add_parser("entropy", help="Compute entropy of a CA state")
    add_common(sp_entropy)
    sp_entropy.add_argument("--steps", type=int, default=50)
    sp_entropy.add_argument("--block-size", type=int, default=1, help="Block size for block entropy")
    sp_entropy.add_argument("--spacetime", action="store_true", help="Compute spacetime entropy")
    sp_entropy.set_defaults(func=cmd_entropy)

    # sweep
    sp_sweep = sub.add_parser("sweep", help="Parameter sweep over rule parameters")
    sp_sweep.add_argument("--rule", required=True, help="Rule name")
    sp_sweep.add_argument("--params", default="{}", help='JSON dict of param→values, e.g. \'{"p":[0.01,0.05],"g":[0.05,0.1]}\'')
    sp_sweep.add_argument("--width", type=int, default=50)
    sp_sweep.add_argument("--height", type=int, default=50)
    sp_sweep.add_argument("--steps", type=int, default=100)
    sp_sweep.add_argument("--seed", type=int, default=42)
    sp_sweep.set_defaults(func=cmd_sweep)

    # config
    sp_config = sub.add_parser("config", help="Run from a config file (JSON/YAML/TOML)")
    sp_config.add_argument("config_file", help="Path to config file")
    sp_config.add_argument("--output", "-o", default=None, help="Override output path")
    sp_config.add_argument("--format", default=None, help="Override output format")
    sp_config.add_argument("--steps", type=int, default=None, help="Override number of steps")
    sp_config.set_defaults(func=cmd_config)

    # multistate
    sp_ms = sub.add_parser("multistate", help="Run a multi-state CA")
    sp_ms.add_argument("--rule", required=True,
                       choices=list(MULTISTATE_RULES.keys()),
                       help="Multi-state rule name")
    sp_ms.add_argument("--width", type=int, default=40)
    sp_ms.add_argument("--height", type=int, default=20)
    sp_ms.add_argument("--boundary", default="periodic",
                       choices=[b.value for b in Boundary])
    sp_ms.add_argument("--random", type=float, default=None, help="Random density (binary init)")
    sp_ms.add_argument("--random-states", type=float, default=None,
                       help="Random multi-state init (fraction of non-zero cells)")
    sp_ms.add_argument("--seed", type=int, default=None)
    sp_ms.add_argument("--steps", type=int, default=20)
    sp_ms.add_argument("--format", default="ascii", choices=["ascii", "ansi"])
    sp_ms.add_argument("--pattern", default=None, help="Named pattern (placed as binary)")
    sp_ms.add_argument("--px", type=int, default=5)
    sp_ms.add_argument("--py", type=int, default=5)
    sp_ms.add_argument("--params", default=None,
                       help="Comma-separated key=value params for the rule, e.g. p=0.01,g=0.1")
    sp_ms.set_defaults(func=cmd_multistate)

    # gif
    sp_gif = sub.add_parser("gif", help="Render a CA evolution as an animated GIF")
    add_common(sp_gif)
    sp_gif.add_argument("--steps", type=int, default=50, help="Number of frames")
    sp_gif.add_argument("--output", "-o", default="output.gif", help="Output GIF path")
    sp_gif.add_argument("--cell-size", type=int, default=4, help="Pixel size per cell")
    sp_gif.add_argument("--duration", type=int, default=100, help="Frame duration (ms)")
    sp_gif.add_argument("--random-states", type=float, default=None,
                        help="Random multi-state init (for multistate rules)")
    sp_gif.add_argument("--params", default=None,
                        help="Comma-separated key=value params for multistate rules")
    sp_gif.set_defaults(func=cmd_gif)

    # rle-file
    sp_rle = sub.add_parser("rle-file", help="Load a pattern from an RLE file and run it")
    sp_rle.add_argument("rle_file", help="Path to the .rle file")
    sp_rle.add_argument("--rule", default="GameOfLife", help="Rule to use")
    sp_rle.add_argument("--width", type=int, default=60, help="Grid width")
    sp_rle.add_argument("--height", type=int, default=None, help="Grid height")
    sp_rle.add_argument("--boundary", default="periodic",
                        choices=[b.value for b in Boundary])
    sp_rle.add_argument("--px", type=int, default=5, help="Pattern x offset")
    sp_rle.add_argument("--py", type=int, default=5, help="Pattern y offset")
    sp_rle.add_argument("--steps", type=int, default=100, help="Number of steps")
    sp_rle.add_argument("--format", default="ascii", choices=["ascii", "ansi", "svg", "png"])
    sp_rle.add_argument("--output", "-o", default=None, help="Output file (for svg/png)")
    sp_rle.set_defaults(func=cmd_rle_file)

    # ltl — Larger than Life
    sp_ltl = sub.add_parser("ltl", help="Run a Larger-than-Life CA (Bxx/Sxx/Rn)")
    sp_ltl.add_argument("--rule", required=True,
                        help="LtL rule name (Boon, Grenville, Bugs) or Bxx/Sxx/Rn notation")
    sp_ltl.add_argument("--width", type=int, default=40)
    sp_ltl.add_argument("--height", type=int, default=None)
    sp_ltl.add_argument("--boundary", default="periodic",
                        choices=[b.value for b in Boundary])
    sp_ltl.add_argument("--random", type=float, default=None, help="Random density")
    sp_ltl.add_argument("--seed", type=int, default=None)
    sp_ltl.add_argument("--pattern", default=None, help="Named pattern")
    sp_ltl.add_argument("--px", type=int, default=5)
    sp_ltl.add_argument("--py", type=int, default=5)
    sp_ltl.add_argument("--steps", type=int, default=20)
    sp_ltl.add_argument("--format", default="ascii", choices=["ascii", "ansi"])
    sp_ltl.set_defaults(func=cmd_ltl)

    # continuous — reaction-diffusion
    sp_cont = sub.add_parser("continuous", help="Run a continuous CA (reaction-diffusion)")
    sp_cont.add_argument("--model", required=True,
                         choices=list(CONTINUOUS_MODELS.keys()),
                         help="Continuous model name")
    sp_cont.add_argument("--preset", default=None,
                         help="Gray-Scott preset (spots, stripes, maze, worms, solitons, ...)")
    sp_cont.add_argument("--width", type=int, default=60)
    sp_cont.add_argument("--height", type=int, default=None)
    sp_cont.add_argument("--steps", type=int, default=500)
    sp_cont.add_argument("--seed", type=int, default=None)
    sp_cont.add_argument("--seed-radius", type=int, default=5,
                         help="Radius of initial seed square (Gray-Scott)")
    sp_cont.add_argument("--random", action="store_true",
                         help="Use random initial seeds instead of a centre seed")
    sp_cont.add_argument("--format", default="ascii", choices=["ascii", "png", "gif"])
    sp_cont.add_argument("--output", "-o", default=None, help="Output file (for png/gif)")
    sp_cont.add_argument("--duration", type=int, default=50, help="GIF frame duration (ms)")
    sp_cont.set_defaults(func=cmd_continuous)

    return p


def main(argv: Optional[list] = None) -> int:
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())