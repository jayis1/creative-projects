"""Command-line interface for earley-parser.

Subcommands:
    recognize  — Check if input is in the grammar's language
    tree       — Parse and show parse tree(s)
    forest     — Parse and output the parse forest as JSON
    check      — Validate a grammar file
    analyze    — Analyze a grammar (LL(1), FOLLOW sets, stats, ambiguity)
    demo       — Run the built-in demo
    cyk        — Parse using the CYK algorithm
    ll1        — Build and display the LL(1) parsing table
    chart      — Dump chart contents after parsing
    config     — Parse using a config file
"""
from __future__ import annotations

import argparse
import json
import sys
import logging
from typing import List, Optional

from .grammar import Grammar, GrammarLoader
from .parser import EarleyParser, ParseForest
from .tokenizer import Tokenizer, TokenSpec
from .errors import ParseError, GrammarError
from .analysis import LL1Table, is_ll1, grammar_summary, detect_ambiguity
from .config import load_config


def _build_demo_grammar() -> Grammar:
    """Build the classic ambiguous expression grammar."""
    return Grammar.from_rules(
        start="E",
        rules=[
            ("E", ("E", "+", "E")),
            ("E", ("E", "*", "E")),
            ("E", ("(", "E", ")")),
            ("E", ("id",)),
        ],
        name="demo-expr",
    )


def _load_grammar(path: Optional[str]) -> Grammar:
    """Load a grammar from a file path, or fall back to the demo grammar."""
    if path:
        return GrammarLoader.load_file(path)
    return _build_demo_grammar()


def _cmd_demo(args: argparse.Namespace) -> int:
    """Run the built-in demo."""
    g = _build_demo_grammar()
    parser = EarleyParser(g)
    inputs = [
        ["id"],
        ["id", "+", "id"],
        ["id", "+", "id", "*", "id"],
        ["(", "id", "+", "id", ")", "*", "id"],
        ["id", "+"],
        ["+", "id"],
    ]
    print("=== Recognition Demo ===\n")
    for tokens in inputs:
        ok = parser.parse(tokens)
        print(f"{'✓' if ok else '✗'}  {' '.join(tokens)}")
    print("\n=== Parse Tree Demo ===")
    print("Parse tree for 'id + id * id':")
    try:
        trees = parser.trees(["id", "+", "id", "*", "id"], max_trees=3)
        for i, t in enumerate(trees):
            print(f"\n--- Tree {i + 1} ---")
            print(t.pretty())
    except ParseError as e:
        print(f"Error: {e}")
    print("\n=== Forest Demo ===")
    forest = parser.forest(["id", "+", "id", "*", "id"], max_trees=10)
    print(f"Forest: {forest.ambiguity_count} tree(s), ambiguous={forest.is_ambiguous}")
    print(forest.stats())
    print("\n=== Analysis Demo ===")
    print(grammar_summary(g))
    return 0


def _cmd_recognize(args: argparse.Namespace) -> int:
    """Check if input is in the grammar's language."""
    g = _load_grammar(args.grammar)
    parser = EarleyParser(g)
    tokens = args.input
    if not tokens:
        print("Error: no input tokens provided.", file=sys.stderr)
        return 1
    result = parser.parse_or_error(tokens)
    if result is True:
        print(f"✓ Accepted: {' '.join(tokens)}")
        return 0
    else:
        print(f"✗ {result}")
        return 1


def _cmd_tree(args: argparse.Namespace) -> int:
    """Parse and show parse tree(s)."""
    g = _load_grammar(args.grammar)
    parser = EarleyParser(g)
    tokens = args.input
    if not tokens:
        print("Error: no input tokens provided.", file=sys.stderr)
        return 1
    try:
        trees = parser.trees(tokens, max_trees=args.max)
        print(f"Found {len(trees)} parse tree(s):\n")
        for i, t in enumerate(trees):
            print(f"--- Tree {i + 1} ---")
            print(t.pretty())
            print()
    except ParseError as e:
        print(f"✗ {e}")
        return 1
    return 0


