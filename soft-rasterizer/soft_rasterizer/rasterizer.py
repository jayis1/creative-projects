"""Core software rasterizer: framebuffer, vertex pipeline, triangle rasterization.

This module implements the full software rendering pipeline:

1. **Vertex shader stage** — transform vertices to clip space
2. **Clipping** — near-plane clipping (and simple frustum cull)
3. **Perspective divide** — clip space → NDC
4. **Viewport transform** — NDC → screen coordinates
5. **Rasterization** — scanline triangle fill with z-buffer test
6. **Fragment shader stage** — per-pixel shading

Perspective-correct interpolation is used for all per-vertex attributes
(normals, UVs, colours) by dividing by ``w`` before interpolation and
multiplying back after.
"""

from __future__ import annotations

import logging
import math
from typing import Protocol

from .math3d import Vec2, Vec3, Vec4, Mat4, barycentric
from .mesh import Mesh, Triangle, Vertex
from .texture import Texture

__all__ = ["Framebuffer", "Renderer", "VertexData", "FragmentData",
           "Shader", "DISCARD"]

logger = logging.getLogger(__name__)

# Sentinel returned by a fragment shader to indicate the fragment should
# be discarded (not written to the framebuffer).  The renderer checks for
# this *before* clamping, so it is never mistaken for a colour value.
DISCARD = object()


