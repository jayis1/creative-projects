"""
turing_machine.cli
==================

Command-line interface for running and inspecting Turing machines.

Usage examples
--------------
Run a built-in machine::

    python -m turing_machine.cli run binary_incrementer --input 1011 --trace

Parse and run a definition file::

    python -m turing_machine.cli run-file increment.tm --input 1011

List built-in machines::

    python -m turing_machine.cli list

Render a tape::

    python -m turing_machine.cli render --input 10110
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from .machine import Tape, TMDirection, TuringMachine
from .machines import list_machines, get_machine
from .def_parser import parse_file


def _parse_input(s: Optional[str], blank: str = "_") -> List:
    """Parse an input string into a list of symbols.

    By default each character is one symbol.  If ``s`` is None, return [].
    """
    if s is None:
        return []
    return list(s)


def cmd_run(args: argparse.Namespace) -> int:
    name = args.machine
    try:
        program = get_machine(name)
    except KeyError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    input_symbols = _parse_input(args.input)
    blank = "_"
    halt = {"halt", "accept", "reject", "HALT"}
    tm = TuringMachine(program, initial_state="s0" if name != "busy_beaver_4" else "A",
                       tape=input_symbols, blank=blank, halt_states=halt,
                       max_steps=args.max_steps)
    if args.trace:
        tm.run(record=True, verbose=True)
    else:
        tm.run()
    print(f"final state: {tm.state}")
    print(f"steps:       {tm.steps}")
    print(f"halted:       {tm.halted}")
    print("tape:")
    print(tm.tapes[0].render())
    if args.json:
        out = {
            "state": tm.state,
            "steps": tm.steps,
            "halted": tm.halted,
            "tape": [str(s) for s in tm.tapes[0].to_list()],
        }
        print(json.dumps(out, indent=2))
    return 0


def cmd_run_file(args: argparse.Namespace) -> int:
    try:
        md = parse_file(args.file)
    except FileNotFoundError:
        print(f"error: file not found: {args.file}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    input_symbols = _parse_input(args.input, str(md.blank))
    tm = md.to_machine(tape=input_symbols, max_steps=args.max_steps)
    if args.trace:
        tm.run(record=True, verbose=True)
    else:
        tm.run()
    print(f"final state: {tm.state}")
    print(f"steps:       {tm.steps}")
    print(f"halted:       {tm.halted}")
    print("tape:")
    print(tm.tapes[0].render())
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    print("Available machines:")
    for name in list_machines():
        print(f"  {name}")
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    input_symbols = _parse_input(args.input)
    t = Tape("_", input_symbols)
    print(t.render())
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Run the palindrome checker on the given input and report accept/reject."""
    program = get_machine("palindrome_checker")
    input_symbols = _parse_input(args.input)
    halt = {"halt", "accept", "reject"}
    tm = TuringMachine(program, initial_state="s0", tape=input_symbols, blank="_",
                       halt_states=halt, max_steps=args.max_steps)
    final = tm.run()
    if final == "accept":
        print("ACCEPT")
        return 0
    elif final == "reject":
        print("REJECT")
        return 1
    else:
        print(f"UNKNOWN (state={final})")
        return 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="turing_machine", description="Turing machine simulator")
    sub = p.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run a built-in machine")
    run.add_argument("machine", help="Name of the built-in machine")
    run.add_argument("--input", "-i", default="", help="Input tape symbols (a string)")
    run.add_argument("--max-steps", type=int, default=1_000_000)
    run.add_argument("--trace", action="store_true", help="Trace each step to stderr")
    run.add_argument("--json", action="store_true", help="Output results as JSON")
    run.set_defaults(func=cmd_run)

    rf = sub.add_parser("run-file", help="Run a machine defined in a .tm file")
    rf.add_argument("file", help="Path to the .tm definition file")
    rf.add_argument("--input", "-i", default="", help="Input tape symbols")
    rf.add_argument("--max-steps", type=int, default=1_000_000)
    rf.add_argument("--trace", action="store_true")
    rf.set_defaults(func=cmd_run_file)

    ls = sub.add_parser("list", help="List built-in machines")
    ls.set_defaults(func=cmd_list)

    rd = sub.add_parser("render", help="Render an input tape")
    rd.add_argument("--input", "-i", default="", help="Input tape")
    rd.set_defaults(func=cmd_render)

    ck = sub.add_parser("check", help="Check if input is a palindrome")
    ck.add_argument("input", help="The binary string to check")
    ck.add_argument("--max-steps", type=int, default=1_000_000)
    ck.set_defaults(func=cmd_check)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())