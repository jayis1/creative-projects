"""Command-line interface for suffix automaton analytics."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys
from typing import Sequence

from .commands import execute_batch_jobs, execute_lcs_command, execute_text_command, render_payload, resolve_text
from .config import JobConfig, load_config
from .core import SuffixAutomaton

LOGGER = logging.getLogger("suffix_automaton")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="suffix-automaton",
        description="Substring analytics with a suffix automaton",
    )
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="WARNING",
        help="set logging verbosity",
    )
    parser.add_argument("--log-file", type=Path, help="optional file for logs")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="analyze one string")
    _add_text_argument(analyze)
    analyze.add_argument("--json", action="store_true", help="emit JSON")

    contains = subparsers.add_parser("contains", help="check substring membership")
    _add_text_argument(contains)
    contains.add_argument("substring")

    count = subparsers.add_parser("count", help="count substring occurrences")
    _add_text_argument(count)
    count.add_argument("substring")

    locate = subparsers.add_parser("locate", help="locate substring matches")
    _add_text_argument(locate)
    locate.add_argument("substring")
    locate.add_argument("--limit", type=int)

    export = subparsers.add_parser("export", help="export automaton JSON")
    _add_text_argument(export)
    export.add_argument("--output", type=Path)

    dot = subparsers.add_parser("dot", help="export automaton Graphviz DOT")
    _add_text_argument(dot)
    dot.add_argument("--output", type=Path)

    kth = subparsers.add_parser("kth", help="k-th lexicographic distinct substring")
    _add_text_argument(kth)
    kth.add_argument("k", type=int)

    absent = subparsers.add_parser("absent", help="shortest absent substring")
    _add_text_argument(absent)
    absent.add_argument("--alphabet", help="alphabet to search over; defaults to text alphabet")

    repeats = subparsers.add_parser("repeats", help="top repeated substrings")
    _add_text_argument(repeats)
    repeats.add_argument("--limit", type=int, default=10)
    repeats.add_argument("--min-length", type=int, default=1)
    repeats.add_argument("--json", action="store_true", help="emit JSON")

    complexity = subparsers.add_parser("complexity", help="distinct substring counts by length")
    _add_text_argument(complexity)
    complexity.add_argument("--json", action="store_true", help="emit JSON")

    mus = subparsers.add_parser("mus", help="minimal unique substrings per position")
    _add_text_argument(mus)
    mus.add_argument("--limit", type=int)
    mus.add_argument("--json", action="store_true", help="emit JSON")

    lcs = subparsers.add_parser("lcs", help="longest common substring")
    lcs.add_argument("strings", nargs="+", help="two or more strings")
    lcs.add_argument("--pairwise", action="store_true", help="also emit pairwise matches as JSON")

    run_config = subparsers.add_parser("run-config", help="run a batch workload from JSON or TOML")
    run_config.add_argument("config", type=Path)

    return parser


def _add_text_argument(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="literal input text")
    group.add_argument("--file", type=Path, help="read input text from a file")


def configure_logging(level: str, log_file: Path | None) -> None:
    """Configure process logging."""
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if log_file is not None:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def _write_or_print(payload: str, output: Path | None) -> None:
    if output is None:
        print(payload)
    else:
        output.write_text(payload, encoding="utf-8")
        LOGGER.info("wrote output to %s", output)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.log_level, args.log_file)

    try:
        if args.command == "run-config":
            payload = execute_batch_jobs(load_config(args.config))
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0

        if args.command == "lcs":
            payload = execute_lcs_command(args.strings, pairwise=args.pairwise)
            print(render_payload(payload, as_json=args.pairwise))
            return 0

        text = resolve_text(text=args.text, file=args.file)
        automaton = SuffixAutomaton(text)
        LOGGER.info("built automaton with %d states for text length %d", len(automaton.states), len(text))

        command_config = JobConfig(
            substring=getattr(args, "substring", None),
            k=getattr(args, "k", None),
            alphabet=getattr(args, "alphabet", None),
            limit=getattr(args, "limit", None),
            min_length=getattr(args, "min_length", None),
            as_json=getattr(args, "json", False),
        )
        payload = execute_text_command(args.command, automaton, command_config)
        rendered = render_payload(payload, as_json=command_config.as_json)
        output = getattr(args, "output", None)
        _write_or_print(rendered, output)
        return 0
    except Exception as exc:
        LOGGER.error("%s", exc)
        return 1
