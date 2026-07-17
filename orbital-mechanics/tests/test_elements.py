"""Tests for orbital element conversions."""
import math
import numpy as np
import pytest
from orbital.elements import (
    OrbitalElements, StateVector, rv_to_elements, elements_to_rv,
    true_to_eccentric, eccentric_to_true, true_to_mean, mean_to_true,
)
from orbital.bodies import EARTH


class TestStateVector:
    def test_construction(self):
        sv = StateVector(r=[7000e3, 0, 0], v=[0, 7500, 0])
        assert sv.r.shape == (3,)
        assert sv.v.shape == (3,)
        assert sv.t == 0.0

    def test_speed(self):
        sv = StateVector(r=[0, 0, 0], v=[3, 4, 0])
        assert abs(sv.speed - 5.0) < 1e-12

    def test_radius(self):
        sv = StateVector(r=[3, 4, 0], v=[0, 0, 0])
        assert abs(sv.radius - 5.0) < 1e-12

    def test_copy(self):
        sv = StateVector(r=[1, 2, 3], v=[4, 5, 6], t=10)
        sv2 = sv.copy()
        sv2.r[0] = 999
        assert sv.r[0] == 1  # original unchanged

    def test_equality(self):
        sv1 = StateVector(r=[1, 2, 3], v=[4, 5, 6])
        sv2 = StateVector(r=[1, 2, 3], v=[4, 5, 6])
        assert sv1 == sv2

    def test_inequality(self):
        sv1 = StateVector(r=[1, 2, 3], v=[4, 5, 6])
        sv2 = StateVector(r=[1, 2, 3], v=[4, 5, 99])
        assert sv1 != sv2

    def test_repr(self):
        sv = StateVector(r=[1, 2, 3], v=[4, 5, 6])
        assert "StateVector" in repr(sv)


class TestOrbitalElements:
    def test_elliptic(self):
        e = OrbitalElements(a=7000e3, e=0.1, i=0, raan=0, argp=0, nu=0)
        assert e.is_elliptic
        assert not e.is_hyperbolic
        assert not e.is_parabolic
        assert e.orbit_type == "elliptic"

    def test_hyperbolic(self):
        e = OrbitalElements(a=-10e6, e=1.5, i=0, raan=0, argp=0, nu=0)
        assert e.is_hyperbolic
        assert e.orbit_type == "hyperbolic"

    def test_parabolic(self):
        e = OrbitalElements(a=float("inf"), e=1.0, i=0, raan=0, argp=0, nu=0)
        assert e.is_parabolic
        assert e.orbit_type == "parabolic"

    def test_circular(self):
        e = OrbitalElements(a=7000e3, e=1e-10, i=0, raan=0, argp=0, nu=0)
        assert e.is_circular
        assert e.orbit_type == "circular"

    def test_period(self):
        a = 7000e3
        e = OrbitalElements(a=a, e=0, i=0, raan=0, argp=0, nu=0)
        expected = 2 * math.pi * math.sqrt(a ** 3 / EARTH.mu)
        assert abs(e.period - expected) < 1e-6

    def test_period_hyperbolic_inf(self):
        e = OrbitalElements(a=-10e6, e=1.5, i=0, raan=0, argp=0, nu=0)
        assert math.isinf(e.period)

    def test_mean_motion(self):
        a = 7000e3
        e = OrbitalElements(a=a, e=0, i=0, raan=0, argp=0, nu=0)
        expected = math.sqrt(EARTH.mu / a ** 3)
        assert abs(e.mean_motion - expected) < 1e-12

    def test_perigee_apogee(self):
        e = OrbitalElements(a=10000e3, e=0.5, i=0, raan=0, argp=0, nu=0)
        assert abs(e.perigee - 5000e3) < 1e-6
        assert abs(e.apogee - 15000e3) < 1e-6

    def test_apogee_hyperbolic(self):
        e = OrbitalElements(a=-10e6, e=1.5, i=0, raan=0, argp=0, nu=0)
        assert math.isinf(e.apogee)

    def test_energy(self):
        e = OrbitalElements(a=7000e3, e=0.1, i=0, raan=0, argp=0, nu=0)
        expected = -EARTH.mu / (2 * 7000e3)
        assert abs(e.energy - expected) < 1e-3

    def test_invalid_eccentricity(self):
        with pytest.raises(ValueError, match="Eccentricity"):
            OrbitalElements(a=7000e3, e=-0.1, i=0, raan=0, argp=0, nu=0)

    def test_invalid_a_zero(self):
        with pytest.raises(ValueError, match="Semi-major axis"):
            OrbitalElements(a=0, e=0.1, i=0, raan=0, argp=0, nu=0)

    def test_invalid_mu(self):
        with pytest.raises(ValueError, match="Gravitational"):
            OrbitalElements(a=7000e3, e=0.1, i=0, raan=0, argp=0, nu=0, mu=-1)

    def test_semi_latus_rectum(self):
        e = OrbitalElements(a=10000e3, e=0.5, i=0, raan=0, argp=0, nu=0)
        assert abs(e.p - 7500e3) < 1e-6

    def test_angular_momentum(self):
        e = OrbitalElements(a=10000e3, e=0.5, i=0, raan=0, argp=0, nu=0)
        expected = math.sqrt(EARTH.mu * e.p)
        assert abs(e.h - expected) < 1e-3


