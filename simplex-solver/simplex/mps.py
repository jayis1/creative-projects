"""MPS (Mathematical Programming System) file format reader/writer.

Supports the classic fixed-column MPS format (most widely supported by
commercial solvers) for *linear* programs.  Integer markers (MARKER INTORG /
INTEND) are honoured.

This is a deliberately compact implementation: enough to round-trip our
:class:`LPProblem` and interoperate with models from the OR-Library / MIPLIB
when they avoid free-format quirks.  Bound types LO, UP, FX, MI, PL, FR, BV,
LI, UI are recognised.
"""

from __future__ import annotations

import re
from fractions import Fraction

from .problem import LPProblem

__all__ = ["read_mps", "write_mps"]

_SECTIONS = (
    "NAME", "OBJSENSE", "ROWS", "COLUMNS", "RHS", "RANGES",
    "BOUNDS", "MARKERS", "ENDATA",
)


def _parse_num(s: str) -> Fraction:
    """Parse a possibly-exponential numeric token into a Fraction."""
    s = s.strip()
    if not s:
        return Fraction(0)
    # Handle Fortran-style double precision (1.0D-3).
    s = s.replace("D", "E").replace("d", "e")
    # Parse via float then Fraction to keep precision reasonable.
    try:
        return Fraction(s)
    except (ValueError, ZeroDivisionError):
        return Fraction(float(s))


def read_mps(path: str) -> LPProblem:
    """Read an MPS file and return an :class:`LPProblem`."""
    with open(path, "r") as fh:
        lines = fh.readlines()
    name = "mps"
    sense = "max"
    # row labels: rowname -> relation ('N' for objective, 'L'/'G'/'E')
    rows: dict[str, str] = {}
    obj_row_name: str | None = None
    # column data: colname -> {rowname: coeff}
    columns: dict[str, dict[str, Fraction]] = {}
    col_order: list[str] = []
    rhs: dict[str, Fraction] = {}
    ranges: dict[str, Fraction] = {}
    bounds: dict[str, tuple] = {}
    integer_marker_on = False
    integer_vars: set[str] = set()
    section = None
    for raw in lines:
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        if line.startswith("*"):
            continue  # comment
        # Detect section header (column 1 non-blank).
        if line and not line[0].isspace():
            tok = line.split()[0].upper()
            if tok in _SECTIONS:
                section = tok
                if section == "NAME":
                    parts = line.split(None, 1)
                    name = parts[1].strip() if len(parts) > 1 else "mps"
                elif section == "ENDATA":
                    break
                continue
        # Parse section body.  MPS uses fixed columns but many files are
        # free-format; we tokenise by whitespace which handles both for the
        # common cases.
        tokens = line.split()
        if not tokens:
            continue
        if section == "OBJSENSE":
            s = tokens[0].upper()
            sense = "max" if s.startswith("MAX") else "min"
        elif section == "ROWS":
            rel = tokens[0].upper()
            rname = tokens[1] if len(tokens) > 1 else ""
            if rel not in ("N", "L", "G", "E"):
                raise ValueError(f"bad row type {rel!r} in ROWS")
            rows[rname] = rel
            if rel == "N":
                if obj_row_name is None or rname.upper() == "COST" or rname.upper() == "OBJ":
                    obj_row_name = rname
        elif section == "COLUMNS":
            # format: colname rowname coeff [rowname coeff ...]
            # but also MARKER lines: colname 'MARKER' 'INTORG'/'INTEND'
            col = tokens[0]
            if len(tokens) >= 3 and tokens[1] == "'MARKER'":
                if tokens[2].startswith("'INTORG") or tokens[2] == "'INTORG'":
                    integer_marker_on = True
                elif tokens[2].startswith("'INTEND") or tokens[2] == "'INTEND'":
                    integer_marker_on = False
                continue
            if col not in columns:
                columns[col] = {}
                col_order.append(col)
            if integer_marker_on:
                integer_vars.add(col)
            # parse (row, coeff) pairs
            rest = tokens[1:]
            for i in range(0, len(rest), 2):
                if i + 1 >= len(rest):
                    break
                rn = rest[i]
                coeff = _parse_num(rest[i + 1])
                columns[col][rn] = coeff
        elif section == "RHS":
            # format: rhsname rowname value [rowname value ...]
            rest = tokens[1:] if len(tokens) > 1 else []
            for i in range(0, len(rest), 2):
                if i + 1 >= len(rest):
                    break
                rn = rest[i]
                rhs[rn] = _parse_num(rest[i + 1])
        elif section == "RANGES":
            rest = tokens[1:] if len(tokens) > 1 else []
            for i in range(0, len(rest), 2):
                if i + 1 >= len(rest):
                    break
                rn = rest[i]
                ranges[rn] = _parse_num(rest[i + 1])
        elif section == "BOUNDS":
            # format: boundtype boundname colname [value]
            btype = tokens[0].upper()
            col = tokens[2] if len(tokens) > 2 else ""
            val = _parse_num(tokens[3]) if len(tokens) > 3 else None
            lo, hi = bounds.get(col, (Fraction(0), None))
            if btype == "LO":
                lo = val
            elif btype == "UP":
                hi = val
            elif btype == "FX":
                lo = hi = val
            elif btype == "MI":
                lo = None
            elif btype == "PL":
                hi = None
            elif btype == "FR":
                lo = hi = None
            elif btype == "BV":
                lo, hi = Fraction(0), Fraction(1)
                integer_vars.add(col)
            elif btype == "LI":
                lo = val
                integer_vars.add(col)
            elif btype == "UI":
                hi = val
                integer_vars.add(col)
            bounds[col] = (lo, hi)
    # Build LPProblem.
    if obj_row_name is None:
        # find any N row
        for rn, rel in rows.items():
            if rel == "N":
                obj_row_name = rn
                break
    if obj_row_name is None:
        raise ValueError("MPS file has no objective (N) row")
    # variables = column order; objective coeffs from obj_row column entries.
    objective_coeffs = {c: columns[c].get(obj_row_name, Fraction(0)) for c in col_order}
    # constraints
    constraints = []
    for rn, rel in rows.items():
        if rel == "N":
            continue
        coeffs = {}
        for c in col_order:
            a = columns[c].get(rn, Fraction(0))
            if a != 0:
                coeffs[c] = a
        b = rhs.get(rn, Fraction(0))
        relation = {"L": "<=", "G": ">=", "E": "="}[rel]
        # Apply RANGES: for L, range r means b' = b + |r| (if r>0) or b-|r|.
        # Standard semantics:
        #   L row with range r:  b <= a.x <= b + |r|   (if r>=0)
        #   G row with range r:  b - |r| <= a.x <= b
        #   E row with range r:  b <= a.x <= b+|r| (r>0) or b-|r|<=a.x<=b (r<0)
        cname = rn
        if rn in ranges:
            r = ranges[rn]
            if rel == "L":
                # L row with range: b - |r| <= a.x <= b
                constraints.append({"coeffs": coeffs, "relation": "<=", "rhs": b, "name": cname})
                constraints.append({"coeffs": coeffs, "relation": ">=", "rhs": b - abs(r), "name": cname + "_lo"})
            elif rel == "G":
                # G row with range: b <= a.x <= b + |r|
                constraints.append({"coeffs": coeffs, "relation": ">=", "rhs": b, "name": cname})
                constraints.append({"coeffs": coeffs, "relation": "<=", "rhs": b + abs(r), "name": cname + "_hi"})
            else:  # E
                if r >= 0:
                    constraints.append({"coeffs": coeffs, "relation": ">=", "rhs": b, "name": cname})
                    constraints.append({"coeffs": coeffs, "relation": "<=", "rhs": b + r, "name": cname + "_hi"})
                else:
                    constraints.append({"coeffs": coeffs, "relation": "<=", "rhs": b, "name": cname})
                    constraints.append({"coeffs": coeffs, "relation": ">=", "rhs": b + r, "name": cname + "_lo"})
        else:
            constraints.append({"coeffs": coeffs, "relation": relation, "rhs": b, "name": cname})
    # default bounds: non-negative unless specified
    norm_bounds = {}
    for c in col_order:
        norm_bounds[c] = bounds.get(c, (Fraction(0), None))
    return LPProblem(
        name=name,
        objective=sense,
        variables=tuple(col_order),
        objective_coeffs=objective_coeffs,
        constraints=constraints,
        bounds=norm_bounds,
        integer=integer_vars,
    )


