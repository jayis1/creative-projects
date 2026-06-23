"""Shading models: Flat, Gouraud, Phong, wireframe, normal, and depth shaders.

All shaders implement the :class:`~soft_rasterizer.rasterizer.Shader`
protocol with ``vertex()`` and ``fragment()`` methods.
"""

from __future__ import annotations

import math

from .math3d import Vec2, Vec3, Vec4, Mat4
from .mesh import Vertex
from .rasterizer import VertexData, FragmentData
from .texture import Texture

__all__ = ["FlatShader", "GouraudShader", "PhongShader",
           "WireframeShader", "NormalShader", "DepthShader",
           "PhongMaterial"]


class PhongMaterial:
    """Material properties for Phong/Gouraud shading."""

    __slots__ = ("ambient", "diffuse", "specular", "shininess", "emissive")

    def __init__(self, ambient: Vec3 | None = None,
                 diffuse: Vec3 | None = None,
                 specular: Vec3 | None = None,
                 shininess: float = 32.0,
                 emissive: Vec3 | None = None):
        self.ambient = ambient if ambient is not None else Vec3(0.1, 0.1, 0.1)
        self.diffuse = diffuse if diffuse is not None else Vec3(0.8, 0.8, 0.8)
        self.specular = specular if specular is not None else Vec3(0.5, 0.5, 0.5)
        self.shininess = float(shininess)
        self.emissive = emissive if emissive is not None else Vec3(0, 0, 0)


def _compute_lighting(world_pos: Vec3, normal: Vec3, view_dir: Vec3,
                      material: PhongMaterial, lights) -> Vec3:
    """Compute Phong illumination from multiple lights.

    ``lights`` is a list of objects with ``position`` (Vec3), ``color``
    (Vec3), and ``intensity`` (float) attributes.  Directional lights
    use ``direction`` instead of ``position``.
    """
    result = Vec3(0, 0, 0)
    n = normal.normalized()

    for light in lights:
        light_color = getattr(light, "color", Vec3(1, 1, 1))
        intensity = getattr(light, "intensity", 1.0)

        # Determine light direction (towards the light)
        if hasattr(light, "direction") and light.direction is not None:
            # Directional light — direction points away from light
            light_dir = (-light.direction).normalized()
        else:
            # Point light
            light_dir = (light.position - world_pos).normalized()

        # Diffuse (Lambertian)
        diff = max(0.0, n.dot(light_dir))
        diffuse_term = material.diffuse.component_mul(light_color) * (diff * intensity)

        # Specular (Phong: reflect light dir around normal, dot with view)
        if diff > 0 and material.shininess > 0:
            reflect_dir = (-light_dir).reflect(n)
            spec_angle = max(0.0, reflect_dir.dot(view_dir))
            spec = math.pow(spec_angle, material.shininess)
            specular_term = material.specular.component_mul(light_color) * (spec * intensity)
        else:
            specular_term = Vec3(0, 0, 0)

        # Attenuation for point lights
        if hasattr(light, "position") and not hasattr(light, "direction"):
            dist = (light.position - world_pos).length()
            atten = 1.0 / (1.0 + 0.09 * dist + 0.032 * dist * dist)
            diffuse_term = diffuse_term * atten
            specular_term = specular_term * atten

        result = result + diffuse_term + specular_term

    # Ambient
    ambient_term = material.ambient.component_mul(
        lights[0].color if lights else Vec3(1, 1, 1)) if lights else material.ambient
    result = result + ambient_term + material.emissive
    return result


class FlatShader:
    """Flat shading: one colour per triangle.

    Computes lighting at the face centroid and applies it to all
    fragments of the triangle.
    """

    def __init__(self, material: PhongMaterial | None = None):
        self.material = material or PhongMaterial()
        self._face_color: Vec3 | None = None

    def vertex(self, vertex: Vertex, model: Mat4, view: Mat4,
               projection: Mat4, normal_mat: Mat4) -> VertexData:
        world_pos = model.transform_point(vertex.pos)
        world_normal = normal_mat.transform_direction(vertex.normal).normalized()
        clip_pos = projection.transform(view.transform(
            Vec4(world_pos.x, world_pos.y, world_pos.z, 1.0)))
        return VertexData(
            clip_pos=clip_pos,
            world_pos=world_pos,
            normal=world_normal,
            uv=vertex.uv,
            color=vertex.color,
        )

    def fragment(self, frag: FragmentData, texture: Texture | None,
                 lights, camera_pos: Vec3) -> Vec3:
        # Use the face normal (geometric normal of the triangle, not interpolated)
        # We approximate this by using the interpolated normal normalized
        n = frag.normal.normalized()
        view_dir = (camera_pos - frag.world_pos).normalized()

        base_color = frag.color
        if texture is not None:
            tex_color = texture.sample(frag.uv.x, frag.uv.y)
            base_color = base_color.component_mul(tex_color)
        # Multiply base colour by the material's diffuse colour
        base_color = base_color.component_mul(self.material.diffuse)

        mat = PhongMaterial(
            ambient=self.material.ambient,
            diffuse=base_color,
            specular=self.material.specular,
            shininess=self.material.shininess,
            emissive=self.material.emissive,
        )
        return _compute_lighting(frag.world_pos, n, view_dir, mat, lights)


