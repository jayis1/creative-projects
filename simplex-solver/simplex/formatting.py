"""LP file-format reader/writer (CPLEX LP format) and pretty-printing.

This module provides:

* :func:`write_lp`  — serialise an :class:`~simplex.problem.LPProblem` to the
  widely-supported CPLEX LP text format.
* :func:`read_lp`  — parse a (subset of the) CPLEX LP format back into an
  :class:`~simplex.problem.LPProblem`.
* :func:`format_tableau` — render a solved tableau as an ASCII table.
* :func:`format_result` — produce a rich, human-readable solve report.

The LP format is human-readable and supported by CPLEX, Gurobi, GLPK, and
others.  Our writer produces a clean, canonical file; the reader handles the
common subset (linear constraints, bounds, integer declarations, min/max
objective).
"""

from __future__ import annotations

import re
from fractions import Fraction
from typing import Any

from .problem import LPProblem, LPResult, LPStatus

__all__ = ["write_lp", "read_lp", "format_tableau", "format_result"]


# --------------------------------------------------------------------------- #
# Writer
# --------------------------------------------------------------------------- #
def write_lp(problem: LPProblem, path: str) -> None:
    """Write ``problem`` to ``path`` in CPLEX LP format.

    Parameters
    ----------
    problem : LPProblem
        The problem to serialise.
    path : str
        Destination file path.
    """
    lines: list[str] = []
    lines.append(f"\\ Problem: {problem.name}")
    lines.append("")
    # Objective section.
    sense_kw = "Maximize" if problem.objective == "max" else "Minimize"
    lines.append(sense_kw)
    obj_terms: list[str] = []
    for v in problem.variables:
        c = problem.objective_coeffs.get(v, Fraction(0))
        if c == 0:
            continue
        if c == 1:
            obj_terms.append(f"+ {v}")
        elif c == -1:
            obj_terms.append(f"- {v}")
        elif c > 0:
            obj_terms.append(f"+ {_fmt_num(c)} {v}")
        else:
            obj_terms.append(f"- {_fmt_num(-c)} {v}")
    obj_expr = " ".join(obj_terms) if obj_terms else "0"
    lines.append(f"  obj: {obj_expr}")
    lines.append("")
    # Subject To.
    if problem.constraints:
        lines.append("Subject To")
        for i, c in enumerate(problem.constraints):
            cname = c.get("name", f"c{i}")
            terms: list[str] = []
            for v in problem.variables:
                a = c["coeffs"].get(v, Fraction(0))
                if a == 0:
                    continue
                if a == 1:
                    terms.append(f"+ {v}")
                elif a == -1:
                    terms.append(f"- {v}")
                elif a > 0:
                    terms.append(f"+ {_fmt_num(a)} {v}")
                else:
                    terms.append(f"- {_fmt_num(-a)} {v}")
            expr = " ".join(terms) if terms else "0"
            rel = {"<=": "<=", ">=": ">=", "=": "="}[c["relation"]]
            rhs = _fmt_num(c["rhs"])
            lines.append(f"  {cname}: {expr} {rel} {rhs}")
        lines.append("")
    # Bounds.
    has_bounds = False
    bound_lines: list[str] = []
    for v in problem.variables:
        lo, hi = problem.bounds.get(v, (Fraction(0), None))
        if lo is None and hi is None:
            bound_lines.append(f"  {v} free")
            has_bounds = True
        elif lo is not None and hi is not None and lo == hi:
            bound_lines.append(f"  {v} = {_fmt_num(lo)}")
            has_bounds = True
        else:
            # Write the lower bound explicitly (even if 0) when there's an
            # upper bound, so the LP reader can reconstruct (0, hi) correctly.
            if lo is not None:
                if lo != 0 or hi is not None:
                    bound_lines.append(f"  {_fmt_num(lo)} <= {v}")
                    has_bounds = True
            elif lo is None:
                bound_lines.append(f"  -inf <= {v}")
                has_bounds = True
            if hi is not None:
                bound_lines.append(f"  {v} <= {_fmt_num(hi)}")
                has_bounds = True
    if has_bounds:
        lines.append("Bounds")
        lines.extend(bound_lines)
        lines.append("")
    # Integer / binary declarations.
    int_vars = sorted(problem.integer)
    if int_vars:
        lines.append("Integer")
        for v in int_vars:
            lines.append(f"  {v}")
        lines.append("")
    lines.append("End")
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")


