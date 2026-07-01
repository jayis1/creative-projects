"""
Patch parser and applier.

Parses unified-diff patches and applies them to text with optional
fuzz tolerance and reject (.rej) file generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from .format import Hunk

__all__ = ["parse_unified_diff", "apply_patch", "PatchError"]


class PatchError(Exception):
    """Raised when a patch cannot be applied."""


@dataclass
class PatchResult:
    """Result of applying a patch."""
    patched: List[str]
    applied_hunks: int = 0
    rejected_hunks: int = 0
    fuzz_used: int = 0
    offsets: List[int] = field(default_factory=list)
    rejected: List[Hunk] = field(default_factory=list)


def parse_unified_diff(lines: List[str]) -> List[Hunk]:
    """Parse a unified-diff patch into a list of :class:`Hunk` objects.

    Only hunk bodies are extracted; file headers (---/+++) are skipped.
    """
    hunks: List[Hunk] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # Skip file headers and other non-hunk lines
        if line.startswith("---") or line.startswith("+++"):
            i += 1
            continue

        if line.startswith("@@"):
            # Parse hunk header
            hunk = _parse_hunk_header(line)
            i += 1
            # Read hunk body
            while i < n and not lines[i].startswith("@@"):
                body = lines[i]
                if body.startswith("---") or body.startswith("+++"):
                    break
                if body.startswith(" "):
                    hunk.lines.append((" ", body[1:]))
                elif body.startswith("-"):
                    hunk.lines.append(("-", body[1:]))
                elif body.startswith("+"):
                    hunk.lines.append(("+", body[1:]))
                elif body.startswith("\\"):
                    # "\ No newline at end of file" marker
                    pass
                elif body == "":
                    hunk.lines.append((" ", ""))
                else:
                    # Unknown line — stop
                    break
                i += 1
            hunks.append(hunk)
        else:
            i += 1

    return hunks


def _parse_hunk_header(header: str) -> Hunk:
    """Parse a @@ -old_start,old_count +new_start,new_count @@ line."""
    # Expected: @@ -start,count +start,count @@
    # count may be omitted (defaults to 1)
    import re

    m = re.match(
        r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@", header
    )
    if not m:
        raise PatchError(f"Invalid hunk header: {header!r}")

    old_start = int(m.group(1))
    old_count = int(m.group(2)) if m.group(2) is not None else 1
    new_start = int(m.group(3))
    new_count = int(m.group(4)) if m.group(4) is not None else 1

    return Hunk(
        old_start=old_start,
        old_count=old_count,
        new_start=new_start,
        new_count=new_count,
        lines=[],
    )


def apply_patch(
    source: List[str],
    hunks: List[Hunk],
    *,
    fuzz: int = 0,
    max_offset: int = 100,
) -> PatchResult:
    """Apply *hunks* to *source* lines.

    Parameters
    ----------
    source : list of lines (strings, may or may not include trailing \\n)
    hunks : list of parsed Hunk objects
    fuzz : allowed number of context lines to ignore at edges (default 0)
    max_offset : max line offset to search for a match

    Returns
    -------
    PatchResult with patched lines and statistics
    """
    if not hunks:
        return PatchResult(patched=list(source))

    result: List[str] = list(source)
    applied = 0
    rejected = 0
    fuzz_total = 0
    offsets: List[int] = []
    rejected_hunks: List[Hunk] = []

    cumulative_offset = 0

    for hunk in hunks:
        # The expected position (0-based) in the current result
        expected_pos = hunk.old_start - 1 + cumulative_offset

        # Extract context+delete lines (the "old" content to match)
        old_content = [
            text for sign, text in hunk.lines if sign in (" ", "-")
        ]
        # Extract new content (context + insert)
        new_content = [
            text for sign, text in hunk.lines if sign in (" ", "+")
        ]

        # Try to find a match at expected_pos, searching outward
        match_pos, used_fuzz = _find_match(
            result, expected_pos, old_content,
            fuzz=fuzz, max_offset=max_offset,
        )

        if match_pos is not None:
            # Apply: replace old_content region with new_content
            end_pos = match_pos + len(old_content)
            result[match_pos:end_pos] = new_content
            actual_offset = match_pos - (hunk.old_start - 1)
            offsets.append(actual_offset)
            cumulative_offset += len(new_content) - len(old_content)
            applied += 1
            fuzz_total += used_fuzz
        else:
            rejected += 1
            rejected_hunks.append(hunk)

    return PatchResult(
        patched=result,
        applied_hunks=applied,
        rejected_hunks=rejected,
        fuzz_used=fuzz_total,
        offsets=offsets,
        rejected=rejected_hunks,
    )


def _find_match(
    source: List[str],
    expected: int,
    old_content: List[str],
    *,
    fuzz: int,
    max_offset: int,
) -> Tuple[int | None, int]:
    """Find the position in *source* where *old_content* matches.

    Searches outward from *expected*, trying exact match first, then
    progressively more fuzz (stripping leading/trailing context lines).

    Returns (match_position, fuzz_used) or (None, 0).
    """
    if not old_content:
        # Empty old content — insert at expected position
        return (max(0, min(expected, len(source))), 0)

    # Try exact match at expected, then offset search
    for offset in range(0, max_offset + 1):
        for direction in (1, -1) if offset > 0 else (1,):
            pos = expected + direction * offset
            if pos < 0 or pos + len(old_content) > len(source):
                continue
            if _lines_match(source, pos, old_content, fuzz_lines=0):
                return (pos, 0)

    # Try with fuzz
    for f in range(1, fuzz + 1):
        # Strip f context lines from each end
        stripped = _strip_context(old_content, f)
        if stripped is None:
            continue
        trimmed, trim_count = stripped
        for offset in range(0, max_offset + 1):
            for direction in (1, -1) if offset > 0 else (1,):
                pos = expected + direction * offset
                # The stripped content starts at pos + trim_count_leading
                lead_trim = f if len(old_content) > f else len(old_content)
                actual_pos = pos + lead_trim
                if actual_pos < 0 or actual_pos + len(trimmed) > len(source):
                    continue
                if _lines_match(source, actual_pos, trimmed, fuzz_lines=0):
                    # Verify position is reasonable
                    if pos >= 0 and pos + len(old_content) <= len(source):
                        return (pos, f)

    return (None, 0)


def _lines_match(
    source: List[str], pos: int, content: List[str], *, fuzz_lines: int
) -> bool:
    """Check if source[pos:pos+len(content)] matches content,
    allowing *fuzz_lines* of mismatch at the start and end."""
    if pos + len(content) > len(source):
        return False

    start = fuzz_lines
    end = len(content) - fuzz_lines
    for k in range(start, end):
        if source[pos + k] != content[k]:
            return False
    return True


def _strip_context(
    content: List[str], f: int
) -> Tuple[List[str], int] | None:
    """Strip *f* context lines from the start and end of *content*.

    Since we don't have the sign info here (context vs deletion),
    we just strip f lines from each end if the content is long enough.
    This is a known limitation: fuzz may strip deletion lines, not just
    context lines.  For proper context-aware fuzz, the caller would need
    to pass the hunk's sign information.

    Returns (stripped_content, total_trimmed) or None if content too short.
    """
    if len(content) <= 2 * f:
        return None
    return (content[f:-f], 2 * f)