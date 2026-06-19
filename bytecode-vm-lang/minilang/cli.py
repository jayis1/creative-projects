"""MiniLang CLI — run, disassemble, type-check, benchmark, or REPL.

Usage::

    python -m minilang run <file>          # Execute a MiniLang file
    python -m minilang dis <file>          # Disassemble bytecode
    python -m minilang check <file>        # Type-check only
    python -m minilang repl                # Start the REPL
    python -m minilang benchmark <file>     # Benchmark execution time
    python -m minilang explain <file>      # Show AST + compilation pipeline info
    python -m minilang run <file> --no-opt # Disable optimizer
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from . import __version__
from .compiler import compile_program
from .bytecode import Disassembler, OpCode
from .errors import MiniLangError
from .lexer import tokenize
from .parser import Parser
from .types import check_program
from .optimizer import optimize
from .vm import VM

logger = logging.getLogger("minilang")


def _read_source(path: str) -> str:
    """Read a source file, raising a user-friendly error on failure."""
    p = Path(path)
    if not p.exists():
        print(f"error: file not found: {path}", file=sys.stderr)
        sys.exit(2)
    return p.read_text(encoding="utf-8")


def _load_config(path: str | None) -> dict:
    """Load a JSON configuration file (if provided).

    Recognised keys:
      - ``max_steps`` (int) — VM step limit
      - ``max_call_depth`` (int) — VM call depth limit
      - ``debug`` (bool) — enable debug/GC output
      - ``optimize`` (bool) — run the AST optimizer (default true)
    """
    if path is None:
        return {}
    p = Path(path)
    if not p.exists():
        print(f"error: config file not found: {path}", file=sys.stderr)
        sys.exit(2)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"error: invalid JSON config: {e}", file=sys.stderr)
        sys.exit(2)


def _setup_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level,
        format="[%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )


def cmd_run(args: argparse.Namespace) -> int:
    cfg = _load_config(args.config)
    _setup_logging(args.debug or cfg.get("debug", False))
    code = _read_source(args.file)
    try:
        do_opt = cfg.get("optimize", True)
        if args.no_opt:
            do_opt = False
        program = compile_program(code, name=args.file,
                                  debug=args.debug or cfg.get("debug", False),
                                  optimize_ast=do_opt)
        max_steps = cfg.get("max_steps", 10_000_000)
        max_call_depth = cfg.get("max_call_depth", 512)
        vm = VM(program, debug=args.debug or cfg.get("debug", False),
                max_steps=max_steps, max_call_depth=max_call_depth)
        vm.run()
    except MiniLangError as e:
        print(e.format(), file=sys.stderr)
        return 1
    return 0


def cmd_dis(args: argparse.Namespace) -> int:
    _setup_logging(args.debug)
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
    _setup_logging(args.debug)
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
    _setup_logging(args.debug)
    print(f"MiniLang {__version__} REPL. Type 'quit' to exit.")
    print("Supported: let/const, fn, if/elif/else, while, for, break, continue")
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


def cmd_benchmark(args: argparse.Namespace) -> int:
    """Benchmark MiniLang program execution time."""
    _setup_logging(False)
    code = _read_source(args.file)
    try:
        program = compile_program(code, name=args.file)
    except MiniLangError as e:
        print(e.format(), file=sys.stderr)
        return 1

    # Warmup run.
    vm = VM(program)
    vm.run()
    warmup_output = list(vm.output)

    # Timed runs.
    times: list[float] = []
    for _ in range(args.iterations):
        vm = VM(program)
        t0 = time.perf_counter()
        vm.run()
        t1 = time.perf_counter()
        times.append(t1 - t0)
        if vm.output != warmup_output:
            print("warning: non-deterministic output across runs", file=sys.stderr)

    avg = sum(times) / len(times)
    mn = min(times)
    mx = max(times)
    print(f"Benchmark: {args.file}")
    print(f"  Iterations:  {args.iterations}")
    print(f"  Average:     {avg * 1000:.3f} ms")
    print(f"  Min:         {mn * 1000:.3f} ms")
    print(f"  Max:         {mx * 1000:.3f} ms")
    print(f"  Throughput:  {1.0 / avg:.0f} runs/s" if avg > 0 else "")
    return 0


def cmd_explain(args: argparse.Namespace) -> int:
    """Show the full compilation pipeline for a source file."""
    _setup_logging(args.debug)
    code = _read_source(args.file)

    # Step 1: Lex
    print("=== LEXER ===")
    try:
        tokens = tokenize(code, name=args.file)
    except MiniLangError as e:
        print(e.format(), file=sys.stderr)
        return 1
    for tok in tokens:
        print(f"  {tok}")

    # Step 2: Parse
    print("\n=== PARSER ===")
    try:
        ast = Parser(tokens, name=args.file).parse_program()
    except MiniLangError as e:
        print(e.format(), file=sys.stderr)
        return 1
    _print_ast(ast, indent=0)

    # Step 3: Type check
    print("\n=== TYPE CHECKER ===")
    try:
        tc = check_program(ast)
    except MiniLangError as e:
        print(e.format(), file=sys.stderr)
        return 1
    print(f"  Functions: {len(tc.functions)}")
    for name, meta in tc.functions.items():
        print(f"    {name}: {meta.ftype} (nlocals={meta.nlocals})")
    print(f"  Expression types: {len(tc.expr_types)}")

    # Step 4: Optimize
    print("\n=== OPTIMIZER ===")
    opt_ast = optimize(ast)
    print(f"  Statements before: {len(ast.stmts)}")
    print(f"  Statements after:  {len(opt_ast.stmts)}")

    # Step 5: Compile
    print("\n=== COMPILER ===")
    try:
        program = compile_program(code, name=args.file, debug=args.debug)
    except MiniLangError as e:
        print(e.format(), file=sys.stderr)
        return 1
    total_instrs = sum(len(c.code) for c in program.all_chunks())
    print(f"  Chunks:          {1 + len(program.functions)}")
    print(f"  Total instructions: {total_instrs}")
    print(f"  String pool:     {len(program.strings)} entries")

    # Step 6: VM
    print("\n=== VM ===")
    vm = VM(program, debug=args.debug)
    t0 = time.perf_counter()
    vm.run()
    t1 = time.perf_counter()
    print(f"  Output:          {vm.output}")
    print(f"  Execution time:  {(t1 - t0) * 1000:.3f} ms")
    print(f"  Heap objects:    {len(vm.heap)}")
    return 0


def _print_ast(node, indent: int = 0) -> None:
    """Recursively print an AST node."""
    prefix = "  " * indent
    name = type(node).__name__
    if hasattr(node, "__dataclass_fields__"):
        fields = []
        for fname in node.__dataclass_fields__:
            val = getattr(node, fname)
            if isinstance(val, (int, str, bool, float)):
                fields.append(f"{fname}={val!r}")
            elif val is None:
                fields.append(f"{fname}=None")
            elif isinstance(val, tuple):
                fields.append(f"{fname}=<{len(val)} items>")
            else:
                fields.append(f"{fname}=<{type(val).__name__}>")
        print(f"{prefix}{name}({', '.join(fields)})")
        for fname in node.__dataclass_fields__:
            val = getattr(node, fname)
            if isinstance(val, tuple):
                for item in val:
                    _print_ast(item, indent + 1)
            elif hasattr(val, "__dataclass_fields__"):
                _print_ast(val, indent + 1)
    else:
        print(f"{prefix}{name}: {node!r}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="minilang",
        description="MiniLang — a statically-typed language with a bytecode VM",
    )
    p.add_argument("--version", action="version", version=f"minilang {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Execute a MiniLang file")
    run.add_argument("file")
    run.add_argument("--debug", action="store_true", help="Enable debug output")
    run.add_argument("--no-opt", action="store_true", help="Disable AST optimizer")
    run.add_argument("--config", type=str, default=None,
                     help="Path to JSON config file")
    run.set_defaults(func=cmd_run)

    dis = sub.add_parser("dis", help="Disassemble a MiniLang file")
    dis.add_argument("file")
    dis.add_argument("--debug", action="store_true", help="Enable debug output")
    dis.set_defaults(func=cmd_dis)

    chk = sub.add_parser("check", help="Type-check a MiniLang file")
    chk.add_argument("file")
    chk.add_argument("--debug", action="store_true", help="Enable debug output")
    chk.set_defaults(func=cmd_check)

    repl = sub.add_parser("repl", help="Start the interactive REPL")
    repl.add_argument("--debug", action="store_true")
    repl.set_defaults(func=cmd_repl)

    bench = sub.add_parser("benchmark", help="Benchmark execution time")
    bench.add_argument("file")
    bench.add_argument("--iterations", "-n", type=int, default=100,
                       help="Number of iterations (default 100)")
    bench.set_defaults(func=cmd_benchmark)

    exp = sub.add_parser("explain", help="Show full compilation pipeline")
    exp.add_argument("file")
    exp.add_argument("--debug", action="store_true")
    exp.set_defaults(func=cmd_explain)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    rc = args.func(args)
    return rc if rc is not None else 0


if __name__ == "__main__":
    sys.exit(main())