# --------------------------------------------------------------------------- #
# Reader
# --------------------------------------------------------------------------- #
# Token regex for a coefficient: optional sign + number, optional variable.
_TERM_RE = re.compile(
    r"(?P<sign>[+-]?)"          # optional sign
    r"(?P<coeff>\d+\.?\d*|\.\d+|[A-Za-z_]\w*)?"  # coeff or var
    r"(?P<var>[A-Za-z_]\w*)?"    # variable (if coeff was numeric)
)


def _parse_lp_value(tok: str) -> Fraction:
    """Parse a numeric token (int, float, 'inf', etc.) into a Fraction."""
    tok = tok.strip()
    low = tok.lower()
    if low in ("inf", "+inf", "infinity"):
        raise ValueError("infinity cannot be a literal coefficient")
    if low in ("-inf", "-infinity"):
        raise ValueError("-infinity cannot be a literal coefficient")
    return Fraction(tok)


def _parse_expr(tokens: list[str]) -> dict[str, Fraction]:
    """Parse a linear expression token list into ``{var: coeff}`` dict.

    Handles forms like ``3 * x + 2 * y - z``, ``+ x``, ``- 2 * y``, ``5``
    (constant).  The ``*`` separator between a coefficient and a variable is
    optional.
    """
    coeffs: dict[str, Fraction] = {}
    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        # Determine sign.
        sign = Fraction(1)
        if tok == "+":
            i += 1
            tok = tokens[i] if i < n else ""
        elif tok == "-":
            sign = Fraction(-1)
            i += 1
            tok = tokens[i] if i < n else ""
        if not tok:
            break
        # Check if this token is a number.
        try:
            val = Fraction(tok)
            i += 1
            # Skip optional '*' separator.
            if i < n and tokens[i] == "*":
                i += 1
            # Next token might be a variable name.
            if i < n and _is_identifier(tokens[i]):
                var = tokens[i]
                i += 1
                coeffs[var] = coeffs.get(var, Fraction(0)) + sign * val
            else:
                # Bare constant — store under "" key.
                coeffs[""] = coeffs.get("", Fraction(0)) + sign * val
        except (ValueError, ZeroDivisionError):
            # Must be a variable name with implicit coefficient 1.
            if _is_identifier(tok):
                var = tok
                i += 1
                coeffs[var] = coeffs.get(var, Fraction(0)) + sign * Fraction(1)
            else:
                raise ValueError(f"cannot parse token {tok!r} in expression")
    return coeffs


def _is_identifier(tok: str) -> bool:
    return bool(re.match(r"^[A-Za-z_]\w*$", tok))


def _tokenise_lp_expr(expr: str) -> list[str]:
    """Split an LP expression into tokens, handling signs and * separators."""
    expr = expr.strip()
    if not expr:
        return []
    # Insert spaces around + and - (but not inside numbers like 1e-3).
    expr = re.sub(r"(?<=[^\s\d.eE*])\+", " + ", expr)
    expr = re.sub(r"(?<=[^\s\d.eE*])\-", " - ", expr)
    # Insert spaces around * (coefficient separator: 2*x → 2 * x).
    expr = expr.replace("*", " * ")
    # Handle leading sign.
    if expr.startswith("+"):
        expr = expr[1:].strip()
    if expr.startswith("-"):
        expr = "- " + expr[1:].strip()
    return expr.split()


