"""scene.py — Scene presets and scene description helpers."""

from __future__ import annotations

from typing import List

from .vec import Vec3
from .ray import Ray
from .material import (
    Material,
    Matte,
    Metal,
    Dielectric,
    Emissive,
    Checker,
)
from .primitive import Sphere, Plane, Triangle, XYRect
from .bvh import BVHNode, HittableList, _Hittable
from .camera import Camera
from .renderer import Renderer, sky_gradient, constant_background

__all__ = ["Scene", "build_three_balls", "build_cornell_box", "build_random_spheres"]


class Scene:
    """A bundle of world hittables + a default camera."""

    def __init__(
        self,
        world: _Hittable,
        camera: Camera,
        background=None,
    ) -> None:
        self.world = world
        self.camera = camera
        self.background = background

    def make_renderer(self, **kw) -> Renderer:
        return Renderer(self.world, self.background, **kw)


def build_three_balls(aspect: float = 16.0 / 9.0) -> "Scene":
    """The canonical 'three glassy / metallic balls on a checker plane' scene."""
    mat_ground = Checker(
        Matte(Vec3(0.85, 0.85, 0.85)),
        Matte(Vec3(0.15, 0.15, 0.15)),
        scale=2.0,
    )
    ground = Plane(Vec3(0, -0.5, 0), Vec3(0, 1, 0), mat_ground)
    s1 = Sphere(Vec3(0, 0, -1), 0.5, Dielectric(1.5))
    s2 = Sphere(Vec3(-1.0, 0, -1.0), 0.5, Metal(Vec3(0.8, 0.6, 0.2), fuzz=0.05))
    s3 = Sphere(Vec3(1.0, 0, -1.0), 0.5, Metal(Vec3(0.7, 0.7, 0.75), fuzz=0.0))
    world = BVHNode([ground, s1, s2, s3])
    cam = Camera(
        look_from=Vec3(0, 0.5, 2.0),
        look_at=Vec3(0, 0, -1),
        up=Vec3(0, 1, 0),
        vfov_deg=50.0,
        aspect=aspect,
        aperture=0.05,
        focus_dist=3.0,
    )
    return Scene(world, cam, background=sky_gradient)


def build_cornell_box(aspect: float = 1.0) -> "Scene":
    """The classic Cornell box with two colored walls and a light."""
    white = Matte(Vec3(0.73, 0.73, 0.73))
    red = Matte(Vec3(0.65, 0.05, 0.05))
    green = Matte(Vec3(0.12, 0.45, 0.15))
    light_mat = Emissive(Vec3(1, 1, 1), intensity=8.0)

    # Walls: each is a large XY / XZ / YZ rect would be ideal, but we keep this
    # first-cut version using planes with the appropriate normals. Planes are
    # infinite so we use them only as back/left/right walls at the box faces;
    # the renderer still works because rays that exit through the open top hit
    # the background.  For a real closed box we add a floor & ceiling plane.
    floor = Plane(Vec3(0, 0, 0), Vec3(0, 1, 0), white)
    ceiling = Plane(Vec3(0, 5, 0), Vec3(0, -1, 0), white)
    back = Plane(Vec3(0, 0, -5), Vec3(0, 0, 1), white)
    left = Plane(Vec3(-5, 0, 0), Vec3(1, 0, 0), green)
    right = Plane(Vec3(5, 0, 0), Vec3(-1, 0, 0), red)
    # Area light on the ceiling.
    light = XYRect(-1.5, 1.5, 2.5, 4.5, 4.999, light_mat)
    # Two spheres.
    ball1 = Sphere(Vec3(-1.2, 1.0, -2.5), 1.0, Dielectric(1.5))
    ball2 = Sphere(Vec3(1.5, 0.7, -1.5), 0.7, Metal(Vec3(0.85, 0.85, 0.9), fuzz=0.0))

    world = BVHNode([floor, ceiling, back, left, right, light, ball1, ball2])
    cam = Camera(
        look_from=Vec3(0, 2.5, 6.0),
        look_at=Vec3(0, 2.0, -2),
        up=Vec3(0, 1, 0),
        vfov_deg=40.0,
        aspect=aspect,
        aperture=0.0,
        focus_dist=8.0,
    )
    # Black background for a closed room.
    return Scene(world, cam, background=constant_background(Vec3(0, 0, 0)))


def build_random_spheres(n: int = 64, aspect: float = 16.0 / 9.0) -> "Scene":
    """A field of random small spheres over a checker ground plane."""
    import random as _r
    rng = _r.Random(42)
    items: List[_Hittable] = []
    ground_mat = Checker(
        Matte(Vec3(0.6, 0.6, 0.6)),
        Matte(Vec3(0.2, 0.2, 0.2)),
        scale=1.0,
    )
    items.append(Plane(Vec3(0, -0.5, 0), Vec3(0, 1, 0), ground_mat))
    for _ in range(n):
        x = rng.uniform(-4, 4)
        z = rng.uniform(-4, 0)
        r = rng.uniform(0.1, 0.4)
        y = -0.5 + r
        mat_choice = rng.random()
        if mat_choice < 0.4:
            m: Material = Matte(Vec3(rng.random(), rng.random(), rng.random()))
        elif mat_choice < 0.7:
            m = Metal(Vec3(rng.random(), rng.random(), rng.random()), fuzz=rng.uniform(0, 0.3))
        else:
            m = Dielectric(1.5)
        items.append(Sphere(Vec3(x, y, z), r, m))
    world = BVHNode(items)
    cam = Camera(
        look_from=Vec3(0, 1.0, 5.0),
        look_at=Vec3(0, 0, -2),
        up=Vec3(0, 1, 0),
        vfov_deg=55.0,
        aspect=aspect,
        aperture=0.05,
        focus_dist=6.0,
    )
    return Scene(world, cam, background=sky_gradient)