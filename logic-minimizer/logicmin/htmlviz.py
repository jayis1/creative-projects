"""
HTML visualization for truth tables and Karnaugh maps.

Generates self-contained HTML pages with CSS styling to display boolean
functions, truth tables, K-maps, and minimized covers in a visual format
suitable for documentation or web display.

Functions
---------
* ``truth_table_html(func)`` — render a styled HTML truth table.
* ``kmap_html(func)`` — render a styled HTML K-map (2–5 variables).
* ``kmap_with_cover_html(func, cubes)`` — K-map with highlighted cover.
* ``full_report_html(func, result)`` — complete analysis report (truth table
  + K-map + prime implicants + minimized expression).
"""

from __future__ import annotations

from typing import List, Optional, Sequence

from .boolean import BooleanFunction, var_names, cube_covers
from .kmap import KarnaughMap, gray_code
from .quine_mccluskey import MinimizationResult

_HTML_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; margin: 2em; background: #f5f5f5; }}
  h1, h2 {{ color: #333; }}
  table {{ border-collapse: collapse; margin: 1em 0; background: white; }}
  th, td {{ border: 1px solid #999; padding: 6px 14px; text-align: center; }}
  th {{ background: #4a6fa5; color: white; font-weight: 600; }}
  td.on {{ background: #d4edda; color: #155724; font-weight: bold; }}
  td.off {{ background: #f8d7da; color: #721c24; }}
  td.dc {{ background: #fff3cd; color: #856404; font-weight: bold; }}
  td.covered {{ background: #cce5ff; color: #004085; font-weight: bold; border: 2px solid #004085; }}
  .info {{ background: white; padding: 1em; border-radius: 8px; margin: 1em 0; }}
  .sop {{ font-family: 'Courier New', monospace; font-size: 1.2em; background: #e9ecef; padding: 0.5em; border-radius: 4px; display: inline-block; }}
  .badge {{ display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 0.85em; font-weight: 600; }}
  .badge-qm {{ background: #007bff; color: white; }}
  .badge-espresso {{ background: #28a745; color: white; }}
  .badge-pos {{ background: #ffc107; color: #333; }}
</style>
</head>
<body>
"""

_HTML_FOOT = "\n</body>\n</html>\n"


def truth_table_html(func: BooleanFunction) -> str:
    """Render a boolean function's truth table as styled HTML."""
    names = func.var_names
    n = func.n_vars
    rows: List[str] = []
    rows.append(_HTML_HEAD.format(title=f"Truth Table — {func.name}"))
    rows.append(f"<h1>Truth Table: {func.name}</h1>")
    rows.append(f"<p>{n} variables: {', '.join(names)}</p>")
    rows.append("<table>")
    # Header
    header = "".join(f"<th>{name}</th>" for name in names)
    rows.append(f"<tr>{header}<th>f</th></tr>")
    # Rows
    for i in range(1 << n):
        bits = format(i, f"0{n}b")
        cells = "".join(f"<td>{b}</td>" for b in bits)
        if i in func.minterms:
            val_cell = '<td class="on">1</td>'
        elif i in func.dontcare:
            val_cell = '<td class="dc">-</td>'
        else:
            val_cell = '<td class="off">0</td>'
        rows.append(f"<tr>{cells}{val_cell}</tr>")
    rows.append("</table>")
    rows.append(_HTML_FOOT)
    return "\n".join(rows)


def kmap_html(func: BooleanFunction) -> str:
    """Render a Karnaugh map as styled HTML (2–5 variables)."""
    if func.n_vars < 2 or func.n_vars > 5:
        raise ValueError("HTML K-map supports 2–5 variables")
    n = func.n_vars
    if n == 2:
        row_vars, col_vars = 1, 1
    elif n == 3:
        row_vars, col_vars = 1, 2
    elif n == 4:
        row_vars, col_vars = 2, 2
    else:
        row_vars, col_vars = 2, 3
    row_grays = gray_code(row_vars)
    col_grays = gray_code(col_vars)
    names = var_names(n)
    row_names = names[:row_vars]
    col_names = names[row_vars:row_vars + col_vars]
    lines: List[str] = []
    lines.append(_HTML_HEAD.format(title=f"K-map — {func.name}"))
    lines.append(f"<h1>Karnaugh Map: {func.name}</h1>")
    lines.append("<table>")
    # Header
    header_cells = "".join(f"<th>{name}</th>" for name in row_names)
    col_header_cells = "".join(
        f"<th>{format(cg, f'0{col_vars}b')}</th>" for cg in col_grays
    )
    lines.append(f"<tr>{header_cells}{col_header_cells}</tr>")
    # Rows
    for rg in row_grays:
        row_label = format(rg, f"0{row_vars}b")
        label_cells = "".join(f"<th>{row_label}</th>")
        cells: List[str] = []
        for cg in col_grays:
            minterm = (rg << col_vars) | cg
            if minterm in func.minterms:
                cells.append('<td class="on">1</td>')
            elif minterm in func.dontcare:
                cells.append('<td class="dc">-</td>')
            else:
                cells.append('<td class="off">0</td>')
        lines.append(f"<tr>{label_cells}{''.join(cells)}</tr>")
    lines.append("</table>")
    lines.append(_HTML_FOOT)
    return "\n".join(lines)


def kmap_with_cover_html(
    func: BooleanFunction, cubes: Sequence[str]
) -> str:
    """Render a K-map with the minimized cover highlighted."""
    if func.n_vars < 2 or func.n_vars > 5:
        raise ValueError("HTML K-map supports 2–5 variables")
    n = func.n_vars
    if n == 2:
        row_vars, col_vars = 1, 1
    elif n == 3:
        row_vars, col_vars = 1, 2
    elif n == 4:
        row_vars, col_vars = 2, 2
    else:
        row_vars, col_vars = 2, 3
    row_grays = gray_code(row_vars)
    col_grays = gray_code(col_vars)
    names = var_names(n)
    row_names = names[:row_vars]
    col_names = names[row_vars:row_vars + col_vars]
    lines: List[str] = []
    lines.append(_HTML_HEAD.format(title=f"K-map with Cover — {func.name}"))
    lines.append(f"<h1>Karnaugh Map with Cover: {func.name}</h1>")
    lines.append("<table>")
    header_cells = "".join(f"<th>{name}</th>" for name in row_names)
    col_header_cells = "".join(
        f"<th>{format(cg, f'0{col_vars}b')}</th>" for cg in col_grays
    )
    lines.append(f"<tr>{header_cells}{col_header_cells}</tr>")
    for rg in row_grays:
        row_label = format(rg, f"0{row_vars}b")
        label_cells = "".join(f"<th>{row_label}</th>")
        cells: List[str] = []
        for cg in col_grays:
            minterm = (rg << col_vars) | cg
            if minterm in func.minterms:
                covered = any(cube_covers(c, minterm) for c in cubes)
                if covered:
                    cells.append('<td class="covered">1</td>')
                else:
                    cells.append('<td class="on">1</td>')
            elif minterm in func.dontcare:
                cells.append('<td class="dc">-</td>')
            else:
                cells.append('<td class="off">0</td>')
        lines.append(f"<tr>{label_cells}{''.join(cells)}</tr>")
    lines.append("</table>")
    lines.append(_HTML_FOOT)
    return "\n".join(lines)


def full_report_html(
    func: BooleanFunction,
    result: Optional[MinimizationResult] = None,
) -> str:
    """Generate a full HTML report: truth table, K-map, and minimized expression."""
    lines: List[str] = []
    lines.append(_HTML_HEAD.format(title=f"Logic Report — {func.name}"))
    lines.append(f"<h1>Boolean Function Analysis: {func.name}</h1>")
    lines.append("<div class='info'>")
    lines.append(f"<p><strong>Variables:</strong> {func.n_vars} ({', '.join(func.var_names)})</p>")
    lines.append(f"<p><strong>On-set minterms:</strong> {sorted(func.minterms)}</p>")
    if func.dontcare:
        lines.append(f"<p><strong>Don't-cares:</strong> {sorted(func.dontcare)}</p>")
    lines.append("</div>")
    if result is not None:
        lines.append("<h2>Minimized Expression</h2>")
        method_label = result.method.replace("-", " ").title()
        badge_class = "badge-qm" if "mccluskey" in result.method else \
                      "badge-espresso" if "espresso" in result.method else "badge-pos"
        lines.append(f"<p><span class='badge {badge_class}'>{method_label}</span></p>")
        lines.append(f"<p class='sop'>{result.sop}</p>")
        lines.append(f"<p><strong>Terms:</strong> {result.n_terms} &nbsp; "
                     f"<strong>Literals:</strong> {result.n_literals}</p>")
        if result.prime_implicants:
            names = func.var_names
            lines.append("<h2>Prime Implicants</h2>")
            lines.append("<table>")
            lines.append("<tr><th>Cube</th><th>Product Term</th><th>Literals</th><th>Essential</th></tr>")
            for p in result.prime_implicants:
                ess = "Yes" if p in result.essential_implicants else "No"
                lines.append(
                    f"<tr><td>{p.cube}</td><td>{p.sop_term(names)}</td>"
                    f"<td>{p.n_literals}</td><td>{ess}</td></tr>"
                )
            lines.append("</table>")
    # Truth table
    lines.append("<h2>Truth Table</h2>")
    lines.append(_truth_table_table_html(func))
    # K-map
    if 2 <= func.n_vars <= 5:
        lines.append("<h2>Karnaugh Map</h2>")
        if result is not None:
            lines.append(_kmap_table_html(func, result.sop_cubes, highlight=True))
        else:
            lines.append(_kmap_table_html(func, [], highlight=False))
    lines.append(_HTML_FOOT)
    return "\n".join(lines)


def _truth_table_table_html(func: BooleanFunction) -> str:
    """Just the truth table (HTML table element), for embedding."""
    names = func.var_names
    n = func.n_vars
    rows: List[str] = ["<table>"]
    header = "".join(f"<th>{name}</th>" for name in names)
    rows.append(f"<tr>{header}<th>f</th></tr>")
    for i in range(1 << n):
        bits = format(i, f"0{n}b")
        cells = "".join(f"<td>{b}</td>" for b in bits)
        if i in func.minterms:
            val_cell = '<td class="on">1</td>'
        elif i in func.dontcare:
            val_cell = '<td class="dc">-</td>'
        else:
            val_cell = '<td class="off">0</td>'
        rows.append(f"<tr>{cells}{val_cell}</tr>")
    rows.append("</table>")
    return "\n".join(rows)


def _kmap_table_html(
    func: BooleanFunction,
    cubes: Sequence[str],
    highlight: bool = False,
) -> str:
    """Just the K-map (HTML table element), for embedding."""
    n = func.n_vars
    if n == 2:
        row_vars, col_vars = 1, 1
    elif n == 3:
        row_vars, col_vars = 1, 2
    elif n == 4:
        row_vars, col_vars = 2, 2
    else:
        row_vars, col_vars = 2, 3
    row_grays = gray_code(row_vars)
    col_grays = gray_code(col_vars)
    names = var_names(n)
    row_names = names[:row_vars]
    rows: List[str] = ["<table>"]
    header_cells = "".join(f"<th>{name}</th>" for name in row_names)
    col_header_cells = "".join(
        f"<th>{format(cg, f'0{col_vars}b')}</th>" for cg in col_grays
    )
    rows.append(f"<tr>{header_cells}{col_header_cells}</tr>")
    for rg in row_grays:
        row_label = format(rg, f"0{row_vars}b")
        label_cells = "".join(f"<th>{row_label}</th>")
        cells: List[str] = []
        for cg in col_grays:
            minterm = (rg << col_vars) | cg
            if minterm in func.minterms:
                if highlight and any(cube_covers(c, minterm) for c in cubes):
                    cells.append('<td class="covered">1</td>')
                else:
                    cells.append('<td class="on">1</td>')
            elif minterm in func.dontcare:
                cells.append('<td class="dc">-</td>')
            else:
                cells.append('<td class="off">0</td>')
        rows.append(f"<tr>{label_cells}{''.join(cells)}</tr>")
    rows.append("</table>")
    return "\n".join(rows)