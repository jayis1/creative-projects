"""Output formatting for query results.

Provides multiple output formats for query results:

* ``binding`` — the classic Prolog-style ``X = value`` format.
* ``table`` — aligned ASCII table.
* ``json`` — JSON array of binding objects.
* ``csv`` — comma-separated values.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any, Dict, List


def _format_value(v: Any) -> str:
    """Format a single value for display."""
    if isinstance(v, str):
        return repr(v)
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def format_binding(binding: Dict[str, Any]) -> str:
    """Format a query result binding as ``X = value, Y = value``."""
    parts = []
    for k in sorted(binding):
        parts.append(f"{k} = {_format_value(binding[k])}")
    return ", ".join(parts)


def format_results(
    results: List[Dict[str, Any]], fmt: str = "binding"
) -> str:
    """Format a list of query results in the specified format.

    Parameters
    ----------
    results : list of dict
        Query result bindings (each maps variable name → Python value).
    fmt : str
        Output format: 'binding', 'table', 'json', or 'csv'.

    Returns
    -------
    str
        Formatted output string.
    """
    if fmt == "binding":
        if not results:
            return "false."
        lines = []
        for r in results:
            lines.append(format_binding(r))
        n = len(results)
        lines.append(f"({n} answer{'s' if n != 1 else ''})")
        return "\n".join(lines)

    if fmt == "json":
        return json.dumps(results, indent=2, default=str)

    if fmt == "csv":
        if not results:
            return ""
        buf = io.StringIO()
        # Collect all column names across all results
        cols: List[str] = sorted(
            set(k for r in results for k in r)
        )
        writer = csv.DictWriter(buf, fieldnames=cols)
        writer.writeheader()
        for r in results:
            writer.writerow(r)
        return buf.getvalue().strip()

    if fmt == "table":
        if not results:
            return "(no results)"
        # Collect all column names
        cols: List[str] = sorted(
            set(k for r in results for k in r)
        )
        # Compute column widths
        widths = {c: len(c) for c in cols}
        rows = []
        for r in results:
            row = {c: _format_value(r.get(c, "")) for c in cols}
            for c in cols:
                widths[c] = max(widths[c], len(str(row[c])))
            rows.append(row)
        # Build table
        sep = "+" + "+".join("-" * (widths[c] + 2) for c in cols) + "+"
        header = "|" + "|".join(
            f" {c:<{widths[c]}} " for c in cols
        ) + "|"
        lines = [sep, header, sep]
        for row in rows:
            lines.append(
                "|"
                + "|".join(f" {str(row[c]):<{widths[c]}} " for c in cols)
                + "|"
            )
        lines.append(sep)
        lines.append(f"({len(results)} row{'s' if len(results) != 1 else ''})")
        return "\n".join(lines)

    raise ValueError(f"unknown output format: {fmt!r}")