"""
Visualization module for reaction-diffusion simulations.

Supports:
- Static PNG output (single frame or grid of frames)
- Animated GIF output
- MP4/WebM video output via matplotlib
- Real-time matplotlib animation
- Colormap selection
- Field selection (u, v, composite, difference, gradient)
- Fast rendering via PIL (falls back to matplotlib)
- Channel mixing for multi-field visualization
- Custom color map creation
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
from numpy.typing import NDArray

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import animation
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

logger = logging.getLogger(__name__)

# Available colormaps with display names
COLORMAPS: Dict[str, str] = {
    "inferno": "inferno",
    "viridis": "viridis",
    "plasma": "plasma",
    "magma": "magma",
    "hot": "hot",
    "cool": "cool",
    "gray": "gray",
    "bone": "bone",
    "copper": "copper",
    "twilight": "twilight",
    "ocean": "ocean",
    "rd_yl_bu": "RdYlBu",
    "spectral": "Spectral",
    "seismic": "seismic",
    "bwr": "bwr",
    "hsv": "hsv",
    "cividis": "cividis",
    "turbo": "turbo",
    "nipy_spectral": "nipy_spectral",
    "terrain": "terrain",
}


def _apply_colormap(
    data: NDArray[np.floating],
    cmap_name: str = "inferno",
) -> NDArray[np.uint8]:
    """Apply a matplotlib colormap to a normalized 2D array.

    Args:
        data: 2D numpy array.
        cmap_name: Name of the matplotlib colormap.

    Returns:
        RGB uint8 array of shape (H, W, 3).
    """
    dmin, dmax = data.min(), data.max()
    if dmax - dmin > 1e-10:
        normalized = (data - dmin) / (dmax - dmin)
    else:
        normalized = np.zeros_like(data)

    if HAS_MATPLOTLIB:
        cm = plt.get_cmap(cmap_name)
        rgba = cm(normalized)
        return (rgba[:, :, :3] * 255).astype(np.uint8)
    else:
        return (np.stack([normalized] * 3, axis=-1) * 255).astype(np.uint8)


def render_frame(
    u: NDArray[np.floating],
    v: NDArray[np.floating],
    field: str = "v",
    cmap: str = "inferno",
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    title: Optional[str] = None,
) -> Any:
    """Render a single frame as a matplotlib figure.

    Args:
        u, v: 2D concentration arrays.
        field: "u", "v", "composite", "difference", or "gradient".
        cmap: matplotlib colormap name.
        vmin, vmax: value range for colormap.
        title: Optional title string.

    Returns:
        matplotlib.figure.Figure

    Raises:
        ImportError: If matplotlib is not available.
    """
    if not HAS_MATPLOTLIB:
        raise ImportError("matplotlib is required for rendering")

    data = _select_field(u, v, field)
    if vmin is None:
        vmin = data.min()
    if vmax is None:
        vmax = data.max()

    fig, ax = plt.subplots(1, 1, figsize=(6, 6), dpi=100)
    im = ax.imshow(data, cmap=cmap, vmin=vmin, vmax=vmax,
                   interpolation="bilinear", origin="lower")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(title or f"{field} field", fontsize=10)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    return fig


def save_frame(
    u: NDArray[np.floating],
    v: NDArray[np.floating],
    filepath: str,
    field: str = "v",
    cmap: str = "inferno",
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    title: Optional[str] = None,
) -> None:
    """Render and save a single frame as a PNG image.

    Args:
        u, v: 2D concentration arrays.
        filepath: Output file path (PNG).
        field: "u", "v", "composite", "difference", or "gradient".
        cmap: colormap name.
        vmin, vmax: value range.
        title: Optional title.
    """
    fig = render_frame(u, v, field, cmap, vmin, vmax, title)
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    fig.savefig(filepath, dpi=100, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved frame to {filepath}")


def save_frame_fast(
    u: NDArray[np.floating],
    v: NDArray[np.floating],
    filepath: str,
    field: str = "v",
    cmap: str = "inferno",
) -> None:
    """Save a frame without matplotlib figure overhead (using PIL + colormap).

    Much faster for batch rendering.

    Args:
        u, v: 2D concentration arrays.
        filepath: Output file path.
        field: "u", "v", "composite", "difference", or "gradient".
        cmap: colormap name.
    """
    data = _select_field(u, v, field)
    rgb = _apply_colormap(data, cmap)

    if HAS_PIL:
        img = Image.fromarray(rgb)
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        img.save(filepath)
    elif HAS_MATPLOTLIB:
        fig, ax = plt.subplots(1, 1, figsize=(6, 6))
        ax.imshow(data, cmap=cmap, interpolation="bilinear", origin="lower")
        ax.set_xticks([])
        ax.set_yticks([])
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        fig.savefig(filepath, dpi=100, bbox_inches="tight")
        plt.close(fig)
    else:
        raise ImportError("Either matplotlib or PIL is required for rendering")


def save_gif(
    solver: Any,
    total_steps: int,
    frames: int = 100,
    filepath: str = "output.gif",
    field: str = "v",
    cmap: str = "inferno",
    fps: int = 15,
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    method: str = "euler",
) -> None:
    """Create an animated GIF of the simulation progression.

    Args:
        solver: ReactionDiffusionSolver instance.
        total_steps: Total simulation steps.
        frames: Number of frames in the animation.
        filepath: Output GIF file path.
        field: Field to visualize.
        cmap: colormap name.
        fps: Frames per second in the output.
        vmin, vmax: value range (auto-detected if None).
        method: Integration method.

    Raises:
        ImportError: If PIL is not available.
    """
    if not HAS_PIL:
        raise ImportError("PIL (Pillow) is required for GIF output")

    steps_per_frame = max(1, total_steps // frames)
    images = []

    if vmin is None or vmax is None:
        data_init = _select_field(solver.u, solver.v, field)
        if vmin is None:
            vmin = data_init.min()
        if vmax is None:
            vmax = data_init.max()

    for i in range(frames):
        solver.step(steps_per_frame, method=method)
        data = _select_field(solver.u, solver.v, field)
        if vmin is not None:
            data = np.clip(data, vmin, vmax)
        rgb = _apply_colormap(data, cmap)
        img = Image.fromarray(rgb)
        images.append(img)
        if (i + 1) % 20 == 0 or i == frames - 1:
            logger.info(f"  GIF frame {i + 1}/{frames} (step {solver.step_count})")

    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    images[0].save(
        filepath, save_all=True, append_images=images[1:],
        duration=int(1000 / fps), loop=0,
    )
    logger.info(f"Saved GIF: {filepath} ({len(images)} frames, {fps} fps)")


def save_video(
    solver: Any,
    total_steps: int,
    frames: int = 100,
    filepath: str = "output.mp4",
    field: str = "v",
    cmap: str = "inferno",
    fps: int = 30,
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    method: str = "euler",
    dpi: int = 100,
) -> None:
    """Create an MP4/WebM video of the simulation progression.

    Uses matplotlib's animation writer. Requires ffmpeg for MP4 output.

    Args:
        solver: ReactionDiffusionSolver instance.
        total_steps: Total simulation steps.
        frames: Number of frames in the animation.
        filepath: Output video file path (extension determines format).
        field: Field to visualize.
        cmap: colormap name.
        fps: Frames per second.
        vmin, vmax: value range.
        method: Integration method.
        dpi: Resolution for rendering.

    Raises:
        ImportError: If matplotlib is not available.
    """
    if not HAS_MATPLOTLIB:
        raise ImportError("matplotlib is required for video output")

    steps_per_frame = max(1, total_steps // frames)
    data = _select_field(solver.u, solver.v, field)

    if vmin is None:
        vmin = data.min()
    if vmax is None:
        vmax = data.max()

    fig, ax = plt.subplots(1, 1, figsize=(6, 6), dpi=dpi)
    im = ax.imshow(data, cmap=cmap, vmin=vmin, vmax=vmax,
                   interpolation="bilinear", origin="lower")
    ax.set_xticks([])
    ax.set_yticks([])
    title_text = ax.set_title(f"Step {solver.step_count}", fontsize=10)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    def update(frame_idx: int):
        solver.step(steps_per_frame, method=method)
        data = _select_field(solver.u, solver.v, field)
        im.set_data(data)
        title_text.set_text(f"Step {solver.step_count}")
        return [im, title_text]

    anim = animation.FuncAnimation(
        fig, update, frames=frames, interval=int(1000 / fps), blit=True,
    )

    writer = animation.FFMpegWriter(fps=fps)
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    anim.save(filepath, writer=writer, dpi=dpi)
    plt.close(fig)
    logger.info(f"Saved video: {filepath}")


def render_animation(
    solver: Any,
    total_steps: int,
    frames: int = 100,
    field: str = "v",
    cmap: str = "inferno",
    interval: int = 50,
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
) -> Any:
    """Create a matplotlib animation of the simulation.

    Note: This returns a FuncAnimation object. Call anim.save() or plt.show().

    Args:
        solver: ReactionDiffusionSolver instance.
        total_steps: Total simulation steps.
        frames: Number of animation frames.
        field: Field to display.
        cmap: colormap name.
        interval: milliseconds between frames.
        vmin, vmax: value range.

    Returns:
        matplotlib.animation.FuncAnimation

    Raises:
        ImportError: If matplotlib is not available.
    """
    if not HAS_MATPLOTLIB:
        raise ImportError("matplotlib is required for animation")

    steps_per_frame = max(1, total_steps // frames)
    data = _select_field(solver.u, solver.v, field)

    if vmin is None:
        vmin = data.min()
    if vmax is None:
        vmax = data.max()

    fig, ax = plt.subplots(1, 1, figsize=(6, 6))
    im = ax.imshow(data, cmap=cmap, vmin=vmin, vmax=vmax,
                   interpolation="bilinear", origin="lower")
    ax.set_xticks([])
    ax.set_yticks([])
    title = ax.set_title(f"Step {solver.step_count}", fontsize=10)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    def update(frame_idx: int):
        solver.step(steps_per_frame)
        data = _select_field(solver.u, solver.v, field)
        im.set_data(data)
        title.set_text(f"Step {solver.step_count}")
        return [im, title]

    anim = animation.FuncAnimation(
        fig, update, frames=frames, interval=interval, blit=True,
    )
    fig.tight_layout()
    return anim


def render_frame_grid(
    solver: Any,
    total_steps: int,
    grid_shape: Tuple[int, int] = (3, 3),
    field: str = "v",
    cmap: str = "inferno",
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    method: str = "euler",
) -> Any:
    """Render a grid of snapshots showing the simulation progression.

    Args:
        solver: ReactionDiffusionSolver instance.
        total_steps: Total simulation steps.
        grid_shape: (rows, cols) layout.
        field: Field to display.
        cmap: colormap name.
        vmin, vmax: value range.
        method: Integration method.

    Returns:
        matplotlib.figure.Figure
    """
    if not HAS_MATPLOTLIB:
        raise ImportError("matplotlib is required for rendering")

    rows, cols = grid_shape
    total_frames = rows * cols
    steps_per_frame = max(1, total_steps // total_frames)

    fig, axes = plt.subplots(rows, cols, figsize=(3 * cols, 3 * rows))
    if rows == 1:
        axes = axes.reshape(1, -1)
    if cols == 1:
        axes = axes.reshape(-1, 1)

    for i in range(rows):
        for j in range(cols):
            solver.step(steps_per_frame, method=method)
            data = _select_field(solver.u, solver.v, field)
            ax = axes[i, j]
            ax.imshow(data, cmap=cmap, interpolation="bilinear", origin="lower",
                      vmin=vmin, vmax=vmax)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_title(f"t={solver.step_count}", fontsize=8)

    fig.suptitle(f"{solver.model_name} | {field} field", fontsize=12)
    fig.tight_layout()
    return fig


def _select_field(
    u: NDArray[np.floating],
    v: NDArray[np.floating],
    field: str,
) -> NDArray[np.floating]:
    """Select and return the visualization field.

    Args:
        u, v: 2D concentration arrays.
        field: One of:
            - "u": activator field
            - "v": inhibitor field
            - "composite": normalized u+v blend
            - "difference": u-v difference field
            - "gradient": magnitude of gradient of v

    Returns:
        2D numpy array for visualization.
    """
    if field == "u":
        return u
    elif field == "v":
        return v
    elif field == "composite":
        u_norm = (u - u.min()) / max(u.max() - u.min(), 1e-10)
        v_norm = (v - v.min()) / max(v.max() - v.min(), 1e-10)
        return 0.5 * u_norm + 0.5 * v_norm
    elif field == "difference":
        return u - v
    elif field == "gradient":
        gy, gx = np.gradient(v)
        return np.sqrt(gx ** 2 + gy ** 2)
    else:
        return v