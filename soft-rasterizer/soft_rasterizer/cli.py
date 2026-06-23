"""Command-line interface for the software rasterizer.

Supports:
  - Rendering primitives or OBJ files with various shaders
  - Loading scenes from JSON config files
  - Multi-frame turntable animation
  - Post-processing effects (grayscale, edge detect, vignette)
  - BMP and PPM output
  - Render statistics and ASCII preview
  - Gradient backgrounds
"""

from __future__ import annotations

import argparse
import logging
import math
import sys

from . import __version__
from .math3d import Vec3
from .rasterizer import (Renderer, post_grayscale, post_edge_detect,
                         post_vignette)
from .scene import Scene, Camera, Light, Object3D
from .shaders import (FlatShader, GouraudShader, PhongShader,
                      WireframeShader, NormalShader, DepthShader,
                      ToonShader, FogShader, CrosshatchShader,
                      PhongMaterial)
from .texture import CheckerTexture
from .primitives import (make_cube, make_sphere, make_plane, make_cylinder,
                         make_torus, make_tetrahedron, make_octahedron)
from .mesh import OBJLoader
from .config import SceneConfig
from .animation import AnimationBuilder

SHADERS = {
    "flat": FlatShader,
    "gouraud": GouraudShader,
    "phong": PhongShader,
    "normal": NormalShader,
    "depth": DepthShader,
    "wireframe": WireframeShader,
    "toon": ToonShader,
    "crosshatch": CrosshatchShader,
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


def build_scene(args) -> tuple[Scene, Camera]:
    """Build a scene from CLI arguments."""
    scene = Scene()

    # Lights
    scene.lights.append(Light.directional(
        Vec3(-0.5, -1, -0.3), Vec3(1, 1, 0.9), 0.8))
    scene.lights.append(Light.point(
        Vec3(5, 5, 5), Vec3(0.4, 0.4, 0.6), 0.5))

    # Gradient background (6 floats: top_rgb, bottom_rgb)
    if getattr(args, "bg_gradient", None):
        tr, tg, tb, br, bg_, bb = args.bg_gradient
        scene.background = Vec3(br, bg_, bb)
        scene.background_top = Vec3(tr, tg, tb)
    elif getattr(args, "bg_color", None):
        scene.background = Vec3(*args.bg_color)

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
        prim = args.primitive
        size = args.size
        if prim == "cube":
            mesh = make_cube(size=size)
        elif prim == "sphere":
            mesh = make_sphere(radius=size)
        elif prim == "plane":
            mesh = make_plane(size=size)
        elif prim == "cylinder":
            mesh = make_cylinder(radius=size)
        elif prim == "torus":
            mesh = make_torus(major_radius=size)
        elif prim == "tetrahedron":
            mesh = make_tetrahedron(size=size)
        elif prim == "octahedron":
            mesh = make_octahedron(size=size)
        else:
            mesh = PRIMITIVES[prim]()
    else:
        print(f"Unknown primitive: {args.primitive}", file=sys.stderr)
        sys.exit(1)

    # Shader
    shader_name = args.shader
    if shader_name not in SHADERS:
        print(f"Unknown shader: {shader_name}", file=sys.stderr)
        sys.exit(1)

    if shader_name == "wireframe":
        shader = WireframeShader(line_width=getattr(args, "line_width", 0.01))
    elif shader_name == "toon":
        material = PhongMaterial(
            diffuse=Vec3(*args.color) if getattr(args, "color", None) else Vec3(0.8, 0.6, 0.4),
            ambient=Vec3(0.3, 0.3, 0.3),
        )
        shader = ToonShader(material=material, bands=getattr(args, "bands", 3))
    elif shader_name == "crosshatch":
        shader = CrosshatchShader(material=PhongMaterial(
            diffuse=Vec3(*args.color) if getattr(args, "color", None) else Vec3(0.8, 0.6, 0.4)))
    elif shader_name in (["flat", "gouraud", "phong"]):
        material = PhongMaterial(
            diffuse=Vec3(*args.color) if getattr(args, "color", None) else Vec3(0.8, 0.6, 0.4),
            specular=Vec3(0.8, 0.8, 0.8),
            shininess=getattr(args, "shininess", 32.0),
        )
        shader = SHADERS[shader_name](material=material)
    else:
        shader = SHADERS[shader_name]()

    # Wrap in fog if requested
    if getattr(args, "fog", False):
        shader = FogShader(shader, density=getattr(args, "fog_density", 0.05),
                           fog_near=getattr(args, "fog_near", 5.0))

    # Texture
    texture = None
    if getattr(args, "texture", None) == "checker":
        texture = CheckerTexture(squares=8)
        mesh.texture = texture

    obj = Object3D(mesh, shader=shader,
                   rotation=Vec3(0, args.rotation, 0))
    scene.add(obj)

    return scene, cam


def apply_post_processing(renderer: Renderer, args):
    """Apply post-processing effects to the rendered framebuffer."""
    if args.grayscale:
        post_grayscale(renderer.framebuffer)
    if args.edge:
        post_edge_detect(renderer.framebuffer, threshold=args.edge_threshold)
    if args.vignette:
        post_vignette(renderer.framebuffer, strength=args.vignette_strength)


def cmd_render(args):
    """Render a scene to an image file."""
    if args.scene:
        scene, cam = SceneConfig.load(args.scene)
    else:
        scene, cam = build_scene(args)

    renderer = Renderer(args.width, args.height,
                        cull_backface=not args.no_cull)
    renderer.render(scene, cam)

    apply_post_processing(renderer, args)

    # Determine output path
    output = args.output
    ext = output.rsplit(".", 1)[-1].lower() if "." in output else "ppm"
    if ext in ("ppm", "bmp"):
        renderer.save(output)
    else:
        output = output.rsplit(".", 1)[0] + ".ppm"
        renderer.save(output)

    print(f"Rendered {args.width}x{args.height} → {output}")

    if args.stats:
        s = renderer.stats
        print(f"\nRender Statistics:")
        print(f"  Objects: {s['objects_total']} total, {s['objects_frustum_culled']} frustum-culled")
        print(f"  Triangles: {s['triangles_input']} input, {s['triangles_culled']} culled, "
              f"{s['triangles_rasterized']} rasterized")
        print(f"  Fragments: {s['fragments_processed']} shaded, "
              f"{s['fragments_depth_failed']} depth-failed, "
              f"{s.get('fragments_discarded', 0)} discarded")

    if args.ascii:
        print(renderer.to_ascii(width=80))


def cmd_animate(args):
    """Render a turntable animation (multiple frames)."""
    if args.scene:
        scene, cam = SceneConfig.load(args.scene)
    else:
        scene, cam = build_scene(args)

    renderer = Renderer(args.width, args.height,
                        cull_backface=not args.no_cull)
    builder = AnimationBuilder(renderer, scene, cam)

    files = builder.render_turntable(
        output_dir=args.output_dir,
        frames=args.frames,
        camera_orbit=not args.no_camera_orbit,
        object_rotation=not args.no_object_rotation,
        fmt=args.format,
        prefix=args.prefix,
    )

    print(f"Rendered {len(files)} frames to {args.output_dir}/")
    print(f"  Format: {args.format}")
    print(f"  Resolution: {args.width}x{args.height}")

    if args.stats:
        s = renderer.stats
        print(f"\nLast frame statistics:")
        print(f"  Triangles: {s['triangles_rasterized']} rasterized")
        print(f"  Fragments: {s['fragments_processed']} shaded")


def cmd_list(args):
    """List available primitives and shaders."""
    print("Primitives:")
    for name in sorted(PRIMITIVES):
        print(f"  {name}")
    print("\nShaders:")
    for name in sorted(SHADERS):
        print(f"  {name}")
    print("\nPost-processing:")
    for name in ["grayscale", "edge-detect", "vignette"]:
        print(f"  {name}")
    print("\nOutput formats:")
    for name in ["ppm", "bmp"]:
        print(f"  {name}")


def cmd_template(args):
    """Write a template JSON scene file."""
    SceneConfig.save_template(args.output)
    print(f"Template scene written to: {args.output}")


def add_render_args(parser):
    """Add common rendering arguments to a subparser."""
    parser.add_argument("-o", "--output", default="output.ppm",
                        help="Output file path (.ppm or .bmp)")
    parser.add_argument("--scene", default=None,
                        help="Load scene from JSON config file (overrides primitive/shader args)")
    parser.add_argument("-W", "--width", type=int, default=640,
                        help="Image width in pixels")
    parser.add_argument("-H", "--height", type=int, default=480,
                        help="Image height in pixels")
    parser.add_argument("-p", "--primitive", default="cube",
                        choices=list(PRIMITIVES.keys()),
                        help="Primitive to render")
    parser.add_argument("--obj", default=None,
                        help="Load an OBJ file instead of a primitive")
    parser.add_argument("-s", "--shader", default="phong",
                        choices=list(SHADERS.keys()),
                        help="Shading model to use")
    parser.add_argument("--texture", choices=["checker", "none"],
                        default="none", help="Texture to apply")
    parser.add_argument("--size", type=float, default=1.5,
                        help="Size of the primitive")
    parser.add_argument("--fov", type=float, default=60.0,
                        help="Field of view in degrees")
    parser.add_argument("--distance", type=float, default=5.0,
                        help="Camera distance from origin")
    parser.add_argument("--cam-height", type=float, default=2.0,
                        dest="height",
                        help="Camera height")
    parser.add_argument("--angle", type=float, default=0.6,
                        help="Camera orbit angle in radians")
    parser.add_argument("--rotation", type=float, default=0.0,
                        help="Object Y rotation in radians")
    parser.add_argument("--shininess", type=float, default=32.0,
                        help="Material shininess (Phong specular exponent)")
    parser.add_argument("--color", nargs=3, type=float, default=None,
                        metavar=("R", "G", "B"),
                        help="Base colour (0-1 range)")
    parser.add_argument("--bg-color", nargs=3, type=float, default=None,
                        metavar=("R", "G", "B"),
                        help="Background colour (0-1 range)")
    parser.add_argument("--bg-gradient", nargs=6, type=float, default=None,
                        metavar=("TR", "TG", "TB", "BR", "BG", "BB"),
                        help="Gradient background: top RGB then bottom RGB (6 values 0-1)")
    parser.add_argument("--no-cull", action="store_true",
                        help="Disable backface culling")
    parser.add_argument("--ascii", action="store_true",
                        help="Print ASCII preview to stdout")
    parser.add_argument("--fog", action="store_true",
                        help="Enable distance-based fog effect")
    parser.add_argument("--fog-density", type=float, default=0.05,
                        dest="fog_density",
                        help="Fog density (exponential)")
    parser.add_argument("--fog-near", type=float, default=5.0,
                        dest="fog_near",
                        help="Distance at which fog begins")
    parser.add_argument("--bands", type=int, default=3,
                        help="Number of colour bands for toon shader")
    parser.add_argument("--line-width", type=float, default=0.01,
                        dest="line_width",
                        help="Line width for wireframe shader")
    parser.add_argument("--stats", action="store_true",
                        help="Print render statistics")
    # Post-processing
    parser.add_argument("--grayscale", action="store_true",
                        help="Apply grayscale post-processing")
    parser.add_argument("--edge", action="store_true",
                        help="Apply edge detection post-processing")
    parser.add_argument("--edge-threshold", type=float, default=0.2,
                        dest="edge_threshold",
                        help="Edge detection threshold")
    parser.add_argument("--vignette", action="store_true",
                        help="Apply vignette post-processing")
    parser.add_argument("--vignette-strength", type=float, default=0.5,
                        dest="vignette_strength",
                        help="Vignette strength (0-1)")


class _AppendNArgs(argparse.Action):
    """Custom action for --bg-gradient that takes two groups of 3 floats."""
    # Simplified: handled via nargs=6 instead
    pass


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="soft-rasterizer",
        description="Software 3D rasterizer — render 3D scenes to PPM/BMP images",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable verbose logging")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # render
    render_parser = subparsers.add_parser("render", help="Render a scene to an image")
    add_render_args(render_parser)
    render_parser.set_defaults(func=cmd_render)

    # animate
    anim_parser = subparsers.add_parser("animate", help="Render a turntable animation")
    anim_parser.add_argument("-o", "--output-dir", default="frames",
                             help="Output directory for frames")
    anim_parser.add_argument("-W", "--width", type=int, default=320,
                              help="Image width in pixels")
    anim_parser.add_argument("-H", "--height", type=int, default=240,
                              help="Image height in pixels")
    anim_parser.add_argument("-n", "--frames", type=int, default=36,
                              help="Number of frames to render")
    anim_parser.add_argument("--format", choices=["ppm", "bmp"], default="ppm",
                              help="Output format for frames")
    anim_parser.add_argument("--prefix", default="frame",
                              help="Filename prefix for frames")
    anim_parser.add_argument("--no-camera-orbit", action="store_true",
                              dest="no_camera_orbit",
                              help="Disable camera orbiting")
    anim_parser.add_argument("--no-object-rotation", action="store_true",
                              dest="no_object_rotation",
                              help="Disable object rotation")
    anim_parser.add_argument("--scene", default=None,
                              help="Load scene from JSON config file")
    # Include basic scene-building args
    anim_parser.add_argument("-p", "--primitive", default="cube",
                              choices=list(PRIMITIVES.keys()))
    anim_parser.add_argument("-s", "--shader", default="phong",
                              choices=list(SHADERS.keys()))
    anim_parser.add_argument("--obj", default=None)
    anim_parser.add_argument("--size", type=float, default=1.5)
    anim_parser.add_argument("--fov", type=float, default=60.0)
    anim_parser.add_argument("--distance", type=float, default=5.0)
    anim_parser.add_argument("--cam-height", type=float, default=2.0,
                              dest="height")
    anim_parser.add_argument("--angle", type=float, default=0.6)
    anim_parser.add_argument("--rotation", type=float, default=0.0)
    anim_parser.add_argument("--no-cull", action="store_true")
    anim_parser.add_argument("--stats", action="store_true")
    anim_parser.set_defaults(func=cmd_animate)

    # list
    list_parser = subparsers.add_parser("list", help="List primitives, shaders, and options")
    list_parser.set_defaults(func=cmd_list)

    # template
    template_parser = subparsers.add_parser("template",
                                             help="Write a template JSON scene file")
    template_parser.add_argument("-o", "--output", default="scene_template.json",
                                  help="Output file path")
    template_parser.set_defaults(func=cmd_template)

    args = parser.parse_args(argv)

    # Set up logging
    level = logging.DEBUG if getattr(args, "verbose", False) else logging.WARNING
    logging.basicConfig(level=level, format="%(name)s: %(message)s")

    # Handle bg-gradient specially (can't use custom action easily)
    if hasattr(args, "bg_gradient") and args.bg_gradient:
        # Parse as: --bg-gradient "0.1 0.1 0.3" "0.05 0.05 0.08"
        # This is handled via string parsing in build_scene
        pass

    args.func(args)


if __name__ == "__main__":
    main()