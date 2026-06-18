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

Analyze a machine::

    python -m turing_machine.cli analyze binary_incrementer

Save/restore machine state::

    python -m turing_machine.cli save binary_incrementer --input 1011 --output state.json
    python -m turing_machine.cli load state.json
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from .machine import Tape, TMDirection, TuringMachine
from .machines import list_machines, get_machine
from .def_parser import parse_file
from .analysis import analyze_machine
from .serialization import save_machine, load_machine, serialize_machine


# Machine name to initial state mapping
INITIAL_STATES = {
    "binary_incrementer": "s0",
    "binary_decrementer": "s0",
    "unary_adder": "s0",
    "palindrome_checker": "s0",
    "copy_machine": "s0",
    "busy_beaver_4": "A",
}

# Machine name to blank symbol mapping
MACHINE_BLANKS = {
    "busy_beaver_4": "0",
}


def _parse_input(s: Optional[str], blank: str = "_") -> List:
    """Parse an input string into a list of symbols.

    By default each character is one symbol.  If ``s`` is None, return [].
    """
    if s is None:
        return []
    return list(s)


def _make_machine(name: str, input_str: str, max_steps: int) -> TuringMachine:
    """Create a TuringMachine from a built-in name."""
    program = get_machine(name)
    blank = MACHINE_BLANKS.get(name, "_")
    initial = INITIAL_STATES.get(name, "s0")
    halt = {"halt", "accept", "reject", "HALT"}
    input_symbols = _parse_input(input_str, blank)
    return TuringMachine(program, initial_state=initial, tape=input_symbols,
                          blank=blank, halt_states=halt, max_steps=max_steps)


def cmd_run(args: argparse.Namespace) -> int:
    name = args.machine
    try:
        tm = _make_machine(name, args.input, args.max_steps)
    except KeyError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
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


def cmd_analyze(args: argparse.Namespace) -> int:
    """Analyze a built-in machine's structure."""
    name = args.machine
    try:
        tm = _make_machine(name, args.input or "", args.max_steps)
    except KeyError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    # Run the machine first
    tm.run()
    analysis = analyze_machine(tm)
    if args.json:
        print(json.dumps(analysis, indent=2, default=str))
    else:
        print(f"Machine: {name}")
        print(f"  Initial state:    {analysis['initial_state']}")
        print(f"  Halt states:      {analysis['halt_states']}")
        print(f"  Total states:     {analysis['total_states']}")
        print(f"  Total transitions:{analysis['total_transitions']}")
        print(f"  Reachable states: {analysis['reachable_states']}")
        print(f"  Dead states:      {analysis['dead_states']}")
        if analysis['dead_states']:
            print(f"  ⚠ Dead states are reachable but can never halt!")
        print(f"  Unused states:    {analysis['unused_states']}")
        print(f"  Steps executed:   {analysis['steps_executed']}")
        print(f"  Halted:           {analysis['halted']}")
        if analysis['transitions_per_state']:
            print(f"  Transitions per state:")
            for state, count in sorted(analysis['transitions_per_state'].items()):
                print(f"    {state}: {count}")
    return 0


def cmd_save(args: argparse.Namespace) -> int:
    """Run a machine and save its final state to a JSON file."""
    name = args.machine
    try:
        tm = _make_machine(name, args.input, args.max_steps)
    except KeyError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    tm.run()
    save_machine(tm, args.output)
    print(f"Saved machine state to {args.output}")
    print(f"  final state: {tm.state}, steps: {tm.steps}, halted: {tm.halted}")
    return 0


