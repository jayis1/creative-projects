"""Animation utilities: multi-frame rendering for simple turntable animations.

Produces a sequence of frames (PPM/BMP images) with the camera orbiting
or the object rotating, suitable for assembling into a GIF or video.
"""

from __future__ import annotations

import logging
import math
import os
from pathlib import Path

from .math3d import Vec3
from .rasterizer import Renderer
from .scene import Scene, Camera

__all__ = ["AnimationBuilder"]

logger = logging.getLogger(__name__)


class AnimationBuilder:
    """Build a multi-frame animation by orbiting the camera and/or rotating objects.

    Example::

        builder = AnimationBuilder(renderer, scene, camera)
        builder.render_turntable(
            output_dir="frames/",
            frames=36,
            camera_orbit=True,
            object_rotation=True,
            fmt="ppm",
        )
    """

    def __init__(self, renderer: Renderer, scene: Scene, camera: Camera):
        self.renderer = renderer
        self.scene = scene
        self.camera = camera

    def render_turntable(self, output_dir: str,
                         frames: int = 36,
                         camera_orbit: bool = True,
                         object_rotation: bool = True,
                         fmt: str = "ppm",
                         prefix: str = "frame") -> list[str]:
        """Render a turntable animation.

        Args:
            output_dir: Directory to write frames to (created if needed).
            frames: Number of frames to render.
            camera_orbit: If True, orbit the camera around the target.
            object_rotation: If True, rotate all objects around Y.
            fmt: Output format — "ppm" or "bmp".
            prefix: Filename prefix for frames.

        Returns:
            List of output file paths.
        """
        if frames < 1:
            raise ValueError("frames must be >= 1")

        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        # Save initial camera state
        initial_pos = Vec3(self.camera.position.x, self.camera.position.y,
                           self.camera.position.z)
        initial_target = Vec3(self.camera.target.x, self.camera.target.y,
                              self.camera.target.z)
        # Save initial object rotations
        initial_rotations = [
            Vec3(o.rotation.x, o.rotation.y, o.rotation.z)
            for o in self.scene.objects
        ]

        # Compute orbit parameters
        distance = (initial_pos - initial_target).length()
        height = initial_pos.y - initial_target.y
        initial_angle = math.atan2(
            initial_pos.z - initial_target.z,
            initial_pos.x - initial_target.x)

        output_files = []
        for i in range(frames):
            angle = initial_angle + 2 * math.pi * i / frames

            if camera_orbit:
                self.camera.orbit(angle, distance, height, initial_target)

            if object_rotation:
                for j, obj in enumerate(self.scene.objects):
                    obj.rotation = Vec3(
                        initial_rotations[j].x,
                        initial_rotations[j].y + 2 * math.pi * i / frames,
                        initial_rotations[j].z)

            self.renderer.render(self.scene, self.camera)

            fname = f"{prefix}_{i:04d}.{fmt}"
            fpath = str(out / fname)
            self.renderer.save(fpath)
            output_files.append(fpath)
            logger.info("Rendered frame %d/%d: %s", i + 1, frames, fname)

        # Restore initial state
        self.camera.position = initial_pos
        self.camera.target = initial_target
        for j, obj in enumerate(self.scene.objects):
            obj.rotation = initial_rotations[j]

        logger.info("Animation complete: %d frames in %s", frames, output_dir)
        return output_files