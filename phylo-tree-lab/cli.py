"""Command-line interface for scoring one Newick tree."""
import argparse
import sys
from pathlib import Path

from parsimony import fitch_score, parse_newick


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="score aligned sequences by Fitch parsimony")
    parser.add_argument("file", nargs="?", help="Newick input file (default: stdin)")
    args = parser.parse_args(argv)
    try:
        text = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
        print(fitch_score(parse_newick(text)))
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"phylo-tree-lab: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
