"""Tests for the 2D vector class."""
import math
import pytest
from rigidbody.core.vec2 import Vec2


class TestVec2Construction:
    def test_default(self):
        v = Vec2()
        assert v.x == 0.0 and v.y == 0.0

    def test_from_coords(self):
        v = Vec2(3.0, 4.0)
        assert v.x == 3.0 and v.y == 4.0

    def test_zero(self):
        assert Vec2.zero() == Vec2(0.0, 0.0)

    def test_from_angle(self):
        v = Vec2.from_angle(0.0, 5.0)
        assert v.almost_eq(Vec2(5.0, 0.0))

    def test_from_angle_90(self):
        v = Vec2.from_angle(math.pi / 2, 2.0)
        assert v.almost_eq(Vec2(0.0, 2.0))


class TestVec2Arithmetic:
    def test_add(self):
        assert Vec2(1, 2) + Vec2(3, 4) == Vec2(4, 6)

    def test_sub(self):
        assert Vec2(5, 6) - Vec2(2, 3) == Vec2(3, 3)

    def test_mul(self):
        assert Vec2(1, 2) * 3 == Vec2(3, 6)

    def test_rmul(self):
        assert 3 * Vec2(1, 2) == Vec2(3, 6)

    def test_div(self):
        assert Vec2(6, 8) / 2 == Vec2(3, 4)

    def test_div_by_zero(self):
        with pytest.raises(ZeroDivisionError):
            Vec2(1, 2) / 0

    def test_neg(self):
        assert -Vec2(1, -2) == Vec2(-1, 2)


class TestVec2Products:
    def test_dot(self):
        assert Vec2(1, 2).dot(Vec2(3, 4)) == 11

    def test_cross(self):
        assert Vec2(1, 0).cross(Vec2(0, 1)) == 1
        assert Vec2(0, 1).cross(Vec2(1, 0)) == -1

    def test_cross_scalar(self):
        v = Vec2(1, 2)
        result = v.cross_scalar(3.0)
        assert result.almost_eq(Vec2(-6.0, 3.0))


class TestVec2Geometry:
    def test_length(self):
        assert Vec2(3, 4).length() == 5.0

    def test_length_sq(self):
        assert Vec2(3, 4).length_sq() == 25.0

    def test_normalize(self):
        assert Vec2(3, 4).normalize().almost_eq(Vec2(0.6, 0.8))

    def test_normalize_zero(self):
        assert Vec2(0, 0).normalize() == Vec2(0, 0)

    def test_perpendicular(self):
        assert Vec2(1, 0).perpendicular() == Vec2(0, 1)

    def test_rotate(self):
        v = Vec2(1, 0).rotate(math.pi / 2)
        assert v.almost_eq(Vec2(0, 1))

    def test_angle(self):
        assert Vec2(1, 0).angle() == 0.0
        assert abs(Vec2(0, 1).angle() - math.pi / 2) < 1e-9


class TestVec2Comparison:
    def test_eq(self):
        assert Vec2(1, 2) == Vec2(1, 2)

    def test_neq(self):
        assert Vec2(1, 2) != Vec2(2, 1)

    def test_eq_wrong_type(self):
        assert (Vec2(1, 2) == "foo") is False

    def test_almost_eq(self):
        assert Vec2(1, 1).almost_eq(Vec2(1 + 1e-12, 1 - 1e-12))

    def test_hash(self):
        assert hash(Vec2(1, 2)) == hash(Vec2(1, 2))


class TestVec2Iter:
    def test_iter(self):
        assert list(Vec2(3, 4)) == [3.0, 4.0]

    def test_to_tuple(self):
        assert Vec2(3, 4).to_tuple() == (3.0, 4.0)

    def test_repr(self):
        assert "Vec2" in repr(Vec2(1, 2))