def _cmd_forest(args: argparse.Namespace) -> int:
    """Parse and output the parse forest as JSON."""
    g = _load_grammar(args.grammar)
    parser = EarleyParser(g)
    tokens = args.input
    if not tokens:
        print("Error: no input tokens provided.", file=sys.stderr)
        return 1
    try:
        forest = parser.forest(tokens, max_trees=args.max)
        if args.format == "json":
            print(forest.to_json())
        elif args.format == "dot":
            print(forest.to_dot())
        elif args.format == "lisp":
            print(forest.to_lisp())
        else:
            print(forest.pretty())
    except ParseError as e:
        print(json.dumps({"error": str(e)}))
        return 1
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    """Validate a grammar file."""
    g = GrammarLoader.load_file(args.grammar)
    problems = g.validate()
    if problems:
        print("Grammar problems found:")
        for prob in problems:
            print(f"  - {prob}")
        return 1
    print("Grammar is valid.")
    print(f"  Start: {g.start}")
    print(f"  Non-terminals: {len(g.productions)}")
    print(f"  Productions: {sum(len(v) for v in g.productions.values())}")
    print(f"  Nullable: {sorted(g.nullable())}")
    stats = g.stats()
    print(f"  Terminals: {stats.terminal_count}")
    print(f"  Max RHS length: {stats.max_rhs_length}")
    return 0


def _cmd_analyze(args: argparse.Namespace) -> int:
    """Analyze a grammar."""
    g = GrammarLoader.load_file(args.grammar)
    print(grammar_summary(g))
    if args.ambiguity:
        print("\n=== Ambiguity Detection ===")
        ambiguous = detect_ambiguity(g, max_length=args.max_length)
        if ambiguous:
            print(f"Found {len(ambiguous)} ambiguous input(s):")
            for tokens in ambiguous[:10]:
                print(f"  {' '.join(tokens)}")
            if len(ambiguous) > 10:
                print(f"  ... and {len(ambiguous) - 10} more")
        else:
            print("No ambiguity detected (up to length "
                  f"{args.max_length}).")
    return 0


def _cmd_ll1(args: argparse.Namespace) -> int:
    """Build and display the LL(1) parsing table."""
    g = GrammarLoader.load_file(args.grammar)
    table = LL1Table(g).build()
    print(f"LL(1): {'yes' if table.is_ll1 else 'NO'}")
    if table.conflicts:
        print(f"\nConflicts ({len(table.conflicts)}):")
        for c in table.conflicts:
            print(f"  - {c}")
    print()
    print(table.pretty())
    return 0 if table.is_ll1 else 1


def _cmd_chart(args: argparse.Namespace) -> int:
    """Dump chart contents after parsing."""
    g = _load_grammar(args.grammar)
    parser = EarleyParser(g)
    tokens = args.input
    if not tokens:
        print("Error: no input tokens provided.", file=sys.stderr)
        return 1
    parser.parse(tokens)
    print(parser.chart_dump())
    print("\nChart sizes:", parser.chart_stats())
    return 0


def _cmd_cyk(args: argparse.Namespace) -> int:
    """Parse using the CYK algorithm."""
    from .cyk import CNFGrammar, CYKParser
    g = GrammarLoader.load_file(args.grammar)
    # For demo purposes, build a simple CNF grammar manually
    # (full CNF conversion is out of scope for the CLI)
    cnf = CNFGrammar(start=g.start)
    has_rules = False
    for nt, rhss in g.productions.items():
        for rhs in rhss:
            if len(rhs) == 1 and g.is_terminal(rhs[0]):
                cnf.add_terminal(nt, rhs[0])
                has_rules = True
            elif len(rhs) == 2 and all(g.is_nonterminal(s) for s in rhs):
                cnf.add_binary(nt, rhs[0], rhs[1])
                has_rules = True
            elif len(rhs) == 0:
                if nt == g.start:
                    cnf.set_start_nullable()
                has_rules = True
            else:
                print(f"Warning: skipping non-CNF rule {nt} -> {rhs}",
                      file=sys.stderr)
    if not has_rules:
        print("Error: grammar has no CNF-compatible rules.", file=sys.stderr)
        return 1
    cyk_parser = CYKParser(cnf)
    tokens = args.input
    if not tokens:
        print("Error: no input tokens provided.", file=sys.stderr)
        return 1
    if cyk_parser.parse(tokens):
        print(f"✓ Accepted (CYK): {' '.join(tokens)}")
        if args.tree:
            trees = cyk_parser.trees(tokens, max_trees=args.max)
            print(f"\nFound {len(trees)} parse tree(s):")
            for i, t in enumerate(trees):
                print(f"\n--- Tree {i + 1} ---")
                print(t.pretty())
        return 0
    else:
        print(f"✗ Rejected (CYK): {' '.join(tokens)}")
        return 1


