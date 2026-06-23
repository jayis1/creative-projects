"""Tests for scene config, animation, and primitives."""

import json
import os
import tempfile
import pytest
from soft_rasterizer.math3d import Vec3
from soft_rasterizer.scene import Scene, Camera, Light, Object3D
from soft_rasterizer.shaders import PhongShader, PhongMaterial
from soft_rasterizer.primitives import (make_cube, make_sphere, make_plane,
                                         make_cylinder, make_torus,
                                         make_tetrahedron, make_octahedron)
from soft_rasterizer.config import SceneConfig
from soft_rasterizer.animation import AnimationBuilder
from soft_rasterizer.rasterizer import Renderer


class TestPrimitives:
    def test_cube(self):
        m = make_cube(2.0)
        assert m.vertex_count == 24  # 4 per face × 6 faces
        assert m.triangle_count == 12  # 2 per face × 6 faces

    def test_sphere(self):
        m = make_sphere(1.0, segments=16, rings=8)
        assert m.vertex_count == 16 * 9  # segments × (rings + 1)
        assert m.triangle_count > 0

    def test_sphere_invalid(self):
        with pytest.raises(ValueError):
            make_sphere(1.0, segments=2, rings=8)
        with pytest.raises(ValueError):
            make_sphere(1.0, segments=16, rings=1)

    def test_plane(self):
        m = make_plane(4.0, divisions=2)
        assert m.vertex_count == 9  # 3×3 grid
        assert m.triangle_count == 8  # 2×2×2

    def test_plane_invalid(self):
        with pytest.raises(ValueError):
            make_plane(4.0, divisions=0)

    def test_cylinder(self):
        m = make_cylinder(1.0, 2.0, segments=8)
        assert m.triangle_count > 0

    def test_cylinder_invalid(self):
        with pytest.raises(ValueError):
            make_cylinder(1.0, 2.0, segments=2)

    def test_torus(self):
        m = make_torus(1.0, 0.3, 16, 8)
        assert m.triangle_count > 0

    def test_torus_invalid(self):
        with pytest.raises(ValueError):
            make_torus(1.0, 0.3, 2, 8)

    def test_tetrahedron(self):
        m = make_tetrahedron(1.0)
        assert m.vertex_count == 12  # 4 faces × 3 verts
        assert m.triangle_count == 4

    def test_octahedron(self):
        m = make_octahedron(1.0)
        assert m.vertex_count == 24  # 8 faces × 3 verts
        assert m.triangle_count == 8


