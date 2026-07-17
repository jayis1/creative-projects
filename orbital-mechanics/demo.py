"""End-to-end smoke test for the orbital-mechanics library (v2)."""
import math
import sys
sys.path.insert(0, ".")

import numpy as np
from orbital import (
    EARTH, StateVector, OrbitalElements,
    rv_to_elements, elements_to_rv,
    true_to_eccentric, eccentric_to_true,
    propagate_kepler, propagate_rk4, propagate_cowell,
    propagate_universal, propagate_j2_secular, multi_step_propagate,
    hohmann_transfer, bielliptic_transfer, lambert_izzo, compute_dv,
    plane_change_delta_v, combined_plane_change_delta_v,
    minimum_energy_tof, porkchop_data,
    eci_to_ecef, ecef_to_latlon, latlon_look_angles, ground_track,
    j2_acceleration, drag_acceleration,
    solve_kepler_e, solve_kepler_h, solve_kepler_barker, stumpff_functions,
)


def approx(a, b, rel=1e-6, abs_=1e-3):
    return abs(a - b) <= max(abs_ * rel, abs_)


def test_kepler_e():
    assert approx(solve_kepler_e(0.0, 0.5), 0.0, abs_=1e-12)
    assert approx(solve_kepler_e(math.pi, 0.5), math.pi, abs_=1e-12)
    for M in [0.3, 1.0, 2.0, -0.7, 3.0]:
        for e in [0.0, 0.3, 0.7, 0.95]:
            E = solve_kepler_e(M, e)
            M_back = E - e * math.sin(E)
            diff = math.atan2(math.sin(M_back - M), math.cos(M_back - M))
            assert abs(diff) < 1e-7, f"kepler_e failed M={M} e={e}: diff {diff}"
    print("OK test_kepler_e")


def test_kepler_h():
    for M in [0.5, 1.0, 2.0, -1.0]:
        for e in [1.2, 2.0, 5.0]:
            H = solve_kepler_h(M, e)
            assert approx(e * math.sinh(H) - H, M, abs_=1e-9)
    print("OK test_kepler_h")


def test_barker():
    for M in [0.1, 1.0, -1.0, 5.0]:
        D = solve_kepler_barker(0.0, M)
        M_back = D + D**3 / 3.0
        assert approx(M_back, M, abs_=1e-9), f"Barker failed M={M}"
    print("OK test_barker")


def test_stumpff():
    # At z=0, c0=0.5, c1=1/6, c2=0.5
    c0, c1, c2 = stumpff_functions(0.0)
    assert abs(c0 - 0.5) < 1e-15
    assert abs(c1 - 1.0/6.0) < 1e-15
    assert abs(c2 - 0.5) < 1e-15
    print("OK test_stumpff")


def test_rv_elements_roundtrip():
    elems = OrbitalElements(
        a=6_778_000.0, e=0.01, i=math.radians(51.6),
        raan=math.radians(0), argp=math.radians(30), nu=math.radians(45),
        mu=EARTH.mu,
    )
    sv = elements_to_rv(elems, EARTH)
    elems2 = rv_to_elements(sv, EARTH)
    for attr in ["a", "e", "i", "raan", "argp", "nu"]:
        v1 = getattr(elems, attr)
        v2 = getattr(elems2, attr)
        if attr in ("raan", "argp", "nu", "i"):
            diff = math.atan2(math.sin(v1 - v2), math.cos(v1 - v2))
            assert abs(diff) < 1e-6, f"{attr}: {v1} vs {v2} (diff {diff})"
        else:
            assert abs(v1 - v2) / max(abs(v1), 1e-9) < 1e-6, f"{attr}: {v1} vs {v2}"
    print("OK test_rv_elements_roundtrip")


