"""Command-line interface for the software rasterizer."""

from __future__ import annotations

import argparse
import math
import sys

from . import __version__
from .math3d import Vec3
from .rasterizer import Renderer
from .scene import Scene, Camera, Light, Object3D
from .shaders import (FlatShader, GouraudShader, PhongShader,
                      WireframeShader, NormalShader, DepthShader,
                      PhongMaterial)
from .texture import CheckerTexture
from .primitives import (make_cube, make_sphere, make_plane, make_cylinder,
                         make_torus, make_tetrahedron, make_octahedron)
from .mesh import OBJLoader

SHADERS = {
    "flat": FlatShader,
    "gouraud": GouraudShader,
    "phong": PhongShader,
    "normal": NormalShader,
    "depth": DepthShader,
    "wireframe": WireframeShader,
}

PRIMITIVES = {
    "cube": make_cube,
    "sphere": make_sphere,
    "plane": make_plane,
    "cylinder": make_cylinder,
    "torus": make_torus,
    "tetrahedron": make_tetrahedron,
    "octahedron": make_octahedron,
}


def build_scene(args) -> Scene:
    """Build a scene from CLI arguments."""
    scene = Scene()

    # Lights
    scene.lights.append(Light.directional(
        Vec3(-0.5, -1, -0.3), Vec3(1, 1, 0.9), 0.8))
    scene.lights.append(Light.point(
        Vec3(5, 5, 5), Vec3(0.4, 0.4, 0.6), 0.5))

    # Camera
    dist = args.distance
    cam = Camera(
        position=Vec3(dist * math.cos(args.angle), args.height,
                      dist * math.sin(args.angle)),
        target=Vec3(0, 0, 0),
        fov=args.fov,
        near=0.1,
        far=100.0,
    )

    # Mesh
    if args.obj:
        mesh = OBJLoader.load(args.obj)
        # Center and scale the model
        c = mesh.center()
        mesh.translate(Vec3(-c.x, -c.y, -c.z))
        minp, maxp = mesh.bounds()
        max_extent = max(maxp.x - minp.x, maxp.y - minp.y, maxp.z - minp.z)
        if max_extent > 0:
            mesh.scale(2.0 / max_extent)
    elif args.primitive in PRIMITIVES:
        mesh = PRIMITIVES[args.primitive](size=args.size)
    else:
        print(f"Unknown primitive: {args.primitive}", file=sys.stderr)
        sys.exit(1)

    # Shader
    shader_name = args.shader
    if shader_name not in SHADERS:
        print(f"Unknown shader: {shader_name}", file=sys.stderr)
        sys.exit(1)

    if shader_name == "wireframe":
        shader = WireframeShader()
    elif shader_name in ("flat", "gouraud", "phong"):
        material = PhongMaterial(
            diffuse=Vec3(*args.color) if args.color else Vec3(0.8, 0.6, 0.4),
            specular=Vec3(0.8, 0.8, 0.8),
            shininess=args.shininess,
        )
        shader = SHADERS[shader_name](material=material)
    else:
        shader = SHADERS[shader_name]()

    # Texture
    texture = None
    if args.texture == "checker":
        texture = CheckerTexture(squares=8)
        mesh.texture = texture

    obj = Object3D(mesh, shader=shader,
                   rotation=Vec3(0, args.rotation, 0))
    scene.add(obj)

    # Store camera on scene for renderer
    scene._camera = cam
    return scene


def cmd_render(args):
    """Render a scene to an image file."""
    scene = build_scene(args)
    cam = scene._camera

    renderer = Renderer(args.width, args.height,
                        cull_backface=not args.no_cull)
    fb = renderer.render(scene, cam)

    if args.output.endswith(".ppm"):
        renderer.save_ppm(args.output)
    else:
        # Always save as PPM (could add PNG conversion later)
        ppm_path = args.output.rsplit(".", 1)[0] + ".ppm"
        renderer.save_ppm(ppm_path)

    print(f"Rendered {args.width}x{args.height} → {args.output}")

    if args.ascii:
        print(renderer.to_ascii(width=80))


def cmd_list(args):
    """List available primitives and shaders."""
    print("Primitives:")
    for name in sorted(PRIMITIVES):
        print(f"  {name}")
    print("\nShaders:")
    for name in sorted(SHADERS):
        print(f"  {name}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="soft-rasterizer",
        description="Software 3D rasterizer — render 3D scenes to PPM images",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # render
    render_parser = subparsers.add_parser("render", help="Render a scene to an image")
    render_parser.add_argument("-o", "--output", default="output.ppm",
                               help="Output file path (PPM format)")
    render_parser.add_argument("-W", "--width", type=int, default=640,
                               help="Image width in pixels")
    render_parser.add_argument("-H", "--height", type=int, default=480,
                               help="Image height in pixels")
    render_parser.add_argument("-p", "--primitive", default="cube",
                               choices=list(PRIMITIVES.keys()),
                               help="Primitive to render")
    render_parser.add_argument("--obj", default=None,
                               help="Load an OBJ file instead of a primitive")
    render_parser.add_argument("-s", "--shader", default="phong",
                               choices=list(SHADERS.keys()),
                               help="Shading model to use")
    render_parser.add_argument("--texture", choices=["checker", "none"],
                               default="none", help="Texture to apply")
    render_parser.add_argument("--size", type=float, default=1.5,
                               help="Size of the primitive")
    render_parser.add_argument("--fov", type=float, default=60.0,
                               help="Field of view in degrees")
    render_parser.add_argument("--distance", type=float, default=5.0,
                               help="Camera distance from origin")
    render_parser.add_argument("--height", type=float, default=2.0,
                               dest="height",
                               help="Camera height")
    render_parser.add_argument("--angle", type=float, default=0.6,
                               help="Camera orbit angle in radians")
    render_parser.add_argument("--rotation", type=float, default=0.0,
                               help="Object Y rotation in radians")
    render_parser.add_argument("--shininess", type=float, default=32.0,
                               help="Material shininess (Phong specular exponent)")
    render_parser.add_argument("--color", nargs=3, type=float, default=None,
                               metavar=("R", "G", "B"),
                               help="Base colour (0-1 range)")
    render_parser.add_argument("--no-cull", action="store_true",
                               help="Disable backface culling")
    render_parser.add_argument("--ascii", action="store_true",
                               help="Print ASCII preview to stdout")
    render_parser.set_defaults(func=cmd_render)

    # list
    list_parser = subparsers.add_parser("list", help="List primitives and shaders")
    list_parser.set_defaults(func=cmd_list)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()