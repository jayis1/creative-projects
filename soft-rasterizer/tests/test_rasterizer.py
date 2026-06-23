"""Tests for the core rasterizer: framebuffer, clipping, rendering pipeline."""

import os
import tempfile
import pytest
from soft_rasterizer.math3d import Vec3, Vec4, Vec2, Mat4
from soft_rasterizer.rasterizer import (Framebuffer, Renderer, DISCARD,
                                         clip_near_plane, _lerp_vertex_data,
                                         VertexData, FragmentData,
                                         post_grayscale, post_edge_detect,
                                         post_vignette)
from soft_rasterizer.scene import Scene, Camera, Light, Object3D
from soft_rasterizer.shaders import (PhongShader, PhongMaterial,
                                      WireframeShader, NormalShader,
                                      DepthShader, FlatShader,
                                      GouraudShader, ToonShader, FogShader)
from soft_rasterizer.primitives import make_cube, make_sphere, make_torus
from soft_rasterizer.texture import CheckerTexture


class TestFramebuffer:
    def test_construction(self):
        fb = Framebuffer(10, 20)
        assert fb.width == 10 and fb.height == 20
        assert len(fb.color) == 200
        assert len(fb.zbuffer) == 200

    def test_invalid_dims(self):
        with pytest.raises(ValueError):
            Framebuffer(0, 10)
        with pytest.raises(ValueError):
            Framebuffer(10, -1)

    def test_clear(self):
        fb = Framebuffer(5, 5)
        fb.clear(Vec3(0.5, 0.5, 0.5))
        assert fb.get_pixel(0, 0) == Vec3(0.5, 0.5, 0.5)
        assert fb.zbuffer[0] == float("inf")

    def test_set_pixel(self):
        fb = Framebuffer(5, 5)
        fb.set_pixel(2, 3, Vec3(1, 0, 0))
        assert fb.get_pixel(2, 3) == Vec3(1, 0, 0)

    def test_set_pixel_out_of_bounds(self):
        fb = Framebuffer(5, 5)
        fb.set_pixel(-1, 0, Vec3(1, 0, 0))  # should not crash
        fb.set_pixel(10, 10, Vec3(1, 0, 0))

    def test_draw_line(self):
        fb = Framebuffer(10, 10)
        fb.draw_line(0, 0, 9, 9, Vec3(1, 1, 1))
        assert fb.get_pixel(0, 0) == Vec3(1, 1, 1)
        assert fb.get_pixel(9, 9) == Vec3(1, 1, 1)

    def test_to_ppm(self):
        fb = Framebuffer(2, 2)
        fb.set_pixel(0, 0, Vec3(1, 0, 0))
        fd, path = tempfile.mkstemp(suffix=".ppm")
        os.close(fd)
        fb.to_ppm(path)
        with open(path, "rb") as f:
            data = f.read()
        assert data[:2] == b"P6"  # PPM header
        os.unlink(path)

    def test_to_ppm_rounding(self):
        """Verify that PPM output uses round() not int() truncation."""
        fb = Framebuffer(1, 1)
        fb.set_pixel(0, 0, Vec3(0.999, 0.999, 0.999))
        fd, path = tempfile.mkstemp(suffix=".ppm")
        os.close(fd)
        fb.to_ppm(path)
        with open(path, "rb") as f:
            f.readline()  # P6
            f.readline()  # dims
            f.readline()  # max val
            pixel = f.read(3)
        # 0.999 * 255 = 254.745, round → 255, int → 254
        assert pixel[0] == 255, f"Expected 255 (round), got {pixel[0]}"
        os.unlink(path)

    def test_to_bmp(self):
        fb = Framebuffer(4, 4)
        fb.set_pixel(0, 0, Vec3(1, 0, 0))
        fd, path = tempfile.mkstemp(suffix=".bmp")
        os.close(fd)
        fb.to_bmp(path)
        with open(path, "rb") as f:
            data = f.read()
        assert data[:2] == b"BM"  # BMP signature
        os.unlink(path)

    def test_to_ascii(self):
        fb = Framebuffer(10, 10)
        fb.set_pixel(0, 0, Vec3(1, 1, 1))
        s = fb.to_ascii(width=10)
        assert isinstance(s, str)
        assert len(s) > 0


