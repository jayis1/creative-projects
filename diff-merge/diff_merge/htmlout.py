"""
HTML diff output.

Generates a self-contained HTML document showing a colourised, line-numbered
diff between two files — ideal for web-based code review or email reports.

The output is a complete ``<html>`` document with inline CSS (no external
dependencies) so it can be opened directly in any browser or attached to
an email.
"""

from __future__ import annotations

from html import escape
from typing import List, Sequence

from .myers import DiffOp, Operation
from .inline import word_diff

__all__ = ["html_diff", "html_diff_document"]

# CSS for the diff table
_CSS = """
.diff-container { font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace; font-size: 13px; }
.diff-header { background: #f4f4f4; padding: 8px 12px; border-bottom: 2px solid #ddd; font-weight: bold; }
.diff-table { border-collapse: collapse; width: 100%; }
.diff-table td { padding: 0; vertical-align: top; white-space: pre-wrap; }
.diff-lineno { color: #999; padding: 0 8px; text-align: right; user-select: none;
               background: #fafafa; border-right: 1px solid #eee; min-width: 40px; }
.diff-add { background: #e6ffed; }
.diff-del { background: #ffeef0; }
.diff-add-line { color: #22863a; }
.diff-del-line { color: #cb2431; }
.diff-sign { font-weight: bold; padding: 0 4px 0 8px; }
.diff-content { padding: 0 8px 0 0; }
.diff-hunk-header { background: #f1f8ff; color: #6a737d; padding: 4px 12px;
                    font-weight: bold; border-top: 1px solid #d8ebff; border-bottom: 1px solid #d8ebff; }
ins { background: #acf2bd; text-decoration: none; }
del { background: #fdb8c0; text-decoration: none; }
"""


def _word_diff_html(a: str, b: str) -> tuple[str, str]:
    """Return ``(a_html, b_html)`` with ``<ins>``/``<del>`` tags."""
    parts = word_diff(a, b)
    a_out: List[str] = []
    b_out: List[str] = []
    for tag, a_part, b_part in parts:
        if tag == "equal":
            a_out.append(escape(a_part))
            b_out.append(escape(b_part))
        elif tag == "delete":
            a_out.append(f"<del>{escape(a_part)}</del>")
        elif tag == "insert":
            b_out.append(f"<ins>{escape(b_part)}</ins>")
        elif tag == "replace":
            a_out.append(f"<del>{escape(a_part)}</del>")
            b_out.append(f"<ins>{escape(b_part)}</ins>")
    return ("".join(a_out), "".join(b_out))