class Framebuffer:
    """Holds the colour buffer and z-buffer for a render target.

    The colour buffer stores ``Vec3`` colours in linear [0, 1] space.
    The z-buffer stores NDC z-values in [-1, 1] (higher = farther).
    """

    __slots__ = ("width", "height", "color", "zbuffer")

    def __init__(self, width: int, height: int):
        if width <= 0 or height <= 0:
            raise ValueError(f"Framebuffer dimensions must be positive, got {width}x{height}")
        self.width = int(width)
        self.height = int(height)
        # Colour buffer: list of Vec3
        self.color: list[Vec3] = [Vec3(0, 0, 0)] * (width * height)
        # Z-buffer: initialised to +inf (farthest)
        self.zbuffer: list[float] = [float("inf")] * (width * height)

    def clear(self, color: Vec3 | None = None):
        """Clear both buffers. ``color`` defaults to black."""
        bg = color if color is not None else Vec3(0, 0, 0)
        self.color = [Vec3(bg.x, bg.y, bg.z) for _ in range(self.width * self.height)]
        self.zbuffer = [float("inf")] * (self.width * self.height)

    def set_pixel(self, x: int, y: int, color: Vec3):
        """Set a pixel. Coordinates outside the buffer are ignored."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.color[y * self.width + x] = color

    def get_pixel(self, x: int, y: int) -> Vec3:
        """Get a pixel colour."""
        return self.color[y * self.width + x]

    def draw_line(self, x0: int, y0: int, x1: int, y1: int, color: Vec3):
        """Bresenham line draw (used for wireframe rendering)."""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.set_pixel(x0, y0, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def to_ppm(self, filepath: str):
        """Write the framebuffer to a PPM (P6 binary) file.

        Uses ``round()`` to convert [0,1] floats to 0-255 integers,
        avoiding the slight darkening that ``int()`` truncation causes
        for bright pixels (e.g. 0.999 → 254 instead of 255).
        """
        with open(filepath, "wb") as f:
            header = f"P6\n{self.width} {self.height}\n255\n"
            f.write(header.encode("ascii"))
            data = bytearray()
            for c in self.color:
                # Use round() not int() — int() truncates, darkening bright pixels
                data.append(max(0, min(255, round(c.x * 255))))
                data.append(max(0, min(255, round(c.y * 255))))
                data.append(max(0, min(255, round(c.z * 255))))
            f.write(bytes(data))

    def to_bmp(self, filepath: str):
        """Write the framebuffer to a BMP (24-bit, BGR) file.

        BMP is more widely supported than PPM and can be opened by
        virtually any image viewer or browser without conversion.
        """
        w, h = self.width, self.height
        row_size = (w * 3 + 3) & ~3  # rows padded to 4-byte boundary
        pixel_data_size = row_size * h
        file_size = 54 + pixel_data_size

        with open(filepath, "wb") as f:
            # BMP file header (14 bytes)
            f.write(b"BM")                          # signature
            f.write(file_size.to_bytes(4, "little"))  # file size
            f.write((0).to_bytes(2, "little"))       # reserved
            f.write((0).to_bytes(2, "little"))       # reserved
            f.write((54).to_bytes(4, "little"))      # pixel data offset

            # DIB header (BITMAPINFOHEADER, 40 bytes)
            f.write((40).to_bytes(4, "little"))       # header size
            f.write(w.to_bytes(4, "little", signed=True))   # width
            f.write(h.to_bytes(4, "little", signed=True))   # height (positive = bottom-up)
            f.write((1).to_bytes(2, "little"))        # planes
            f.write((24).to_bytes(2, "little"))       # bits per pixel
            f.write((0).to_bytes(4, "little"))        # compression (none)
            f.write(pixel_data_size.to_bytes(4, "little"))  # image size
            f.write((2835).to_bytes(4, "little"))     # x pixels per meter
            f.write((2835).to_bytes(4, "little"))     # y pixels per meter
            f.write((0).to_bytes(4, "little"))        # colours in table
            f.write((0).to_bytes(4, "little"))        # important colours

            # Pixel data — BMP is bottom-up, BGR order
            for row in range(h - 1, -1, -1):
                row_data = bytearray()
                for col in range(w):
                    c = self.color[row * w + col]
                    r = max(0, min(255, round(c.x * 255)))
                    g = max(0, min(255, round(c.y * 255)))
                    b = max(0, min(255, round(c.z * 255)))
                    row_data.append(b)
                    row_data.append(g)
                    row_data.append(r)
                # Pad row to 4-byte boundary
                while len(row_data) < row_size:
                    row_data.append(0)
                f.write(bytes(row_data))

    def to_ascii(self, width: int = 80) -> str:
        """Return an ASCII-art representation of the framebuffer."""
        ramp = " .:-=+*#%@"
        aspect = self.width / self.height
        h = max(1, int(width / (2 * aspect)))
        result = []
        for row in range(h):
            line = []
            for col in range(width):
                sx = int(col * self.width / width)
                sy = int(row * self.height / h)
                c = self.color[sy * self.width + sx]
                brightness = (c.x + c.y + c.z) / 3.0
                idx = min(len(ramp) - 1, int(brightness * (len(ramp) - 1)))
                line.append(ramp[idx])
            result.append("".join(line))
        return "\n".join(result)


# ---------------------------------------------------------------------------
# Shader interface and per-vertex/fragment data
# ---------------------------------------------------------------------------

class VertexData:
    """Data passed from the vertex shader to the rasterizer.

    Contains the clip-space position and any varying attributes needed
    by the fragment shader.
    """

    __slots__ = ("clip_pos", "world_pos", "normal", "uv", "color")

    def __init__(self, clip_pos: Vec4, world_pos: Vec3 | None = None,
                 normal: Vec3 | None = None, uv: Vec2 | None = None,
                 color: Vec3 | None = None):
        self.clip_pos = clip_pos
        self.world_pos = world_pos if world_pos is not None else Vec3(0, 0, 0)
        self.normal = normal if normal is not None else Vec3(0, 0, 1)
        self.uv = uv if uv is not None else Vec2(0, 0)
        self.color = color if color is not None else Vec3(1, 1, 1)


class FragmentData:
    """Interpolated data at a fragment (pixel) position."""

    __slots__ = ("world_pos", "normal", "uv", "color", "bary")

    def __init__(self, world_pos: Vec3, normal: Vec3, uv: Vec2,
                 color: Vec3, bary: tuple[float, float, float]):
        self.world_pos = world_pos
        self.normal = normal
        self.uv = uv
        self.color = color
        self.bary = bary


class Shader(Protocol):
    """Shader protocol implemented by all shading models."""

    def vertex(self, vertex: Vertex, model: Mat4, view: Mat4,
               projection: Mat4, normal_mat: Mat4) -> VertexData:
        ...

    def fragment(self, frag: FragmentData, texture: Texture | None,
                 lights, camera_pos: Vec3) -> Vec3:
        ...


# ---------------------------------------------------------------------------
# Near-plane clipping
# ---------------------------------------------------------------------------

def _lerp_vertex_data(a: VertexData, b: VertexData, t: float) -> VertexData:
    """Linearly interpolate between two VertexData structs."""
    return VertexData(
        clip_pos=Vec4(
            a.clip_pos.x + (b.clip_pos.x - a.clip_pos.x) * t,
            a.clip_pos.y + (b.clip_pos.y - a.clip_pos.y) * t,
            a.clip_pos.z + (b.clip_pos.z - a.clip_pos.z) * t,
            a.clip_pos.w + (b.clip_pos.w - a.clip_pos.w) * t,
        ),
        world_pos=a.world_pos.lerp(b.world_pos, t),
        normal=a.normal.lerp(b.normal, t),
        uv=Vec2(
            a.uv.x + (b.uv.x - a.uv.x) * t,
            a.uv.y + (b.uv.y - a.uv.y) * t,
        ),
        color=a.color.lerp(b.color, t),
    )


def clip_near_plane(verts: list[VertexData], near: float) -> list[VertexData]:
    """Clip a polygon against the near plane (clip-space z >= -w, i.e. w + z >= 0).

    The near plane in clip space is ``z = -w``, so a vertex is inside
    if ``z >= -w`` (equivalently ``w + z >= 0``).  We use the Sutherland-
    Hodgman algorithm.
    """
    if not verts:
        return []

    def inside(v: VertexData) -> bool:
        return v.clip_pos.w + v.clip_pos.z >= 0.0

    def intersect(a: VertexData, b: VertexData) -> VertexData:
        # Solve for t where w + z = 0 on the segment a→b
        da = a.clip_pos.w + a.clip_pos.z
        db = b.clip_pos.w + b.clip_pos.z
        t = da / (da - db)
        return _lerp_vertex_data(a, b, t)

    result: list[VertexData] = []
    n = len(verts)
    for i in range(n):
        curr = verts[i]
        next_v = verts[(i + 1) % n]
        curr_in = inside(curr)
        next_in = inside(next_v)
        if curr_in:
            result.append(curr)
        if curr_in != next_in:
            result.append(intersect(curr, next_v))
    return result


# ---------------------------------------------------------------------------
# Perspective-correct interpolation helper
# ---------------------------------------------------------------------------

def _persp_correct_attr(a, b, c, wa, wb, wc, u, v, w):
    """Perspective-correct interpolation of an attribute.

    Given attribute values at three vertices and their corresponding
    ``1/w`` weights, plus barycentric coordinates (u, v, w), return
    the interpolated attribute.

    For a Vec3 attribute ``attr``::

        attr_over_w = (u * a/w_a + v * b/w_b + w * c/w_c)
        one_over_w = (u * 1/w_a + v * 1/w_b + w * 1/w_c)
        attr = attr_over_w / one_over_w
    """
    inv_w = u * wa + v * wb + w * wc
    if inv_w == 0.0:
        # Degenerate — just return the weighted average
        if isinstance(a, Vec3):
            return a * u + b * v + c * w
        elif isinstance(a, Vec2):
            return a * u + b * v + c * w
        else:
            return a * u + b * v + c * w

    if isinstance(a, Vec3):
        val = a * (u * wa) + b * (v * wb) + c * (w * wc)
        return val / inv_w
    elif isinstance(a, Vec2):
        val = a * (u * wa) + b * (v * wb) + c * (w * wc)
        return val / inv_w
    else:
        val = a * (u * wa) + b * (v * wb) + c * (w * wc)
        return val / inv_w


# ---------------------------------------------------------------------------
# Post-processing effects
# ---------------------------------------------------------------------------

def post_grayscale(fb: Framebuffer) -> None:
    """Convert the framebuffer to grayscale (in-place)."""
    for i in range(len(fb.color)):
        c = fb.color[i]
        g = 0.299 * c.x + 0.587 * c.y + 0.114 * c.z
        fb.color[i] = Vec3(g, g, g)


def post_edge_detect(fb: Framebuffer, threshold: float = 0.2) -> None:
    """Simple Sobel edge detection (in-place).

    Highlights edges where the brightness gradient exceeds ``threshold``.
    """
    w, h = fb.width, fb.height
    new_color = [Vec3(0, 0, 0)] * (w * h)
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            idx = y * w + x
            # Brightness of 3x3 neighbourhood
            def brightness(px, py):
                c = fb.color[py * w + px]
                return (c.x + c.y + c.z) / 3.0
            gx = (brightness(x+1, y-1) + 2*brightness(x+1, y) + brightness(x+1, y+1)) - \
                 (brightness(x-1, y-1) + 2*brightness(x-1, y) + brightness(x-1, y+1))
            gy = (brightness(x-1, y-1) + 2*brightness(x, y-1) + brightness(x+1, y-1)) - \
                 (brightness(x-1, y+1) + 2*brightness(x, y+1) + brightness(x+1, y+1))
            mag = math.sqrt(gx*gx + gy*gy)
            if mag > threshold:
                new_color[idx] = Vec3(1, 1, 1)
            else:
                new_color[idx] = fb.color[idx] * 0.5
    fb.color = new_color


def post_vignette(fb: Framebuffer, strength: float = 0.5,
                  falloff: float = 0.8) -> None:
    """Apply a vignette effect — darkening at the edges (in-place)."""
    w, h = fb.width, fb.height
    cx, cy = w / 2.0, h / 2.0
    max_dist = math.sqrt(cx*cx + cy*cy)
    for y in range(h):
        for x in range(w):
            dx = x - cx
            dy = y - cy
            dist = math.sqrt(dx*dx + dy*dy) / max_dist
            factor = max(0.0, 1.0 - strength * (dist / falloff) ** 2)
            idx = y * w + x
            fb.color[idx] = fb.color[idx] * factor


# ---------------------------------------------------------------------------
# The Renderer
# ---------------------------------------------------------------------------

class Renderer:
    """Software rendering engine.

    Usage::

        renderer = Renderer(width=640, height=480)
        renderer.render(scene, camera)
        renderer.save("output.ppm")
    """

    def __init__(self, width: int, height: int,
                 cull_backface: bool = True,
                 bilinear: bool = True):
        self.width = int(width)
        self.height = int(height)
        self.framebuffer = Framebuffer(width, height)
        self.cull_backface = cull_backface
        self.bilinear = bilinear
        self.clear_color = Vec3(0.05, 0.05, 0.08)
        # Render statistics (updated each render() call)
        self.stats = {
            "triangles_input": 0,
            "triangles_culled": 0,
            "triangles_clipped": 0,
            "triangles_rasterized": 0,
            "fragments_processed": 0,
            "fragments_depth_failed": 0,
            "fragments_discarded": 0,
            "objects_total": 0,
            "objects_frustum_culled": 0,
        }

    def clear(self, color: Vec3 | None = None):
        self.framebuffer.clear(color if color else self.clear_color)

    def _frustum_cull(self, mesh, model: Mat4, view: Mat4,
                      proj: Mat4) -> bool:
        """Broad-phase frustum cull: test the mesh's bounding sphere
        against the view frustum in clip space.

        Returns ``True`` if the mesh is at least partially inside the
        frustum (should be rendered), ``False`` if fully outside.
        """
        if not mesh.vertices:
            return False
        minp, maxp = mesh.bounds()
        center = Vec3(
            (minp.x + maxp.x) * 0.5,
            (minp.y + maxp.y) * 0.5,
            (minp.z + maxp.z) * 0.5,
        )
        # Bounding sphere radius
        radius = 0.0
        for v in mesh.vertices:
            d = (v.pos - center).length()
            if d > radius:
                radius = d
        # Transform center to clip space
        mvp = proj @ (view @ model)
        clip_center = mvp.transform(Vec4(center.x, center.y, center.z, 1.0))
        if clip_center.w <= 0:
            # Behind the camera — could still be partially visible if very large
            if radius > abs(clip_center.w):
                return True
            return False
        # Perspective divide
        inv_w = 1.0 / clip_center.w
        ndc_x = clip_center.x * inv_w
        ndc_y = clip_center.y * inv_w
        ndc_z = clip_center.z * inv_w
        # Approximate radius in NDC using inv_w as a uniform scale factor.
        # This is conservative — it overestimates the radius slightly,
        # which is safe (false-positives keep visible objects; false-negatives
        # drop them).  The previous code used mvp[0] which mixed the projection
        # scale into the radius calculation, producing incorrect results.
        ndc_radius = radius * inv_w
        # Test against the 6 frustum planes (NDC cube [-1, 1]³)
        if ndc_x + ndc_radius < -1 or ndc_x - ndc_radius > 1:
            return False
        if ndc_y + ndc_radius < -1 or ndc_y - ndc_radius > 1:
            return False
        if ndc_z + ndc_radius < -1 or ndc_z - ndc_radius > 1:
            return False
        return True

    def render(self, scene, camera) -> Framebuffer:
        """Render the scene and return the framebuffer."""
        # Reset stats
        for k in self.stats:
            self.stats[k] = 0

        # Use scene's gradient background if available, otherwise simple clear
        if hasattr(scene, "clear_background"):
            scene.clear_background(self.framebuffer)
        else:
            self.clear()
        view = camera.view_matrix()
        proj = camera.projection_matrix(self.width / self.height)
        lights = scene.lights if hasattr(scene, "lights") else []
        self.stats["objects_total"] = len(scene.objects)

        logger.debug("Rendering %d objects, %d lights",
                      len(scene.objects), len(lights))

        for obj in scene.objects:
            mesh = obj.mesh if hasattr(obj, "mesh") else obj
            model = obj.model_matrix() if hasattr(obj, "model_matrix") else Mat4.identity()

            # Frustum culling
            if self._frustum_cull(mesh, model, view, proj):
                self._render_object(obj, mesh, model, view, proj,
                                    lights, camera)
            else:
                self.stats["objects_frustum_culled"] += 1
                logger.debug("Frustum-culled object: %s", getattr(mesh, "name", "?"))

        logger.debug("Render complete: %s", self.stats)
        return self.framebuffer

    def _render_object(self, obj, mesh, model, view, proj, lights, camera):
        """Render a single (non-culled) object."""
        shader = obj.shader if hasattr(obj, "shader") else mesh.shader if hasattr(mesh, "shader") else None
        if shader is None:
            from .shaders import GouraudShader
            shader = GouraudShader()
        # Inject lights and camera position for Gouraud per-vertex lighting
        # GouraudShader uses _lights and _camera_pos if available
        if "Gouraud" in type(shader).__name__:
            shader._lights = lights  # type: ignore[attr-defined]
            shader._camera_pos = camera.position  # type: ignore[attr-defined]
        # Also check for FogShader wrapping a GouraudShader
        if hasattr(shader, "inner") and "Gouraud" in type(shader.inner).__name__:
            shader.inner._lights = lights  # type: ignore[attr-defined]
            shader.inner._camera_pos = camera.position  # type: ignore[attr-defined]
        normal_mat = model.normal_matrix()
        texture = mesh.texture if hasattr(mesh, "texture") else None
        self._render_mesh(mesh, model, view, proj, normal_mat,
                          shader, texture, lights, camera.position)

    def _render_mesh(self, mesh: Mesh, model: Mat4, view: Mat4,
                     proj: Mat4, normal_mat: Mat4,
                     shader: Shader, texture: Texture | None,
                     lights, camera_pos: Vec3):
        # Vertex shader stage: transform all vertices to clip space
        vert_data: list[VertexData] = []
        for v in mesh.vertices:
            vd = shader.vertex(v, model, view, proj, normal_mat)
            vert_data.append(vd)

        mvp = proj @ (view @ model)

        for tri in mesh.triangles:
            self.stats["triangles_input"] += 1
            self._render_triangle(
                tri, vert_data, mesh, model, view, proj, normal_mat,
                shader, texture, lights, camera_pos)

    def _render_triangle(self, tri: Triangle,
                         vert_data: list[VertexData],
                         mesh: Mesh, model: Mat4, view: Mat4,
                         proj: Mat4, normal_mat: Mat4,
                         shader: Shader, texture: Texture | None,
                         lights, camera_pos: Vec3):
        v0 = vert_data[tri.a]
        v1 = vert_data[tri.b]
        v2 = vert_data[tri.c]

        # Backface culling (in screen space after we know the winding)
        # We'll do this after perspective divide

        # Near-plane clipping
        clipped = clip_near_plane([v0, v1, v2], 0.0)
        if len(clipped) < 3:
            self.stats["triangles_culled"] += 1
            return

        self.stats["triangles_clipped"] += 1
        # Fan-triangulate the clipped polygon
        for i in range(1, len(clipped) - 1):
            self._rasterize_triangle(
                clipped[0], clipped[i], clipped[i + 1],
                shader, texture, lights, camera_pos)

    def _rasterize_triangle(self, v0: VertexData, v1: VertexData, v2: VertexData,
                            shader: Shader, texture: Texture | None,
                            lights, camera_pos: Vec3):
        """Rasterize a single triangle with z-buffering and per-pixel shading."""
        # Perspective divide → NDC
        w0 = v0.clip_pos.w
        w1 = v1.clip_pos.w
        w2 = v2.clip_pos.w

        if w0 == 0 or w1 == 0 or w2 == 0:
            return

        inv_w0 = 1.0 / w0
        inv_w1 = 1.0 / w1
        inv_w2 = 1.0 / w2

        ndc0 = Vec3(v0.clip_pos.x * inv_w0, v0.clip_pos.y * inv_w0, v0.clip_pos.z * inv_w0)
        ndc1 = Vec3(v1.clip_pos.x * inv_w1, v1.clip_pos.y * inv_w1, v1.clip_pos.z * inv_w1)
        ndc2 = Vec3(v2.clip_pos.x * inv_w2, v2.clip_pos.y * inv_w2, v2.clip_pos.z * inv_w2)

        # Viewport transform: NDC [-1, 1] → screen [0, W], [0, H]
        # x_screen = (ndc.x + 1) * 0.5 * width
        # y_screen = (1 - ndc.y) * 0.5 * height   (flip Y)
        half_w = self.width * 0.5
        half_h = self.height * 0.5

        sx0 = (ndc0.x + 1.0) * half_w
        sy0 = (1.0 - ndc0.y) * half_h
        sx1 = (ndc1.x + 1.0) * half_w
        sy1 = (1.0 - ndc1.y) * half_h
        sx2 = (ndc2.x + 1.0) * half_w
        sy2 = (1.0 - ndc2.y) * half_h

        # Screen-space signed area (used for both culling and barycentric)
        # Note: screen Y is flipped ((1 - ndc.y) * half_h), which inverts
        # the winding.  CCW in NDC becomes CW in screen space.
        # So front-facing triangles have signed_area < 0 in screen space.
        signed_area = (sx1 - sx0) * (sy2 - sy0) - (sx2 - sx0) * (sy1 - sy0)

        # Backface culling: after the Y-flip, front-facing = CW = negative area
        if self.cull_backface:
            if signed_area >= 0:
                self.stats["triangles_culled"] += 1
                return

        self.stats["triangles_rasterized"] += 1

        # Bounding box for the triangle, clamped to screen
        min_x = max(0, int(math.floor(min(sx0, sx1, sx2))))
        max_x = min(self.width - 1, int(math.ceil(max(sx0, sx1, sx2))))
        min_y = max(0, int(math.floor(min(sy0, sy1, sy2))))
        max_y = min(self.height - 1, int(math.ceil(max(sy0, sy1, sy2))))

        if min_x > max_x or min_y > max_y:
            return

        # Edge function precomputation for incremental rasterization
        # Using the barycentric approach: for each pixel, compute bary coords
        # and check if all >= 0 (inside the triangle)
        fb = self.framebuffer
        inv_area = 1.0 / signed_area if signed_area != 0 else 0.0

        # Pre-compute 1/w for perspective-correct interpolation
        # (already have inv_w0, inv_w1, inv_w2)

        for py in range(min_y, max_y + 1):
            pcy = py + 0.5  # pixel center
            for px in range(min_x, max_x + 1):
                pcx = px + 0.5

                # Edge functions: edge(a,b,p) = (b.x-a.x)*(p.y-a.y) - (b.y-a.y)*(p.x-a.x)
                # With the Y-flip, front-facing triangles are CW in screen space,
                # so a point is inside when all edge functions are <= 0.
                e01 = (sx1 - sx0) * (pcy - sy0) - (sy1 - sy0) * (pcx - sx0)
                e12 = (sx2 - sx1) * (pcy - sy1) - (sy2 - sy1) * (pcx - sx1)
                e20 = (sx0 - sx2) * (pcy - sy2) - (sy0 - sy2) * (pcx - sx2)

                # For CW winding (front-facing after Y-flip), inside if all edges <= 0
                if e01 > 0 or e12 > 0 or e20 > 0:
                    continue

                # Barycentric weights — note: edges are negative, area is negative,
                # so the ratios are positive.
                b0 = e12 * inv_area  # weight for v0
                b1 = e20 * inv_area  # weight for v1
                b2 = e01 * inv_area  # weight for v2

                # Interpolate depth (NDC z) — linear in screen space is fine
                depth = ndc0.z * b0 + ndc1.z * b1 + ndc2.z * b2

                # Z-buffer test (lower z = closer, since near=-1, far=+1)
                idx = py * self.width + px
                if depth >= fb.zbuffer[idx]:
                    self.stats["fragments_depth_failed"] += 1
                    continue

                self.stats["fragments_processed"] += 1

                # Perspective-correct interpolation of attributes
                # 1/w interpolated
                inv_w = b0 * inv_w0 + b1 * inv_w1 + b2 * inv_w2
                if inv_w == 0.0:
                    continue
                corr_w = 1.0 / inv_w

                # Interpolate world position
                wp = _persp_correct_attr(
                    v0.world_pos, v1.world_pos, v2.world_pos,
                    inv_w0, inv_w1, inv_w2, b0, b1, b2)

                # Interpolate normal
                nrm = _persp_correct_attr(
                    v0.normal, v1.normal, v2.normal,
                    inv_w0, inv_w1, inv_w2, b0, b1, b2)
                if nrm.length_squared() > 0:
                    nrm = nrm.normalized()

                # Interpolate UV
                uv = _persp_correct_attr(
                    v0.uv, v1.uv, v2.uv,
                    inv_w0, inv_w1, inv_w2, b0, b1, b2)

                # Interpolate color
                clr = _persp_correct_attr(
                    v0.color, v1.color, v2.color,
                    inv_w0, inv_w1, inv_w2, b0, b1, b2)

                frag = FragmentData(
                    world_pos=wp,
                    normal=nrm,
                    uv=Vec2(uv.x, uv.y),
                    color=clr,
                    bary=(b0, b1, b2),
                )

                # Run fragment shader
                color = shader.fragment(frag, texture, lights, camera_pos)

                # Check for discard sentinel (used by WireframeShader, etc.)
                if color is DISCARD:
                    self.stats["fragments_discarded"] += 1
                    continue

                color = color.clamp(0.0, 1.0)

                # Write to framebuffer
                fb.color[idx] = color
                fb.zbuffer[idx] = depth

    def save_ppm(self, filepath: str):
        """Save the current framebuffer as a PPM image."""
        self.framebuffer.to_ppm(filepath)
        logger.info("Saved PPM: %s (%dx%d)", filepath, self.width, self.height)

    def save_bmp(self, filepath: str):
        """Save the current framebuffer as a BMP image."""
        self.framebuffer.to_bmp(filepath)
        logger.info("Saved BMP: %s (%dx%d)", filepath, self.width, self.height)

    def save(self, filepath: str):
        """Save the framebuffer, auto-detecting format from the extension.

        Supported formats: ``.ppm`` (PPM P6), ``.bmp`` (24-bit BMP).
        """
        ext = filepath.rsplit(".", 1)[-1].lower() if "." in filepath else ""
        if ext == "bmp":
            self.save_bmp(filepath)
        elif ext == "ppm":
            self.save_ppm(filepath)
        else:
            # Default to PPM
            self.save_ppm(filepath)
            logger.warning("Unknown extension '%s', saved as PPM", ext)

    def to_ascii(self, width: int = 80) -> str:
        """Return an ASCII representation of the current framebuffer."""
        return self.framebuffer.to_ascii(width)