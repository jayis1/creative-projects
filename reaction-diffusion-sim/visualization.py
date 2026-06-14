"""
Visualization module for reaction-diffusion simulations.

Supports:
- Static PNG output (single frame or grid of frames)
- Real-time matplotlib animation
- Colormap selection
- Field selection (u, v, or composite)
"""

import os
import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend for headless
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


COLORMAPS = {
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
}


def render_frame(u, v, field="v", cmap="inferno", vmin=None, vmax=None):
    """
    Render a single frame as a matplotlib figure.
    
    Args:
        u, v: 2D concentration arrays
        field: "u", "v", or "composite" (u+v normalized)
        cmap: matplotlib colormap name
        vmin, vmax: value range for colormap
    
    Returns:
        matplotlib.figure.Figure
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
    ax.set_title(f"Step 0 | {field}", fontsize=10)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    return fig


def save_frame(u, v, filepath, field="v", cmap="inferno", vmin=None, vmax=None):
    """
    Render and save a single frame as a PNG image.
    
    Args:
        u, v: 2D concentration arrays
        filepath: Output file path (PNG)
        field: "u", "v", or "composite"
        cmap: colormap name
        vmin, vmax: value range
    """
    fig = render_frame(u, v, field, cmap, vmin, vmax)
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    fig.savefig(filepath, dpi=100, bbox_inches="tight")
    plt.close(fig)


def save_frame_fast(u, v, filepath, field="v", cmap="inferno"):
    """
    Save a frame without matplotlib (using PIL or raw NumPy).
    Much faster for batch rendering. Falls back to matplotlib if PIL unavailable.
    
    Args:
        u, v: 2D concentration arrays
        filepath: Output file path
        field: "u", "v", or "composite"
        cmap: colormap name (only used if matplotlib is needed as fallback)
    """
    data = _select_field(u, v, field)
    
    if HAS_PIL:
        # Normalize to 0-255
        dmin, dmax = data.min(), data.max()
        if dmax - dmin > 1e-10:
            normalized = (data - dmin) / (dmax - dmin)
        else:
            normalized = np.zeros_like(data)
        
        # Apply colormap via matplotlib.cm if available
        if HAS_MATPLOTLIB:
            cm = plt.get_cmap(cmap)
            rgba = cm(normalized)
            rgb = (rgba[:, :, :3] * 255).astype(np.uint8)
        else:
            # Grayscale fallback
            rgb = (normalized * 255).astype(np.uint8)
        
        img = Image.fromarray(rgb)
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        img.save(filepath)
    else:
        save_frame(u, v, filepath, field, cmap)


def render_animation(solver, total_steps, frames=100, field="v",
                     cmap="inferno", interval=50, vmin=None, vmax=None):
    """
    Create a matplotlib animation of the simulation.
    
    Args:
        solver: ReactionDiffusionSolver instance
        total_steps: Total simulation steps
        frames: Number of frames to render
        field: Field to display
        cmap: colormap name
        interval: milliseconds between frames
        vmin, vmax: value range
    
    Returns:
        matplotlib.animation.FuncAnimation
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
    title = ax.set_title(f"Step 0", fontsize=10)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    def update(frame_idx):
        solver.step(steps_per_frame)
        data = _select_field(solver.u, solver.v, field)
        im.set_data(data)
        title.set_text(f"Step {solver.step_count}")
        return [im, title]

    anim = animation.FuncAnimation(
        fig, update, frames=frames, interval=interval, blit=True
    )
    fig.tight_layout()
    return anim


def render_frame_grid(solver, total_steps, grid_shape=(3, 3), field="v",
                      cmap="inferno", vmin=None, vmax=None):
    """
    Render a grid of snapshots showing the simulation progression.
    
    Args:
        solver: ReactionDiffusionSolver instance
        total_steps: Total simulation steps
        grid_shape: (rows, cols) layout
        field: Field to display
        cmap: colormap name
        vmin, vmax: value range
    
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
            solver.step(steps_per_frame)
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


def _select_field(u, v, field):
    """Select and return the visualization field."""
    if field == "u":
        return u
    elif field == "v":
        return v
    elif field == "composite":
        # Normalize u and v to [0,1] then combine
        u_norm = (u - u.min()) / max(u.max() - u.min(), 1e-10)
        v_norm = (v - v.min()) / max(v.max() - v.min(), 1e-10)
        return 0.5 * u_norm + 0.5 * v_norm
    else:
        return v