class TestSceneConfig:
    def test_load_template(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        SceneConfig.save_template(path)
        scene, cam = SceneConfig.load(path)
        assert len(scene.objects) == 1
        assert len(scene.lights) == 2
        assert cam.fov == 60
        os.unlink(path)

    def test_load_not_found(self):
        with pytest.raises(FileNotFoundError):
            SceneConfig.load("/nonexistent/path.json")

    def test_load_custom(self):
        config = {
            "camera": {"position": [0, 0, 5], "target": [0, 0, 0], "fov": 45},
            "lights": [{"type": "directional", "direction": [0, -1, 0]}],
            "objects": [{"primitive": "sphere", "size": 1.0,
                         "shader": {"name": "phong"}}]
        }
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(config, f)
        scene, cam = SceneConfig.load(path)
        assert cam.fov == 45
        assert len(scene.objects) == 1
        assert len(scene.lights) == 1
        os.unlink(path)

    def test_load_with_fog(self):
        config = {
            "camera": {"position": [0, 0, 5]},
            "lights": [{"type": "point", "position": [5, 5, 5]}],
            "objects": [{"primitive": "cube", "size": 2.0,
                         "shader": {"name": "phong",
                                    "fog": {"density": 0.1, "near": 3.0}}}]
        }
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(config, f)
        scene, cam = SceneConfig.load(path)
        # FogShader should wrap the PhongShader
        assert hasattr(scene.objects[0].shader, "inner")
        os.unlink(path)

    def test_load_toon(self):
        config = {
            "camera": {"position": [0, 0, 5]},
            "lights": [{"type": "directional", "direction": [0, -1, 0]}],
            "objects": [{"primitive": "sphere", "size": 1.0,
                         "shader": {"name": "toon", "bands": 5}}]
        }
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(config, f)
        scene, cam = SceneConfig.load(path)
        assert scene.objects[0].shader.bands == 5
        os.unlink(path)

    def test_load_obj(self):
        # Write a small OBJ file
        fd_obj, obj_path = tempfile.mkstemp(suffix=".obj")
        with os.fdopen(fd_obj, "w") as f:
            f.write("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
        config = {
            "camera": {"position": [0, 0, 5]},
            "lights": [{"type": "directional", "direction": [0, -1, 0]}],
            "objects": [{"obj": obj_path, "shader": {"name": "phong"}}]
        }
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(config, f)
        scene, cam = SceneConfig.load(path)
        assert scene.objects[0].mesh.vertex_count == 3
        os.unlink(path)
        os.unlink(obj_path)

    def test_unknown_shader(self):
        config = {
            "camera": {"position": [0, 0, 5]},
            "lights": [],
            "objects": [{"primitive": "cube",
                         "shader": {"name": "nonexistent"}}]
        }
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(config, f)
        with pytest.raises(ValueError, match="Unknown shader"):
            SceneConfig.load(path)
        os.unlink(path)

    def test_unknown_primitive(self):
        config = {
            "camera": {"position": [0, 0, 5]},
            "lights": [],
            "objects": [{"primitive": "nonexistent"}]
        }
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(config, f)
        with pytest.raises(ValueError, match="Unknown primitive"):
            SceneConfig.load(path)
        os.unlink(path)


class TestAnimation:
    def test_turntable(self):
        scene = Scene()
        scene.lights.append(Light.directional(Vec3(-0.5, -1, -0.3)))
        cam = Camera(position=Vec3(5, 2, 0), target=Vec3(0, 0, 0))
        obj = Object3D(make_cube(1.0), shader=PhongShader(),
                       rotation=Vec3(0, 0, 0))
        scene.add(obj)
        renderer = Renderer(40, 30)
        builder = AnimationBuilder(renderer, scene, cam)

        with tempfile.TemporaryDirectory() as tmpdir:
            files = builder.render_turntable(
                output_dir=tmpdir, frames=4, fmt="ppm")
            assert len(files) == 4
            for f in files:
                assert os.path.exists(f)

    def test_turntable_invalid_frames(self):
        scene = Scene()
        scene.lights.append(Light.directional(Vec3(0, -1, 0)))
        cam = Camera(position=Vec3(5, 0, 0))
        scene.add(Object3D(make_cube(1.0), shader=PhongShader()))
        renderer = Renderer(20, 20)
        builder = AnimationBuilder(renderer, scene, cam)
        with pytest.raises(ValueError):
            builder.render_turntable("/tmp/test_frames", frames=0)

    def test_restores_state(self):
        scene = Scene()
        scene.lights.append(Light.directional(Vec3(0, -1, 0)))
        cam = Camera(position=Vec3(5, 0, 0), target=Vec3(0, 0, 0))
        obj = Object3D(make_cube(1.0), shader=PhongShader(),
                       rotation=Vec3(0, 0, 0))
        scene.add(obj)
        renderer = Renderer(20, 20)
        builder = AnimationBuilder(renderer, scene, cam)

        orig_pos = Vec3(cam.position.x, cam.position.y, cam.position.z)
        orig_rot = Vec3(obj.rotation.x, obj.rotation.y, obj.rotation.z)

        with tempfile.TemporaryDirectory() as tmpdir:
            builder.render_turntable(tmpdir, frames=4)

        # State should be restored
        assert abs(cam.position.x - orig_pos.x) < 1e-10
        assert abs(obj.rotation.y - orig_rot.y) < 1e-10


class TestScene:
    def test_gradient_background_render(self):
        scene = Scene()
        scene.background = Vec3(0.0, 0.0, 0.0)
        scene.background_top = Vec3(1.0, 1.0, 1.0)
        scene.lights.append(Light.directional(Vec3(0, -1, 0)))
        cam = Camera(position=Vec3(0, 0, 5))
        scene.add(Object3D(make_cube(0.1), shader=PhongShader()))
        r = Renderer(20, 20)
        r.render(scene, cam)
        # Top row should be bright, bottom dark
        top = r.framebuffer.color[0]
        bottom = r.framebuffer.color[19 * 20]
        assert top.x > 0.9
        assert bottom.x < 0.1

    def test_add_light(self):
        scene = Scene()
        scene.add(Light.point(Vec3(1, 1, 1)))
        assert len(scene.lights) == 1

    def test_add_mesh(self):
        scene = Scene()
        scene.add(make_cube(1.0))
        assert len(scene.objects) == 1

    def test_add_invalid(self):
        scene = Scene()
        with pytest.raises(TypeError):
            scene.add(42)

    def test_remove(self):
        scene = Scene()
        light = Light.point(Vec3(1, 1, 1))
        scene.add(light)
        scene.remove(light)
        assert len(scene.lights) == 0

    def test_object3d_rotate_y(self):
        obj = Object3D(make_cube(1.0), shader=PhongShader(),
                       rotation=Vec3(0, 0, 0))
        obj.rotate_y(0.5)
        assert abs(obj.rotation.y - 0.5) < 1e-10