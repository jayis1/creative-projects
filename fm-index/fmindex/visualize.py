"""ASCII visualization utilities for FM-Index internals.

Provides functions to visualize:

  - The Burrows–Wheeler Transform matrix (sorted rotations)
  - The suffix array
  - The LCP array as a skyline
  - Match positions on a text ruler
  - Coverage heatmaps
"""

from __future__ import annotations

from typing import List, Optional

from .index import FMIndex


def visualize_bwt_matrix(idx: FMIndex, max_rows: int = 20) -> str:
    """Return an ASCII rendering of the sorted-rotations matrix.

    Shows the first ``max_rows`` rows of the BWT matrix: the rotation,
    its SA value, and the BWT character (last column).
    """
    sa = idx.suffix_array
    text = idx._raw_text
    n = idx.n
    rows_to_show = min(max_rows, n)
    lines: List[str] = []
    col_w = max(3, len(str(n - 1)))
    lines.append(f"{'SA':>{col_w}}  {'rotation':<{n}}  {'BWT'}")
    lines.append(f"{'─' * col_w}  {'─' * n}  ──")
    for i in range(rows_to_show):
        s = sa[i]
        rotation = text[s:] + text[:s]
        bwt_char = idx.bwt[i]
        lines.append(f"{s:>{col_w}}  {rotation:<{n}}  {bwt_char}")
    if n > max_rows:
        lines.append(f"... ({n - max_rows} more rows)")
    return "\n".join(lines)


def visualize_suffix_array(idx: FMIndex, max_entries: int = 30) -> str:
    """Return an ASCII rendering of the suffix array with suffixes."""
    sa = idx.suffix_array
    text = idx._raw_text
    n = idx.n
    entries = min(max_entries, n)
    col_w = max(3, len(str(n - 1)))
    lines: List[str] = []
    lines.append(f"{'i':>{col_w}}  {'SA[i]':>{col_w}}  suffix")
    lines.append(f"{'─' * col_w}  {'─' * col_w}  {'─' * min(40, n)}")
    for i in range(entries):
        s = sa[i]
        suffix = text[s:]
        if len(suffix) > 40:
            suffix = suffix[:37] + "..."
        lines.append(f"{i:>{col_w}}  {s:>{col_w}}  {suffix}")
    if n > max_entries:
        lines.append(f"... ({n - max_entries} more entries)")
    return "\n".join(lines)


def visualize_lcp_skyline(idx: FMIndex, width: int = 60) -> str:
    """Return an ASCII skyline plot of the LCP array."""
    lcp = idx.lcp_array()
    n = len(lcp)
    if n == 0:
        return "(empty)"
    max_lcp = max(lcp) if lcp else 1
    if max_lcp == 0:
        return "(all LCP values are 0 — no repeats)"
    # sample to fit width
    step = max(1, n // width)
    lines: List[str] = []
    for i in range(0, n, step):
        val = lcp[i]
        bar_len = int((val / max_lcp) * width)
        lines.append(f"{i:>5} │{'█' * bar_len} {val}")
    lines.append(f"       └{'─' * width}")
    lines.append(f"        max LCP = {max_lcp}")
    return "\n".join(lines)


def visualize_matches(
    idx: FMIndex,
    pattern: str,
    context: int = 5,
) -> str:
    """Return an ASCII rendering of match positions with context."""
    positions = idx.locate(pattern)
    text = idx.text
    plen = len(pattern)
    if not positions:
        return f"No matches for {pattern!r}"
    lines: List[str] = []
    lines.append(f"Matches for {pattern!r} ({len(positions)} found):")
    lines.append("")
    for p in positions:
        ctx_start = max(0, p - context)
        ctx_end = min(len(text), p + plen + context)
        snippet = text[ctx_start:ctx_end]
        marker_offset = p - ctx_start
        marker = " " * marker_offset + "^" * plen
        pos_str = f"{p:>6}"
        lines.append(f"{pos_str} │ {snippet}")
        lines.append(f"{' ' * len(pos_str)} │ {marker}")
    return "\n".join(lines)


def visualize_coverage(
    idx: FMIndex,
    pattern: str,
    width: int = 70,
) -> str:
    """Return an ASCII coverage bar showing where matches fall in the text."""
    positions = idx.locate(pattern)
    text_len = len(idx.text)
    if text_len == 0:
        return "(empty text)"
    if not positions:
        return f"No matches for {pattern!r}"
    plen = len(pattern)
    # build a coverage bitmap sampled to `width` columns
    covered = [False] * text_len
    for p in positions:
        for j in range(plen):
            if 0 <= p + j < text_len:
                covered[p + j] = True
    bar: List[str] = []
    for col in range(width):
        lo = (col * text_len) // width
        hi = ((col + 1) * text_len) // width
        if hi <= lo:
            hi = lo + 1
        fraction = sum(covered[lo:hi]) / (hi - lo)
        if fraction > 0.7:
            bar.append("█")
        elif fraction > 0.3:
            bar.append("▓")
        elif fraction > 0.1:
            bar.append("░")
        else:
            bar.append(" ")
    lines: List[str] = []
    lines.append(f"Coverage of {pattern!r} ({len(positions)} matches, len={plen}):")
    lines.append(f"|{''.join(bar)}|")
    lines.append(f" 0{'':<{width // 2 - 3}}{text_len // 2}{'':<{width // 2 - 3}}{text_len}")
    total = sum(covered)
    lines.append(f" Covered: {total}/{text_len} ({100 * total / text_len:.1f}%)")
    return "\n".join(lines)


def visualize_alphabet_distribution(idx: FMIndex, width: int = 50) -> str:
    """Return an ASCII bar chart of character frequencies."""
    text = idx.text
    if not text:
        return "(empty text)"
    freq: dict[str, int] = {}
    for ch in text:
        freq[ch] = freq.get(ch, 0) + 1
    sorted_freq = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
    max_count = sorted_freq[0][1]
    lines: List[str] = []
    for ch, count in sorted_freq:
        bar_len = int((count / max_count) * width)
        display_ch = ch if ch.isprintable() and ch != " " else f"\\x{ord(ch):02x}"
        lines.append(f"  {display_ch:>4} │{'█' * bar_len} {count}")
    return "\n".join(lines)