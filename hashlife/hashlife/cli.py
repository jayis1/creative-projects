#!/usr/bin/env python3
"""Command-line interface for the Hashlife engine.

Usage examples
--------------

Render a glider after 4 steps::

    hashlife --pattern glider --steps 4

Step the Gosper glider gun 1000 generations and print population::

    hashlife --gun --steps 1000 --population

Load an RLE file, evolve 2**20 generations, dump the live cells as CSV::

    hashlife --rle-file pattern.rle --steps 1048576 --csv out.csv
"""

from __future__ import annotations

import argparse
import sys

from .engine import Hashlife
from .rle import load_rle, pattern_to_set
from .render import render


# ---------------------------------------------------------------------------
# Built-in patterns
# ---------------------------------------------------------------------------

PATTERNS = {
    "blinker": pattern_to_set("ooo"),
    "block": pattern_to_set("oo\noo"),
    "glider": pattern_to_set(".o.\n..o\nooo"),
    "lwss": pattern_to_set(".o..o\no....\no...o\noooo."),
    "pulsar": pattern_to_set(
        "..ooo...ooo.." + "\n" +
        "............." + "\n" +
        "o....o.o....o" + "\n" +
        "o....o.o....o" + "\n" +
        "o....o.o....o" + "\n" +
        "............." + "\n" +
        "..ooo...ooo.." + "\n" +
        "............." + "\n" +
        "..ooo...ooo.." + "\n" +
        "............." + "\n" +
        "o....o.o....o" + "\n" +
        "o....o.o....o" + "\n" +
        "o....o.o....o" + "\n" +
        "............." + "\n" +
        "..ooo...ooo.."
    ),
    # Gosper glider gun
    "gun": load_rle(
        "x = 36, y = 9, rule = B3/S23\n"
        "24bo11b$22bobo11b$12b2o6b2o12b2o$11bo3bo4b2o12b2o$2o8bo5bo3b2o$2o8b"
        "o3bo4b2o$10b2o6b2o12b2o$22bobo11b$24bo!"
    ),
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="hashlife",
        description="Hashlife — Conway's Game of Life via memoized quadtrees.",
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--pattern", choices=sorted(PATTERNS),
                     help="built-in pattern to load")
    src.add_argument("--rle", dest="rle_text",
                     help="inline RLE pattern string")
    src.add_argument("--rle-file", dest="rle_file",
                     help="path to an RLE file to load")
    src.add_argument("--gun", action="store_true",
                     help="shortcut for --pattern gun")
    p.add_argument("--steps", type=int, default=0,
                   help="number of generations to evolve (default 0)")
    p.add_argument("--render", action="store_true",
                   help="ASCII-render the final universe")
    p.add_argument("--population", action="store_true",
                   help="print the live-cell count after evolving")
    p.add_argument("--cells", action="store_true",
                   help="print every live cell as 'x,y'")
    p.add_argument("--csv", metavar="FILE",
                   help="write live cells to a CSV file")
    p.add_argument("--stats", action="store_true",
                   help="print engine statistics (node count, memo size)")
    p.add_argument("--quiet", "-q", action="store_true",
                   help="suppress all output except errors")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    # ---- load pattern -------------------------------------------------
    if args.gun or args.pattern == "gun" and args.pattern:
        pass  # handled below

    if args.gun:
        cells = PATTERNS["gun"]
    elif args.pattern:
        cells = PATTERNS[args.pattern]
    elif args.rle_text is not None:
        cells = load_rle(args.rle_text)
    elif args.rle_file:
        with open(args.rle_file, "r", encoding="utf-8") as fh:
            cells = load_rle(fh.read())
    else:
        # unreachable due to argparse required group
        cells = set()

    life = Hashlife(root_level=4)
    life.add_pattern(cells)

    # ---- evolve -------------------------------------------------------
    if args.steps:
        life.step(args.steps)

    # ---- output -------------------------------------------------------
    if not args.quiet:
        if args.population:
            print(f"population: {life.population}")
        if args.cells:
            for cx, cy in sorted(life.get_live_cells()):
                print(f"{cx},{cy}")
        if args.render:
            print(render(life.get_live_cells()))
        if args.stats:
            print(f"generation: {life.generation}")
            print(f"pool_size:  {len(life._pool)}")
            print(f"memo_size:  {len(life._memo)}")
            print(f"root_level:  {life.root.level}")

    if args.csv:
        with open(args.csv, "w", encoding="utf-8") as fh:
            fh.write("x,y\n")
            for cx, cy in sorted(life.get_live_cells()):
                fh.write(f"{cx},{cy}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())