def _cmd_config(args: argparse.Namespace) -> int:
    """Parse using a config file."""
    cfg = load_config(args.config)
    cfg.setup_logging()
    g = cfg.get_grammar()
    parser = EarleyParser(g)

    # Build tokenizer if specified
    if cfg.tokenizer_specs:
        tok = Tokenizer(cfg.get_token_specs())
        text = " ".join(args.input)
        tokens = tok.tokenize(text)
    else:
        tokens = args.input

    if not tokens:
        print("Error: no input provided.", file=sys.stderr)
        return 1

    try:
        forest = parser.forest(tokens, max_trees=cfg.max_trees)
        print(f"Found {len(forest)} parse tree(s):")
        print(forest.pretty())
        return 0
    except ParseError as e:
        print(f"✗ {e}")
        return 1


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    p = argparse.ArgumentParser(
        prog="earley",
        description=(
            "Earley parser for general context-free grammars. "
            "Supports recognition, parse tree extraction, ambiguity "
            "detection, LL(1) analysis, CYK parsing, and more."
        ),
    )
    sub = p.add_subparsers(dest="command", required=True)

    # recognize
    p_rec = sub.add_parser(
        "recognize", help="Check if input is in the grammar's language"
    )
    p_rec.add_argument("--grammar", "-g", help="Grammar file (.bnf)", default=None)
    p_rec.add_argument("input", nargs="*", help="Tokens (space-separated)")
    p_rec.set_defaults(func=_cmd_recognize)

    # tree
    p_tree = sub.add_parser("tree", help="Parse and show parse tree(s)")
    p_tree.add_argument("--grammar", "-g", help="Grammar file (.bnf)", default=None)
    p_tree.add_argument("--max", type=int, default=10, help="Max trees to show")
    p_tree.add_argument("input", nargs="*", help="Tokens (space-separated)")
    p_tree.set_defaults(func=_cmd_tree)

    # forest
    p_forest = sub.add_parser("forest", help="Parse and output the parse forest")
    p_forest.add_argument("--grammar", "-g", help="Grammar file (.bnf)", default=None)
    p_forest.add_argument("--max", type=int, default=50, help="Max trees")
    p_forest.add_argument(
        "--format", choices=["json", "dot", "lisp", "text"],
        default="text", help="Output format"
    )
    p_forest.add_argument("input", nargs="*", help="Tokens")
    p_forest.set_defaults(func=_cmd_forest)

    # check
    p_check = sub.add_parser("check", help="Validate a grammar file")
    p_check.add_argument("grammar", help="Grammar file path")
    p_check.set_defaults(func=_cmd_check)

    # analyze
    p_analyze = sub.add_parser("analyze", help="Analyze a grammar")
    p_analyze.add_argument("grammar", help="Grammar file path")
    p_analyze.add_argument("--ambiguity", action="store_true",
                           help="Run empirical ambiguity detection")
    p_analyze.add_argument("--max-length", type=int, default=5,
                           help="Max input length for ambiguity check")
    p_analyze.set_defaults(func=_cmd_analyze)

    # ll1
    p_ll1 = sub.add_parser("ll1", help="Build and display the LL(1) parsing table")
    p_ll1.add_argument("grammar", help="Grammar file path")
    p_ll1.set_defaults(func=_cmd_ll1)

    # chart
    p_chart = sub.add_parser("chart", help="Dump chart contents after parsing")
    p_chart.add_argument("--grammar", "-g", help="Grammar file (.bnf)", default=None)
    p_chart.add_argument("input", nargs="*", help="Tokens")
    p_chart.set_defaults(func=_cmd_chart)

    # cyk
    p_cyk = sub.add_parser("cyk", help="Parse using the CYK algorithm (CNF only)")
    p_cyk.add_argument("grammar", help="Grammar file path (must be near-CNF)")
    p_cyk.add_argument("--tree", action="store_true", help="Show parse trees")
    p_cyk.add_argument("--max", type=int, default=10, help="Max trees")
    p_cyk.add_argument("input", nargs="*", help="Tokens")
    p_cyk.set_defaults(func=_cmd_cyk)

    # demo
    p_demo = sub.add_parser("demo", help="Run the built-in demo")
    p_demo.set_defaults(func=_cmd_demo)

    # config
    p_config = sub.add_parser("config", help="Parse using a config file")
    p_config.add_argument("config", help="Config file (.json/.yaml/.toml)")
    p_config.add_argument("input", nargs="*", help="Input text or tokens")
    p_config.set_defaults(func=_cmd_config)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entry point.

    Parameters
    ----------
    argv : list[str] or None
        Command-line arguments (defaults to ``sys.argv[1:]``).

    Returns
    -------
    int
        Exit code (0 for success, 1 for error).
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except GrammarError as e:
        print(f"Grammar error: {e}", file=sys.stderr)
        return 1
    except ParseError as e:
        print(f"Parse error: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"File not found: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())