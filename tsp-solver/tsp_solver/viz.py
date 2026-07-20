"""Tour visualization using ASCII art and optional matplotlib backend."""

from __future__ import annotations

from typing import List, Optional, Tuple

from .instance import TSPInstance
from .tour import Tour


def ascii_plot(instance: TSPInstance, tour: Tour, width: int = 60, height: int = 20) -> str:
    """Render a tour as an ASCII-art plot.

    Works with coordinate-based instances. For matrix-only instances, only
    the tour order is shown.
    """
    if instance.coords is None:
        # No coordinates — just show the order
        return "Tour (no coordinates): " + " → ".join(str(c) for c in tour.order) + " → 0"

    coords = instance.coords
    xs = coords[:, 0]
    ys = coords[:, 1]
    xmin, xmax = xs.min(), xs.max()
    ymin, ymax = ys.min(), ys.max()

    # Handle degenerate cases
    if xmax == xmin:
        xmax += 1
    if ymax == ymin:
        ymax += 1

    grid = [[" "] * width for _ in range(height)]

    def to_grid(x: float, y: float) -> Tuple[int, int]:
        gx = int((x - xmin) / (xmax - xmin) * (width - 1))
        gy = int((1 - (y - ymin) / (ymax - ymin)) * (height - 1))
        return gx, gy

    # Draw edges
    order = list(tour.order) + [tour.order[0]]
    for idx in range(len(order) - 1):
        c1 = order[idx]
        c2 = order[idx + 1]
        x1, y1 = to_grid(coords[c1, 0], coords[c1, 1])
        x2, y2 = to_grid(coords[c2, 0], coords[c2, 1])
        # Bresenham's line algorithm
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        cx, cy = x1, y1
        while True:
            if 0 <= cy < height and 0 <= cx < width:
                grid[cy][cx] = "."
            if cx == x2 and cy == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                cx += sx
            if e2 < dx:
                err += dx
                cy += sy

    # Draw cities
    for i in range(instance.n):
        gx, gy = to_grid(coords[i, 0], coords[i, 1])
        if 0 <= gy < height and 0 <= gx < width:
            grid[gy][gx] = "#"

    # Mark start city differently
    gx, gy = to_grid(coords[order[0], 0], coords[order[0], 1])
    if 0 <= gy < height and 0 <= gx < width:
        grid[gy][gx] = "@"

    lines = ["".join(row) for row in grid]
    header = f"Tour (len={tour.length:.2f}, n={instance.n})  @=start #=city .=edge"
    return header + "\n" + "\n".join(lines)


def tour_to_json(instance: TSPInstance, tour: Tour) -> dict:
    """Serialize a tour and instance to a JSON-serializable dict."""
    return {
        "name": instance.name,
        "n": instance.n,
        "length": tour.length,
        "order": list(tour.order),
        "coords": instance.coords.tolist() if instance.coords is not None else None,
    }