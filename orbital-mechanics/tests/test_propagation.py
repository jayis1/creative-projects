"""Tests for orbit propagators."""
import math
import numpy as np
import pytest
from orbital.twobody import (
    propagate_kepler, propagate_rk4, propagate_cowell,
    propagate_universal, propagate_j2_secular, multi_step_propagate,
)
from orbital.adaptive import propagate_rkf45, propagate_bs
from orbital.elements import OrbitalElements, StateVector, elements_to_rv, rv_to_elements
from orbital.bodies import EARTH
from orbital.perturbations import j2_acceleration, drag_acceleration


def make_orbit(a=7000e3, e=0.1, i_deg=20, raan=0, argp=0, nu=0):
    elems = OrbitalElements(a=a, e=e, i=math.radians(i_deg),
                            raan=raan, argp=argp, nu=nu, mu=EARTH.mu)
    return elements_to_rv(elems, EARTH)


class TestPropagateKepler:
    def test_one_period_returns(self):
        """After one orbital period, the satellite should return to start."""
        sv = make_orbit(a=7000e3, e=0.1)
        T = 2 * math.pi * math.sqrt(7000e3 ** 3 / EARTH.mu)
        sv2 = propagate_kepler(sv, EARTH, T)
        err = np.linalg.norm(sv.r - sv2.r)
        assert err < 1.0  # < 1 metre

    def test_backward_propagation(self):
        sv = make_orbit()
        sv_f = propagate_kepler(sv, EARTH, 1800)
        sv_b = propagate_kepler(sv_f, EARTH, -1800)
        err = np.linalg.norm(sv.r - sv_b.r)
        assert err < 1e-3

    def test_hyperbolic(self):
        elems = OrbitalElements(a=-10e6, e=1.5, i=0, raan=0, argp=0,
                                nu=math.radians(30), mu=EARTH.mu)
        sv = elements_to_rv(elems, EARTH)
        sv2 = propagate_kepler(sv, EARTH, 600)
        elems2 = rv_to_elements(sv2, EARTH)
        assert elems2.e > 1.0

    def test_parabolic_raises(self):
        # Parabolic orbit: e=1 with finite periapsis distance stored in `a`.
        elems = OrbitalElements(a=7000e3, e=1.0, i=0, raan=0, argp=0,
                                nu=math.radians(30), mu=EARTH.mu)
        sv = elements_to_rv(elems, EARTH)
        # rv_to_elements reconstructs e≈1; propagate_kepler should reject it.
        elems2 = rv_to_elements(sv, EARTH)
        assert elems2.is_parabolic or abs(elems2.e - 1.0) < 1e-6
        with pytest.raises(ValueError, match="parabolic"):
            propagate_kepler(sv, EARTH, 100)


class TestPropagateRK4:
    def test_matches_kepler(self):
        sv = make_orbit(a=7000e3, e=0.1)
        dt = 1800
        sv_k = propagate_kepler(sv, EARTH, dt)
        sv_r = propagate_rk4(sv, EARTH, dt, step=30)
        err = np.linalg.norm(sv_k.r - sv_r.r)
        assert err < 1000  # < 1 km with 30s steps

    def test_with_perturbation(self):
        sv = make_orbit(a=7000e3, e=0.01, i_deg=51.6)
        sv_j2 = propagate_cowell(sv, EARTH, 3600, step=30,
                                 extra_accel=lambda r, v, t: j2_acceleration(r, EARTH))
        # Should not diverge wildly in 1 hour
        assert np.linalg.norm(sv_j2.r) > 6000e3
        assert np.linalg.norm(sv_j2.r) < 8000e3

    def test_zero_dt(self):
        sv = make_orbit()
        sv2 = propagate_rk4(sv, EARTH, 0, step=60)
        assert np.allclose(sv.r, sv2.r)


