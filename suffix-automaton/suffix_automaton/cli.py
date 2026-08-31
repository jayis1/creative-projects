"""Command-line interface for suffix automaton analytics."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import Sequence

from .core import (
    SuffixAutomaton,
    longest_common_substring,
    longest_common_substring_by_pairs,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="suffix-automaton",
        description="Substring analytics with a suffix automaton",
    )
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

    lcs = subparsers.add_parser("lcs", help="longest common substring")
    lcs.add_argument("strings", nargs="+", help="two or more strings")
    lcs.add_argument("--pairwise", action="store_true", help="also emit pairwise matches as JSON")

    return parser


def _add_text_argument(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="literal input text")
    group.add_argument("--file", type=Path, help="read input text from a file")


def _resolve_text(args: argparse.Namespace) -> str:
    if args.text is not None:
        return args.text
    if args.file is None:
        raise ValueError("expected either --text or --file")
    return args.file.read_text(encoding="utf-8")


def _write_or_print(payload: str, output: Path | None) -> None:
    if output is None:
        print(payload)
    else:
        output.write_text(payload, encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "lcs":
        lcs_result: dict[str, object] = {"longest_common_substring": longest_common_substring(args.strings)}
        if args.pairwise:
            pairs = {
                f"{left}-{right}": value
                for (left, right), value in longest_common_substring_by_pairs(args.strings).items()
            }
            lcs_result["pairwise"] = pairs
            print(json.dumps(lcs_result, ensure_ascii=False, indent=2))
        else:
            print(lcs_result["longest_common_substring"])
        return 0

    text = _resolve_text(args)
    automaton = SuffixAutomaton(text)

    if args.command == "analyze":
        result = automaton.analysis()
        if args.json:
            print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
        else:
            print(f"length: {result.text_length}")
            print(f"states: {result.state_count}")
            print(f"distinct_substrings: {result.distinct_substrings}")
            print(f"longest_repeated_substring: {result.longest_repeated_substring!r}")
            print(f"longest_repeated_count: {result.longest_repeated_count}")
            print(f"alphabet: {''.join(result.alphabet)}")
        return 0

    if args.command == "contains":
        print("yes" if automaton.contains(args.substring) else "no")
        return 0

    if args.command == "count":
        print(automaton.occurrence_count(args.substring))
        return 0

    if args.command == "locate":
        locations = [asdict(location) for location in automaton.locate(args.substring, limit=args.limit)]
        print(json.dumps(locations, indent=2))
        return 0

    if args.command == "export":
        _write_or_print(automaton.to_json(), args.output)
        return 0

    if args.command == "dot":
        _write_or_print(automaton.to_graphviz(), args.output)
        return 0

    if args.command == "kth":
        print(automaton.kth_distinct_substring(args.k))
        return 0

    if args.command == "absent":
        alphabet = None if args.alphabet is None else list(args.alphabet)
        print(automaton.shortest_absent_substring(alphabet=alphabet))
        return 0

    if args.command == "repeats":
        repeated = automaton.top_repeated_substrings(limit=args.limit, min_length=args.min_length)
        if args.json:
            print(json.dumps([asdict(item) for item in repeated], ensure_ascii=False, indent=2))
        else:
            for item in repeated:
                print(f"{item.substring}\tlen={item.length}\tcount={item.occurrences}")
        return 0

    parser.error(f"unsupported command: {args.command}")
    return 2
