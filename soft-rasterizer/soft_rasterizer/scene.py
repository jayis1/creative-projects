"""Scene graph: cameras, lights, objects, and scene management."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .math3d import Vec3, Mat4
from .mesh import Mesh
from .texture import Texture

__all__ = ["Camera", "Light", "Object3D", "Scene"]


class Camera:
    """Perspective camera with position and orientation.

    The camera looks down its local -Z axis (right-handed convention,
    matching OpenGL).
    """

    def __init__(self, position: Vec3 | None = None,
                 target: Vec3 | None = None,
                 up: Vec3 | None = None,
                 fov: float = 60.0,
                 near: float = 0.1,
                 far: float = 100.0):
        self.position = position or Vec3(0, 0, 5)
        self.target = target or Vec3(0, 0, 0)
        self.up = up or Vec3(0, 1, 0)
        self.fov = float(fov)
        self.near = float(near)
        self.far = float(far)

    def view_matrix(self) -> Mat4:
        """Return the view (world-to-camera) matrix."""
        return Mat4.look_at(self.position, self.target, self.up)

    def projection_matrix(self, aspect: float) -> Mat4:
        """Return the perspective projection matrix."""
        fovy = math.radians(self.fov)
        return Mat4.perspective(fovy, aspect, self.near, self.far)

    def look_at(self, target: Vec3):
        self.target = target

    def orbit(self, angle: float, distance: float, height: float = 0.0,
              center: Vec3 | None = None):
        """Position the camera on an orbit around a center point."""
        c = center or self.target
        self.position = Vec3(
            c.x + distance * math.cos(angle),
            c.y + height,
            c.z + distance * math.sin(angle),
        )
        self.target = c


@dataclass
class Light:
    """A light source.

    For point lights, set ``position`` and leave ``direction`` as None.
    For directional lights, set ``direction`` (the direction the light
    travels) and leave ``position`` as None.
    """

    position: Vec3 | None = None
    direction: Vec3 | None = None
    color: Vec3 = field(default_factory=lambda: Vec3(1, 1, 1))
    intensity: float = 1.0

    @staticmethod
    def point(pos: Vec3, color: Vec3 | None = None,
              intensity: float = 1.0) -> "Light":
        return Light(position=pos, direction=None,
                     color=color or Vec3(1, 1, 1), intensity=intensity)

    @staticmethod
    def directional(direction: Vec3, color: Vec3 | None = None,
                    intensity: float = 1.0) -> "Light":
        return Light(position=None, direction=direction.normalized(),
                     color=color or Vec3(1, 1, 1), intensity=intensity)

    @staticmethod
    def ambient(color: Vec3 | None = None, intensity: float = 0.2) -> "Light":
        """A simple ambient light (implemented as a directional light
        with zero direction, so only ambient contributes)."""
        return Light(position=Vec3(0, 0, 0), direction=Vec3(0, 0, 0),
                     color=color or Vec3(1, 1, 1), intensity=intensity)


class Object3D:
    """A scene object: mesh + transform + material/shader."""

    def __init__(self, mesh: Mesh, shader=None,
                 position: Vec3 | None = None,
                 rotation: Vec3 | None = None,
                 scale: float = 1.0,
                 texture: Texture | None = None):
        self.mesh = mesh
        self.shader = shader
        self.position = position or Vec3(0, 0, 0)
        self.rotation = rotation or Vec3(0, 0, 0)  # Euler angles in radians
        self.scale = float(scale)
        # Allow overriding the mesh's texture
        if texture is not None:
            mesh.texture = texture

    def model_matrix(self) -> Mat4:
        """Build the model (local-to-world) matrix from position/rotation/scale."""
        t = Mat4.translation(self.position.x, self.position.y, self.position.z)
        rx = Mat4.rotation_x(self.rotation.x)
        ry = Mat4.rotation_y(self.rotation.y)
        rz = Mat4.rotation_z(self.rotation.z)
        s = Mat4.scaling(self.scale, self.scale, self.scale)
        return t @ (ry @ (rx @ rz)) @ s

    def rotate_y(self, angle: float):
        """Incrementally rotate the object around Y by ``angle`` radians."""
        self.rotation = Vec3(self.rotation.x, self.rotation.y + angle,
                             self.rotation.z)


class Scene:
    """A scene containing objects, lights, and background.

    Supports both a solid background colour and a vertical gradient
    between two colours for a more visually appealing backdrop.
    """

    def __init__(self, objects: list[Object3D] | None = None,
                 lights: list[Light] | None = None,
                 background: Vec3 | None = None,
                 background_top: Vec3 | None = None):
        self.objects: list[Object3D] = list(objects) if objects else []
        self.lights: list[Light] = list(lights) if lights else []
        self.background = background or Vec3(0.05, 0.05, 0.08)
        # Optional gradient background: if background_top is set, the
        # framebuffer clear will produce a vertical gradient from
        # background_top (top of screen) to background (bottom).
        self.background_top = background_top

    def add(self, obj):
        """Add an object or light to the scene."""
        if isinstance(obj, Object3D):
            self.objects.append(obj)
        elif isinstance(obj, Light):
            self.lights.append(obj)
        elif isinstance(obj, Mesh):
            self.objects.append(Object3D(obj))
        else:
            raise TypeError(f"Cannot add {type(obj)} to scene")

    def remove(self, obj):
        """Remove an object or light from the scene."""
        if isinstance(obj, Object3D) and obj in self.objects:
            self.objects.remove(obj)
        elif isinstance(obj, Light) and obj in self.lights:
            self.lights.remove(obj)

    def clear_background(self, framebuffer) -> None:
        """Fill the framebuffer with the background colour or gradient."""
        if self.background_top is not None:
            # Vertical gradient: top → background_top, bottom → background
            h = framebuffer.height
            for y in range(h):
                t = y / max(1, h - 1)
                c = self.background_top.lerp(self.background, t)
                for x in range(framebuffer.width):
                    framebuffer.color[y * framebuffer.width + x] = Vec3(c.x, c.y, c.z)
            framebuffer.zbuffer = [float("inf")] * (framebuffer.width * framebuffer.height)
        else:
            framebuffer.clear(self.background)