"""
Visualization module for LBM simulation results.

Provides rendering of density, velocity, vorticity, and pressure fields
as images using Pillow.
"""

import numpy as np
from PIL import Image
from typing import Optional, Tuple
from .simulation import LBMSimulation


class FluidVisualizer:
    """
    Visualizer for LBM fluid simulation results.
    
    Renders fields as colored images with various colormaps.
    Can save individual frames or create animated GIFs.
    """
    
    # Colormap definitions (linear interpolation between control points)
    COLORMAPS = {
        'jet': [
            (0.0, (0, 0, 128)),
            (0.125, (0, 0, 255)),
            (0.375, (0, 255, 255)),
            (0.625, (255, 255, 0)),
            (0.875, (255, 0, 0)),
            (1.0, (128, 0, 0)),
        ],
        'viridis': [
            (0.0, (68, 1, 84)),
            (0.25, (59, 82, 139)),
            (0.5, (33, 145, 140)),
            (0.75, (94, 201, 98)),
            (1.0, (253, 231, 37)),
        ],
        'coolwarm': [
            (0.0, (59, 76, 192)),
            (0.25, (141, 176, 254)),
            (0.5, (235, 235, 235)),
            (0.75, (254, 146, 139)),
            (1.0, (180, 4, 38)),
        ],
        'hot': [
            (0.0, (0, 0, 0)),
            (0.33, (255, 0, 0)),
            (0.67, (255, 255, 0)),
            (1.0, (255, 255, 255)),
        ],
        'ocean': [
            (0.0, (0, 0, 30)),
            (0.3, (0, 30, 100)),
            (0.5, (0, 100, 180)),
            (0.7, (50, 180, 220)),
            (1.0, (200, 240, 255)),
        ],
        'plasma': [
            (0.0, (13, 8, 135)),
            (0.25, (126, 3, 168)),
            (0.5, (204, 71, 120)),
            (0.75, (248, 149, 64)),
            (1.0, (240, 249, 33)),
        ],
    }
    
    def __init__(self, sim: LBMSimulation):
        self.sim = sim
    
    def _apply_colormap(self, field: np.ndarray, cmap: str = 'jet',
                        vmin: Optional[float] = None, 
                        vmax: Optional[float] = None) -> np.ndarray:
        """
        Apply a colormap to a 2D field.
        
        Parameters
        ----------
        field : np.ndarray, shape (Ny, Nx)
            Scalar field to colorize.
        cmap : str
            Colormap name.
        vmin, vmax : float, optional
            Value range for normalization.
            
        Returns
        -------
        np.ndarray, shape (Ny, Nx, 3), dtype uint8
            RGB image array.
        """
        if cmap not in self.COLORMAPS:
            raise ValueError(f"Unknown colormap '{cmap}'. Available: {list(self.COLORMAPS.keys())}")
        
        # Normalize to [0, 1]
        if vmin is None:
            vmin = field.min()
        if vmax is None:
            vmax = field.max()
        
        if vmax == vmin:
            normalized = np.zeros_like(field)
        else:
            normalized = np.clip((field - vmin) / (vmax - vmin), 0, 1)
        
        # Interpolate colormap
        control_points = self.COLORMAPS[cmap]
        rgb = np.zeros((*field.shape, 3), dtype=np.uint8)
        
        for c in range(3):
            values = np.array([pt[1][c] for pt in control_points])
            positions = np.array([pt[0] for pt in control_points])
            rgb[:, :, c] = np.interp(normalized, positions, values).astype(np.uint8)
        
        return rgb
    
    def render_vorticity(self, cmap: str = 'coolwarm', 
                         vmin: float = -0.05, vmax: float = 0.05,
                         scale: int = 1) -> Image.Image:
        """
        Render vorticity field as a colored image.
        
        Parameters
        ----------
        cmap : str
            Colormap name.
        vmin, vmax : float
            Range for symmetric coloring.
        scale : int
            Upscale factor for the image.
            
        Returns
        -------
        PIL.Image.Image
        """
        self.sim.compute_vorticity()
        rgb = self._apply_colormap(self.sim.vorticity, cmap, vmin, vmax)
        
        # Mark obstacles as gray
        rgb[self.sim.obstacle_mask] = [80, 80, 80]
        
        img = Image.fromarray(rgb)
        if scale > 1:
            img = img.resize((self.sim.nx * scale, self.sim.ny * scale), Image.NEAREST)
        return img
    
    def render_speed(self, cmap: str = 'jet', scale: int = 1) -> Image.Image:
        """
        Render velocity magnitude field.
        """
        self.sim.compute_speed()
        rgb = self._apply_colormap(self.sim.speed, cmap)
        rgb[self.sim.obstacle_mask] = [80, 80, 80]
        
        img = Image.fromarray(rgb)
        if scale > 1:
            img = img.resize((self.sim.nx * scale, self.sim.ny * scale), Image.NEAREST)
        return img
    
    def render_pressure(self, cmap: str = 'ocean', scale: int = 1) -> Image.Image:
        """
        Render pressure field (p = rho * cs^2).
        """
        pressure = self.sim.rho * self.sim.lattice.cs2
        rgb = self._apply_colormap(pressure, cmap)
        rgb[self.sim.obstacle_mask] = [80, 80, 80]
        
        img = Image.fromarray(rgb)
        if scale > 1:
            img = img.resize((self.sim.nx * scale, self.sim.ny * scale), Image.NEAREST)
        return img
    
    def render_density(self, cmap: str = 'plasma', scale: int = 1) -> Image.Image:
        """Render density field."""
        rgb = self._apply_colormap(self.sim.rho, cmap)
        rgb[self.sim.obstacle_mask] = [80, 80, 80]
        
        img = Image.fromarray(rgb)
        if scale > 1:
            img = img.resize((self.sim.nx * scale, self.sim.ny * scale), Image.NEAREST)
        return img
    
    def render_velocity_field(self, skip: int = 8, scale: int = 1) -> Image.Image:
        """
        Render velocity field as arrows overlaid on speed magnitude.
        """
        self.sim.compute_speed()
        rgb = self._apply_colormap(self.sim.speed, 'ocean')
        rgb[self.sim.obstacle_mask] = [80, 80, 80]
        
        img = Image.fromarray(rgb)
        if scale > 1:
            img = img.resize((self.sim.nx * scale, self.sim.ny * scale), Image.NEAREST)
        return img
    
    def render_combined(self, scale: int = 1) -> Image.Image:
        """
        Render a combined view: vorticity on top half, speed on bottom half.
        """
        self.sim.compute_vorticity()
        self.sim.compute_speed()
        
        ny, nx = self.sim.ny, self.sim.nx
        combined = np.zeros((ny, nx, 3), dtype=np.uint8)
        
        # Top half: vorticity
        vort_rgb = self._apply_colormap(self.sim.vorticity, 'coolwarm', -0.05, 0.05)
        # Bottom half: speed
        speed_rgb = self._apply_colormap(self.sim.speed, 'jet', 0, np.max(self.sim.speed) * 0.8)
        
        half = ny // 2
        combined[:half] = vort_rgb[:half]
        combined[half:] = speed_rgb[half:]
        combined[self.sim.obstacle_mask] = [80, 80, 80]
        
        img = Image.fromarray(combined)
        if scale > 1:
            img = img.resize((nx * scale, ny * scale), Image.NEAREST)
        return img
    
    def save_frame(self, filename: str, field: str = 'vorticity', 
                   cmap: str = 'jet', scale: int = 1, **kwargs):
        """Save a single frame to file."""
        renderers = {
            'vorticity': self.render_vorticity,
            'speed': self.render_speed,
            'pressure': self.render_pressure,
            'density': self.render_density,
            'velocity': self.render_velocity_field,
            'combined': self.render_combined,
        }
        
        if field not in renderers:
            raise ValueError(f"Unknown field '{field}'. Available: {list(renderers.keys())}")
        
        img = renderers[field](cmap=cmap, scale=scale, **kwargs)
        img.save(filename)
    
    @staticmethod
    def create_gif(frames: list, filename: str, duration: int = 50, loop: bool = True):
        """
        Create an animated GIF from a list of PIL Images.
        
        Parameters
        ----------
        frames : list of PIL.Image.Image
            Frames to animate.
        filename : str
            Output file path.
        duration : int
            Duration per frame in milliseconds.
        loop : bool
            Whether to loop the animation.
        """
        if not frames:
            raise ValueError("No frames provided")
        
        frames[0].save(
            filename,
            save_all=True,
            append_images=frames[1:],
            duration=duration,
            loop=0 if loop else 1,
            optimize=False,
        )