def read_lp(path: str) -> LPProblem:
    """Read a CPLEX LP file and return an :class:`LPProblem`.

    Supports a practical subset: ``Maximize``/``Minimize``, ``Subject To``,
    ``Bounds``, ``Integer``, ``Binary``, ``General``, ``End``.
    """
    with open(path) as fh:
        text = fh.read()
    lines = text.splitlines()
    name = "lp"
    sense = "max"
    obj_coeffs: dict[str, Fraction] = {}
    variables: list[str] = []
    constraints: list[dict] = []
    bounds: dict[str, tuple] = {}
    integer: set[str] = set()
    _free_vars: set[str] = set()  # variables explicitly declared "free"
    section: str | None = None
    obj_name = "obj"

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("\\"):
            continue
        upper = line.upper()
        # Section detection.
        if upper in ("MAXIMIZE", "MAX", "MAXIMISE"):
            sense = "max"
            section = "obj"
            continue
        if upper in ("MINIMIZE", "MIN", "MINIMISE"):
            sense = "min"
            section = "obj"
            continue
        if upper in ("SUBJECT TO", "SUCH THAT", "S.T.", "ST", "CONSTRAINTS"):
            section = "constraints"
            continue
        if upper in ("BOUNDS",):
            section = "bounds"
            continue
        if upper in ("INTEGER", "GENERAL", "GENERALS"):
            section = "integer"
            continue
        if upper in ("BINARY", "BINARIES", "BIN"):
            section = "binary"
            continue
        if upper in ("END", "ENDATA"):
            break
        # Parse section content.
        if section == "obj":
            # "obj: 3x + 2y" or just "3x + 2y"
            if ":" in line:
                obj_name, rest = line.split(":", 1)
                obj_name = obj_name.strip()
            else:
                rest = line
            tokens = _tokenise_lp_expr(rest)
            parsed = _parse_expr(tokens)
            for var, coeff in parsed.items():
                if var == "":
                    continue
                obj_coeffs[var] = coeff
                if var not in variables:
                    variables.append(var)
        elif section == "constraints":
            # "cname: 3x + 2y <= 10"
            cname: str | None = None
            expr_part = line
            if ":" in line:
                parts = line.split(":", 1)
                cname = parts[0].strip()
                expr_part = parts[1].strip()
            # Split on relation.
            for rel in ("<=", ">=", "<", ">", "=", "=<", "=>"):
                idx = _find_relation(expr_part, rel)
                if idx is not None:
                    lhs = expr_part[:idx]
                    rhs_str = expr_part[idx + len(rel):].strip()
                    relation = {"<=": "<=", ">=": ">=", "<": "<=",
                                ">": ">=", "=": "=", "=<": "<=",
                                "=>": ">="}[rel]
                    break
            else:
                raise ValueError(f"constraint {line!r} has no relation")
            lhs_tokens = _tokenise_lp_expr(lhs)
            coeffs = _parse_expr(lhs_tokens)
            coeffs.pop("", None)  # drop constant (shouldn't be one)
            rhs = _parse_lp_value(rhs_str)
            # Track variables.
            for var in coeffs:
                if var not in variables:
                    variables.append(var)
            constraints.append({
                "coeffs": coeffs,
                "relation": relation,
                "rhs": rhs,
                "name": cname,
            })
        elif section == "bounds":
            # Forms: "lo <= var <= hi", "var free", "var = val", "var <= hi"
            tokens = line.split()
            if len(tokens) == 2 and tokens[1].lower() == "free":
                var = tokens[0]
                bounds[var] = (None, None)
                _free_vars.add(var)
            elif "=" in line and "<=" not in line and ">=" not in line:
                # var = val
                parts = line.split("=")
                var = parts[0].strip()
                val = _parse_lp_value(parts[-1].strip())
                bounds[var] = (val, val)
            elif "<=" in line or ">=" in line:
                # Could be "lo <= var <= hi" or "var <= hi" or "lo <= var".
                lo, hi = _parse_bound_line(line)
                var = _extract_var_name_from_bound(line)
                if var:
                    # Merge with existing bounds (multiple lines per var).
                    cur_lo, cur_hi = bounds.get(var, (Fraction(0), None))
                    if lo is not None:
                        cur_lo = lo if cur_lo is None else max(cur_lo, lo)
                    if hi is not None:
                        cur_hi = hi if cur_hi is None else min(cur_hi, hi)
                    bounds[var] = (cur_lo, cur_hi)
        elif section == "integer":
            for tok in line.split():
                if _is_identifier(tok):
                    integer.add(tok)
                    if tok not in variables:
                        variables.append(tok)
        elif section == "binary":
            for tok in line.split():
                if _is_identifier(tok):
                    var = tok
                    integer.add(var)
                    bounds[var] = (Fraction(0), Fraction(1))
                    if var not in variables:
                        variables.append(var)

    # Normalise bounds: default (0, None) for declared variables.
    # Variables that appear in the bounds dict but only have an upper bound
    # line ("x <= 5") should have their lower bound set to 0, not None.
    norm_bounds: dict[str, tuple] = {}
    for v in variables:
        lo, hi = bounds.get(v, (Fraction(0), None))
        # If lo is None but the variable wasn't declared free, default to 0.
        if lo is None and v not in _free_vars:
            lo = Fraction(0)
        norm_bounds[v] = (lo, hi)

    return LPProblem(
        name=name,
        objective=sense,
        variables=tuple(variables),
        objective_coeffs=obj_coeffs,
        constraints=constraints,
        bounds=norm_bounds,
        integer=integer,
    )