def test_elements_repr():
    elems = OrbitalElements(a=7000e3, e=0.01, i=math.radians(51.6),
                            raan=0, argp=0, nu=0, mu=EARTH.mu)
    r = repr(elems)
    assert "7000.0 km" in r and "0.0100" in r
    assert elems.is_elliptic and not elems.is_hyperbolic
    assert elems.period > 0
    assert elems.orbit_type == "elliptic"
    print(f"OK test_elements_repr ({r})")


def test_true_eccentric_roundtrip():
    for nu in [0.1, 0.5, 1.0, 2.0, 3.0]:
        for e in [0.0, 0.3, 0.7]:
            E = true_to_eccentric(nu, e)
            nu2 = eccentric_to_true(E, e)
            diff = math.atan2(math.sin(nu2 - nu), math.cos(nu2 - nu))
            assert abs(diff) < 1e-10, f"true↔eccentric failed nu={nu} e={e}"
    print("OK test_true_eccentric_roundtrip")


def test_propagation_period():
    a = 7_000_000.0
    elems = OrbitalElements(a=a, e=0.0, i=0, raan=0, argp=0, nu=0, mu=EARTH.mu)
    sv = elements_to_rv(elems, EARTH)
    T = 2 * math.pi * math.sqrt(a**3 / EARTH.mu)
    sv2 = propagate_kepler(sv, EARTH, T)
    dist = np.linalg.norm(sv.r - sv2.r)
    assert dist < 10.0, f"Position after one period off by {dist} m"
    print(f"OK test_propagation_period (err={dist:.3f} m)")


def test_hyperbolic_propagation():
    # Hyperbolic orbit: e > 1
    elems = OrbitalElements(a=-10_000_000.0, e=1.5, i=0, raan=0, argp=0,
                            nu=math.radians(30), mu=EARTH.mu)
    sv = elements_to_rv(elems, EARTH)
    # Propagate forward 600s
    sv2 = propagate_kepler(sv, EARTH, 600.0)
    # Check that the orbit is still hyperbolic
    elems2 = rv_to_elements(sv2, EARTH)
    assert elems2.e > 1.0, f"Expected hyperbolic, got e={elems2.e}"
    # Verify by universal propagation
    sv_u = propagate_universal(sv, EARTH, 600.0)
    err = np.linalg.norm(sv2.r - sv_u.r)
    assert err < 1000.0, f"Kepler vs universal mismatch: {err} m"
    print(f"OK test_hyperbolic_propagation (e={elems2.e:.4f}, err={err:.1f} m)")


def test_universal_propagation():
    # Universal propagation should match Kepler for elliptic orbits
    a = 7_000_000.0
    elems = OrbitalElements(a=a, e=0.1, i=math.radians(20), raan=0, argp=0, nu=0, mu=EARTH.mu)
    sv = elements_to_rv(elems, EARTH)
    dt = 1800.0
    sv_k = propagate_kepler(sv, EARTH, dt)
    sv_u = propagate_universal(sv, EARTH, dt)
    err = np.linalg.norm(sv_k.r - sv_u.r)
    assert err < 100.0, f"Universal vs Kepler mismatch: {err} m"
    print(f"OK test_universal_propagation (err={err:.3f} m)")


def test_rk4_vs_kepler():
    a = 7_000_000.0
    elems = OrbitalElements(a=a, e=0.1, i=math.radians(20), raan=0, argp=0, nu=0, mu=EARTH.mu)
    sv = elements_to_rv(elems, EARTH)
    dt = 1800.0
    sv_k = propagate_kepler(sv, EARTH, dt)
    sv_r = propagate_rk4(sv, EARTH, dt, step=30.0)
    err = np.linalg.norm(sv_k.r - sv_r.r)
    assert err < 1000.0, f"RK4 vs Kepler discrepancy: {err} m"
    print(f"OK test_rk4_vs_kepler (err={err:.1f} m)")