class TestClipping:
    def test_all_inside(self):
        verts = [
            VertexData(Vec4(0, 0, 0, 1)),
            VertexData(Vec4(1, 0, 0, 1)),
            VertexData(Vec4(0, 1, 0, 1)),
        ]
        result = clip_near_plane(verts, 0.0)
        assert len(result) == 3

    def test_all_outside(self):
        verts = [
            VertexData(Vec4(0, 0, -2, 1)),  # w+z = 1 + (-2) = -1 < 0
            VertexData(Vec4(1, 0, -2, 1)),
            VertexData(Vec4(0, 1, -2, 1)),
        ]
        result = clip_near_plane(verts, 0.0)
        assert len(result) == 0

    def test_empty(self):
        result = clip_near_plane([], 0.0)
        assert result == []

    def test_partial_clip(self):
        # One vertex behind, two in front
        verts = [
            VertexData(Vec4(0, 0, -2, 1)),   # behind (w+z = -1)
            VertexData(Vec4(1, 0, 0, 1)),    # in front (w+z = 1)
            VertexData(Vec4(0, 1, 0, 1)),    # in front (w+z = 1)
        ]
        result = clip_near_plane(verts, 0.0)
        # Should produce a quad (4 vertices: 2 original + 2 intersection)
        assert len(result) == 4


class TestRenderer:
    def _basic_scene(self):
        scene = Scene()
        scene.lights.append(Light.directional(Vec3(-0.5, -1, -0.3),
                                              Vec3(1, 1, 0.9), 0.8))
        cam = Camera(position=Vec3(3, 2, 4), target=Vec3(0, 0, 0), fov=60)
        cube = make_cube(2.0)
        obj = Object3D(cube, shader=PhongShader(material=PhongMaterial()))
        scene.add(obj)
        return scene, cam

    def test_render_basic(self):
        scene, cam = self._basic_scene()
        r = Renderer(80, 60)
        fb = r.render(scene, cam)
        assert fb.width == 80 and fb.height == 60
        # Should have some non-black pixels
        non_black = sum(1 for c in fb.color
                        if c.x > 0.01 or c.y > 0.01 or c.z > 0.01)
        assert non_black > 50, f"Expected rendered content, got {non_black} non-black pixels"

    def test_render_stats(self):
        scene, cam = self._basic_scene()
        r = Renderer(80, 60)
        r.render(scene, cam)
        assert r.stats["triangles_input"] > 0
        assert r.stats["triangles_rasterized"] > 0
        assert r.stats["fragments_processed"] > 0

    def test_render_discard_count(self):
        """Wireframe shader discards interior fragments."""
        scene = Scene()
        scene.lights.append(Light.directional(Vec3(-0.5, -1, -0.3),
                                              Vec3(1, 1, 0.9), 0.8))
        cam = Camera(position=Vec3(3, 2, 4), target=Vec3(0, 0, 0), fov=60)
        cube = make_cube(2.0)
        obj = Object3D(cube, shader=WireframeShader())
        scene.add(obj)
        r = Renderer(80, 60)
        r.render(scene, cam)
        # Some fragments should be discarded
        assert r.stats.get("fragments_discarded", 0) > 0

    def test_save_ppm(self):
        scene, cam = self._basic_scene()
        r = Renderer(40, 30)
        r.render(scene, cam)
        fd, path = tempfile.mkstemp(suffix=".ppm")
        os.close(fd)
        r.save_ppm(path)
        assert os.path.exists(path)
        os.unlink(path)

    def test_save_bmp(self):
        scene, cam = self._basic_scene()
        r = Renderer(40, 30)
        r.render(scene, cam)
        fd, path = tempfile.mkstemp(suffix=".bmp")
        os.close(fd)
        r.save_bmp(path)
        assert os.path.exists(path)
        os.unlink(path)

    def test_save_auto_format(self):
        scene, cam = self._basic_scene()
        r = Renderer(40, 30)
        r.render(scene, cam)
        fd, path = tempfile.mkstemp(suffix=".bmp")
        os.close(fd)
        r.save(path)
        assert os.path.exists(path)
        os.unlink(path)

    def test_frustum_cull(self):
        # Object far off-screen should be culled
        scene = Scene()
        scene.lights.append(Light.directional(Vec3(0, -1, 0)))
        cam = Camera(position=Vec3(0, 0, 5), target=Vec3(0, 0, 0), fov=30)
        cube = make_cube(0.5)
        obj = Object3D(cube, shader=PhongShader(),
                       position=Vec3(100, 100, 100))
        scene.add(obj)
        r = Renderer(80, 60)
        r.render(scene, cam)
        assert r.stats["objects_frustum_culled"] == 1

    def test_backface_culling(self):
        scene, cam = self._basic_scene()
        r_cull = Renderer(80, 60, cull_backface=True)
        r_cull.render(scene, cam)
        r_no_cull = Renderer(80, 60, cull_backface=False)
        r_no_cull.render(scene, cam)
        # With culling, fewer triangles should be rasterized
        assert r_cull.stats["triangles_rasterized"] <= r_no_cull.stats["triangles_rasterized"]

    def test_gradient_background(self):
        scene = Scene()
        scene.background = Vec3(0.1, 0.1, 0.1)
        scene.background_top = Vec3(0.9, 0.9, 0.9)
        scene.lights.append(Light.directional(Vec3(0, -1, 0)))
        cam = Camera(position=Vec3(0, 0, 5), target=Vec3(0, 0, 0), fov=60)
        r = Renderer(10, 10)
        r.render(scene, cam)
        # Top pixel should be brighter than bottom
        top = r.framebuffer.get_pixel(0, 0)
        bottom = r.framebuffer.get_pixel(0, 9)
        assert top.x > bottom.x