def _find_relation(expr: str, rel: str) -> int | None:
    """Find the first occurrence of ``rel`` in ``expr`` not inside a number."""
    idx = expr.find(rel)
    # Avoid matching <= inside a number's exponent (e.g. 1e-5).
    while idx is not None and idx >= 0:
        # Check the character before rel: if it's a digit or '.', it's part of a number.
        if idx > 0 and (expr[idx - 1].isdigit() or expr[idx - 1] == "."):
            idx = expr.find(rel, idx + 1)
            continue
        return idx
    return None if idx is None or idx < 0 else idx


def _parse_bound_line(line: str) -> tuple:
    """Parse 'lo <= var <= hi' or 'var <= hi' or 'lo <= var'."""
    # Split on <= or >=
    parts = re.split(r"<=|>=", line)
    parts = [p.strip() for p in parts if p.strip()]
    lo: Fraction | None = None
    hi: Fraction | None = None
    if len(parts) == 3:
        lo = _parse_lp_value(parts[0])
        hi = _parse_lp_value(parts[2])
    elif len(parts) == 2:
        # Determine which side is the variable.
        if _is_identifier(parts[0]):
            # var <= hi  or  var >= lo
            # Check which relation was used.
            if "<=" in line:
                hi = _parse_lp_value(parts[1])
            else:
                lo = _parse_lp_value(parts[1])
        else:
            # lo <= var  or  hi >= var
            if "<=" in line:
                lo = _parse_lp_value(parts[0])
            else:
                hi = _parse_lp_value(parts[0])
    return (lo, hi)


def _extract_var_name_from_bound(line: str) -> str | None:
    parts = re.split(r"<=|>=", line)
    for p in parts:
        p = p.strip()
        if _is_identifier(p):
            return p
    return None


# --------------------------------------------------------------------------- #
# Pretty-printing
# --------------------------------------------------------------------------- #
def _fmt_num(v: Fraction | int | float) -> str:
    """Format a number for display."""
    if isinstance(v, Fraction):
        if v.denominator == 1:
            return str(v.numerator)
        return f"{float(v):.6g}"
    return f"{v:.6g}"


def _fmt_coeff(v: Fraction | int | float) -> str:
    """Format a coefficient for LP-format expressions (includes '*' separator)."""
    if isinstance(v, Fraction):
        if v == 1:
            return "+"
        if v == -1:
            return "-"
        if v.denominator == 1:
            return f"{int(v)}*"
        return f"{float(v):.6g}*"
    if v == 1:
        return "+"
    if v == -1:
        return "-"
    return f"{v:.6g}*"


