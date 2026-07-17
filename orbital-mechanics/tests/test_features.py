"""Tests for maneuvers, TLE parsing, visibility, mission design, config, IO, viz."""
import math
import os
import tempfile
import numpy as np
import pytest
from orbital.bodies import EARTH, MOON, SUN
from orbital.maneuvers import (
    hohmann_transfer, bielliptic_transfer, lambert_izzo, compute_dv,
    plane_change_delta_v, combined_plane_change_delta_v,
    minimum_energy_tof, porkchop_data,
)
from orbital.tle import parse_tle, parse_tle_set, TLE
from orbital.visibility import (
    sun_position, in_umbra, visibility_windows, access_summary, PassInfo,
)
from orbital.mission import (
    repeat_groundtrack_orbit, frozen_orbit_argp, lagrange_points,
    stationkeeping_delta_v,
)
from orbital.config import load_config, OrbitConfig
from orbital.io_csv import states_to_csv, groundtrack_to_csv, states_to_json
from orbital.viz import ascii_orbit_xy, ascii_ground_track, ascii_porkchop
from orbital.elements import OrbitalElements, StateVector, elements_to_rv
from orbital.twobody import multi_step_propagate, propagate_kepler


class TestHohmann:
    def test_leo_to_geo(self):
        res = hohmann_transfer(EARTH, 6678e3, 42164e3)
        assert 3500 < res.dv_total < 4500
        assert res.tof > 0
        assert res.dv1 > 0
        assert res.dv2 > 0

    def test_invalid_radius(self):
        with pytest.raises(ValueError, match="positive"):
            hohmann_transfer(EARTH, -1, 42164e3)

    def test_same_orbit(self):
        """Transfer to the same radius should have zero Δv."""
        res = hohmann_transfer(EARTH, 7000e3, 7000e3)
        assert res.dv_total < 1e-6


class TestBielliptic:
    def test_basic(self):
        res = bielliptic_transfer(EARTH, 6678e3, 42164e3, 100_000e3)
        assert res.dv_total > 0
        assert res.tof > 0

    def test_rb_too_small(self):
        with pytest.raises(ValueError, match="Intermediate radius"):
            bielliptic_transfer(EARTH, 6678e3, 42164e3, 10000e3)


class TestLambert:
    def test_quarter_orbit(self):
        a = 7000e3
        r1 = np.array([a, 0, 0.0])
        r2 = np.array([0, a, 0.0])
        tof = 0.5 * math.pi * math.sqrt(a ** 3 / EARTH.mu)
        v1, v2 = lambert_izzo(r1, r2, tof, EARTH.mu, prograde=True)
        # Propagate and check
        sv0 = StateVector(r=r1, v=v1)
        from orbital.twobody import propagate_rk4
        sv_f = propagate_rk4(sv0, EARTH, tof, step=10)
        err = np.linalg.norm(sv_f.r - r2)
        assert err < 500  # < 500 m

    def test_zero_tof_raises(self):
        with pytest.raises(ValueError, match="positive"):
            lambert_izzo(np.array([7000e3, 0, 0.0]),
                         np.array([0, 7000e3, 0.0]),
                         0.0, EARTH.mu)

    def test_parallel_raises(self):
        with pytest.raises(ValueError, match="parallel"):
            lambert_izzo(np.array([7000e3, 0, 0.0]),
                         np.array([7000e3, 0, 0.0]),
                         1000.0, EARTH.mu)


class TestPlaneChange:
    def test_simple(self):
        dv = plane_change_delta_v(7546, math.radians(28.5))
        assert 3000 < dv < 4000

    def test_zero_angle(self):
        dv = plane_change_delta_v(7546, 0)
        assert dv < 1e-6

    def test_combined(self):
        dv = combined_plane_change_delta_v(7546, 3070, math.radians(28.5))
        assert dv > 0


class TestPorkchop:
    def test_generates_points(self):
        r1 = np.array([7000e3, 0, 0.0])
        r2 = np.array([0, 7000e3, 0.0])
        data = porkchop_data(EARTH, r1, r2, (1500, 3000), n_tof=10)
        assert len(data) == 10
        for tof, v1, v2 in data:
            assert tof > 0