def cmd_load(args: argparse.Namespace) -> int:
    """Load and display a saved machine state."""
    try:
        tm = load_machine(args.file)
    except FileNotFoundError:
        print(f"error: file not found: {args.file}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(f"Loaded machine from {args.file}")
    print(f"  state: {tm.state}, steps: {tm.steps}, halted: {tm.halted}")
    print(f"  tape:")
    print(tm.tapes[0].render())
    if args.json:
        print(json.dumps(serialize_machine(tm), indent=2))
    return 0


def cmd_step(args: argparse.Namespace) -> int:
    """Step through a machine N steps and display each."""
    name = args.machine
    try:
        tm = _make_machine(name, args.input, args.max_steps)
    except KeyError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    n = args.n
    print(f"Stepping {n} steps:")
    for i in range(n):
        if not tm.step():
            print(f"  Machine halted at step {tm.steps} (state={tm.state})")
            break
        print(f"  step {tm.steps}: state={tm.state}")
        print(f"  {tm.tapes[0].render()}")
        print()
    return 0


def cmd_visualize(args: argparse.Namespace) -> int:
    """Generate an HTML animation of a machine's execution."""
    from .visualizer import html_animation, svg_diagram, text_trace, csv_trace
    name = args.machine
    try:
        tm = _make_machine(name, args.input, args.max_steps)
    except KeyError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    fmt = args.format
    if fmt == "html":
        output = args.output or f"{name}_animation.html"
        html_animation(tm, output, title=name, delay_ms=args.delay)
        print(f"HTML animation saved to {output}")
    elif fmt == "svg":
        output = args.output or f"{name}_diagram.svg"
        svg_diagram(tm.program, tm.initial_state, tm.halt_states, output)
        print(f"SVG diagram saved to {output}")
    elif fmt == "text":
        if args.output:
            with open(args.output, "w") as f:
                f.write(text_trace(tm))
            print(f"Text trace saved to {args.output}")
        else:
            print(text_trace(tm))
    elif fmt == "csv":
        if args.output:
            with open(args.output, "w") as f:
                f.write(csv_trace(tm))
            print(f"CSV trace saved to {args.output}")
        else:
            print(csv_trace(tm))
    else:
        print(f"error: unknown format '{fmt}'", file=sys.stderr)
        return 2
    return 0


def cmd_compose(args: argparse.Namespace) -> int:
    """Run a pipeline of machines."""
    from .composition import Pipeline
    from .machines import get_machine
    pipe = Pipeline()
    for spec in args.machines:
        parts = spec.split(":")
        name = parts[0]
        init = parts[1] if len(parts) > 1 else "s0"
        halt = parts[2] if len(parts) > 2 else "halt"
        try:
            prog = get_machine(name)
        except KeyError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        pipe.add(prog, init, halt, name=name)
    result = pipe.run(list(args.input))
    print(pipe.summary())
    print(f"\nFinal tape: {''.join(str(c) for c in result)}")
    return 0


def cmd_universal(args: argparse.Namespace) -> int:
    """Run a machine through the Universal Turing Machine."""
    from .universal import simulate, encode_machine, UniversalTuringMachine
    name = args.machine
    try:
        tm = _make_machine(name, args.input, args.max_steps)
    except KeyError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    # Reset and encode
    tm.reset()
    input_symbols = list(args.input) if args.input else []
    encoded = encode_machine(tm, input_symbols)
    print(f"Encoded length: {len(encoded)} chars")
    print(f"Encoded: {encoded[:200]}{'...' if len(encoded) > 200 else ''}")
    # Run via UTM
    utm = UniversalTuringMachine(encoded)
    final = utm.run()
    print(f"UTM final state: {final}")
    print(f"UTM steps: {utm.steps}")
    print(f"UTM tape: {''.join(str(c) for c in utm.tape.to_list())}")
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    """Load and run a machine from a config file."""
    from .config import load_config, config_to_machine, ConfigError
    try:
        data = load_config(args.file)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except ConfigError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    input_symbols = _parse_input(args.input)
    try:
        tm = config_to_machine(data, tape=input_symbols, max_steps=args.max_steps)
    except ConfigError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    tm.run()
    print(f"Machine: {data.get('name', '<unnamed>')}")
    print(f"  final state: {tm.state}")
    print(f"  steps:       {tm.steps}")
    print(f"  halted:      {tm.halted}")
    print(f"  tape:")
    print(tm.tapes[0].render())
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="turing_machine",
        description="Turing machine simulator — run, debug, analyze, and visualize",
    )
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

    an = sub.add_parser("analyze", help="Analyze a machine's structure")
    an.add_argument("machine", help="Name of the built-in machine")
    an.add_argument("--input", "-i", default="", help="Input tape symbols")
    an.add_argument("--max-steps", type=int, default=1_000_000)
    an.add_argument("--json", action="store_true", help="Output as JSON")
    an.set_defaults(func=cmd_analyze)

    sv = sub.add_parser("save", help="Run a machine and save its state to JSON")
    sv.add_argument("machine", help="Name of the built-in machine")
    sv.add_argument("--input", "-i", default="", help="Input tape symbols")
    sv.add_argument("--output", "-o", required=True, help="Output JSON file path")
    sv.add_argument("--max-steps", type=int, default=1_000_000)
    sv.set_defaults(func=cmd_save)

    ld = sub.add_parser("load", help="Load and display a saved machine state")
    ld.add_argument("file", help="Path to the saved JSON file")
    ld.add_argument("--json", action="store_true", help="Output full JSON")
    ld.set_defaults(func=cmd_load)

    st = sub.add_parser("step", help="Step through a machine N steps")
    st.add_argument("machine", help="Name of the built-in machine")
    st.add_argument("--input", "-i", default="", help="Input tape symbols")
    st.add_argument("--n", type=int, default=10, help="Number of steps to execute")
    st.add_argument("--max-steps", type=int, default=1_000_000)
    st.set_defaults(func=cmd_step)

    vz = sub.add_parser("visualize", help="Generate visual output (HTML/SVG/text/CSV)")
    vz.add_argument("machine", help="Name of the built-in machine")
    vz.add_argument("--input", "-i", default="", help="Input tape symbols")
    vz.add_argument("--format", "-f", choices=["html", "svg", "text", "csv"], default="html")
    vz.add_argument("--output", "-o", default=None, help="Output file path")
    vz.add_argument("--delay", type=int, default=500, help="Animation delay in ms (HTML)")
    vz.add_argument("--max-steps", type=int, default=1_000_000)
    vz.set_defaults(func=cmd_visualize)

    cp = sub.add_parser("compose", help="Run a pipeline of machines")
    cp.add_argument("machines", nargs="+", help="Machine specs: name[:init_state:halt_state]")
    cp.add_argument("--input", "-i", default="", help="Input tape symbols")
    cp.set_defaults(func=cmd_compose)

    ut = sub.add_parser("universal", help="Run a machine through the Universal Turing Machine")
    ut.add_argument("machine", help="Name of the built-in machine")
    ut.add_argument("--input", "-i", default="", help="Input tape symbols")
    ut.add_argument("--max-steps", type=int, default=1_000_000)
    ut.set_defaults(func=cmd_universal)

    cf = sub.add_parser("config", help="Load and run a machine from a JSON/YAML config file")
    cf.add_argument("file", help="Path to the config file (.json or .yaml)")
    cf.add_argument("--input", "-i", default="", help="Input tape symbols")
    cf.add_argument("--max-steps", type=int, default=1_000_000)
    cf.set_defaults(func=cmd_config)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())