class TestShaders:
    def test_flat_shader(self):
        scene = Scene()
        scene.lights.append(Light.directional(Vec3(-0.5, -1, -0.3),
                                              Vec3(1, 1, 1), 1.0))
        cam = Camera(position=Vec3(3, 2, 4), target=Vec3(0, 0, 0))
        obj = Object3D(make_cube(2.0), shader=FlatShader())
        scene.add(obj)
        r = Renderer(80, 60)
        r.render(scene, cam)
        assert r.stats["fragments_processed"] > 0

    def test_gouraud_shader(self):
        scene = Scene()
        scene.lights.append(Light.directional(Vec3(-0.5, -1, -0.3),
                                              Vec3(1, 1, 1), 1.0))
        cam = Camera(position=Vec3(3, 2, 4), target=Vec3(0, 0, 0))
        obj = Object3D(make_cube(2.0), shader=GouraudShader())
        scene.add(obj)
        r = Renderer(80, 60)
        r.render(scene, cam)
        assert r.stats["fragments_processed"] > 0

    def test_phong_shader(self):
        scene = Scene()
        scene.lights.append(Light.directional(Vec3(-0.5, -1, -0.3),
                                              Vec3(1, 1, 1), 1.0))
        cam = Camera(position=Vec3(3, 2, 4), target=Vec3(0, 0, 0))
        obj = Object3D(make_sphere(1.0), shader=PhongShader())
        scene.add(obj)
        r = Renderer(80, 60)
        r.render(scene, cam)
        assert r.stats["fragments_processed"] > 0

    def test_wireframe_shader_discard(self):
        """Wireframe shader should use DISCARD for interior pixels."""
        frag = FragmentData(
            world_pos=Vec3(0, 0, 0), normal=Vec3(0, 0, 1),
            uv=Vec2(0, 0), color=Vec3(1, 1, 1),
            bary=(0.5, 0.3, 0.2))  # interior — no bary near 0
        shader = WireframeShader(line_width=0.01)
        result = shader.fragment(frag, None, [], Vec3(0, 0, 5))
        assert result is DISCARD

    def test_wireframe_shader_edge(self):
        """Wireframe shader should draw edge pixels."""
        frag = FragmentData(
            world_pos=Vec3(0, 0, 0), normal=Vec3(0, 0, 1),
            uv=Vec2(0, 0), color=Vec3(1, 1, 1),
            bary=(0.001, 0.5, 0.499))  # near edge
        shader = WireframeShader(line_width=0.01, line_color=Vec3(0, 1, 0))
        result = shader.fragment(frag, None, [], Vec3(0, 0, 5))
        assert result == Vec3(0, 1, 0)

    def test_normal_shader(self):
        scene = Scene()
        scene.lights.append(Light.directional(Vec3(0, -1, 0)))
        cam = Camera(position=Vec3(0, 0, 5), target=Vec3(0, 0, 0))
        obj = Object3D(make_sphere(1.0), shader=NormalShader())
        scene.add(obj)
        r = Renderer(80, 60)
        r.render(scene, cam)
        assert r.stats["fragments_processed"] > 0

    def test_depth_shader(self):
        scene = Scene()
        scene.lights.append(Light.directional(Vec3(0, -1, 0)))
        cam = Camera(position=Vec3(0, 0, 5), target=Vec3(0, 0, 0))
        obj = Object3D(make_sphere(1.0), shader=DepthShader())
        scene.add(obj)
        r = Renderer(80, 60)
        r.render(scene, cam)
        assert r.stats["fragments_processed"] > 0

    def test_toon_shader(self):
        scene = Scene()
        scene.lights.append(Light.directional(Vec3(-0.5, -1, -0.3),
                                              Vec3(1, 1, 1), 1.0))
        cam = Camera(position=Vec3(3, 2, 4), target=Vec3(0, 0, 0))
        obj = Object3D(make_sphere(1.0), shader=ToonShader(bands=4))
        scene.add(obj)
        r = Renderer(80, 60)
        r.render(scene, cam)
        assert r.stats["fragments_processed"] > 0

    def test_fog_shader(self):
        scene = Scene()
        scene.lights.append(Light.directional(Vec3(-0.5, -1, -0.3),
                                              Vec3(1, 1, 1), 1.0))
        cam = Camera(position=Vec3(3, 2, 4), target=Vec3(0, 0, 0))
        inner = PhongShader()
        fog = FogShader(inner, density=0.1)
        obj = Object3D(make_cube(2.0), shader=fog)
        scene.add(obj)
        r = Renderer(80, 60)
        r.render(scene, cam)
        assert r.stats["fragments_processed"] > 0

    def test_fog_shader_passthrough_discard(self):
        """FogShader should pass through DISCARD from inner shader."""
        frag = FragmentData(
            world_pos=Vec3(0, 0, 0), normal=Vec3(0, 0, 1),
            uv=Vec2(0, 0), color=Vec3(1, 1, 1),
            bary=(0.5, 0.3, 0.2))
        inner = WireframeShader(line_width=0.01)
        fog = FogShader(inner)
        result = fog.fragment(frag, None, [], Vec3(0, 0, 5))
        assert result is DISCARD

    def test_ambient_neutral(self):
        """Ambient term should not be tinted by the first light's color."""
        from soft_rasterizer.shaders import _compute_lighting
        mat = PhongMaterial(ambient=Vec3(0.5, 0.5, 0.5),
                            diffuse=Vec3(0, 0, 0),
                            specular=Vec3(0, 0, 0))
        lights = [Light.point(Vec3(0, 0, 10), Vec3(1, 0, 0), 1.0)]
        # With diffuse=0 and specular=0, only ambient contributes
        result = _compute_lighting(Vec3(0, 0, 0), Vec3(0, 0, 1),
                                   Vec3(0, 0, 5), mat, lights)
        # Ambient should be (0.5, 0.5, 0.5) — NOT tinted red by the light
        assert abs(result.x - 0.5) < 1e-6
        assert abs(result.y - 0.5) < 1e-6
        assert abs(result.z - 0.5) < 1e-6


