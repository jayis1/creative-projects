"""Deterministic guillotine sheet-cutting planner with rotation and waste metrics."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Part:
    name: str
    width: int
    height: int
    quantity: int = 1


@dataclass(frozen=True)
class Placement:
    name: str
    x: int
    y: int
    width: int
    height: int
    rotated: bool


class LayoutError(ValueError):
    """Raised for invalid dimensions or impossible part requests."""


def plan(width, height, parts, allow_rotation=True):
    """Pack parts using best-short-side-fit guillotine splitting.

    Returns (placements, free_rectangles). Coordinates and dimensions are integer units.
    Parts are sorted largest-first; each placement partitions one free rectangle into
    non-overlapping right and bottom remnants.
    """
    if type(width) is not int or type(height) is not int or width <= 0 or height <= 0:
        raise LayoutError("sheet dimensions must be positive integers")
    expanded = []
    for part in parts:
        if not isinstance(part, Part) or not part.name or type(part.width) is not int or type(part.height) is not int or part.width <= 0 or part.height <= 0 or type(part.quantity) is not int or part.quantity < 1:
            raise LayoutError("each part needs a name, positive integer dimensions, and positive integer quantity")
        expanded.extend([part] * part.quantity)
    expanded.sort(key=lambda p: (max(p.width, p.height), min(p.width, p.height), p.name), reverse=True)
    free = [(0, 0, width, height)]
    placed = []
    for part in expanded:
        choices = []
        for i, (x, y, fw, fh) in enumerate(free):
            for rw, rh, rotated in ((part.width, part.height, False), (part.height, part.width, True)):
                if rotated and (not allow_rotation or part.width == part.height):
                    continue
                if rw <= fw and rh <= fh:
                    choices.append(((min(fw-rw, fh-rh), max(fw-rw, fh-rh), y, x, i, rotated), i, rw, rh, rotated))
        if not choices:
            raise LayoutError("part {!r} does not fit on remaining sheet area".format(part.name))
        _, i, rw, rh, rotated = min(choices)
        x, y, fw, fh = free.pop(i)
        placed.append(Placement(part.name, x, y, rw, rh, rotated))
        # Split along the shorter leftover span to avoid needlessly thin remnants.
        if fw-rw < fh-rh:
            remnants = [(x+rw, y, fw-rw, fh), (x, y+rh, rw, fh-rh)]
        else:
            remnants = [(x+rw, y, fw-rw, rh), (x, y+rh, fw, fh-rh)]
        free.extend(r for r in remnants if r[2] > 0 and r[3] > 0)
    return placed, free


def waste_summary(width, height, placements):
    """Return used area, leftover area, and utilization fraction."""
    if type(width) is not int or type(height) is not int or width <= 0 or height <= 0:
        raise LayoutError("sheet dimensions must be positive integers")
    used = sum(p.width * p.height for p in placements)
    total = width * height
    return {"used": used, "waste": total-used, "utilization": used/total}