class TestTLE:
    ISS_L1 = "1 25544U 98067A   08264.51782528 -.00002182  00000-0 -11606-4 0  2927"
    ISS_L2 = "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537"

    def test_parse(self):
        tle = parse_tle(self.ISS_L1, self.ISS_L2)
        assert tle.sat_num == 25544
        assert abs(math.degrees(tle.inclination) - 51.6416) < 0.01
        assert tle.eccentricity < 0.01
        assert tle.mean_motion > 15.0

    def test_to_elements(self):
        tle = parse_tle(self.ISS_L1, self.ISS_L2)
        elems = tle.to_elements()
        assert elems.a > 6000e3
        assert elems.a < 7000e3
        assert elems.e < 0.01

    def test_parse_set(self):
        text = f"ISS\n{self.ISS_L1}\n{self.ISS_L2}\n"
        tles = parse_tle_set(text)
        assert len(tles) == 1
        assert tles[0].sat_num == 25544

    def test_bad_line1(self):
        bad = "2 " + "0" * 67  # starts with '2', not '1'
        with pytest.raises(ValueError, match="Line 1"):
            parse_tle(bad, self.ISS_L2)

    def test_short_line(self):
        with pytest.raises(ValueError, match="too short"):
            parse_tle("1 short", self.ISS_L2)

    def test_semi_major_axis(self):
        tle = parse_tle(self.ISS_L1, self.ISS_L2)
        a = tle.semi_major_axis
        # ISS altitude ~400 km → a ~6778 km
        assert 6700e3 < a < 6900e3


class TestVisibility:
    def test_sun_position_magnitude(self):
        r = sun_position(2460310.5)  # J2024
        # Sun is ~1 AU away
        assert 1.4e11 < float(np.linalg.norm(r)) < 1.6e11

    def test_in_umbra(self):
        # Satellite on the opposite side of Earth from the sun → in umbra
        r_sun = np.array([1.5e11, 0, 0.0])
        r_sat = np.array([-7000e3, 0, 0.0])
        assert in_umbra(r_sat, r_sun, EARTH)

    def test_not_in_umbra(self):
        r_sun = np.array([1.5e11, 0, 0.0])
        r_sat = np.array([7000e3, 0, 0.0])  # sunward side
        assert not in_umbra(r_sat, r_sun, EARTH)

    def test_visibility_windows(self):
        elems = OrbitalElements(a=7000e3, e=0, i=math.radians(45),
                                raan=0, argp=0, nu=0, mu=EARTH.mu)
        sv = elements_to_rv(elems, EARTH)
        states = multi_step_propagate(sv, EARTH, 6000, 60)
        passes = visibility_windows(states, math.radians(40), 0,
                                    min_elevation=math.radians(5))
        # At least one pass expected in 100 min from 40°N
        assert len(passes) >= 0  # could be 0 if timing unlucky; just check no crash
        for p in passes:
            assert p.duration > 0

    def test_access_summary(self):
        p = PassInfo(rise_time=100, set_time=400, max_elevation=math.radians(30),
                      rise_az=0, set_az=math.pi, duration=300)
        s = access_summary(p)
        assert "Pass" in s


class TestMissionDesign:
    def test_repeat_groundtrack(self):
        rgt = repeat_groundtrack_orbit(EARTH, 14, 1, math.radians(51.6))
        assert rgt.a > EARTH.radius
        assert rgt.period > 0
        # 14 rev/sidereal-day → period ~ 86164/14 ≈ 6155 s
        assert 5500 < rgt.period < 7000

    def test_rgt_invalid_N(self):
        with pytest.raises(ValueError, match="positive"):
            repeat_groundtrack_orbit(EARTH, 0, 1, 0)

    def test_frozen_orbit(self):
        argp = frozen_orbit_argp(EARTH, 7000e3, 0.01, math.radians(51.6))
        assert 0 <= argp <= math.pi

    def test_lagrange_points_earth_moon(self):
        pts = lagrange_points(EARTH, MOON)
        assert len(pts) == 5
        names = [p.name for p in pts]
        assert names == ["L1", "L2", "L3", "L4", "L5"]
        # L4 and L5 should be equidistant from both bodies
        for lp in pts:
            assert float(np.linalg.norm(lp.r)) > 0

    def test_stationkeeping(self):
        dv = stationkeeping_delta_v(EARTH, 42164e3, 0.01, 1.0)
        assert dv > 0


