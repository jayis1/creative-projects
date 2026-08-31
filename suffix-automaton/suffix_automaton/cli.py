"""Command-line interface for suffix automaton analytics."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import Sequence

from .core import SuffixAutomaton, longest_common_substring


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

    lcs = subparsers.add_parser("lcs", help="longest common substring")
    lcs.add_argument("strings", nargs="+", help="two or more strings")

    return parser


def _add_text_argument(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="literal input text")
    group.add_argument("--file", type=Path, help="read input text from a file")


def _resolve_text(args: argparse.Namespace) -> str:
    if args.text is not None:
        return args.text
    return args.file.read_text(encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "lcs":
        value = longest_common_substring(args.strings)
        print(value)
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
        payload = automaton.to_json()
        if args.output is None:
            print(payload)
        else:
            args.output.write_text(payload, encoding="utf-8")
        return 0

    parser.error(f"unsupported command: {args.command}")
    return 2