class TestPostProcessing:
    def test_grayscale(self):
        fb = Framebuffer(4, 4)
        fb.set_pixel(0, 0, Vec3(1, 0, 0))
        post_grayscale(fb)
        c = fb.get_pixel(0, 0)
        # Luminance of red = 0.299
        assert abs(c.x - 0.299) < 1e-6
        assert abs(c.y - 0.299) < 1e-6

    def test_edge_detect(self):
        fb = Framebuffer(5, 5)
        # Create a sharp edge: left half white, right half black
        for y in range(5):
            fb.set_pixel(0, y, Vec3(1, 1, 1))
            fb.set_pixel(1, y, Vec3(1, 1, 1))
            fb.set_pixel(3, y, Vec3(0, 0, 0))
            fb.set_pixel(4, y, Vec3(0, 0, 0))
        post_edge_detect(fb, threshold=0.1)
        # Edge pixels should be white
        assert fb.get_pixel(2, 2) == Vec3(1, 1, 1)

    def test_vignette(self):
        fb = Framebuffer(10, 10)
        fb.clear(Vec3(1, 1, 1))
        post_vignette(fb, strength=0.9, falloff=1.0)
        # Center should be brighter than corners
        center = fb.get_pixel(5, 5)
        corner = fb.get_pixel(0, 0)
        assert center.x > corner.x