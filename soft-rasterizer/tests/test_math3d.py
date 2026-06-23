"""Tests for 3D math primitives: Vec2, Vec3, Vec4, Mat4, barycentric."""

import math
import pytest
from soft_rasterizer.math3d import Vec2, Vec3, Vec4, Mat4, barycentric


class TestVec2:
    def test_construction(self):
        v = Vec2(3, 4)
        assert v.x == 3.0
        assert v.y == 4.0

    def test_default(self):
        v = Vec2()
        assert v.x == 0.0 and v.y == 0.0

    def test_addition(self):
        v = Vec2(1, 2) + Vec2(3, 4)
        assert v.x == 4.0 and v.y == 6.0

    def test_subtraction(self):
        v = Vec2(5, 3) - Vec2(2, 1)
        assert v.x == 3.0 and v.y == 2.0

    def test_scalar_mult(self):
        v = Vec2(2, 3) * 2
        assert v.x == 4.0 and v.y == 6.0

    def test_rmul(self):
        v = 3 * Vec2(2, 4)
        assert v.x == 6.0 and v.y == 12.0

    def test_division(self):
        v = Vec2(6, 8) / 2
        assert v.x == 3.0 and v.y == 4.0

    def test_negation(self):
        v = -Vec2(1, 2)
        assert v.x == -1.0 and v.y == -2.0

    def test_dot(self):
        assert Vec2(1, 0).dot(Vec2(0, 1)) == 0.0
        assert Vec2(3, 4).dot(Vec2(3, 4)) == 25.0

    def test_length(self):
        assert Vec2(3, 4).length() == 5.0

    def test_length_squared(self):
        assert Vec2(3, 4).length_squared() == 25.0

    def test_normalized(self):
        v = Vec2(3, 4).normalized()
        assert abs(v.length() - 1.0) < 1e-10

    def test_normalized_zero(self):
        v = Vec2(0, 0).normalized()
        assert v.x == 0.0 and v.y == 0.0

    def test_lerp(self):
        v = Vec2(0, 0).lerp(Vec2(10, 20), 0.5)
        assert v.x == 5.0 and v.y == 10.0

    def test_equality(self):
        assert Vec2(1, 2) == Vec2(1, 2)
        assert Vec2(1, 2) != Vec2(1, 3)

    def test_iter(self):
        vals = list(Vec2(1, 2))
        assert vals == [1.0, 2.0]

    def test_hash(self):
        assert hash(Vec2(1, 2)) == hash(Vec2(1, 2))


class TestVec3:
    def test_construction(self):
        v = Vec3(1, 2, 3)
        assert v.x == 1.0 and v.y == 2.0 and v.z == 3.0

    def test_addition(self):
        v = Vec3(1, 2, 3) + Vec3(4, 5, 6)
        assert v == Vec3(5, 7, 9)

    def test_subtraction(self):
        v = Vec3(4, 5, 6) - Vec3(1, 2, 3)
        assert v == Vec3(3, 3, 3)

    def test_scalar_mult(self):
        assert (Vec3(1, 2, 3) * 2) == Vec3(2, 4, 6)

    def test_cross(self):
        c = Vec3(1, 0, 0).cross(Vec3(0, 1, 0))
        assert c == Vec3(0, 0, 1)

    def test_cross_anti_commutative(self):
        a, b = Vec3(1, 0, 0), Vec3(0, 1, 0)
        assert a.cross(b) == -(b.cross(a))

    def test_dot(self):
        assert Vec3(1, 0, 0).dot(Vec3(0, 1, 0)) == 0.0
        assert Vec3(1, 1, 0).dot(Vec3(1, 1, 0)) == 2.0

    def test_length(self):
        assert Vec3(0, 3, 4).length() == 5.0

    def test_normalized(self):
        v = Vec3(0, 3, 4).normalized()
        assert abs(v.length() - 1.0) < 1e-10

    def test_reflect(self):
        d = Vec3(1, -1, 0)
        n = Vec3(0, 1, 0)
        r = d.reflect(n)
        assert abs(r.x - 1.0) < 1e-10
        assert abs(r.y - 1.0) < 1e-10

    def test_component_mul(self):
        r = Vec3(1, 2, 3).component_mul(Vec3(4, 5, 6))
        assert r == Vec3(4, 10, 18)

    def test_clamp(self):
        v = Vec3(-1, 0.5, 2).clamp(0, 1)
        assert v == Vec3(0, 0.5, 1)

    def test_lerp(self):
        v = Vec3(0, 0, 0).lerp(Vec3(10, 20, 30), 0.1)
        assert v == Vec3(1, 2, 3)

    def test_iter(self):
        assert list(Vec3(1, 2, 3)) == [1.0, 2.0, 3.0]


class TestVec4:
    def test_construction(self):
        v = Vec4(1, 2, 3, 4)
        assert v.w == 4.0

    def test_to_vec3_divide(self):
        v = Vec4(2, 4, 6, 2)
        assert v.to_vec3() == Vec3(1, 2, 3)

    def test_to_vec3_w1(self):
        v = Vec4(1, 2, 3, 1)
        assert v.to_vec3() == Vec3(1, 2, 3)

    def test_xyz(self):
        v = Vec4(1, 2, 3, 4)
        assert v.xyz() == Vec3(1, 2, 3)