def write_mps(problem: LPProblem, path: str) -> None:
    """Write ``problem`` to ``path`` in fixed-column MPS format."""
    lines: list[str] = []
    lines.append(f"NAME          {problem.name}")
    lines.append("OBJSENSE")
    lines.append(f"  {problem.objective.upper()}")
    lines.append("ROWS")
    lines.append(f" N  OBJ")
    for i, c in enumerate(problem.constraints):
        rel = c["relation"]
        code = {"<=": "L", ">=": "G", "=": "E"}[rel]
        cname = c.get("name", f"R{i}")
        lines.append(f" {code}  {cname}")
    lines.append("COLUMNS")
    int_active = False
    for v in problem.variables:
        if v in problem.integer and not int_active:
            lines.append(f"    {v:<8} 'MARKER'                 'INTORG'")
            int_active = True
        elif v not in problem.integer and int_active:
            lines.append(f"    {v:<8} 'MARKER'                 'INTEND'")
            int_active = False
        entries = [("OBJ", problem.objective_coeffs.get(v, Fraction(0)))]
        for i, c in enumerate(problem.constraints):
            a = c["coeffs"].get(v, Fraction(0))
            if a != 0:
                cname = c.get("name", f"R{i}")
                entries.append((cname, a))
        # MPS allows up to 2 (row, coeff) pairs per line.
        for k in range(0, len(entries), 2):
            chunk = entries[k:k + 2]
            parts = [f"    {v:<8}"]
            for rn, val in chunk:
                parts.append(f"    {rn:<8} {float(val):<14.6g}")
            lines.append("".join(parts))
    if int_active:
        # Use the last variable's name as the column field for the INTEND
        # marker, matching the INTORG format.  Without a column name the
        # marker line is malformed and may be rejected by strict parsers.
        last_var = problem.variables[-1]
        lines.append(f"    {last_var:<8} 'MARKER'                 'INTEND'")
        int_active = False
    lines.append("RHS")
    rhs_name = "RHS1"
    for i, c in enumerate(problem.constraints):
        cname = c.get("name", f"R{i}")
        b = float(c["rhs"])
        lines.append(f"    {rhs_name:<8}    {cname:<8} {b:<14.6g}")
    lines.append("BOUNDS")
    bnd_name = "BND1"
    for v in problem.variables:
        lo, hi = problem.bounds.get(v, (Fraction(0), None))
        if lo is None and hi is None:
            lines.append(f" FR {bnd_name:<8} {v:<8}")
        elif lo is not None and hi is not None and lo == hi:
            lines.append(f" FX {bnd_name:<8} {v:<8} {float(lo):<14.6g}")
        else:
            if lo is not None and lo != 0:
                lines.append(f" LO {bnd_name:<8} {v:<8} {float(lo):<14.6g}")
            elif lo is None:
                lines.append(f" MI {bnd_name:<8} {v:<8}")
            if hi is not None:
                lines.append(f" UP {bnd_name:<8} {v:<8} {float(hi):<14.6g}")
    lines.append("ENDATA")
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")