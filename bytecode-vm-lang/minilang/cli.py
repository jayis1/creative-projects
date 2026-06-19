"""MiniLang CLI — run, disassemble, or type-check MiniLang programs.

Usage::

    python -m minilang run <file>
    python -m minilang dis <file>
    python -m minilang check <file>
    python -m minilang repl
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .compiler import compile_program
from .bytecode import Disassembler
from .errors import MiniLangError
from .lexer import tokenize
from .parser import Parser
from .types import check_program
from .optimizer import optimize
from .vm import VM


def _read_source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def cmd_run(args: argparse.Namespace) -> int:
    code = _read_source(args.file)
    try:
        program = compile_program(code, name=args.file, debug=args.debug)
        vm = VM(program, debug=args.debug)
        vm.run()
    except MiniLangError as e:
        print(e.format(), file=sys.stderr)
        return 1
    return 0


def cmd_dis(args: argparse.Namespace) -> int:
    code = _read_source(args.file)
    try:
        program = compile_program(code, name=args.file, debug=args.debug)
    except MiniLangError as e:
        print(e.format(), file=sys.stderr)
        return 1
    print(Disassembler(program.main.code, program.strings, "main").disassemble())
    for name, chunk in program.functions.items():
        print()
        print(Disassembler(chunk.code, program.strings, name).disassemble())
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    code = _read_source(args.file)
    try:
        tokens = tokenize(code, name=args.file)
        ast = Parser(tokens, name=args.file).parse_program()
        check_program(ast)
    except MiniLangError as e:
        print(e.format(), file=sys.stderr)
        return 1
    print("OK: no type errors.")
    return 0


def cmd_repl(args: argparse.Namespace) -> int:
    """A simple REPL that evaluates one line at a time."""
    print(f"MiniLang {__version__} REPL. Type 'quit' to exit.")
    while True:
        try:
            line = input("ml> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if line.strip() in ("quit", "exit"):
            break
        if not line.strip():
            continue
        # Wrap in a print() so the result is displayed.
        wrapped = line if line.rstrip().endswith(";") else line + ";"
        try:
            program = compile_program(wrapped, name="<repl>", debug=args.debug)
            vm = VM(program, debug=args.debug)
            result = vm.run()
            if result.tag.value != 3:  # not NIL
                print(f"=> {result.display()}")
        except MiniLangError as e:
            print(e.format())


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="minilang",
                                description="MiniLang bytecode VM")
    p.add_argument("--version", action="version", version=f"minilang {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Execute a MiniLang file")
    run.add_argument("file")
    run.add_argument("--debug", action="store_true", help="Enable debug output")
    run.set_defaults(func=cmd_run)

    dis = sub.add_parser("dis", help="Disassemble a MiniLang file")
    dis.add_argument("file")
    dis.add_argument("--debug", action="store_true")
    dis.set_defaults(func=cmd_dis)

    chk = sub.add_parser("check", help="Type-check a MiniLang file")
    chk.add_argument("file")
    chk.set_defaults(func=cmd_check)

    repl = sub.add_parser("repl", help="Start the REPL")
    repl.add_argument("--debug", action="store_true")
    repl.set_defaults(func=cmd_repl)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    rc = args.func(args)
    return rc if rc is not None else 0


if __name__ == "__main__":
    sys.exit(main())