class TestMat4:
    def test_identity(self):
        m = Mat4.identity()
        v = m.transform(Vec4(1, 2, 3, 1))
        assert v.x == 1.0 and v.y == 2.0 and v.z == 3.0

    def test_translation(self):
        m = Mat4.translation(1, 2, 3)
        v = m.transform(Vec4(0, 0, 0, 1))
        assert v.x == 1.0 and v.y == 2.0 and v.z == 3.0

    def test_scaling(self):
        m = Mat4.scaling(2, 3, 4)
        v = m.transform(Vec4(1, 1, 1, 1))
        assert v.x == 2.0 and v.y == 3.0 and v.z == 4.0

    def test_rotation_x_90(self):
        m = Mat4.rotation_x(math.pi / 2)
        v = m.transform(Vec4(0, 1, 0, 1))
        assert abs(v.z - 1.0) < 1e-10
        assert abs(v.y) < 1e-10

    def test_rotation_y_90(self):
        m = Mat4.rotation_y(math.pi / 2)
        v = m.transform(Vec4(1, 0, 0, 1))
        assert abs(v.z + 1.0) < 1e-10  # rotates towards -Z

    def test_mul_identity(self):
        m = Mat4.translation(1, 2, 3) @ Mat4.identity()
        v = m.transform(Vec4(0, 0, 0, 1))
        assert v.x == 1.0

    def test_mul_compose(self):
        t = Mat4.translation(5, 0, 0)
        s = Mat4.scaling(2, 1, 1)
        m = t @ s
        v = m.transform(Vec4(1, 0, 0, 1))
        # s first: (2,0,0), then t: (7,0,0)
        assert v.x == 7.0

    def test_transform_point(self):
        m = Mat4.translation(1, 2, 3)
        p = m.transform_point(Vec3(0, 0, 0))
        assert p == Vec3(1, 2, 3)

    def test_transform_direction(self):
        m = Mat4.translation(1, 2, 3)
        d = m.transform_direction(Vec3(1, 0, 0))
        # Direction is not affected by translation
        assert d == Vec3(1, 0, 0)

    def test_inverse(self):
        m = Mat4.translation(1, 2, 3)
        inv = m.inverse()
        v = inv.transform(Vec4(1, 2, 3, 1))
        assert abs(v.x) < 1e-10
        assert abs(v.y) < 1e-10
        assert abs(v.z) < 1e-10

    def test_inverse_singular(self):
        m = Mat4([0] * 16)
        with pytest.raises(ValueError):
            m.inverse()

    def test_normal_matrix(self):
        m = Mat4.scaling(2, 2, 2)
        nm = m.normal_matrix()
        # Normal matrix should undo the scaling for normals
        n = nm.transform_direction(Vec3(1, 0, 0))
        assert abs(n.x - 0.5) < 1e-6

    def test_perspective(self):
        m = Mat4.perspective(math.radians(90), 1.0, 0.1, 100)
        # A point at origin should be at z=0 in clip space after divide
        v = m.transform(Vec4(0, 0, -1, 1))
        assert v.w == 1.0  # w = -z = 1 for z=-1

    def test_perspective_invalid_near(self):
        with pytest.raises(ValueError):
            Mat4.perspective(math.radians(90), 1.0, -1, 100)

    def test_perspective_invalid_far(self):
        with pytest.raises(ValueError):
            Mat4.perspective(math.radians(90), 1.0, 1, 0.5)

    def test_look_at(self):
        m = Mat4.look_at(Vec3(0, 0, 5), Vec3(0, 0, 0), Vec3(0, 1, 0))
        # Camera at (0,0,5) looking at origin — origin should map to (0,0,-5) in view space
        v = m.transform(Vec4(0, 0, 0, 1))
        assert abs(v.z + 5.0) < 1e-10

    def test_matmul_operator(self):
        m1 = Mat4.translation(1, 0, 0)
        m2 = Mat4.translation(0, 2, 0)
        m = m1 @ m2
        v = m.transform(Vec4(0, 0, 0, 1))
        assert v.x == 1.0 and v.y == 2.0

    def test_getitem(self):
        m = Mat4.identity()
        assert m[0] == 1.0
        assert m[5] == 1.0
        assert m[15] == 1.0

    def test_transposed(self):
        m = Mat4([1, 2, 3, 4,
                   5, 6, 7, 8,
                   9, 10, 11, 12,
                   13, 14, 15, 16])
        t = m.transposed()
        assert t[1] == 5.0  # m[4] was 5, now at position 1
        assert t[4] == 2.0  # m[1] was 2, now at position 4

    def test_invalid_length(self):
        with pytest.raises(ValueError):
            Mat4([1, 2, 3])


class TestBarycentric:
    def test_centroid(self):
        # Centroid of a triangle is at (1/3, 1/3, 1/3)
        u, v, w = barycentric(0, 0, 0, 0, 2, 0, 1, 2)
        assert abs(u + v + w - 1.0) < 1e-10

    def test_vertex_a(self):
        u, v, w = barycentric(0, 0, 0, 0, 2, 0, 1, 2)
        assert abs(u - 1.0) < 1e-10

    def test_vertex_b(self):
        u, v, w = barycentric(2, 0, 0, 0, 2, 0, 1, 2)
        assert abs(v - 1.0) < 1e-10

    def test_vertex_c(self):
        u, v, w = barycentric(1, 2, 0, 0, 2, 0, 1, 2)
        assert abs(w - 1.0) < 1e-10

    def test_degenerate(self):
        # Degenerate triangle (all points the same)
        u, v, w = barycentric(0, 0, 0, 0, 0, 0, 0, 0)
        assert u == 0.0 and v == 0.0 and w == 0.0