"""Console CLI for the LALR(1) parser generator.

Usage:
  python -m lalr.cli grammar_file --action=parse --input="1 + 2 * 3"
  python -m lalr.cli grammar_file --action=table
  python -m lalr.cli grammar_file --action=conflicts
  python -m lalr.cli grammar_file --action=dump --output=table.txt
  python -m lalr.cli grammar_file --action=slr-compare
  python -m lalr.cli grammar_file --action=save-table --output=table.json
  python -m lalr.cli grammar_file --action=load-table table.json --input="..."
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List

from .bnf_loader import load_bnf_full
from .grammar import Grammar
from .parser import Parser, Token
from .precedence import PrecedenceTable
from .slr_table import SLRTable
from .table import LALRTable


def _load_grammar_and_prec(path: str):
    with open(path) as f:
        text = f.read()
    return load_bnf_full(text)


def _lex_simple(text: str, terminals: set):
    """Very simple lexer: splits on whitespace, but keeps multi-char
    quoted terminals.  This is a convenience for testing — real users
    should provide their own lexer."""
    import re

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
            m = re.match(r"[A-Za-z_][A-Za-z0-9_]*", text[i:])
            if m:
                word = m.group()
                if word in terminals:
                    tokens.append(Token(word, word, i))
                elif "ID" in terminals:
                    tokens.append(Token("ID", word, i))
                else:
                    print(
                        f"Warning: unrecognized token '{word}' at pos {i}",
                        file=sys.stderr,
                    )
                    tokens.append(Token(word, word, i))
                i += len(word)
            else:
                # Try to match a number
                m = re.match(r"\d+", text[i:])
                if m and "NUMBER" in terminals:
                    tokens.append(Token("NUMBER", m.group(), i))
                    i += len(m.group())
                else:
                    print(
                        f"Warning: unrecognized character '{text[i]}' at pos {i}",
                        file=sys.stderr,
                    )
                    i += 1
    return tokens


def _cmd_visualize(args) -> int:
    """Generate Graphviz DOT output of the automaton."""
    from .visualize import automaton_to_dot, conflict_report
    grammar, precedence = _load_grammar_and_prec(args.grammar)
    table = LALRTable(grammar, precedence=precedence)
    dot = automaton_to_dot(
        table,
        title=args.grammar,
        show_lookaheads=args.lookaheads,
        horizontal=args.horizontal,
    )
    if args.output:
        with open(args.output, "w") as f:
            f.write(dot)
        print(f"DOT file written to {args.output}")
        print(f"Render with: dot -Tpng {args.output} -o {args.output}.png")
    else:
        print(dot)
    return 0


def _cmd_config(args) -> int:
    """Load a config file and run the parser."""
    from .config import LALRConfig
    config = LALRConfig.load(args.config_file)
    config.apply_logging()
    if not config.grammar_file:
        print("Error: config file has no grammar_file", file=sys.stderr)
        return 2
    with open(config.grammar_file) as f:
        grammar, precedence = load_bnf_full(f.read())
    table = LALRTable(grammar, precedence=precedence)
    if args.input:
        tokens = _lex_simple(args.input, grammar.terminals - {"$"})
        from .parser import Parser as StdParser
        from .error_recovery import RecoveringParser
        if config.parser.error_recovery:
            p = RecoveringParser(
                grammar, table=table,
                sync_tokens=set(config.parser.sync_tokens),
                max_errors=config.parser.max_errors,
            )
            p.debug = args.debug
            errors = []
            try:
                result = p.parse(tokens, on_error=errors.append)
                print(f"Parse successful. Result: {result}")
                if errors:
                    print(f"\n{len(errors)} error(s) recovered:")
                    for e in errors:
                        print(f"  {e}")
            except Exception as e:
                print(f"Parse error: {e}", file=sys.stderr)
                return 1
        else:
            p = StdParser(grammar, table=table)
            p.debug = args.debug
            try:
                result = p.parse(tokens)
                print(f"Parse successful. Result: {result}")
            except Exception as e:
                print(f"Parse error: {e}", file=sys.stderr)
                return 1
    else:
        print(table.summary())
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lalr",
        description="LALR(1) parser generator and analysis tool",
    )
    parser.add_argument("grammar", help="Path to BNF grammar file")
    parser.add_argument(
        "--action",
        choices=[
            "parse", "table", "conflicts", "dump", "states",
            "first-follow", "slr-compare", "save-table", "load-table",
            "precedence", "visualize", "config",
        ],
        default="table",
        help="What to do (default: table)",
    )
    parser.add_argument("--input", default=None, help="Input string to parse")
    parser.add_argument("--output", "-o", default=None, help="Output file")
    parser.add_argument("--debug", action="store_true", help="Debug parsing")
    parser.add_argument(
        "--table-file", default=None,
        help="Pre-computed table JSON (for load-table action)",
    )
    parser.add_argument(
        "--lookaheads", action="store_true",
        help="Show LALR(1) lookaheads in visualization",
    )
    parser.add_argument(
        "--horizontal", action="store_true",
        help="Horizontal layout for visualization",
    )
    parser.add_argument(
        "--config-file", default=None,
        help="JSON configuration file (for config action)",
    )
    args = parser.parse_args(argv)

    if args.action == "load-table":
        return _cmd_load_table(args)

    if args.action == "visualize":
        return _cmd_visualize(args)

    if args.action == "config":
        if args.config_file is None:
            print("Error: --config-file required for config action",
                  file=sys.stderr)
            return 2
        return _cmd_config(args)

    grammar, precedence = _load_grammar_and_prec(args.grammar)
    table = LALRTable(grammar, precedence=precedence)

    if args.action == "table":
        print(table.summary())
        if table.has_conflicts:
            return 1

    elif args.action == "conflicts":
        if table.has_conflicts:
            print(f"{len(table.conflicts)} unresolved conflict(s):")
            for c in table.conflicts:
                print(f"  {c}")
            return 1
        elif table.resolved_conflicts:
            print(f"No unresolved conflicts ({len(table.resolved_conflicts)} resolved by precedence).")
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

    elif args.action == "slr-compare":
        slr = SLRTable(grammar)
        print("=== LALR(1) ===")
        print(table.summary())
        print()
        print("=== SLR(1) ===")
        print(slr.summary())
        print()
        if table.has_conflicts and not slr.has_conflicts:
            print("Unexpected: LALR has conflicts but SLR doesn't!")
        elif not table.has_conflicts and slr.has_conflicts:
            print("Grammar is LALR(1) but NOT SLR(1) — LALR is more powerful.")
        elif not table.has_conflicts and not slr.has_conflicts:
            print("Grammar is both LALR(1) and SLR(1).")
        else:
            print("Grammar is neither LALR(1) nor SLR(1) — needs rewriting.")

    elif args.action == "save-table":
        data = table.to_json()
        out = json.dumps(data, indent=2)
        if args.output:
            with open(args.output, "w") as f:
                f.write(out)
            print(f"Table saved to {args.output}")
        else:
            print(out)

    elif args.action == "precedence":
        if precedence.levels:
            print(precedence.describe())
        else:
            print("No precedence declarations found.")

    elif args.action == "parse":
        if args.input is None:
            print("Error: --input required for parse action", file=sys.stderr)
            return 2
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


def _cmd_load_table(args) -> int:
    """Load a pre-computed table and parse input."""
    if args.table_file is None:
        print("Error: --table-file required for load-table action", file=sys.stderr)
        return 2
    with open(args.table_file) as f:
        data = json.load(f)
    table = LALRTable.from_json(data)
    if args.input is None:
        print("Error: --input required for parse action", file=sys.stderr)
        return 2
    tokens = _lex_simple(args.input, table.grammar.terminals - {"$"})
    p = Parser(table.grammar, table=table)
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
    sys.exit(main())