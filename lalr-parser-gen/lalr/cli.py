"""Console CLI for the LALR(1) parser generator.

Usage:
  python -m lalr.cli grammar_file --action=parse --input="1 + 2 * 3"
  python -m lalr.cli grammar_file --action=table
  python -m lalr.cli grammar_file --action=conflicts
  python -m lalr.cli grammar_file --action=dump --output=table.txt
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List

from .bnf_loader import load_bnf
from .parser import Parser, Token
from .table import LALRTable


def _load_grammar(path: str):
    with open(path) as f:
        text = f.read()
    return load_bnf(text)


def _lex_simple(text: str, terminals: set):
    """Very simple lexer: splits on whitespace, but keeps multi-char
    quoted terminals.  This is a convenience for testing — real users
    should provide their own lexer."""
    tokens = []
    i = 0
    while i < len(text):
        if text[i].isspace():
            i += 1
            continue
        # Try longest match against terminals
        matched = None
        for t in sorted(terminals, key=len, reverse=True):
            if text[i : i + len(t)] == t:
                matched = t
                break
        if matched:
            tokens.append(Token(matched, matched, i))
            i += len(matched)
        else:
            # Try to match an identifier-like token
            import re

            m = re.match(r"[A-Za-z_][A-Za-z0-9_]*", text[i:])
            if m:
                word = m.group()
                if word in terminals:
                    tokens.append(Token(word, word, i))
                else:
                    # Treat as a generic ID token if 'ID' is a terminal
                    if "ID" in terminals:
                        tokens.append(Token("ID", word, i))
                    else:
                        print(
                            f"Warning: unrecognized token '{word}' at pos {i}",
                            file=sys.stderr,
                        )
                        tokens.append(Token(word, word, i))
                i += len(word)
            else:
                print(
                    f"Warning: unrecognized character '{text[i]}' at pos {i}",
                    file=sys.stderr,
                )
                i += 1
    return tokens


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lalr",
        description="LALR(1) parser generator and analysis tool",
    )
    parser.add_argument("grammar", help="Path to BNF grammar file")
    parser.add_argument(
        "--action",
        choices=["parse", "table", "conflicts", "dump", "states", "first-follow"],
        default="table",
        help="What to do (default: table)",
    )
    parser.add_argument("--input", default=None, help="Input string to parse")
    parser.add_argument("--output", "-o", default=None, help="Output file")
    parser.add_argument("--debug", action="store_true", help="Debug parsing")
    args = parser.parse_args(argv)

    grammar = _load_grammar(args.grammar)
    table = LALRTable(grammar)

    if args.action == "table":
        print(table.summary())
        if table.has_conflicts:
            print("\nConflicts:")
            for c in table.conflicts:
                print(f"  {c}")
            return 1

    elif args.action == "conflicts":
        if table.has_conflicts:
            print(f"{len(table.conflicts)} conflict(s):")
            for c in table.conflicts:
                print(f"  {c}")
            return 1
        else:
            print("No conflicts — grammar is LALR(1).")
        return 0

    elif args.action == "dump":
        out = _dump_table(grammar, table)
        if args.output:
            with open(args.output, "w") as f:
                f.write(out)
            print(f"Table dumped to {args.output}")
        else:
            print(out)

    elif args.action == "states":
        _dump_states(grammar, table)

    elif args.action == "first-follow":
        print("FIRST sets:")
        for nt in sorted(grammar.nonterminals):
            if nt == Grammar.AUGMENTED_START:
                continue
            print(f"  {nt}: {sorted(grammar.first[nt])}")
        print("\nFOLLOW sets:")
        for nt in sorted(grammar.nonterminals):
            if nt == Grammar.AUGMENTED_START:
                continue
            print(f"  {nt}: {sorted(grammar.follow[nt])}")

    elif args.action == "parse":
        if args.input is None:
            print("Error: --input required for parse action", file=sys.stderr)
            return 2
        # Simple lexer
        tokens = _lex_simple(args.input, grammar.terminals - {"$"})
        p = Parser(grammar, table=table)
        p.debug = args.debug
        try:
            result = p.parse(tokens)
            print(f"Parse successful. Result: {result}")
        except Exception as e:
            print(f"Parse error: {e}", file=sys.stderr)
            return 1

    return 0


def _dump_table(grammar, table) -> str:
    lines = []
    lines.append(f"Grammar: {len(grammar.productions)} productions, "
                 f"{table.num_states} states\n")
    lines.append("Productions:")
    for p in grammar.productions:
        lines.append(f"  {p.index}: {p}")
    lines.append("")
    # ACTION table
    terms = sorted(grammar.terminals)
    lines.append("ACTION table:")
    header = f"{'State':>6} " + " ".join(f"{t:>8}" for t in terms)
    lines.append(header)
    for s in range(table.num_states):
        row = f"{s:>6} "
        for t in terms:
            act = table.action.get(s, {}).get(t)
            if act is None:
                cell = ""
            elif act[0] == "shift":
                cell = f"s{act[1]}"
            elif act[0] == "reduce":
                cell = f"r{act[1]}"
            elif act[0] == "accept":
                cell = "acc"
            else:
                cell = ""
            row += f" {cell:>8}"
        lines.append(row)
    # GOTO table
    nonterms = sorted(grammar.nonterminals - {Grammar.AUGMENTED_START})
    lines.append("\nGOTO table:")
    header = f"{'State':>6} " + " ".join(f"{nt:>8}" for nt in nonterms)
    lines.append(header)
    for s in range(table.num_states):
        row = f"{s:>6} "
        for nt in nonterms:
            g = table.goto.get(s, {}).get(nt, -1)
            cell = str(g) if g >= 0 else ""
            row += f" {cell:>8}"
        lines.append(row)
    return "\n".join(lines)


def _dump_states(grammar, table) -> None:
    for idx in range(table.num_states):
        state = table.automaton.get_state(idx)
        print(f"\n=== State {idx} ===")
        for item in sorted(state, key=lambda i: (i.production.index, i.dot)):
            las = table.lalr.lookaheads.get((idx, item), set())
            la_str = f"  / {sorted(las)}" if las else ""
            print(f"  {item}{la_str}")
        trans = table.automaton.transitions.get(idx, {})
        if trans:
            print("  Transitions:")
            for sym, target in sorted(trans.items()):
                print(f"    {sym} -> state {target}")


if __name__ == "__main__":
    from .grammar import Grammar
    sys.exit(main())