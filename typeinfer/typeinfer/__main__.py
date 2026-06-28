"""CLI entry point: ``python -m typeinfer "\\x. x"``."""

from __future__ import annotations

import sys

from . import infer, parse, type_to_string, InferError, ParserError, LexerError


_BUILTINS_HELP = """\
Built-in identifiers available in expressions:
  (none by default — use --with-basics to enable Int/Bool primitives)
"""


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print("Usage: python -m typeinfer \"<expression>\"")
        print(_BUILTINS_HELP)
        return 0 if argv else 1
    source = " ".join(argv)
    try:
        t = infer(source)
        print(type_to_string(t))
        return 0
    except (LexerError, ParserError, InferError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())