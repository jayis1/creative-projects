"""Tests for 2x2 matrix utilities."""
import math
import pytest
from rigidbody.core.mat22 import Mat22, solve_2x2


class TestMat22:
    def test_identity(self):
        m = Mat22.identity()
        assert m.multiply_vec(3, 4) == (3.0, 4.0)

    def test_rotation_90(self):
        m = Mat22.rotation(math.pi / 2)
        x, y = m.multiply_vec(1, 0)
        assert abs(x) < 1e-9 and abs(y - 1.0) < 1e-9

    def test_determinant(self):
        assert Mat22(1, 2, 3, 4).determinant() == -2.0

    def test_inverse(self):
        m = Mat22(2, 0, 0, 4)
        inv = m.inverse()
        # m * inv should give identity
        x, y = inv.multiply_vec(2, 4)
        assert abs(x - 1.0) < 1e-9 and abs(y - 1.0) < 1e-9

    def test_inverse_singular(self):
        with pytest.raises(ZeroDivisionError):
            Mat22(1, 2, 2, 4).inverse()

    def test_transpose_multiply(self):
        m = Mat22(1, 2, 3, 4)
        result = m.transpose_multiply_vec(1, 1)
        assert result == (4.0, 6.0)


class TestSolve2x2:
    def test_basic(self):
        # [[2,0],[0,4]] @ (s,t) = (2, 8) => s=1, t=2
        s, t = solve_2x2(2, 0, 0, 4, 2, 8)
        assert abs(s - 1.0) < 1e-9 and abs(t - 2.0) < 1e-9

    def test_singular(self):
        with pytest.raises(ZeroDivisionError):
            solve_2x2(1, 2, 2, 4, 1, 1)