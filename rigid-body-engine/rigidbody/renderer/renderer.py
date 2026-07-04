"""Headless renderers: ASCII art and PPM image output.

The engine is simulation-only; rendering is decoupled so it can run on any
backend.  These two renderers need only the standard library.

* :class:`AsciiRenderer` — prints a top-down view to the terminal using
  characters shaded by body type.  Great for quick debugging.
* :class:`PPMRenderer` — writes uncompressed P6 PPM images frame-by-frame,
  suitable for converting to a GIF/MP4 with ffmpeg.
"""

from __future__ import annotations

import math
import os
from typing import List, Optional

from ..core.body import RigidBody
from ..core.shapes import Circle, Polygon
from ..core.vec2 import Vec2

__all__ = ["AsciiRenderer", "PPMRenderer"]


# Palette for ASCII rendering — one char per body type / shape.
_ASCII_DYNAMIC = "#"
_ASCII_STATIC = "H"
_ASCII_KINEMATIC = "K"
_ASCII_EMPTY = " "


class AsciiRenderer:
    """Render the world as a grid of characters.

    The viewport maps a world-space rectangle to a character grid.  Bodies are
    rasterised by testing whether each cell's centre falls inside a body's
    world-space shape (circles get a distance test, polygons a point-in-poly).
    """

    def __init__(self, width: int = 70, height: int = 30,
                 world_min: Vec2 = Vec2(-10, -1), world_max: Vec2 = Vec2(10, 19)) -> None:
        self.width = width
        self.height = height
        self.world_min = world_min
        self.world_max = world_max

    def _to_cell(self, x: float, y: float) -> tuple[int, int]:
        col = int((x - self.world_min.x) / (self.world_max.x - self.world_min.x) * self.width)
        row = int((self.world_max.y - y) / (self.world_max.y - self.world_min.y) * self.height)
        return col, row

    def _cell_center_world(self, col: int, row: int) -> Vec2:
        wx = self.world_min.x + (col + 0.5) / self.width * (self.world_max.x - self.world_min.x)
        wy = self.world_max.y - (row + 0.5) / self.height * (self.world_max.y - self.world_min.y)
        return Vec2(wx, wy)

    def render(self, bodies: List[RigidBody]) -> str:
        grid = [[_ASCII_EMPTY for _ in range(self.width)] for _ in range(self.height)]
        for body in bodies:
            if body.is_static:
                ch = _ASCII_STATIC
            elif body.is_kinematic:
                ch = _ASCII_KINEMATIC
            else:
                ch = _ASCII_DYNAMIC
            shape = body.shape
            # Compute an AABB for this body and only test cells inside it.
            aabb = body.update_aabb()
            min_col, min_row = self._to_cell(aabb.min.x, aabb.min.y)
            max_col, max_row = self._to_cell(aabb.max.x, aabb.max.y)
            min_col = max(0, min_col)
            max_col = min(self.width - 1, max_col)
            min_row = max(0, min_row)
            max_row = min(self.height - 1, max_row)
            for row in range(min_row, max_row + 1):
                for col in range(min_col, max_col + 1):
                    p = self._cell_center_world(col, row)
                    if isinstance(shape, Circle):
                        center = shape.offset.rotate(body.angle) + body.position
                        if (p - center).length_sq() <= shape.radius * shape.radius:
                            grid[row][col] = ch
                    elif isinstance(shape, Polygon):
                        from ..core.collision import point_in_polygon
                        if point_in_polygon(p, shape, body.position, body.angle):
                            grid[row][col] = ch
        # Frame border.
        top = "+" + "-" * self.width + "+"
        lines = [top]
        for row in grid:
            lines.append("|" + "".join(row) + "|")
        lines.append(top)
        return "\n".join(lines)


