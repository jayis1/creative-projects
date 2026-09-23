#!/usr/bin/env python3
"""Command-line interface for the generative poetry engine."""

from __future__ import annotations
import argparse
import sys
from poetry_gen import PoetryEngine
from poetry_gen.vocabulary import Vocabulary

FORMS = ["haiku", "limerick", "free_verse", "acrostic", "sonnet", "random"]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="poetry",
        description="Generative poetry engine — create poems in multiple forms.",
    )
    p.add_argument(
        "form",
        nargs="?",
        default="random",
        choices=FORMS,
        help="Poem form (default: random)",
    )
    p.add_argument(
        "-t", "--theme",
        choices=Vocabulary.themes(),
        default=None,
        help="Vocabulary theme (default: random)",
    )
    p.add_argument(
        "-k", "--keyword",
        default=None,
        help="Keyword for acrostic poems",
    )
    p.add_argument(
        "-n", "--count",
        type=int,
        default=1,
        metavar="N",
        help="Number of poems to generate (default: 1)",
    )
    p.add_argument(
        "-l", "--lines",
        type=int,
        default=None,
        metavar="L",
        help="Number of lines for free verse (default: random 6-12)",
    )
    p.add_argument(
        "-s", "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )
    p.add_argument(
        "--themes",
        action="store_true",
        help="List available themes and exit",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)

    if args.themes:
        print("Available themes: " + ", ".join(Vocabulary.themes()))
        return 0

    engine = PoetryEngine(theme=args.theme, seed=args.seed)

    for i in range(args.count):
        if i > 0:
            print("\n" + "─" * 40 + "\n")
        form = None if args.form == "random" else args.form
        if form == "acrostic":
            poem = engine.acrostic(keyword=args.keyword)
        elif form == "free_verse":
            poem = engine.free_verse(n_lines=args.lines)
        else:
            poem = engine.random_poem(form=form)
        print(poem)

    return 0


if __name__ == "__main__":
    sys.exit(main())
