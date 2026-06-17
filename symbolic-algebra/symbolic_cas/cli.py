"""
Command-line interface for the Symbolic CAS.

Supports both a REPL mode and single-command mode via argparse.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from symbolic_cas import (
    Expr, Num, Sym, BinOp, UnaryOp, Func, Pow,
    parse, simplify, differentiate, expand_expr,
    substitute, evaluate, collect_symbols, to_latex, solve,
    taylor_series, numerical_integrate, newton_method,
    factor, pretty_print, limit,
    x, y, z,
)
from symbolic_cas.serialize import to_json, from_json


def _format_result(result, output_format: str = 'text') -> str:
    """Format a result for display."""
    if isinstance(result, Expr):
        if output_format == 'latex':
            return result.to_latex()
        elif output_format == 'json':
            return to_json(result, indent=2)
        else:
            return result.pretty()
    elif isinstance(result, (int, float)):
        if output_format == 'json':
            return json.dumps(result)
        return str(result)
    elif isinstance(result, list):
        if output_format == 'json':
            return json.dumps([str(r) for r in result])
        return ', '.join(str(r) if not isinstance(r, Expr) else r.pretty() for r in result)
    elif result is None:
        return "None (limit does not exist)"
    return str(result)


def run_single_command(args: argparse.Namespace) -> None:
    """Execute a single command from command-line arguments."""
    expr_str = args.expression

    try:
        expr = parse(expr_str)
    except ValueError as e:
        print(f"Error parsing expression: {e}", file=sys.stderr)
        sys.exit(1)

    output_format = args.format

    if args.action == 'simplify' or args.action is None:
        result = expr.simplify()
        print(_format_result(result, output_format))

    elif args.action == 'diff':
        var = args.variable or 'x'
        result = expr.diff(var).simplify()
        print(_format_result(result, output_format))

    elif args.action == 'expand':
        result = expr.expand().simplify()
        print(_format_result(result, output_format))

    elif args.action == 'factor':
        var = args.variable or 'x'
        result = expr.factor(var)
        print(_format_result(result, output_format))

    elif args.action == 'latex':
        result = expr.simplify()
        print(_format_result(result, 'latex'))

    elif args.action == 'eval':
        mapping = _parse_vars(args.vars or [])
        try:
            result = expr.evaluate(mapping)
            print(_format_result(result, output_format))
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.action == 'solve':
        var = args.variable or 'x'
        try:
            solutions = expr.solve(var)
            if solutions:
                print(f"Solutions: {_format_result(solutions, output_format)}")
            else:
                print("No real solutions")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.action == 'newton':
        var = args.variable or 'x'
        x0 = args.x0 if args.x0 is not None else 0.0
        try:
            root = expr.newton_solve(var, x0=x0)
            print(f"Root: {var} ≈ {root:.10f}")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.action == 'taylor':
        var = args.variable or 'x'
        point = args.point if args.point is not None else 0
        order = args.order or 5
        result = expr.taylor(var, point=point, order=order)
        print(_format_result(result, output_format))

    elif args.action == 'integrate':
        var = args.variable or 'x'
        a = args.a if args.a is not None else 0
        b = args.b if args.b is not None else 1
        result = expr.integrate(var, a, b)
        print(f"∫_{a}^{b} f({var})dx ≈ {result:.10f}")

    elif args.action == 'symbols':
        syms = expr.symbols()
        print(f"Symbols: {', '.join(sorted(syms))}")

    elif args.action == 'pretty':
        print(expr.pretty())

    elif args.action == 'limit':
        var = args.variable or 'x'
        point = args.point if args.point is not None else 0
        direction = args.direction or 'both'
        result = expr.limit(var, point=point, direction=direction)
        if result is not None:
            print(f"lim({var}→{point}) = {result}")
        else:
            print(f"lim({var}→{point}) does not exist")

    elif args.action == 'json_export':
        print(to_json(expr, indent=2))


def _parse_vars(var_list: List[str]) -> dict:
    """Parse variable assignments from command line (e.g., 'x=2', 'y=3')."""
    mapping = {}
    for v in var_list:
        if '=' in v:
            name, val = v.split('=', 1)
            try:
                mapping[name.strip()] = float(val.strip())
            except ValueError:
                print(f"Warning: Cannot parse value for {name.strip()}", file=sys.stderr)
    return mapping


def run_repl() -> None:
    """Run the interactive REPL."""
    print("=" * 60)
    print("  Symbolic CAS — Interactive REPL  (v2.0)")
    print("=" * 60)
    print("Commands:")
    print("  <expr>            — Parse and simplify an expression")
    print("  diff <expr>       — Differentiate (w.r.t. x)")
    print("  expand <expr>     — Expand an expression")
    print("  factor <expr>     — Factor an expression (w.r.t. x)")
    print("  latex <expr>      — Convert to LaTeX")
    print("  eval <expr>       — Evaluate with x=1, y=2, z=3")
    print("  solve <expr>      — Solve expr=0 for x")
    print("  newton <expr>     — Find root via Newton's method (w.r.t. x)")
    print("  taylor <expr>     — Taylor series around x=0 (5 terms)")
    print("  integrate <expr>  — Numerically integrate from 0 to 1")
    print("  symbols <expr>    — List symbols in expression")
    print("  pretty <expr>     — Pretty-print expression")
    print("  limit <expr>      — Compute limit as x→0")
    print("  json <expr>       — Export as JSON")
    print("  quit              — Exit")
    print("=" * 60)

    while True:
        try:
            line = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not line:
            continue
        if line == 'quit':
            break

        try:
            if line.startswith('diff '):
                expr = parse(line[5:])
                result = expr.diff('x').simplify()
                print(f"  d/dx({expr.simplify()}) = {result}")
            elif line.startswith('expand '):
                expr = parse(line[7:])
                result = expr.expand().simplify()
                print(f"  Expanded: {result}")
            elif line.startswith('factor '):
                expr = parse(line[7:])
                result = expr.factor('x')
                print(f"  Factored: {result.pretty()}")
            elif line.startswith('latex '):
                expr = parse(line[6:])
                result = expr.simplify()
                print(f"  LaTeX: {result.to_latex()}")
            elif line.startswith('eval '):
                expr = parse(line[5:])
                result = expr.evaluate({'x': 1, 'y': 2, 'z': 3})
                print(f"  Result: {result}")
            elif line.startswith('solve '):
                expr = parse(line[6:])
                solutions = expr.solve('x')
                if solutions:
                    print(f"  Solutions: {', '.join(str(s) for s in solutions)}")
                else:
                    print("  No real solutions")
            elif line.startswith('newton '):
                expr = parse(line[7:])
                root = expr.newton_solve('x')
                print(f"  Root (Newton): x ≈ {root:.10f}")
            elif line.startswith('taylor '):
                expr = parse(line[7:])
                result = expr.taylor('x', point=0, order=5)
                print(f"  Taylor series: {result.pretty()}")
            elif line.startswith('integrate '):
                expr = parse(line[10:])
                result = expr.integrate('x', 0, 1)
                print(f"  ∫₀¹ f(x)dx ≈ {result:.10f}")
            elif line.startswith('symbols '):
                expr = parse(line[8:])
                syms = expr.symbols()
                print(f"  Symbols: {', '.join(sorted(syms))}")
            elif line.startswith('pretty '):
                expr = parse(line[7:])
                print(f"  {expr.pretty()}")
            elif line.startswith('limit '):
                expr = parse(line[6:])
                result = expr.limit('x', point=0)
                print(f"  Limit: {result}")
            elif line.startswith('json '):
                expr = parse(line[5:])
                print(f"  {to_json(expr, indent=2)}")
            else:
                expr = parse(line)
                result = expr.simplify()
                print(f"  Simplified: {result}")
        except Exception as exc:
            print(f"  Error: {exc}")


def main():
    """Entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog='symbolic-cas',
        description='Symbolic CAS — A symbolic algebra system in Python',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  symbolic-cas "sin(x)^2 + cos(x)^2"
  symbolic-cas --action simplify "x^2 + 2*x + 1"
  symbolic-cas --action diff "x^3 + 2*x"
  symbolic-cas --action solve "x^2 - 5*x + 6"
  symbolic-cas --action latex "sqrt(x^2 + 1)"
  symbolic-cas --action taylor "exp(x)" --order 6
  symbolic-cas --action integrate "x^2" --a 0 --b 1
  symbolic-cas --action limit "sin(x)/x" --point 0
  symbolic-cas --action eval "x^2 + 2*x" --vars x=3
  symbolic-cas --action json_export "x^2 + 1"
        """,
    )

    parser.add_argument(
        'expression',
        nargs='?',
        help='Mathematical expression to process (e.g., "x^2 + 2*x + 1")',
    )
    parser.add_argument(
        '-a', '--action',
        choices=['simplify', 'diff', 'expand', 'factor', 'latex', 'eval',
                 'solve', 'newton', 'taylor', 'integrate', 'symbols',
                 'pretty', 'limit', 'json_export'],
        default='simplify',
        help='Action to perform on the expression (default: simplify)',
    )
    parser.add_argument(
        '-v', '--variable',
        default='x',
        help='Variable to use for differentiation, solving, etc. (default: x)',
    )
    parser.add_argument(
        '--vars',
        nargs='*',
        help='Variable assignments for evaluation (e.g., x=2 y=3)',
    )
    parser.add_argument(
        '--x0',
        type=float,
        help='Starting point for Newton\'s method (default: 0)',
    )
    parser.add_argument(
        '--point',
        type=float,
        help='Point for Taylor series or limit (default: 0)',
    )
    parser.add_argument(
        '--order',
        type=int,
        help='Order for Taylor series (default: 5)',
    )
    parser.add_argument(
        '--a',
        type=float,
        help='Lower bound for integration (default: 0)',
    )
    parser.add_argument(
        '--b',
        type=float,
        help='Upper bound for integration (default: 1)',
    )
    parser.add_argument(
        '-d', '--direction',
        choices=['left', 'right', 'both'],
        default='both',
        help='Direction for limit computation (default: both)',
    )
    parser.add_argument(
        '-f', '--format',
        choices=['text', 'latex', 'json'],
        default='text',
        help='Output format (default: text)',
    )
    parser.add_argument(
        '--repl',
        action='store_true',
        help='Start interactive REPL mode',
    )
    parser.add_argument(
        '--version',
        action='version',
        version='symbolic-cas 2.0.0',
    )

    args = parser.parse_args()

    if args.repl:
        run_repl()
    elif args.expression:
        run_single_command(args)
    else:
        # No expression and no REPL flag — start REPL by default
        parser.print_help()


if __name__ == '__main__':
    main()