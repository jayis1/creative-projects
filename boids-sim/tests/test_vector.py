"""Tests for the Vector2 class."""

import math
import pytest
from boids.vector import Vector2


class TestVectorCreation:
    def test_default_zero(self):
        v = Vector2()
        assert v.x == 0.0
        assert v.y == 0.0

    def test_from_components(self):
        v = Vector2(3.0, 4.0)
        assert v.x == 3.0
        assert v.y == 4.0

    def test_from_angle(self):
        v = Vector2.from_angle(0, 5)
        assert abs(v.x - 5.0) < 1e-10
        assert abs(v.y - 0.0) < 1e-10

    def test_from_angle_pi(self):
        v = Vector2.from_angle(math.pi, 3)
        assert abs(v.x - (-3.0)) < 1e-10
        assert abs(v.y) < 1e-10

    def test_random_unit(self):
        v = Vector2.random_unit()
        assert abs(v.length() - 1.0) < 1e-10

    def test_random_range(self):
        v = Vector2.random(0, 10)
        assert 0 <= v.x <= 10
        assert 0 <= v.y <= 10


class TestVectorProperties:
    def test_length(self):
        v = Vector2(3, 4)
        assert v.length() == 5.0

    def test_length_sq(self):
        v = Vector2(3, 4)
        assert v.length_sq() == 25.0

    def test_length_zero(self):
        v = Vector2(0, 0)
        assert v.length() == 0.0

    def test_angle(self):
        v = Vector2(1, 0)
        assert abs(v.angle) < 1e-10

    def test_angle_90(self):
        v = Vector2(0, 1)
        assert abs(v.angle - math.pi / 2) < 1e-10

    def test_copy(self):
        v = Vector2(3, 4)
        v2 = v.copy()
        v2.x = 100
        assert v.x == 3  # original unchanged


class TestVectorInPlace:
    def test_add(self):
        v = Vector2(1, 2)
        v.add(Vector2(3, 4))
        assert v.x == 4 and v.y == 6

    def test_sub(self):
        v = Vector2(5, 7)
        v.sub(Vector2(2, 3))
        assert v.x == 3 and v.y == 4

    def test_scale(self):
        v = Vector2(2, 3)
        v.scale(2)
        assert v.x == 4 and v.y == 6

    def test_limit_below(self):
        v = Vector2(1, 0)
        v.limit(5)
        assert v.length() == 1.0

    def test_limit_above(self):
        v = Vector2(10, 0)
        v.limit(5)
        assert abs(v.length() - 5.0) < 1e-10

    def test_set_length(self):
        v = Vector2(1, 1)
        v.set_length(10)
        assert abs(v.length() - 10.0) < 1e-10

    def test_set_length_zero(self):
        v = Vector2(0, 0)
        v.set_length(5)
        assert v.x == 0 and v.y == 0

    def test_normalize(self):
        v = Vector2(3, 4)
        v.normalize()
        assert abs(v.length() - 1.0) < 1e-10

    def test_normalize_zero(self):
        v = Vector2(0, 0)
        v.normalize()
        assert v.x == 0 and v.y == 0


class TestVectorFunctional:
    def test_add_operator(self):
        v1 = Vector2(1, 2)
        v2 = Vector2(3, 4)
        v3 = v1 + v2
        assert v3.x == 4 and v3.y == 6
        assert v1.x == 1  # original unchanged

    def test_sub_operator(self):
        v1 = Vector2(5, 6)
        v2 = Vector2(1, 2)
        v3 = v1 - v2
        assert v3.x == 4 and v3.y == 4

    def test_mul_operator(self):
        v = Vector2(2, 3) * 2
        assert v.x == 4 and v.y == 6

    def test_rmul_operator(self):
        v = 2 * Vector2(2, 3)
        assert v.x == 4 and v.y == 6

    def test_truediv_operator(self):
        v = Vector2(6, 8) / 2
        assert v.x == 3 and v.y == 4

    def test_neg_operator(self):
        v = -Vector2(3, 4)
        assert v.x == -3 and v.y == -4

    def test_eq_operator(self):
        assert Vector2(3, 4) == Vector2(3, 4)

    def test_eq_different(self):
        assert Vector2(3, 4) != Vector2(3, 5)

    def test_eq_non_vector(self):
        assert Vector2(1, 1) != "not a vector"

    def test_iter(self):
        x, y = Vector2(3, 4)
        assert x == 3 and y == 4

    def test_repr(self):
        v = Vector2(1.23456, 2.78901)
        r = repr(v)
        assert "Vector2" in r


class TestVectorStatic:
    def test_dist(self):
        d = Vector2.dist(Vector2(0, 0), Vector2(3, 4))
        assert d == 5.0

    def test_dist_sq(self):
        d = Vector2.dist_sq(Vector2(0, 0), Vector2(3, 4))
        assert d == 25.0

    def test_dist_same_point(self):
        d = Vector2.dist(Vector2(5, 5), Vector2(5, 5))
        assert d == 0.0

    def test_angle_between(self):
        a = Vector2(1, 0)
        b = Vector2(0, 1)
        assert abs(Vector2.angle_between(a, b) - math.pi / 2) < 1e-10

    def test_angle_between_zero_vector(self):
        a = Vector2(0, 0)
        b = Vector2(1, 1)
        assert Vector2.angle_between(a, b) == 0.0

    def test_to_tuple(self):
        assert Vector2(3, 4).to_tuple() == (3.0, 4.0)

    def test_from_tuple(self):
        v = Vector2.from_tuple((5, 6))
        assert v.x == 5 and v.y == 6