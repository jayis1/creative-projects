"""Tests for the Vec3 vector math module."""

import math
import pytest

from mcengine.vec3 import Vec3, dot, cross, normalize, add, sub, scale


class TestVec3:
    def test_construction(self):
        v = Vec3(1.0, 2.0, 3.0)
        assert v.x == 1.0
        assert v.y == 2.0
        assert v.z == 3.0
        assert v[0] == 1.0
        assert v[1] == 2.0
        assert v[2] == 3.0

    def test_default(self):
        v = Vec3()
        assert v == (0.0, 0.0, 0.0)

    def test_addition(self):
        a = Vec3(1, 2, 3)
        b = Vec3(4, 5, 6)
        assert a + b == Vec3(5, 7, 9)

    def test_subtraction(self):
        a = Vec3(4, 5, 6)
        b = Vec3(1, 2, 3)
        assert a - b == Vec3(3, 3, 3)

    def test_scalar_mult(self):
        v = Vec3(1, 2, 3)
        assert v * 2 == Vec3(2, 4, 6)
        assert 2 * v == Vec3(2, 4, 6)

    def test_division(self):
        v = Vec3(2, 4, 6)
        assert v / 2 == Vec3(1, 2, 3)

    def test_negation(self):
        v = Vec3(1, -2, 3)
        assert -v == Vec3(-1, 2, -3)

    def test_dot(self):
        a = Vec3(1, 0, 0)
        b = Vec3(0, 1, 0)
        assert a.dot(b) == 0.0
        assert a.dot(a) == 1.0

    def test_length(self):
        v = Vec3(3, 4, 0)
        assert v.length() == pytest.approx(5.0)
        assert v.length_sq() == pytest.approx(25.0)

    def test_normalized(self):
        v = Vec3(3, 4, 0)
        n = v.normalized()
        assert n.length() == pytest.approx(1.0)

    def test_normalized_zero(self):
        v = Vec3(0, 0, 0)
        n = v.normalized()
        assert n == Vec3(0, 0, 0)


class TestFreeFunctions:
    def test_dot(self):
        assert dot((1, 0, 0), (1, 0, 0)) == 1.0
        assert dot((1, 0, 0), (0, 1, 0)) == 0.0

    def test_cross(self):
        result = cross((1, 0, 0), (0, 1, 0))
        assert result == Vec3(0, 0, 1)

    def test_cross_anti_commutative(self):
        a = (1, 0, 0)
        b = (0, 1, 0)
        assert cross(a, b) == -cross(b, a)

    def test_normalize(self):
        n = normalize((3, 4, 0))
        assert n.length() == pytest.approx(1.0)

    def test_normalize_zero(self):
        n = normalize((0, 0, 0))
        assert n == Vec3(0, 0, 0)

    def test_add(self):
        assert add((1, 2, 3), (4, 5, 6)) == Vec3(5, 7, 9)

    def test_sub(self):
        assert sub((4, 5, 6), (1, 2, 3)) == Vec3(3, 3, 3)

    def test_scale(self):
        assert scale((1, 2, 3), 2) == Vec3(2, 4, 6)