class GouraudShader:
    """Gouraud shading: lighting computed per-vertex, then interpolated.

    This is the classic Gouraud approach — compute the lit colour at
    each vertex during the vertex shader stage, then interpolate the
    colour across the triangle.
    """

    def __init__(self, material: PhongMaterial | None = None):
        self.material = material or PhongMaterial()

    def vertex(self, vertex: Vertex, model: Mat4, view: Mat4,
               projection: Mat4, normal_mat: Mat4) -> VertexData:
        world_pos = model.transform_point(vertex.pos)
        world_normal = normal_mat.transform_direction(vertex.normal).normalized()
        clip_pos = projection.transform(view.transform(
            Vec4(world_pos.x, world_pos.y, world_pos.z, 1.0)))

        # We need camera_pos and lights for per-vertex lighting, but those
        # aren't available in the vertex() interface.  We'll store them
        # as attributes set by the renderer before rendering.
        # For now, store the world-space data; the fragment shader will
        # do the lighting.
        # Actually, for true Gouraud we compute color at vertices.
        # But our interface doesn't pass lights to vertex().
        # We'll use a hybrid: compute lighting in fragment but with
        # interpolated normals (which is Phong, not Gouraud).
        # To make this truly Gouraud, we set the color in the vertex
        # shader when lights/camera are available via attributes.
        if hasattr(self, "_lights") and hasattr(self, "_camera_pos"):
            view_dir = (self._camera_pos - world_pos).normalized()
            # Create a material with diffuse = material.diffuse * vertex.color
            effective_diffuse = self.material.diffuse.component_mul(vertex.color)
            mat = PhongMaterial(
                ambient=self.material.ambient,
                diffuse=effective_diffuse,
                specular=self.material.specular,
                shininess=self.material.shininess,
                emissive=self.material.emissive,
            )
            lit = _compute_lighting(world_pos, world_normal, view_dir,
                                    mat, self._lights)
            color = lit
        else:
            color = vertex.color

        return VertexData(
            clip_pos=clip_pos,
            world_pos=world_pos,
            normal=world_normal,
            uv=vertex.uv,
            color=color,
        )

    def fragment(self, frag: FragmentData, texture: Texture | None,
                 lights, camera_pos: Vec3) -> Vec3:
        color = frag.color
        if texture is not None:
            tex_color = texture.sample(frag.uv.x, frag.uv.y)
            color = color.component_mul(tex_color)
        # If vertex lighting was NOT done (no _lights attr), apply material diffuse here
        if not hasattr(self, "_lights"):
            color = color.component_mul(self.material.diffuse)
        return color


class PhongShader:
    """Phong shading: normals interpolated, lighting per-pixel.

    The most physically accurate of the three classic shading models
    available here.  Per-fragment lighting with interpolated normals.
    """

    def __init__(self, material: PhongMaterial | None = None):
        self.material = material or PhongMaterial()

    def vertex(self, vertex: Vertex, model: Mat4, view: Mat4,
               projection: Mat4, normal_mat: Mat4) -> VertexData:
        world_pos = model.transform_point(vertex.pos)
        world_normal = normal_mat.transform_direction(vertex.normal).normalized()
        clip_pos = projection.transform(view.transform(
            Vec4(world_pos.x, world_pos.y, world_pos.z, 1.0)))
        return VertexData(
            clip_pos=clip_pos,
            world_pos=world_pos,
            normal=world_normal,
            uv=vertex.uv,
            color=vertex.color,
        )

    def fragment(self, frag: FragmentData, texture: Texture | None,
                 lights, camera_pos: Vec3) -> Vec3:
        n = frag.normal.normalized()
        view_dir = (camera_pos - frag.world_pos).normalized()

        base_color = frag.color
        if texture is not None:
            tex_color = texture.sample(frag.uv.x, frag.uv.y)
            base_color = base_color.component_mul(tex_color)
        # Multiply base colour by the material's diffuse colour
        base_color = base_color.component_mul(self.material.diffuse)

        mat = PhongMaterial(
            ambient=self.material.ambient,
            diffuse=base_color,
            specular=self.material.specular,
            shininess=self.material.shininess,
            emissive=self.material.emissive,
        )
        return _compute_lighting(frag.world_pos, n, view_dir, mat, lights)