class TestConversions:
    @pytest.mark.parametrize("a_km,e,i_deg,raan_deg,argp_deg,nu_deg", [
        (7000, 0.01, 51.6, 0, 30, 45),
        (8000, 0.1, 20, 45, 60, 90),
        (7000, 0.0, 0, 0, 0, 0),     # circular equatorial
        (7000, 0.5, 90, 180, 270, 180),  # polar
    ])
    def test_roundtrip(self, a_km, e, i_deg, raan_deg, argp_deg, nu_deg):
        elems = OrbitalElements(
            a=a_km * 1000, e=e, i=math.radians(i_deg),
            raan=math.radians(raan_deg), argp=math.radians(argp_deg),
            nu=math.radians(nu_deg), mu=EARTH.mu,
        )
        sv = elements_to_rv(elems, EARTH)
        elems2 = rv_to_elements(sv, EARTH)
        assert abs(elems2.a - elems.a) / abs(elems.a) < 1e-6
        assert abs(elems2.e - elems.e) < 1e-6
        for attr in ["i", "raan", "argp", "nu"]:
            v1 = getattr(elems, attr)
            v2 = getattr(elems2, attr)
            diff = math.atan2(math.sin(v1 - v2), math.cos(v1 - v2))
            assert abs(diff) < 1e-6, f"{attr}: diff={diff}"

    def test_rv_to_elements_zero_position(self):
        sv = StateVector(r=[0, 0, 0], v=[0, 0, 0])
        with pytest.raises(ValueError, match="Position vector is zero"):
            rv_to_elements(sv, EARTH)

    def test_rv_to_elements_radial(self):
        """Purely radial velocity → zero angular momentum."""
        sv = StateVector(r=[7000e3, 0, 0], v=[1000, 0, 0])
        with pytest.raises(ValueError, match="Angular momentum is zero"):
            rv_to_elements(sv, EARTH)


class TestAnomalyConversions:
    @pytest.mark.parametrize("nu,e", [
        (0.5, 0.0), (0.5, 0.3), (1.0, 0.7), (2.0, 0.1),
    ])
    def test_true_eccentric_roundtrip(self, nu, e):
        E = true_to_eccentric(nu, e)
        nu2 = eccentric_to_true(E, e)
        diff = math.atan2(math.sin(nu2 - nu), math.cos(nu2 - nu))
        assert abs(diff) < 1e-10

    def test_true_mean_roundtrip_elliptic(self):
        for nu in [0.1, 0.5, 1.0, 2.0, 3.0]:
            for e in [0.0, 0.3, 0.7]:
                M = true_to_mean(nu, e)
                nu2 = mean_to_true(M, e)
                diff = math.atan2(math.sin(nu2 - nu), math.cos(nu2 - nu))
                assert abs(diff) < 1e-8

    def test_true_mean_hyperbolic(self):
        for nu in [0.1, 0.5, 1.0]:
            e = 1.5
            nu_max = math.acos(-1.0 / e)
            if abs(nu) < nu_max:
                M = true_to_mean(nu, e)
                nu2 = mean_to_true(M, e)
                diff = math.atan2(math.sin(nu2 - nu), math.cos(nu2 - nu))
                assert abs(diff) < 1e-6