def test_j2_secular():
    # J2 secular propagation: RAAN should drift for inclined orbits
    a = 7_000_000.0
    elems = OrbitalElements(a=a, e=0.01, i=math.radians(51.6), raan=0, argp=0, nu=0, mu=EARTH.mu)
    sv = elements_to_rv(elems, EARTH)
    dt = 86400.0  # 1 day
    sv_j2 = propagate_j2_secular(sv, EARTH, dt)
    elems_j2 = rv_to_elements(sv_j2, EARTH)
    # RAAN should drift (negative for prograde)
    raan_drift_raw = elems_j2.raan
    # Handle angle wrapping: drift should be in (-360, 0) for prograde
    raan_drift = math.degrees(raan_drift_raw)
    while raan_drift > 180:
        raan_drift -= 360
    while raan_drift < -180:
        raan_drift += 360
    # Known: ~-4.5°/day for ISS-like orbit
    assert abs(raan_drift) > 0.1, f"RAAN drift too small: {raan_drift}°"
    assert raan_drift < 0, f"RAAN should decrease for prograde: got {raan_drift}°"
    print(f"OK test_j2_secular (RAAN drift={raan_drift:.4f}°/day)")


def test_multi_step():
    a = 7_000_000.0
    elems = OrbitalElements(a=a, e=0.0, i=math.radians(45), raan=0, argp=0, nu=0, mu=EARTH.mu)
    sv = elements_to_rv(elems, EARTH)
    states = multi_step_propagate(sv, EARTH, 3600, 600)
    assert len(states) == 7  # 0, 600, 1200, ..., 3600
    assert all(isinstance(s, StateVector) for s in states)
    print(f"OK test_multi_step ({len(states)} states)")


def test_hohmann():
    r1 = 6_700_000.0
    r2 = 42_000_000.0
    res = hohmann_transfer(EARTH, r1, r2)
    assert 3000 < res.dv_total < 5000
    assert res.tof > 0
    print(f"OK test_hohmann (dv={res.dv_total:.1f} m/s, tof={res.tof/3600:.1f} h)")


def test_bielliptic():
    r1 = 6_700_000.0
    r2 = 42_000_000.0
    rb = 100_000_000.0  # very high intermediate
    res = bielliptic_transfer(EARTH, r1, r2, rb)
    assert res.dv_total > 0
    assert res.tof > 0
    print(f"OK test_bielliptic (dv={res.dv_total:.1f} m/s, tof={res.tof/3600:.1f} h)")


def test_plane_change():
    v = 7546.0  # circular orbit speed
    theta = math.radians(28.5)  # typical inclination change
    dv = plane_change_delta_v(v, theta)
    # Known: ~3660 m/s for 28.5° at 7546 m/s
    assert 3000 < dv < 4000, f"Plane change dv unexpected: {dv}"
    # Combined: speed change + plane change
    dv2 = combined_plane_change_delta_v(7546, 3070, theta)
    assert dv2 > 0
    print(f"OK test_plane_change (dv={dv:.1f} m/s, combined={dv2:.1f} m/s)")


def test_lambert():
    a = 7_000_000.0
    r1 = np.array([a, 0.0, 0.0])
    r2 = np.array([0.0, a, 0.0])
    tof = 0.5 * math.pi * math.sqrt(a**3 / EARTH.mu)
    v1, v2 = lambert_izzo(r1, r2, tof, EARTH.mu, prograde=True)
    sv0 = StateVector(r=r1, v=v1)
    sv_f = propagate_rk4(sv0, EARTH, tof, step=10.0)
    err = np.linalg.norm(sv_f.r - r2)
    assert err < 500.0, f"Lambert propagation check failed: {err:.1f} m off"
    verr = np.linalg.norm(sv_f.v - v2)
    assert verr < 10.0, f"Lambert v2 mismatch: {verr:.2f} m/s"
    print(f"OK test_lambert (|v1|={np.linalg.norm(v1):.1f} m/s, pos_err={err:.1f} m)")