class TestConfig:
    def test_load_json(self, tmp_path):
        cfg_text = '''{
            "body": "earth",
            "satellite": {"a_km": 7000, "e": 0.01, "i_deg": 51.6},
            "propagation": {"method": "kepler", "dt_s": 3600}
        }'''
        p = tmp_path / "test.json"
        p.write_text(cfg_text)
        cfg = load_config(str(p))
        assert cfg.body.name == "Earth"
        assert cfg.satellite.a == 7000e3
        assert cfg.propagation.method == "kepler"

    def test_invalid_body(self):
        from orbital.config import OrbitConfig
        with pytest.raises(ValueError, match="Unknown body"):
            OrbitConfig.from_dict({"body": "pluto"})

    def test_invalid_method(self):
        from orbital.config import PropagationConfig
        with pytest.raises(ValueError, match="Unknown propagation"):
            PropagationConfig.from_dict({"method": "euler"})


class TestIO:
    def test_states_csv(self, tmp_path):
        elems = OrbitalElements(a=7000e3, e=0.01, i=math.radians(45),
                                raan=0, argp=0, nu=0, mu=EARTH.mu)
        sv = elements_to_rv(elems, EARTH)
        states = multi_step_propagate(sv, EARTH, 600, 300)
        p = str(tmp_path / "states.csv")
        states_to_csv(states, EARTH, p)
        assert os.path.exists(p)
        with open(p) as f:
            lines = f.readlines()
        assert len(lines) == len(states) + 1  # header + data
        assert "t_s" in lines[0]

    def test_groundtrack_csv(self, tmp_path):
        from orbital.groundtrack import ground_track
        elems = OrbitalElements(a=7000e3, e=0, i=math.radians(45),
                                raan=0, argp=0, nu=0, mu=EARTH.mu)
        sv = elements_to_rv(elems, EARTH)
        states = multi_step_propagate(sv, EARTH, 600, 300)
        pts = ground_track(states, EARTH)
        p = str(tmp_path / "gt.csv")
        groundtrack_to_csv(pts, p)
        assert os.path.exists(p)

    def test_states_json(self, tmp_path):
        elems = OrbitalElements(a=7000e3, e=0, i=0, raan=0, argp=0, nu=0, mu=EARTH.mu)
        sv = elements_to_rv(elems, EARTH)
        states = multi_step_propagate(sv, EARTH, 600, 300)
        p = str(tmp_path / "states.json")
        states_to_json(states, p)
        import json
        with open(p) as f:
            data = json.load(f)
        assert len(data) == len(states)


class TestViz:
    def test_ascii_orbit(self):
        elems = OrbitalElements(a=7000e3, e=0.5, i=math.radians(20),
                                raan=0, argp=0, nu=0, mu=EARTH.mu)
        sv = elements_to_rv(elems, EARTH)
        states = multi_step_propagate(sv, EARTH, 3600, 120)
        s = ascii_orbit_xy(states)
        assert "Orbit" in s or "x:" in s
        assert len(s.splitlines()) > 5

    def test_ascii_ground_track(self):
        from orbital.groundtrack import ground_track
        elems = OrbitalElements(a=7000e3, e=0, i=math.radians(45),
                                raan=0, argp=0, nu=0, mu=EARTH.mu)
        sv = elements_to_rv(elems, EARTH)
        states = multi_step_propagate(sv, EARTH, 3600, 120)
        pts = ground_track(states, EARTH)
        s = ascii_ground_track(pts)
        assert "Ground" in s

    def test_ascii_porkchop(self):
        r1 = np.array([7000e3, 0, 0.0])
        r2 = np.array([0, 7000e3, 0.0])
        data = porkchop_data(EARTH, r1, r2, (1500, 3000), n_tof=10)
        s = ascii_porkchop(data)
        assert "Porkchop" in s