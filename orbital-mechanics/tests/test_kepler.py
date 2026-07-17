"""Tests for Kepler equation solvers."""
import math
import pytest
from orbital.kepler import (
    solve_kepler_e, solve_kepler_h, solve_kepler_barker,
    solve_universal_kepler, stumpff_functions, _mikkola_starter,
)


class TestKeplerE:
    def test_zero_mean_anomaly(self):
        assert abs(solve_kepler_e(0.0, 0.5)) < 1e-12

    def test_pi_mean_anomaly(self):
        assert abs(solve_kepler_e(math.pi, 0.5) - math.pi) < 1e-12

    @pytest.mark.parametrize("M", [0.3, 1.0, 2.0, -0.7, 3.0, -3.0, 5.0])
    @pytest.mark.parametrize("e", [0.0, 0.3, 0.7, 0.95])
    def test_roundtrip(self, M, e):
        E = solve_kepler_e(M, e)
        M_back = E - e * math.sin(E)
        diff = math.atan2(math.sin(M_back - M), math.cos(M_back - M))
        assert abs(diff) < 1e-9, f"Failed M={M} e={e}: diff={diff}"

    def test_high_eccentricity(self):
        """e=0.999 should still converge."""
        E = solve_kepler_e(1.0, 0.999)
        M_back = E - 0.999 * math.sin(E)
        assert abs(M_back - 1.0) < 1e-9

    def test_invalid_eccentricity_negative(self):
        with pytest.raises(ValueError, match="0 <= e < 1"):
            solve_kepler_e(0.5, -0.1)

    def test_invalid_eccentricity_hyperbolic(self):
        with pytest.raises(ValueError, match="0 <= e < 1"):
            solve_kepler_e(0.5, 1.5)

    def test_nan_eccentricity(self):
        with pytest.raises(ValueError, match="NaN"):
            solve_kepler_e(0.5, float("nan"))

    def test_wrapping(self):
        """M outside [-pi, pi] should be wrapped."""
        E1 = solve_kepler_e(0.5, 0.3)
        E2 = solve_kepler_e(0.5 + 2 * math.pi, 0.3)
        assert abs(E1 - E2) < 1e-10


class TestKeplerH:
    @pytest.mark.parametrize("M", [0.5, 1.0, 2.0, -1.0, 5.0])
    @pytest.mark.parametrize("e", [1.2, 2.0, 5.0])
    def test_roundtrip(self, M, e):
        H = solve_kepler_h(M, e)
        M_back = e * math.sinh(H) - H
        assert abs(M_back - M) < 1e-9

    def test_invalid_e_elliptic(self):
        with pytest.raises(ValueError, match="e > 1"):
            solve_kepler_h(0.5, 0.5)

    def test_invalid_e_parabolic(self):
        with pytest.raises(ValueError, match="e > 1"):
            solve_kepler_h(0.5, 1.0)


class TestBarker:
    @pytest.mark.parametrize("M", [0.1, 1.0, -1.0, 5.0, -5.0, 100.0])
    def test_roundtrip(self, M):
        D = solve_kepler_barker(0.0, M)
        M_back = D + D ** 3 / 3.0
        assert abs(M_back - M) < 1e-9

    def test_zero(self):
        D = solve_kepler_barker(0.0, 0.0)
        assert abs(D) < 1e-15


class TestStumpff:
    def test_zero(self):
        c0, c1, c2 = stumpff_functions(0.0)
        assert abs(c0 - 0.5) < 1e-15
        assert abs(c1 - 1.0 / 6.0) < 1e-15
        assert abs(c2 - 0.5) < 1e-15

    def test_positive(self):
        c0, c1, c2 = stumpff_functions(1.0)
        assert c0 > 0
        assert c1 > 0

    def test_negative(self):
        c0, c1, c2 = stumpff_functions(-1.0)
        assert c0 > 0

    def test_consistency_c0_c2(self):
        """c0 and c2 should be equal (both are C2 in this implementation)."""
        for z in [0.5, 1.0, -0.5, -1.0]:
            c0, c1, c2 = stumpff_functions(z)
            assert abs(c0 - c2) < 1e-15


class TestMikkolaStarter:
    def test_returns_finite(self):
        E = _mikkola_starter(1.0, 0.9)
        assert math.isfinite(E)

    def test_sign_matches_M(self):
        assert _mikkola_starter(1.0, 0.9) > 0
        assert _mikkola_starter(-1.0, 0.9) < 0


class TestUniversalKepler:
    def test_invalid_mu(self):
        with pytest.raises(ValueError, match="mu must be positive"):
            solve_universal_kepler(0, 7000e3, 0, 7000e3, 100)

    def test_invalid_r0(self):
        with pytest.raises(ValueError, match="r0 must be positive"):
            solve_universal_kepler(3.986e14, 0, 0, 7000e3, 100)