class PPMRenderer:
    """Write P6 PPM frames to disk.

    Each call to :meth:`render_frame` writes ``frame_NNNN.ppm`` in the output
    directory.  Use ``ffmpeg -framerate 30 -i frame_%04d.ppm out.gif`` to
    assemble into an animation.
    """

    def __init__(self, output_dir: str, width: int = 320, height: int = 240,
                 world_min: Vec2 = Vec2(-10, -1), world_max: Vec2 = Vec2(10, 19),
                 bg: tuple[int, int, int] = (15, 15, 25)) -> None:
        os.makedirs(output_dir, exist_ok=True)
        self.output_dir = output_dir
        self.width = width
        self.height = height
        self.world_min = world_min
        self.world_max = world_max
        self.bg = bg
        self.frame = 0

    def _to_pixel(self, x: float, y: float) -> tuple[int, int]:
        px = int((x - self.world_min.x) / (self.world_max.x - self.world_min.x) * self.width)
        py = int((self.world_max.y - y) / (self.world_max.y - self.world_min.y) * self.height)
        return px, py

    def _body_color(self, body: RigidBody) -> tuple[int, int, int]:
        if body.is_static:
            return (120, 120, 120)
        if body.is_kinematic:
            return (80, 180, 255)
        # Dynamic — colour by speed for a little flair.
        speed = body.linear_velocity.length()
        t = min(1.0, speed / 8.0)
        r = int(220 * t + 40 * (1 - t))
        g = int(80 * t + 200 * (1 - t))
        b = int(60 * t + 120 * (1 - t))
        return (r, g, b)

    def render_frame(self, bodies: List[RigidBody]) -> str:
        # Build a pixel buffer.
        buf = bytearray()
        buf.extend(self.bg)
        buf = [bytearray(self.bg) for _ in range(self.width * self.height)]
        # Overwrite background per-pixel — start from bg.
        pixels = [list(self.bg) for _ in range(self.width * self.height)]
        for body in bodies:
            color = self._body_color(body)
            shape = body.shape
            if isinstance(shape, Circle):
                center = shape.offset.rotate(body.angle) + body.position
                cx, cy = self._to_pixel(center.x, center.y)
                r_px = int(shape.radius / (self.world_max.x - self.world_min.x) * self.width)
                # Draw a filled disc via bounding-box test.
                for dy in range(-r_px, r_px + 1):
                    for dx in range(-r_px, r_px + 1):
                        if dx * dx + dy * dy <= r_px * r_px:
                            px = cx + dx
                            py = cy + dy
                            if 0 <= px < self.width and 0 <= py < self.height:
                                pixels[py * self.width + px] = list(color)
            elif isinstance(shape, Polygon):
                # Rasterise polygon via scanline fill on world-space vertices.
                verts = [self._to_pixel(body.to_world(v).x, body.to_world(v).y) for v in shape.vertices]
                if not verts:
                    continue
                ys = [v[1] for v in verts]
                y_min = max(0, min(ys))
                y_max = min(self.height - 1, max(ys))
                for y in range(y_min, y_max + 1):
                    xs = []
                    n = len(verts)
                    for i in range(n):
                        x0, y0 = verts[i]
                        x1, y1 = verts[(i + 1) % n]
                        if (y0 <= y < y1) or (y1 <= y < y0):
                            t = (y - y0) / (y1 - y0)
                            xs.append(x0 + t * (x1 - x0))
                    xs.sort()
                    for k in range(0, len(xs) - 1, 2):
                        x_start = max(0, int(xs[k]))
                        x_end = min(self.width - 1, int(xs[k + 1]))
                        for x in range(x_start, x_end + 1):
                            pixels[y * self.width + x] = list(color)
        # Write PPM.
        path = os.path.join(self.output_dir, f"frame_{self.frame:04d}.ppm")
        with open(path, "wb") as f:
            f.write(f"P6\n{self.width} {self.height}\n255\n".encode())
            data = bytearray()
            for px in pixels:
                data.append(px[0])
                data.append(px[1])
                data.append(px[2])
            f.write(data)
        self.frame += 1
        return path