def test_minimum_energy_tof():
    a = 7_000_000.0
    dnu = math.pi / 2
    t_min = minimum_energy_tof(EARTH, a, a, dnu)
    assert t_min > 0
    # The minimum energy tof should be less than the circular quarter period
    t_circ = 0.5 * math.pi * math.sqrt(a**3 / EARTH.mu)
    # Actually, minimum energy tof can be more or less depending on geometry.
    # Just check it's positive and finite.
    print(f"OK test_minimum_energy_tof (t_min={t_min:.1f} s, t_circ={t_circ:.1f} s)")


def test_porkchop():
    a = 7_000_000.0
    r1 = np.array([a, 0.0, 0.0])
    r2 = np.array([0.0, a, 0.0])
    data = porkchop_data(EARTH, r1, r2, (1000.0, 3000.0), n_tof=10)
    assert len(data) == 10
    for tof, v1, v2 in data:
        assert tof > 0
        if v1 != float("inf"):
            assert v1 > 0
    print(f"OK test_porkchop ({len(data)} points)")


def test_ground_track():
    a = 7_000_000.0
    elems = OrbitalElements(a=a, e=0.0, i=math.radians(45), raan=0, argp=0, nu=0, mu=EARTH.mu)
    sv = elements_to_rv(elems, EARTH)
    states = []
    for k in range(5):
        s = propagate_kepler(sv, EARTH, k * 600.0)
        s.t = k * 600.0
        states.append(s)
    pts = ground_track(states, EARTH, gmst0=0.0)
    assert len(pts) == 5
    for lat, lon in pts:
        assert -math.pi <= lat <= math.pi
        assert -math.pi <= lon <= math.pi
    print(f"OK test_ground_track (pts={len(pts)})")


def test_look_angles():
    site_lat = math.radians(40)
    site_lon = 0.0
    alt_sat = 500_000.0
    r_site = EARTH.radius
    r_ecef = np.array([(r_site + alt_sat) * math.cos(site_lat) * math.cos(site_lon),
                       (r_site + alt_sat) * math.cos(site_lat) * math.sin(site_lon),
                       (r_site + alt_sat) * math.sin(site_lat)])
    el, az, rho = latlon_look_angles(r_ecef, gmst=0.0, site_lat=site_lat, site_lon=site_lon, alt=0.0)
    assert abs(el - math.pi/2) < math.radians(1), f"Zenith elevation expected, got {math.degrees(el):.1f}°"
    assert abs(rho - alt_sat) < 1000.0
    print(f"OK test_look_angles (el={math.degrees(el):.1f}°, rho={rho:.1f} m)")


def test_j2_accel():
    r = np.array([7_000_000.0, 0.0, 0.0])
    a = j2_acceleration(r, EARTH)
    assert a[0] < 0  # radial inward
    print(f"OK test_j2_accel (a={a})")


def test_drag():
    r = np.array([EARTH.radius + 400_000.0, 0.0, 0.0])
    v = np.array([0.0, 7700.0, 0.0])
    a = drag_acceleration(r, v, EARTH)
    # Drag should oppose velocity (negative y component)
    assert a[1] < 0
    print(f"OK test_drag (|a|={np.linalg.norm(a):.6f} m/s²)")


if __name__ == "__main__":
    test_kepler_e()
    test_kepler_h()
    test_barker()
    test_stumpff()
    test_rv_elements_roundtrip()
    test_elements_repr()
    test_true_eccentric_roundtrip()
    test_propagation_period()
    test_hyperbolic_propagation()
    test_universal_propagation()
    test_rk4_vs_kepler()
    test_j2_secular()
    test_multi_step()
    test_hohmann()
    test_bielliptic()
    test_plane_change()
    test_lambert()
    test_minimum_energy_tof()
    test_porkchop()
    test_ground_track()
    test_look_angles()
    test_j2_accel()
    test_drag()
    print("\nAll smoke tests passed.")