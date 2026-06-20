"""scene.py — Scene presets and scene description helpers.

Built-in presets
-----------------
* :func:`build_three_balls`     — canonical glass/metal balls on checker floor
* :func:`build_cornell_box`     — classic Cornell box with colored walls
* :func:`build_random_spheres`  — procedurally generated field of spheres
* :func:`build_solar_system`    — stylized sun + planets with emissive sun
* :func:`build_marble_hall`    — Perlin-marble columns + textured floor
* :func:`build_nebula`         — noisy diffuse spheres in a starry void
"""

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
from .primitive import (
    Sphere, Plane, Triangle, XYRect, XZRect, YZRect, Box, Disk, Cylinder,
)
from .bvh import BVHNode, HittableList, _Hittable
from .camera import Camera
from .renderer import Renderer, sky_gradient, constant_background
from .texture import (
    SolidColor, CheckerTexture, PerlinNoise, NoiseTexture, Turbulence, Marble,
)

__all__ = [
    "Scene",
    "build_three_balls",
    "build_cornell_box",
    "build_random_spheres",
    "build_solar_system",
    "build_marble_hall",
    "build_nebula",
    "PRESETS",
]


class Scene:
    """A bundle of world hittables + a default camera."""

    def __init__(
        self,
        world: _Hittable,
        camera: Camera,
        background=None,
        lights: List[_Hittable] | None = None,
    ) -> None:
        self.world = world
        self.camera = camera
        self.background = background
        self.lights = lights

    def make_renderer(self, **kw) -> Renderer:
        """Create a :class:`Renderer` for this scene.

        If the scene defines a ``lights`` list it is forwarded to the renderer
        for Next Event Estimation (unless the caller overrides ``lights``).
        """
        if "lights" not in kw and self.lights:
            kw["lights"] = self.lights
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
    return Scene(world, cam, background=constant_background(Vec3(0, 0, 0)), lights=[light])


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


# --------------------------------------------------------------------------- #
# New presets
# --------------------------------------------------------------------------- #
def build_solar_system(aspect: float = 16.0 / 9.0) -> "Scene":
    """A stylized solar system: emissive sun + textured planets on a dark plane.

    The sun is a bright emissive sphere; planets are diffuse/metal spheres of
    varying color.  Not to scale — designed as a visually pleasing render.
    """
    sun = Sphere(Vec3(0, 3, -8), 1.5, Emissive(Vec3(1.0, 0.85, 0.4), intensity=12.0))
    planets: List[_Hittable] = [
        Sphere(Vec3(-3, 0, -6), 0.4, Matte(Vec3(0.8, 0.4, 0.2))),       # mercury
        Sphere(Vec3(-1.5, 0, -7), 0.6, Matte(Vec3(0.9, 0.7, 0.4))),     # venus
        Sphere(Vec3(0, 0, -8), 0.5, Matte(Vec3(0.2, 0.4, 0.9))),         # earth
        Sphere(Vec3(2, 0, -7), 0.4, Matte(Vec3(0.8, 0.2, 0.1))),        # mars
        Sphere(Vec3(4, 0, -9), 1.0, Metal(Vec3(0.9, 0.8, 0.5), 0.1)),   # jupiter
    ]
    # Stars: tiny emissive dots in the background via a dark plane.
    ground = Plane(Vec3(0, -1, 0), Vec3(0, 1, 0), Matte(Vec3(0.02, 0.02, 0.05)))
    world = BVHNode([sun, ground] + planets)
    cam = Camera(
        look_from=Vec3(0, 2, 3),
        look_at=Vec3(0, 0.5, -6),
        up=Vec3(0, 1, 0),
        vfov_deg=50.0,
        aspect=aspect,
        aperture=0.02,
        focus_dist=9.0,
    )
    return Scene(
        world,
        cam,
        background=constant_background(Vec3(0.005, 0.005, 0.015)),
        lights=[sun],
    )


def build_marble_hall(aspect: float = 16.0 / 9.0) -> "Scene":
    """A hall of marble columns with a checker floor — showcases procedural
    textures (Perlin marble + turbulence)."""
    marble_mat = Marble(
        Vec3(0.92, 0.90, 0.88),
        Vec3(0.08, 0.06, 0.10),
        scale=3.0,
        depth=6,
        seed=7,
    )
    columns: List[_Hittable] = []
    for x in (-2.5, 0, 2.5):
        for z in (-4, -2):
            col = Cylinder(Vec3(x, 0, z), 0.25, 0.0, 3.0, Matte(marble_mat))
            columns.append(col)
    floor_mat = Checker(
        Matte(Vec3(0.9, 0.9, 0.9)),
        Matte(Vec3(0.1, 0.1, 0.1)),
        scale=1.0,
    )
    floor = Plane(Vec3(0, 0, 0), Vec3(0, 1, 0), floor_mat)
    ceiling = Plane(Vec3(0, 3, 0), Vec3(0, -1, 0), Matte(Vec3(0.5, 0.5, 0.5)))
    # Area light on the ceiling.
    light_mat = Emissive(Vec3(1, 0.98, 0.92), intensity=5.0)
    light = XZRect(-3, 3, -5, -1, 2.999, light_mat)
    world = BVHNode([floor, ceiling, light] + columns)
    cam = Camera(
        look_from=Vec3(0, 1.5, 3),
        look_at=Vec3(0, 1.2, -3),
        up=Vec3(0, 1, 0),
        vfov_deg=50.0,
        aspect=aspect,
        aperture=0.03,
        focus_dist=5.0,
    )
    return Scene(
        world,
        cam,
        background=constant_background(Vec3(0.02, 0.02, 0.03)),
        lights=[light],
    )


def build_nebula(aspect: float = 16.0 / 9.0) -> "Scene":
    """A nebula-like cloud of noise-textured spheres against a starry void.

    Demonstrates :class:`NoiseTexture` and :class:`Turbulence` for volumetric-
    looking surfaces without true volume rendering.
    """
    import random as _r
    rng = _r.Random(123)
    items: List[_Hittable] = []
    for _ in range(40):
        x = rng.uniform(-5, 5)
        y = rng.uniform(-2, 4)
        z = rng.uniform(-8, -3)
        r = rng.uniform(0.2, 0.8)
        if rng.random() < 0.5:
            tex = NoiseTexture(
                Vec3(0.1, 0.05, 0.2),
                Vec3(0.9, 0.3, 0.7),
                scale=rng.uniform(2, 6),
                seed=rng.randint(0, 999),
            )
        else:
            tex = Turbulence(
                Vec3(0.6, 0.4, 0.9),
                scale=rng.uniform(2, 5),
                depth=5,
                seed=rng.randint(0, 999),
            )
        items.append(Sphere(Vec3(x, y, z), r, Matte(tex)))
    world = BVHNode(items)
    cam = Camera(
        look_from=Vec3(0, 1, 4),
        look_at=Vec3(0, 1, -5),
        up=Vec3(0, 1, 0),
        vfov_deg=60.0,
        aspect=aspect,
        aperture=0.0,
        focus_dist=9.0,
    )
    return Scene(world, cam, background=constant_background(Vec3(0.01, 0.01, 0.02)))


PRESETS = {
    "three-balls": build_three_balls,
    "cornell": build_cornell_box,
    "random": build_random_spheres,
    "solar-system": build_solar_system,
    "marble-hall": build_marble_hall,
    "nebula": build_nebula,
}