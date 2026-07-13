"""Graphviz DOT visualization for LR automata.

Generates DOT graph descriptions that can be rendered with Graphviz
(`dot`, `neato`, etc.) to produce visual diagrams of the LR(0)/LALR(1)
state machine.

Usage::

    from lalr import Grammar, LALRTable
    from lalr.visualize import automaton_to_dot

    grammar = Grammar([("S", ["a", "S"]), ("S", ["a"])])
    table = LALRTable(grammar)
    dot = automaton_to_dot(table)
    with open("automaton.dot", "w") as f:
        f.write(dot)
    # Then: dot -Tpng automaton.dot -o automaton.png
"""

from __future__ import annotations

from typing import Optional

from .table import LALRTable


def _escape_dot(text: str) -> str:
    """Escape special characters for DOT format."""
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def automaton_to_dot(
    table: LALRTable,
    title: Optional[str] = None,
    show_lookaheads: bool = False,
    horizontal: bool = False,
) -> str:
    """Generate a Graphviz DOT description of the LR automaton.

    Args:
        table: A built LALRTable (or SLRTable with compatible interface).
        title: Optional graph title.
        show_lookaheads: If True, include LALR(1) lookahead sets in state
            labels (only works if the table has a ``lalr`` attribute).
        horizontal: If True, lay out the graph left-to-right.

    Returns:
        A DOT format string suitable for piping to ``dot``.
    """
    lines = ["digraph LRAutomaton {"]
    if horizontal:
        lines.append('  rankdir=LR;')
    if title:
        lines.append(f'  label="{_escape_dot(title)}";')
        lines.append('  labelloc="t";')
    lines.append('  fontname="Helvetica";')
    lines.append('  node [shape=box, fontname="Helvetica", style=rounded];')
    lines.append('  edge [fontname="Helvetica"];')
    lines.append("")

    # Emit states
    for idx in range(table.num_states):
        state = table.automaton.get_state(idx)
        # Build label
        item_lines = []
        for item in sorted(state, key=lambda i: (i.production.index, i.dot)):
            body = list(item.production.body)
            body.insert(item.dot, "•")
            rhs = " ".join(body) if body != ["•"] else "•"
            line = f"{item.production.head} → {rhs}"
            if show_lookaheads and hasattr(table, 'lalr') and table.lalr is not None:
                las = table.lalr.lookaheads.get((idx, item), set())
                if las:
                    la_str = ", ".join(sorted(las))
                    line += f"  /{{{la_str}}}"
            item_lines.append(line)

        label = f"State {idx}\\n" + "\\n".join(
            _escape_dot(l) for l in item_lines
        )

        # Determine if this is an accept state
        is_accept = (
            "$" in table.action.get(idx, {})
            and table.action[idx]["$"][0] == "accept"
        )
        if is_accept:
            lines.append(
                f'  S{idx} [label="{label}", shape=doubleoctagon, '
                f'fillcolor=lightgreen, style="rounded,filled"];'
            )
        else:
            # Check if any reduce items
            has_reduce = any(item.is_reduce for item in state)
            if has_reduce:
                lines.append(
                    f'  S{idx} [label="{label}", fillcolor=lightyellow, '
                    f'style="rounded,filled"];'
                )
            else:
                lines.append(
                    f'  S{idx} [label="{label}", fillcolor=lightblue, '
                    f'style="rounded,filled"];'
                )

    lines.append("")

    # Emit transitions
    transitions = table.automaton.transitions
    for from_state, trans_map in transitions.items():
        for sym, to_state in sorted(trans_map.items(), key=lambda x: (x[0], x[1])):
            # Distinguish terminal (shift) from non-terminal (goto) edges
            is_terminal = table.grammar.is_terminal(sym)
            if is_terminal:
                edge_style = "solid"
                edge_color = "darkblue"
            else:
                edge_style = "dashed"
                edge_color = "darkgreen"
            lines.append(
                f'  S{from_state} -> S{to_state} '
                f'[label="{_escape_dot(sym)}", style={edge_style}, '
                f'color={edge_color}];'
            )

    lines.append("}")
    return "\n".join(lines)


def table_to_html(table: LALRTable) -> str:
    """Generate an HTML table representation of the ACTION/GOTO tables.

    Useful for embedding in documentation or web pages.
    """
    grammar = table.grammar
    terms = sorted(grammar.terminals)
    nonterms = sorted(grammar.nonterminals - {grammar.AUGMENTED_START})

    lines = ['<table border="1" cellpadding="4" cellspacing="0">']

    # Header row
    header = '<tr><th>State</th>'
    for t in terms:
        header += f'<th>{t}</th>'
    for nt in nonterms:
        header += f'<th>{nt}</th>'
    header += '</tr>'
    lines.append(header)

    # Data rows
    for s in range(table.num_states):
        row = f'<tr><td><b>{s}</b></td>'
        for t in terms:
            act = table.action.get(s, {}).get(t)
            if act is None:
                cell = '&nbsp;'
            elif act[0] == "shift":
                cell = f's{act[1]}'
            elif act[0] == "reduce":
                cell = f'r{act[1]}'
            elif act[0] == "accept":
                cell = '<b>acc</b>'
            elif act[0] == "error":
                cell = '<span style="color:red">err</span>'
            else:
                cell = '&nbsp;'
            row += f'<td style="text-align:center">{cell}</td>'
        for nt in nonterms:
            g = table.goto.get(s, {}).get(nt, -1)
            cell = str(g) if g >= 0 else '&nbsp;'
            row += f'<td style="text-align:center">{cell}</td>'
        row += '</tr>'
        lines.append(row)

    lines.append('</table>')
    return "\n".join(lines)


def conflict_report(table: LALRTable) -> str:
    """Generate a human-readable conflict report.

    Returns a formatted string listing all conflicts (resolved and
    unresolved) with suggestions for fixing them.
    """
    lines = []
    if table.resolved_conflicts:
        lines.append(f"=== Resolved Conflicts ({len(table.resolved_conflicts)}) ===")
        for c in table.resolved_conflicts:
            lines.append(f"  ✓ {c}")
        lines.append("")

    if table.has_conflicts:
        lines.append(f"=== Unresolved Conflicts ({len(table.conflicts)}) ===")
        for c in table.conflicts:
            lines.append(f"  ✗ {c}")
        lines.append("")
        lines.append("Suggestions:")
        lines.append("  • Add precedence/associativity declarations (%left, %right, %nonassoc)")
        lines.append("  • Rewrite the grammar to remove ambiguity")
        lines.append("  • Use %prec directives for unary operators")
    else:
        if not table.resolved_conflicts:
            lines.append("No conflicts detected — grammar is LALR(1).")
        else:
            lines.append("All conflicts resolved by precedence/associativity.")

    return "\n".join(lines)