r"""CLI entry point: ``python -m typeinfer "\x. x"``.

Flags:
  --builtins / -b    load built-in primitives (arithmetic, comparison, ...)
  --explain / -e     print step-by-step inference trace
  --repl             start an interactive REPL
  --ast              print the parsed AST instead of the type
  --version          print version
"""

from __future__ import annotations

import sys

from . import (
    infer, infer_with_trace, parse, type_to_string,
    InferError, ParserError, LexerError,
)
from .primitives import default_env


__version__ = "0.1.0"


def _print_help() -> None:
    print(
        "Usage: python -m typeinfer [OPTIONS] \"<expression>\"\n"
        "\n"
        "Options:\n"
        "  -b, --builtins    load built-in primitives (+, -, *, /, <, >, ==, ...)\n"
        "  -e, --explain     print step-by-step inference trace\n"
        "      --repl        start an interactive REPL\n"
        "      --ast         print the parsed AST instead of the type\n"
        "      --version     print version and exit\n"
        "  -h, --help        show this help\n"
    )


def _repl() -> int:
    """Minimal interactive REPL: read a line, infer & print the type."""
    print("typeinfer REPL — :q to quit, :t <expr> for type, :e <expr> for trace")
    use_builtins = True
    while True:
        try:
            line = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line in (":q", ":quit"):
            break
        if line == ":b":
            use_builtins = not use_builtins
            print(f"builtins: {'on' if use_builtins else 'off'}")
            continue
        trace = False
        src = line
        if line.startswith(":t "):
            src = line[3:]
        elif line.startswith(":e "):
            src = line[3:]
            trace = True
        try:
            if trace:
                t, steps = infer_with_trace(src, use_builtins=use_builtins)
                for s in steps:
                    print(f"  {s}")
                print(f"=> {type_to_string(t)}")
            else:
                t = infer(src, use_builtins=use_builtins)
                print(type_to_string(t))
        except (LexerError, ParserError, InferError) as e:
            print(f"error: {e}", file=sys.stderr)
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        _print_help()
        return 1
    # flag parsing
    use_builtins = False
    explain = False
    show_ast = False
    repl = False
    positional: list = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-h", "--help"):
            _print_help()
            return 0
        if a == "--version":
            print(f"typeinfer {__version__}")
            return 0
        if a in ("-b", "--builtins"):
            use_builtins = True
        elif a in ("-e", "--explain"):
            explain = True
        elif a == "--ast":
            show_ast = True
        elif a == "--repl":
            repl = True
        elif a.startswith("-") and a != "-":
            print(f"Unknown option: {a}", file=sys.stderr)
            return 2
        else:
            positional.append(a)
        i += 1

    if repl:
        return _repl()

    if not positional:
        _print_help()
        return 1

    source = " ".join(positional)
    try:
        if show_ast:
            ast = parse(source)
            print(_ast_to_string(ast))
            return 0
        if explain:
            t, steps = infer_with_trace(source, use_builtins=use_builtins)
            for s in steps:
                print(f"  {s}")
            print(f"=> {type_to_string(t)}")
        else:
            t = infer(source, use_builtins=use_builtins)
            print(type_to_string(t))
        return 0
    except (LexerError, ParserError, InferError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def _ast_to_string(node, indent: int = 0) -> str:
    """Pretty-print an AST node as a tree."""
    pad = "  " * indent
    cls = type(node).__name__
    if isinstance(node, dict):  # pragma: no cover
        return f"{pad}{node}"
    if not hasattr(node, "__dataclass_fields__"):
        return f"{pad}{node!r}"
    fields = []
    for fname in node.__dataclass_fields__:
        val = getattr(node, fname)
        if hasattr(val, "__dataclass_fields__"):
            fields.append(f"{fname}:\n{_ast_to_string(val, indent + 1)}")
        elif isinstance(val, tuple) and val and hasattr(val[0], "__dataclass_fields__"):
            inner = "\n".join(_ast_to_string(v, indent + 1) for v in val)
            fields.append(f"{fname}:\n{inner}")
        else:
            fields.append(f"{fname}={val!r}")
    return f"{pad}{cls}({', '.join(fields)})"


if __name__ == "__main__":
    raise SystemExit(main())