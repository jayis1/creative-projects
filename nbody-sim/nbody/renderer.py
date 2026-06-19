"""PPM (P6) frame renderer for N-body simulations.

The renderer maps simulation coordinates onto a pixel grid, optionally draws
motion trails (alpha-blended on a persistent buffer), and writes either a
single PPM file or a numbered sequence for later encoding into a video.

PPM P6 is chosen for simplicity (no external dependencies) and broad viewer
support. For video, run e.g.::

    ffmpeg -framerate 30 -i frame_%06d.ppm -c:v libx264 out.mp4
"""

from __future__ import annotations

import math
import os
from typing import List, Optional, Sequence, Tuple

from .simulation import Body


class Renderer:
    """Render simulation bodies to PPM images.

    Parameters
    ----------
    width, height:
        Output image dimensions in pixels.
    view_size:
        Half-width of the simulated region mapped onto the image (i.e. the
        view spans ``[-view_size, +view_size]`` in both axes, centered on the
        origin unless ``center`` is given).
    center:
        Optional (cx, cy) world-space center of the view.
    bg_color:
        ``(r, g, b)`` background color (0–255).
    body_color:
        ``(r, g, b)`` body color. Bodies brighter than the background.
    trails:
        If True, keep a persistent alpha buffer so successive frames build up
        motion trails.
    trail_decay:
        Per-frame darkening factor in ``[0, 1]`` for trails (1 = no decay).
    """

    def __init__(
        self,
        width: int = 512,
        height: int = 512,
        view_size: float = 15.0,
        center: Optional[Tuple[float, float]] = None,
        bg_color: Tuple[int, int, int] = (8, 8, 20),
        body_color: Tuple[int, int, int] = (255, 240, 200),
        trails: bool = True,
        trail_decay: float = 0.92,
    ) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("width and height must be positive")
        if view_size <= 0:
            raise ValueError("view_size must be positive")
        self.width = width
        self.height = height
        self.view_size = view_size
        self.center = center or (0.0, 0.0)
        self.bg_color = bg_color
        self.body_color = body_color
        self.trails = trails
        self.trail_decay = trail_decay
        # Persistent pixel buffer for trails (RGB triples per pixel).
        self._buffer: Optional[List[List[List[int]]]] = None
        if trails:
            self._buffer = [
                [list(bg_color) for _ in range(width)] for _ in range(height)
            ]

    # -- coordinate mapping ---------------------------------------------

    def _to_pixel(self, x: float, y: float) -> Tuple[int, int]:
        cx, cy = self.center
        # World -> pixel: scale by half-width.
        half_w = self.view_size
        px = int((x - cx + half_w) / (2.0 * half_w) * self.width)
        # Y flipped: world up = image up.
        py = int((half_w - (y - cy)) / (2.0 * half_w) * self.height)
        return (px, py)

    # -- drawing --------------------------------------------------------

    def _draw_point(self, px: int, py: int, color: Tuple[int, int, int]) -> None:
        if 0 <= px < self.width and 0 <= py < self.height:
            if self._buffer is not None:
                self._buffer[py][px] = list(color)
            else:
                # Fill on demand for the trailless path.
                pass

    def _draw_disc(
        self,
        px: int,
        py: int,
        radius: int,
        color: Tuple[int, int, int],
    ) -> None:
        """Filled disc with crude anti-aliased edge."""
        r2 = radius * radius
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                d2 = dx * dx + dy * dy
                if d2 <= r2:
                    nx = px + dx
                    ny = py + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        # Edge softening.
                        if d2 > (radius - 1) * (radius - 1):
                            blend = max(0.0, (radius - math.sqrt(d2)))
                            c = tuple(
                                int(self.bg_color[i] * (1 - blend)
                                    + color[i] * blend)
                                for i in range(3)
                            )
                        else:
                            c = color
                        if self._buffer is not None:
                            self._buffer[ny][nx] = list(c)

    # -- public API -----------------------------------------------------

    def render_frame(self, bodies: Sequence[Body]) -> bytes:
        """Render a single frame and return raw PPM P6 bytes."""
        # If not using trails, start from a fresh background each frame.
        if not self.trails or self._buffer is None:
            self._buffer = [
                [list(self.bg_color) for _ in range(self.width)]
                for _ in range(self.height)
            ]
        else:
            # Apply trail decay (darken every pixel toward bg_color).
            bg = self.bg_color
            d = self.trail_decay
            for row in self._buffer:
                for px in row:
                    for i in range(3):
                        px[i] = int(px[i] * d + bg[i] * (1 - d))

        # Draw each body.
        for b in bodies:
            px, py = self._to_pixel(b.x, b.y)
            # Radius scales with mass (logarithmic to avoid huge discs).
            r = max(1, int(1 + math.log10(max(b.m, 1e-9)) * 1.5 + 1))
            self._draw_disc(px, py, r, self.body_color)

        return self._encode_ppm()

    def _encode_ppm(self) -> bytes:
        assert self._buffer is not None
        header = f"P6\n{self.width} {self.height}\n255\n".encode("ascii")
        data = bytearray()
        for row in self._buffer:
            for px in row:
                data.append(px[0] & 0xFF)
                data.append(px[1] & 0xFF)
                data.append(px[2] & 0xFF)
        return header + bytes(data)

    def render_to_file(self, bodies: Sequence[Body], path: str) -> None:
        with open(path, "wb") as f:
            f.write(self.render_frame(bodies))

    def render_sequence(
        self,
        snapshots,
        out_dir: str,
        prefix: str = "frame",
    ) -> List[str]:
        """Render every :class:`Snapshot` to a numbered PPM file.

        Returns the list of written file paths.
        """
        os.makedirs(out_dir, exist_ok=True)
        paths: List[str] = []
        # Reset the trail buffer at the start of a sequence for consistency.
        if self.trails:
            self._buffer = [
                [list(self.bg_color) for _ in range(self.width)]
                for _ in range(self.height)
            ]
        for i, snap in enumerate(snapshots):
            path = os.path.join(out_dir, f"{prefix}_{i:06d}.ppm")
            self.render_to_file(snap.bodies, path)
            paths.append(path)
        return paths


__all__ = ["Renderer"]