def format_result(result: LPResult, problem: LPProblem, *,
                  show_basis: bool = False, show_duals: bool = True,
                  show_reduced_costs: bool = True) -> str:
    """Produce a rich, human-readable solve report.

    Parameters
    ----------
    result : LPResult
        The solve result.
    problem : LPProblem
        The original problem (for variable ordering).
    show_basis : bool
        Include the optimal basis in the report.
    show_duals : bool
        Include shadow prices.
    show_reduced_costs : bool
        Include reduced costs.
    """
    lines: list[str] = []
    lines.append("┌─────────────────────────────────────────────┐")
    lines.append(f"│  Problem: {problem.name:<34s}│")
    lines.append(f"│  Sense:    {problem.objective:<34s}│")
    lines.append(f"│  Vars:     {problem.num_vars():<34d}│")
    lines.append(f"│  Constrs:  {problem.num_constraints():<34d}│")
    if problem.integer:
        lines.append(f"│  Integer:  {len(problem.integer):<34d}│")
    lines.append("├─────────────────────────────────────────────┤")
    lines.append(f"│  Status:   {result.status.value:<34s}│")
    if result.status is LPStatus.OPTIMAL:
        lines.append(f"│  Objective: {_fmt_num(result.objective_value or 0):<33s}│")
        lines.append(f"│  Pivots:   {result.iterations:<34d}│")
        lines.append("├─────────────────────────────────────────────┤")
        lines.append("│  Solution:                                  │")
        for v in problem.variables:
            val = result.solution.get(v, 0)
            lines.append(f"│    {v:<10s} = {_fmt_num(val):>24s}        │")
        if show_duals and result.duals:
            lines.append("├─────────────────────────────────────────────┤")
            lines.append("│  Shadow Prices (Duals):                     │")
            for cname, val in result.duals.items():
                lines.append(f"│    {cname:<10s} = {_fmt_num(val):>24s}        │")
        if show_reduced_costs and result.reduced_costs:
            lines.append("├─────────────────────────────────────────────┤")
            lines.append("│  Reduced Costs:                              │")
            for v in problem.variables:
                rc = result.reduced_costs.get(v, 0)
                lines.append(f"│    {v:<10s} = {_fmt_num(rc):>24s}        │")
        if show_basis and result.basis:
            lines.append("├─────────────────────────────────────────────┤")
            lines.append("│  Basis:                                      │")
            lines.append(f"│    {', '.join(result.basis):<43s}│")
        if result.message:
            lines.append("├─────────────────────────────────────────────┤")
            lines.append(f"│  Note: {result.message:<37s}│")
    else:
        if result.message:
            lines.append(f"│  Message:  {result.message[:33]:<33s}│")
    lines.append("└─────────────────────────────────────────────┘")
    return "\n".join(lines)


def format_tableau(problem: LPProblem, result: LPResult) -> str:
    """Render a compact ASCII summary of the solved problem.

    This is *not* the raw simplex tableau (which is internal) but a readable
    summary showing the objective, constraint values, and solution.
    """
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append(f"  {problem.objective.upper()}  {' + '.join(f'{_fmt_coeff(problem.objective_coeffs.get(v, 0))}{v}' for v in problem.variables)}")
    lines.append("subject to:")
    for i, c in enumerate(problem.constraints):
        cname = c.get("name", f"c{i}")
        terms = " + ".join(
            f"{_fmt_coeff(c['coeffs'].get(v, 0))}{v}"
            for v in problem.variables
            if c["coeffs"].get(v, 0) != 0
        )
        lines.append(f"  {cname}: {terms} {c['relation']} {_fmt_num(c['rhs'])}")
    lines.append("-" * 60)
    if result.status is LPStatus.OPTIMAL:
        lines.append(f"  Optimal objective = {_fmt_num(result.objective_value)}")
        lines.append(f"  Solution: {', '.join(f'{v}={_fmt_num(result.solution.get(v, 0))}' for v in problem.variables)}")
        lines.append(f"  Pivots: {result.iterations}")
    else:
        lines.append(f"  Status: {result.status.value}")
    lines.append("=" * 60)
    return "\n".join(lines)