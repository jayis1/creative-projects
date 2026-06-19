"""ASCII visualisation of the simulated heap.

Renders the heap as a row of cells, colour-coding live objects and free
space, and can also render an object-graph dot file for external tools.
"""

from __future__ import annotations

from typing import List

from .heap import Heap, Object


# ANSI colour codes
_RESET = "\033[0m"
_COLORS = [
    "\033[91m",  # red
    "\033[92m",  # green
    "\033[93m",  # yellow
    "\033[94m",  # blue
    "\033[95m",  # magenta
    "\033[96m",  # cyan
    "\033[31m",  # bright red
    "\033[32m",  # bright green
    "\033[33m",  # bright yellow
    "\033[34m",  # bright blue
]


def color_for_oid(oid: int) -> str:
    return _COLORS[oid % len(_COLORS)]


def render_heap_ascii(heap: Heap, *, width: int = 64,
                      use_color: bool = True) -> str:
    """Render the heap as an ASCII bar.

    Each cell is one character.  Occupied cells show the last digit of the
    owning object's ``oid`` (coloured); free cells show ``.``.
    """
    lines: List[str] = []
    lines.append(f"Heap: {heap.size} cells, used={heap.used}, "
                 f"free={heap.free}, frag={heap.fragmentation():.1%}")
    lines.append(f"high water mark = {heap.high_water_mark} cells")
    for start in range(0, heap.size, width):
        row = []
        for i in range(start, min(start + width, heap.size)):
            cell = heap.cells[i]
            if cell is None:
                row.append(".")
            else:
                ch = str(cell.oid % 10)
                if use_color:
                    ch = color_for_oid(cell.oid) + ch + _RESET
                row.append(ch)
        lines.append("".join(row))
    return "\n".join(lines)


def render_object_graph_dot(heap: Heap, roots=None) -> str:
    """Return a Graphviz DOT description of the live object graph."""
    lines = ["digraph heap {", '  rankdir=LR;', '  node [shape=box];']
    root_names = {}
    if roots is not None:
        for name, obj in roots.items():
            root_names[obj.oid] = name
            lines.append(f'  "{name}" [shape=ellipse, style=filled, '
                         f'fillcolor=lightblue];')
            if obj is not None and obj.alive:
                lines.append(f'  "{name}" -> "obj_{obj.oid}";')
    for o in heap.live_objects:
        if not o.alive:
            continue
        label = f"obj_{o.oid}" + (f"\\n({o.name})" if o.name else "")
        lines.append(f'  "obj_{o.oid}" [label="{label}\\nsize={o.size}"];')
        for ref in o.refs:
            tgt = ref.target
            if tgt is not None and tgt.alive:
                lines.append(f'  "obj_{o.oid}" -> "obj_{tgt.oid}"'
                             + (f' [label="{ref.name}"]' if ref.name else "")
                             + ";")
    lines.append("}")
    return "\n".join(lines)


def render_stats_table(records) -> str:
    """Render a list of :class:`CollectionStats` as an ASCII table."""
    if not records:
        return "No collections."
    header = (f"{'cycle':>5} {'collector':<22} {'live_b':>6} {'live_a':>6} "
              f"{'coll':>5} {'freed':>6} {'moved':>6} {'pause':>6} "
              f"{'frag_b':>7} {'frag_a':>7}")
    sep = "-" * len(header)
    lines = [header, sep]
    for r in records:
        lines.append(
            f"{r.cycle:>5} {r.collector:<22} {r.live_before:>6} "
            f"{r.live_after:>6} {r.collected:>5} {r.bytes_freed:>6} "
            f"{r.bytes_moved:>6} {r.pause_cells:>6} "
            f"{r.fragmentation_before:>6.1%} {r.fragmentation_after:>6.1%}")
    return "\n".join(lines)