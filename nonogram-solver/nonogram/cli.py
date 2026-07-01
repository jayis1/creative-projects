"""
Command-line interface for the nonogram solver.

Subcommands:
  solve      — solve a puzzle from a JSON/NON file
  generate   — create a new puzzle
  validate   — check a JSON puzzle file for uniqueness
  hint       — print one hint for a puzzle state
  presets    — list and solve curated preset puzzles
  analyze    — estimate puzzle difficulty
  render     — render a board as ANSI/HTML/SVG/PNG
  count      — count solutions (up to a limit)
  batch      — solve multiple puzzles at once
  benchmark  — run solver benchmarks
  web        — start interactive web solver
  config     — generate or validate a config file
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List

from nonogram.board import Board, Cell
from nonogram.solver import Solver
from nonogram.generator import Generator
from nonogram.player import Player
from nonogram.io import PuzzleIO
from nonogram.renderer import Renderer
from nonogram.analyzer import DifficultyAnalyzer
from nonogram.presets import list_presets, get_preset
from nonogram.config import AppConfig, load_config, save_config, setup_logging, LoggingConfig
from nonogram.batch import BatchSolver
from nonogram.benchmark import BenchmarkSuite

logger = logging.getLogger("nonogram.cli")


def _load_board(path: str) -> Board:
    p = Path(path)
    if p.suffix == ".non":
        return PuzzleIO.load_non(str(p))
    return PuzzleIO.load_json(str(p))


# --------------------------------------------------------------------------- #
# Subcommand handlers
# --------------------------------------------------------------------------- #

def cmd_solve(args: argparse.Namespace) -> int:
    board = _load_board(args.file)
    # Reset grid to unknown for solving.
    for r in range(board.height):
        for c in range(board.width):
            board.grid[r][c] = Cell.UNKNOWN
    solver = Solver(max_backtracks=args.max_backtracks, use_mrv=not args.no_mrv)
    result = solver.solve(board)
    if result.solved:
        if args.color:
            print(Renderer.ansi(board))
        else:
            print(board.render())
        print(f"\nSolved in {result.iterations} iterations, "
              f"{result.backtracks} backtracks.")
        if args.output:
            PuzzleIO.save_json(board, args.output)
            logger.info("Solution saved to %s", args.output)
        return 0
    else:
        print("No solution found.")
        print(f"(iterations={result.iterations}, backtracks={result.backtracks})")
        return 1


def cmd_generate(args: argparse.Namespace) -> int:
    gen = Generator(seed=args.seed)
    board = gen.generate(
        args.width, args.height,
        density=args.density,
        unique=not args.no_unique,
        max_attempts=args.max_attempts,
    )
    if args.output:
        PuzzleIO.save_json(board, args.output)
        logger.info("Puzzle saved to %s", args.output)
    # Print clues only.
    print("Row clues:", board.row_clues)
    print("Col clues:", board.col_clues)
    print()
    print("Solution:")
    print(board.render())
    if args.difficulty:
        analyzer = DifficultyAnalyzer()
        info = analyzer.analyze(board)
        print(f"\nDifficulty: {info['difficulty']} (score: {info['score']})")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    board = _load_board(args.file)
    solver = Solver()
    test = Board(board.row_clues, board.col_clues)
    result = solver.solve(test)
    if not result.solved:
        print("UNSOLVABLE: no solution exists for these clues.")
        return 1
    count = solver.count_solutions(Board(board.row_clues, board.col_clues), limit=2)
    if count == 1:
        print("VALID: puzzle has a unique solution.")
        return 0
    else:
        print(f"AMBIGUOUS: puzzle has at least {count} solutions.")
        return 2


def cmd_hint(args: argparse.Namespace) -> int:
    board = _load_board(args.file)
    player = Player(board)
    hint = player.hint()
    if hint:
        r, c, cell = hint
        print(f"Hint: cell ({r}, {c}) should be "
              f"{'FILLED' if cell is Cell.FILLED else 'EMPTY'}.")
        return 0
    else:
        print("No hint available — the solver is stuck.")
        return 1


def cmd_presets(args: argparse.Namespace) -> int:
    if args.name:
        board = get_preset(args.name)
        if args.solve:
            solve_board = Board(board.row_clues, board.col_clues)
            result = Solver().solve(solve_board)
            if result.solved:
                print(f"Preset '{args.name}' solution:")
                print(solve_board.render())
            else:
                print(f"Preset '{args.name}' could not be solved.")
                return 1
        else:
            print(f"Preset '{args.name}':")
            print(f"Row clues: {board.row_clues}")
            print(f"Col clues: {board.col_clues}")
            print()
            print(board.render())
        if args.output:
            PuzzleIO.save_json(board, args.output)
    else:
        print(f"{'Name':<20} {'Difficulty':<10} Description")
        print("-" * 60)
        for name, diff, desc in list_presets():
            print(f"{name:<20} {diff:<10} {desc}")
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    board = _load_board(args.file)
    analyzer = DifficultyAnalyzer()
    info = analyzer.analyze(board)
    print(f"Difficulty:  {info['difficulty']}")
    print(f"Score:       {info['score']}")
    print(f"Grid:        {info['grid_size']}")
    print(f"Filled ratio:{info['filled_ratio']}")
    print(f"Blocks:      {info['num_blocks']}")
    print(f"Avg block:   {info['avg_block_size']}")
    print(f"Solved:      {info['solved']}")
    print(f"Iterations:  {info['iterations']}")
    print(f"Backtracks:  {info['backtracks']}")
    print(f"Prop only:   {info['propagation_only']}")
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    board = _load_board(args.file)
    fmt = args.format
    if fmt == "ansi":
        print(Renderer.ansi(board))
    elif fmt == "html":
        output = Renderer.html(board, title=args.title or "Nonogram")
        if args.output:
            Path(args.output).write_text(output)
            print(f"HTML written to {args.output}")
        else:
            print(output)
    elif fmt == "svg":
        if args.output:
            PuzzleIO.save_svg(board, args.output)
            print(f"SVG written to {args.output}")
        else:
            print("SVG requires --output FILE")
            return 1
    elif fmt == "png":
        if args.output:
            PuzzleIO.save_png(board, args.output)
            print(f"PNG written to {args.output}")
        else:
            print("PNG requires --output FILE")
            return 1
    elif fmt == "text":
        print(board.render())
    else:
        print(f"Unknown format: {fmt}")
        return 1
    return 0


def cmd_count(args: argparse.Namespace) -> int:
    board = _load_board(args.file)
    solver = Solver()
    count = solver.count_solutions(Board(board.row_clues, board.col_clues),
                                    limit=args.limit)
    print(f"Solutions found: {count}" +
          (f" (stopped at limit {args.limit})" if count >= args.limit else ""))
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    """Batch solve multiple puzzle files."""
    bs = BatchSolver(
        output_dir=args.output_dir,
        check_unique=args.check_unique,
    )
    report = bs.solve_files(args.pattern, recursive=args.recursive)
    print(report.summary())
    if args.report_json:
        Path(args.report_json).write_text(report.to_json())
        print(f"\nReport saved to {args.report_json}")
    if args.report_csv:
        Path(args.report_csv).write_text(report.to_csv())
        print(f"CSV report saved to {args.report_csv}")
    return 0 if report.failed_count == 0 else 1


def cmd_benchmark(args: argparse.Namespace) -> int:
    """Run solver benchmarks."""
    suite = BenchmarkSuite()
    if args.preset:
        result = suite.benchmark_preset(args.preset)
        suite.results.append(result)
    else:
        suite.run_all()
    print(suite.summary())
    if args.output:
        Path(args.output).write_text(suite.to_json())
        print(f"\nResults saved to {args.output}")
    return 0


def cmd_web(args: argparse.Namespace) -> int:
    """Start the interactive web solver."""
    from nonogram.web import serve
    board = _load_board(args.file)
    port = args.port
    print(f"Starting web server on http://localhost:{port}")
    print("Press Ctrl+C to stop.")
    serve(board, port=port, open_browser=not args.no_browser)
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    """Generate a default config file or validate an existing one."""
    if args.generate:
        config = AppConfig()
        save_config(config, args.generate)
        print(f"Default config written to {args.generate}")
        return 0
    if args.validate:
        try:
            config = load_config(args.validate)
            config.validate()
            print(f"Config '{args.validate}' is valid.")
            print(f"  Solver: max_iterations={config.solver.max_iterations}, "
                  f"max_backtracks={config.solver.max_backtracks}, "
                  f"use_mrv={config.solver.use_mrv}")
            print(f"  Generator: density={config.generator.default_density}, "
                  f"max_attempts={config.generator.default_max_attempts}")
            print(f"  Rendering: cell_size={config.rendering.cell_size}")
            print(f"  Logging: level={config.logging.level}")
            return 0
        except Exception as e:
            print(f"Config validation failed: {e}")
            return 1
    print("Use --generate FILE or --validate FILE")
    return 1


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="nonogram",
        description="Nonogram solver, generator, and player.",
        epilog="Use --config FILE to load configuration. Use --verbose for debug output.",
    )
    # Global options.
    p.add_argument("--config", "-c", help="Path to config file (JSON/YAML/TOML).")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="Enable debug logging.")
    p.add_argument("--quiet", "-q", action="store_true",
                   help="Suppress all output except errors.")

    sub = p.add_subparsers(dest="command", required=True)

    # solve
    sp = sub.add_parser("solve", help="Solve a puzzle from a JSON/NON file.")
    sp.add_argument("file", help="Path to puzzle file (.json or .non).")
    sp.add_argument("--output", "-o", help="Save solved board to file.")
    sp.add_argument("--max-backtracks", type=int, default=100000)
    sp.add_argument("--no-mrv", action="store_true",
                    help="Disable MRV cell selection heuristic.")
    sp.add_argument("--color", action="store_true", help="ANSI color output.")
    sp.set_defaults(func=cmd_solve)

    # generate
    sp = sub.add_parser("generate", help="Generate a new puzzle.")
    sp.add_argument("--width", "-w", type=int, default=10)
    sp.add_argument("--height", "-H", type=int, default=10)
    sp.add_argument("--density", "-d", type=float, default=0.55)
    sp.add_argument("--seed", "-s", type=int, default=None)
    sp.add_argument("--no-unique", action="store_true",
                    help="Skip uniqueness check.")
    sp.add_argument("--max-attempts", type=int, default=200)
    sp.add_argument("--output", "-o", help="Save puzzle to JSON file.")
    sp.add_argument("--difficulty", action="store_true",
                    help="Print difficulty analysis.")
    sp.set_defaults(func=cmd_generate)

    # validate
    sp = sub.add_parser("validate", help="Check puzzle uniqueness.")
    sp.add_argument("file", help="Path to puzzle file.")
    sp.set_defaults(func=cmd_validate)

    # hint
    sp = sub.add_parser("hint", help="Get a hint for a puzzle.")
    sp.add_argument("file", help="Path to puzzle file.")
    sp.set_defaults(func=cmd_hint)

    # presets
    sp = sub.add_parser("presets", help="List or solve curated preset puzzles.")
    sp.add_argument("--name", "-n", help="Show a specific preset.")
    sp.add_argument("--solve", "-s", action="store_true",
                    help="Solve the preset and show the solution.")
    sp.add_argument("--output", "-o", help="Save preset to JSON file.")
    sp.set_defaults(func=cmd_presets)

    # analyze
    sp = sub.add_parser("analyze", help="Estimate puzzle difficulty.")
    sp.add_argument("file", help="Path to puzzle file.")
    sp.set_defaults(func=cmd_analyze)

    # render
    sp = sub.add_parser("render", help="Render a board in various formats.")
    sp.add_argument("file", help="Path to puzzle file.")
    sp.add_argument("--format", "-f",
                    choices=["ansi", "html", "svg", "png", "text"],
                    default="text")
    sp.add_argument("--output", "-o", help="Output file for HTML/SVG/PNG.")
    sp.add_argument("--title", "-t", help="Title for HTML output.")
    sp.set_defaults(func=cmd_render)

    # count
    sp = sub.add_parser("count", help="Count solutions (up to a limit).")
    sp.add_argument("file", help="Path to puzzle file.")
    sp.add_argument("--limit", "-l", type=int, default=100,
                    help="Max solutions to count.")
    sp.set_defaults(func=cmd_count)

    # batch
    sp = sub.add_parser("batch", help="Solve multiple puzzle files.")
    sp.add_argument("pattern", help="Glob pattern or directory path.")
    sp.add_argument("--output-dir", "-o", help="Directory for solved JSONs.")
    sp.add_argument("--recursive", "-r", action="store_true",
                    help="Search subdirectories if pattern is a directory.")
    sp.add_argument("--check-unique", "-u", action="store_true",
                    help="Also check solution uniqueness for each puzzle.")
    sp.add_argument("--report-json", help="Save JSON report to file.")
    sp.add_argument("--report-csv", help="Save CSV report to file.")
    sp.set_defaults(func=cmd_batch)

    # benchmark
    sp = sub.add_parser("benchmark", help="Run solver benchmarks.")
    sp.add_argument("--preset", "-p", help="Benchmark a specific preset.")
    sp.add_argument("--output", "-o", help="Save results to JSON file.")
    sp.set_defaults(func=cmd_benchmark)

    # web
    sp = sub.add_parser("web", help="Start interactive web solver.")
    sp.add_argument("file", help="Path to puzzle file.")
    sp.add_argument("--port", "-p", type=int, default=8080)
    sp.add_argument("--no-browser", action="store_true",
                    help="Don't open a browser automatically.")
    sp.set_defaults(func=cmd_web)

    # config
    sp = sub.add_parser("config", help="Generate or validate config files.")
    sp.add_argument("--generate", "-g", metavar="FILE",
                    help="Generate a default config file.")
    sp.add_argument("--validate", "-v", metavar="FILE",
                    help="Validate an existing config file.")
    sp.set_defaults(func=cmd_config)

    return p


def _setup_logging_from_args(args: argparse.Namespace) -> None:
    """Configure logging based on CLI args and optional config file."""
    level = "WARNING"
    if getattr(args, "verbose", False):
        level = "DEBUG"
    elif getattr(args, "quiet", False):
        level = "ERROR"

    log_cfg = LoggingConfig(level=level)
    if getattr(args, "config", None):
        try:
            config = load_config(args.config)
            log_cfg = config.logging
        except Exception as e:
            logger.warning("Could not load config %s: %s", args.config, e)

    setup_logging(log_cfg)


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _setup_logging_from_args(args)
    logger.debug("Starting command: %s", args.command)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())