def html_diff(
    a: Sequence[str],
    b: Sequence[str],
    *,
    fromfile: str = "a",
    tofile: str = "b",
    algorithm: str = "myers",
    inline: bool = True,
) -> List[str]:
    """Generate an HTML diff table.

    Returns a list of HTML line strings (no trailing newlines).
    """
    from .myers import myers_diff
    from .patience import patience_diff
    from .histogram import histogram_diff

    if algorithm == "myers":
        ops = myers_diff(a, b)
    elif algorithm == "patience":
        ops = patience_diff(a, b)
    elif algorithm == "histogram":
        ops = histogram_diff(a, b)
    else:
        ops = myers_diff(a, b)

    lines: List[str] = []
    lines.append(f'<div class="diff-container">')
    lines.append(
        f'<div class="diff-header">{escape(fromfile)} → {escape(tofile)}</div>'
    )
    lines.append('<table class="diff-table">')

    # Track line numbers
    a_ln = 1
    b_ln = 1

    for op in ops:
        if op.tag == Operation.EQUAL:
            for i, j in zip(range(op.i1, op.i2), range(op.j1, op.j2)):
                lines.append(
                    f'<tr><td class="diff-lineno">{a_ln}</td>'
                    f'<td class="diff-lineno">{b_ln}</td>'
                    f'<td class="diff-sign"> </td>'
                    f'<td class="diff-content">{escape(a[i])}</td></tr>'
                )
                a_ln += 1
                b_ln += 1
        elif op.tag == Operation.DELETE:
            for i in range(op.i1, op.i2):
                lines.append(
                    f'<tr class="diff-del"><td class="diff-lineno">{a_ln}</td>'
                    f'<td class="diff-lineno"></td>'
                    f'<td class="diff-sign diff-del-line">-</td>'
                    f'<td class="diff-content">{escape(a[i])}</td></tr>'
                )
                a_ln += 1
        elif op.tag == Operation.INSERT:
            for j in range(op.j1, op.j2):
                lines.append(
                    f'<tr class="diff-add"><td class="diff-lineno"></td>'
                    f'<td class="diff-lineno">{b_ln}</td>'
                    f'<td class="diff-sign diff-add-line">+</td>'
                    f'<td class="diff-content">{escape(b[j])}</td></tr>'
                )
                b_ln += 1
        elif op.tag == Operation.REPLACE:
            a_lines = list(range(op.i1, op.i2))
            b_lines = list(range(op.j1, op.j2))
            if inline:
                # Interleave and show word-level diff
                for idx in range(max(len(a_lines), len(b_lines))):
                    ai = a_lines[idx] if idx < len(a_lines) else None
                    bj = b_lines[idx] if idx < len(b_lines) else None
                    if ai is not None and bj is not None:
                        a_html, b_html = _word_diff_html(a[ai], b[bj])
                        lines.append(
                            f'<tr class="diff-del"><td class="diff-lineno">{a_ln}</td>'
                            f'<td class="diff-lineno"></td>'
                            f'<td class="diff-sign diff-del-line">-</td>'
                            f'<td class="diff-content">{a_html}</td></tr>'
                        )
                        lines.append(
                            f'<tr class="diff-add"><td class="diff-lineno"></td>'
                            f'<td class="diff-lineno">{b_ln}</td>'
                            f'<td class="diff-sign diff-add-line">+</td>'
                            f'<td class="diff-content">{b_html}</td></tr>'
                        )
                        a_ln += 1
                        b_ln += 1
                    elif ai is not None:
                        lines.append(
                            f'<tr class="diff-del"><td class="diff-lineno">{a_ln}</td>'
                            f'<td class="diff-lineno"></td>'
                            f'<td class="diff-sign diff-del-line">-</td>'
                            f'<td class="diff-content">{escape(a[ai])}</td></tr>'
                        )
                        a_ln += 1
                    elif bj is not None:
                        lines.append(
                            f'<tr class="diff-add"><td class="diff-lineno"></td>'
                            f'<td class="diff-lineno">{b_ln}</td>'
                            f'<td class="diff-sign diff-add-line">+</td>'
                            f'<td class="diff-content">{escape(b[bj])}</td></tr>'
                        )
                        b_ln += 1
            else:
                for i in range(op.i1, op.i2):
                    lines.append(
                        f'<tr class="diff-del"><td class="diff-lineno">{a_ln}</td>'
                        f'<td class="diff-lineno"></td>'
                        f'<td class="diff-sign diff-del-line">-</td>'
                        f'<td class="diff-content">{escape(a[i])}</td></tr>'
                    )
                    a_ln += 1
                for j in range(op.j1, op.j2):
                    lines.append(
                        f'<tr class="diff-add"><td class="diff-lineno"></td>'
                        f'<td class="diff-lineno">{b_ln}</td>'
                        f'<td class="diff-sign diff-add-line">+</td>'
                        f'<td class="diff-content">{escape(b[j])}</td></tr>'
                    )
                    b_ln += 1

    lines.append("</table>")
    lines.append("</div>")
    return lines


def html_diff_document(
    a: Sequence[str],
    b: Sequence[str],
    *,
    fromfile: str = "a",
    tofile: str = "b",
    algorithm: str = "myers",
    inline: bool = True,
    title: str = "Diff",
) -> str:
    """Return a complete ``<html>`` document showing the diff."""
    body = "\n".join(
        html_diff(a, b, fromfile=fromfile, tofile=tofile, algorithm=algorithm, inline=inline)
    )
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        f'<meta charset="utf-8">\n<title>{escape(title)}</title>\n'
        f"<style>{_CSS}</style>\n"
        "</head>\n"
        "<body>\n"
        f"{body}\n"
        "</body>\n"
        "</html>"
    )