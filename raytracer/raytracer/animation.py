"""animation.py — Camera animation helpers for rendering frame sequences.

Provides reusable camera-path generators (orbit, linear dolly, spline) and a
high-level :func:`render_animation` driver that renders a sequence of frames
and writes them to an output directory.  Supports both image sequences (PNG
frames) and ASCII previews.

The animation module does not encode video directly — it produces numbered
frames that can be combined with ``ffmpeg`` or similar tools:

    ffmpeg -framerate 24 -i frames/frame_%04d.png -c:v libx264 out.mp4
"""

from __future__ import annotations

import math
import os
import time
from typing import Callable, List, Optional, Tuple

from .vec import Vec3
from .camera import Camera
from .scene import Scene
from . import imageio
from .logging import logger

__all__ = [
    "orbit_path",
    "linear_path",
    "spline_path",
    "render_animation",
]


def orbit_path(
    center: Vec3,
    radius: float,
    height: float,
    frames: int,
    look_at: Optional[Vec3] = None,
    start_angle: float = 0.0,
    end_angle: float = 2.0 * math.pi,
) -> List[Vec3]:
    """Generate a circular camera path around *center*.

    Returns a list of ``frames`` eye positions.  The camera looks at
    ``look_at`` (default: ``center``).
    """
    target = look_at if look_at is not None else center
    positions: List[Vec3] = []
    for i in range(frames):
        t = i / max(1, frames - 1)
        angle = start_angle + t * (end_angle - start_angle)
        x = center.x + radius * math.cos(angle)
        z = center.z + radius * math.sin(angle)
        positions.append(Vec3(x, height, z))
    return positions


def linear_path(
    start: Vec3,
    end: Vec3,
    frames: int,
) -> List[Vec3]:
    """Linear interpolation between *start* and *end* over *frames* positions."""
    positions: List[Vec3] = []
    for i in range(frames):
        t = i / max(1, frames - 1)
        positions.append(start.lerp(end, t))
    return positions


def spline_path(
    points: List[Vec3],
    frames: int,
) -> List[Vec3]:
    """Catmull–Rom spline interpolation through *points*.

    Generates ``frames`` evenly-spaced positions along a smooth spline
    passing through all control points.  The spline is open (no looping).
    """
    if len(points) < 2:
        return list(points) * frames
    if len(points) == 2:
        return linear_path(points[0], points[1], frames)
    # Extend with phantom points for the endpoints.
    extended = [points[0] * 2 - points[1]] + list(points) + [points[-1] * 2 - points[-2]]
    positions: List[Vec3] = []
    total_segments = len(extended) - 3
    for i in range(frames):
        t_global = i / max(1, frames - 1)
        seg = min(total_segments - 1, int(t_global * total_segments))
        local_t = t_global * total_segments - seg
        p0 = extended[seg]
        p1 = extended[seg + 1]
        p2 = extended[seg + 2]
        p3 = extended[seg + 3]
        # Catmull-Rom basis.
        t2 = local_t * local_t
        t3 = t2 * local_t
        x = 0.5 * (
            (2 * p1.x)
            + (-p0.x + p2.x) * local_t
            + (2 * p0.x - 5 * p1.x + 4 * p2.x - p3.x) * t2
            + (-p0.x + 3 * p1.x - 3 * p2.x + p3.x) * t3
        )
        y = 0.5 * (
            (2 * p1.y)
            + (-p0.y + p2.y) * local_t
            + (2 * p0.y - 5 * p1.y + 4 * p2.y - p3.y) * t2
            + (-p0.y + 3 * p1.y - 3 * p2.y + p3.y) * t3
        )
        z = 0.5 * (
            (2 * p1.z)
            + (-p0.z + p2.z) * local_t
            + (2 * p0.z - 5 * p1.z + 4 * p2.z - p3.z) * t2
            + (-p0.z + 3 * p1.z - 3 * p2.z + p3.z) * t3
        )
        positions.append(Vec3(x, y, z))
    return positions


def render_animation(
    scene: Scene,
    eye_positions: List[Vec3],
    out_dir: str,
    width: int = 320,
    height: int = 180,
    samples: int = 4,
    max_depth: int = 6,
    fmt: str = "png",
    look_at: Optional[Vec3] = None,
    progress: bool = True,
) -> List[str]:
    """Render a sequence of frames from a list of camera eye positions.

    Each frame uses the same scene but a camera positioned at the
    corresponding entry in *eye_positions*.  The camera always looks at
    ``look_at`` (default: the scene's existing ``look_at``).

    Returns the list of written file paths.
    """
    os.makedirs(out_dir, exist_ok=True)
    target = look_at if look_at is not None else scene.camera.look_at
    up = scene.camera.up
    vfov = scene.camera.vfov
    aspect = width / max(1, height)
    aperture = scene.camera.aperture
    focus_dist = scene.camera.focus_dist

    written: List[str] = []
    total = len(eye_positions)
    t0 = time.time()
    for i, eye in enumerate(eye_positions):
        cam = Camera(
            look_from=eye,
            look_at=target,
            up=up,
            vfov_deg=vfov,
            aspect=aspect,
            aperture=aperture,
            focus_dist=focus_dist,
        )
        renderer = scene.make_renderer(
            samples=samples, max_depth=max_depth, seed=42 + i,
        )
        pixels = renderer.render(cam, width, height)
        ext = "ppm" if fmt == "ppm" else "png" if fmt == "png" else "txt"
        name = f"frame_{i:04d}.{ext}"
        path = os.path.join(out_dir, name)
        if fmt == "ppm":
            imageio.write_ppm(path, pixels, gamma=renderer.gamma)
        elif fmt == "ascii":
            imageio.write_ascii(path, pixels, width=80)
        else:
            imageio.write_png(path, pixels, gamma=renderer.gamma)
        written.append(path)
        if progress:
            elapsed = time.time() - t0
            rate = (i + 1) / max(0.001, elapsed)
            eta = (total - i - 1) / rate if rate > 0 else 0
            logger.info(
                "frame %d/%d -> %s (%.1f fps, ETA %.0fs)",
                i + 1, total, name, rate, eta,
            )
    return written