class TestPropagateUniversal:
    def test_elliptic_matches_kepler(self):
        sv = make_orbit(a=7000e3, e=0.1)
        dt = 1800
        sv_k = propagate_kepler(sv, EARTH, dt)
        sv_u = propagate_universal(sv, EARTH, dt)
        err = np.linalg.norm(sv_k.r - sv_u.r)
        assert err < 100

    def test_hyperbolic(self):
        elems = OrbitalElements(a=-10e6, e=1.5, i=0, raan=0, argp=0,
                                nu=math.radians(30), mu=EARTH.mu)
        sv = elements_to_rv(elems, EARTH)
        sv_u = propagate_universal(sv, EARTH, 600)
        elems2 = rv_to_elements(sv_u, EARTH)
        assert elems2.e > 1.0


class TestPropagateJ2Secular:
    def test_raan_drift(self):
        sv = make_orbit(a=7000e3, e=0.01, i_deg=51.6)
        sv_j2 = propagate_j2_secular(sv, EARTH, 86400)
        elems = rv_to_elements(sv_j2, EARTH)
        raan_drift = math.degrees(elems.raan)
        while raan_drift > 180:
            raan_drift -= 360
        while raan_drift < -180:
            raan_drift += 360
        # ISS-like RAAN drift ~ -4.5°/day
        assert raan_drift < 0
        assert abs(raan_drift) > 0.1

    def test_raan_drift_sun_synchronous(self):
        """Sun-synchronous orbits (~98°) should have positive RAAN drift."""
        sv = make_orbit(a=7078e3, e=0.001, i_deg=98)
        sv_j2 = propagate_j2_secular(sv, EARTH, 86400)
        elems = rv_to_elements(sv_j2, EARTH)
        raan_drift = math.degrees(elems.raan)
        while raan_drift > 180:
            raan_drift -= 360
        while raan_drift < -180:
            raan_drift += 360
        # SSO: RAAN drifts eastward ~+0.9856°/day
        assert raan_drift > 0

    def test_non_elliptic_raises(self):
        elems = OrbitalElements(a=-10e6, e=1.5, i=0, raan=0, argp=0,
                                nu=math.radians(30), mu=EARTH.mu)
        sv = elements_to_rv(elems, EARTH)
        with pytest.raises(ValueError, match="elliptic"):
            propagate_j2_secular(sv, EARTH, 100)


class TestMultiStep:
    def test_length(self):
        sv = make_orbit()
        states = multi_step_propagate(sv, EARTH, 3600, 600)
        assert len(states) == 7  # 0, 600, 1200, ..., 3600

    def test_times(self):
        sv = make_orbit()
        states = multi_step_propagate(sv, EARTH, 3600, 600)
        for k, s in enumerate(states):
            assert abs(s.t - k * 600) < 1e-9

    def test_all_state_vectors(self):
        sv = make_orbit()
        states = multi_step_propagate(sv, EARTH, 3600, 600)
        assert all(isinstance(s, StateVector) for s in states)


class TestRKF45:
    def test_matches_kepler_elliptic(self):
        sv = make_orbit(a=7000e3, e=0.1)
        dt = 3600
        sv_k = propagate_kepler(sv, EARTH, dt)
        sv_a = propagate_rkf45(sv, EARTH, dt, rtol=1e-10)
        err = np.linalg.norm(sv_k.r - sv_a.r)
        assert err < 10  # < 10 m with high tolerance

    def test_long_propagation(self):
        sv = make_orbit(a=7000e3, e=0.01)
        dt = 86400  # 1 day
        sv_a = propagate_rkf45(sv, EARTH, dt)
        # Energy should be approximately conserved (two-body).
        e0 = np.linalg.norm(sv.v) ** 2 / 2 - EARTH.mu / np.linalg.norm(sv.r)
        e1 = np.linalg.norm(sv_a.v) ** 2 / 2 - EARTH.mu / np.linalg.norm(sv_a.r)
        assert abs(e0 - e1) / abs(e0) < 1e-6


class TestBulirschStoer:
    def test_matches_kepler(self):
        sv = make_orbit(a=7000e3, e=0.1)
        dt = 3600
        sv_k = propagate_kepler(sv, EARTH, dt)
        sv_bs = propagate_bs(sv, EARTH, dt, rtol=1e-10)
        err = np.linalg.norm(sv_k.r - sv_bs.r)
        # BS with a modest sequence should get within ~1 km for 1 hour.
        assert err < 2000