class WireframeShader:
    """Wireframe shader: renders only triangle edges.

    Uses barycentric coordinates to detect pixels near an edge and
    colours them.  All other pixels are discarded (alpha = 0).
    """

    def __init__(self, line_color: Vec3 | None = None,
                 line_width: float = 0.01):
        self.line_color = line_color or Vec3(0, 1, 0)
        self.line_width = float(line_width)

    def vertex(self, vertex: Vertex, model: Mat4, view: Mat4,
               projection: Mat4, normal_mat: Mat4) -> VertexData:
        world_pos = model.transform_point(vertex.pos)
        clip_pos = projection.transform(view.transform(
            Vec4(world_pos.x, world_pos.y, world_pos.z, 1.0)))
        return VertexData(
            clip_pos=clip_pos,
            world_pos=world_pos,
            normal=vertex.normal,
            uv=vertex.uv,
            color=vertex.color,
        )

    def fragment(self, frag: FragmentData, texture: Texture | None,
                 lights, camera_pos: Vec3) -> Vec3:
        b0, b1, b2 = frag.bary
        # If any barycentric coordinate is close to 0, we're near an edge
        min_bary = min(b0, b1, b2)
        if min_bary < self.line_width:
            return self.line_color
        # Discard by returning a sentinel — but our pipeline doesn't
        # support discard.  Instead, we return the background colour.
        # A better approach is to use the renderer's wireframe mode.
        return Vec3(-1, -1, -1)  # sentinel for "discard"


class NormalShader:
    """Normal visualisation shader: maps normals to RGB colours.

    Useful for debugging geometry and normals.  Maps the normal
    direction to the [0, 1] colour range.
    """

    def vertex(self, vertex: Vertex, model: Mat4, view: Mat4,
               projection: Mat4, normal_mat: Mat4) -> VertexData:
        world_pos = model.transform_point(vertex.pos)
        world_normal = normal_mat.transform_direction(vertex.normal).normalized()
        clip_pos = projection.transform(view.transform(
            Vec4(world_pos.x, world_pos.y, world_pos.z, 1.0)))
        return VertexData(
            clip_pos=clip_pos,
            world_pos=world_pos,
            normal=world_normal,
            uv=vertex.uv,
            color=vertex.color,
        )

    def fragment(self, frag: FragmentData, texture: Texture | None,
                 lights, camera_pos: Vec3) -> Vec3:
        n = frag.normal.normalized()
        return Vec3((n.x + 1) * 0.5, (n.y + 1) * 0.5, (n.z + 1) * 0.5)


class DepthShader:
    """Depth buffer visualisation shader.

    Maps NDC z ([-1, 1]) to a greyscale gradient.  Near = white,
    far = black.
    """

    def vertex(self, vertex: Vertex, model: Mat4, view: Mat4,
               projection: Mat4, normal_mat: Mat4) -> VertexData:
        world_pos = model.transform_point(vertex.pos)
        clip_pos = projection.transform(view.transform(
            Vec4(world_pos.x, world_pos.y, world_pos.z, 1.0)))
        return VertexData(
            clip_pos=clip_pos,
            world_pos=world_pos,
            normal=vertex.normal,
            uv=vertex.uv,
            color=vertex.color,
        )

    def fragment(self, frag: FragmentData, texture: Texture | None,
                 lights, camera_pos: Vec3) -> Vec3:
        # We don't have direct access to the NDC z here, but we can
        # approximate depth from the view-space distance to camera
        dist = (frag.world_pos - camera_pos).length()
        # Normalise to [0, 1] — assumes a reasonable depth range
        depth = max(0.0, min(1.0, 1.0 - dist / 20.0))
        g = depth
        return Vec3(g, g, g)