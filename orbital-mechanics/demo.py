"""End-to-end smoke test for the orbital-mechanics library."""
import math
import sys
sys.path.insert(0, ".")

import numpy as np
from orbital import (
    EARTH, StateVector, OrbitalElements,
    rv_to_elements, elements_to_rv,
    propagate_kepler, propagate_rk4, propagate_cowell,
    hohmann_transfer, bielliptic_transfer, lambert_izzo, compute_dv,
    eci_to_ecef, ecef_to_latlon, latlon_look_angles, ground_track,
    j2_acceleration, drag_acceleration,
    solve_kepler_e, solve_kepler_h,
)


def approx(a, b, rel=1e-6, abs_=1e-3):
    return abs(a - b) <= max(abs_ * rel, abs_)


def test_kepler_e():
    # M=0 → E=0
    assert approx(solve_kepler_e(0.0, 0.5), 0.0, abs_=1e-12)
    # M=pi, e=0.5 → E=pi
    assert approx(solve_kepler_e(math.pi, 0.5), math.pi, abs_=1e-12)
    # Round-trip: M = E - e sin E
    for M in [0.3, 1.0, 2.0, -0.7, 3.0]:
        for e in [0.0, 0.3, 0.7, 0.95]:
            E = solve_kepler_e(M, e)
            # M = E - e sin E; compare in wrapped sense
            M_back = E - e * math.sin(E)
            diff = math.atan2(math.sin(M_back - M), math.cos(M_back - M))
            assert abs(diff) < 1e-7, \
                f"kepler_e failed M={M} e={e}: got {M_back} (diff {diff})"
    print("OK test_kepler_e")


def test_kepler_h():
    for M in [0.5, 1.0, 2.0, -1.0]:
        for e in [1.2, 2.0, 5.0]:
            H = solve_kepler_h(M, e)
            assert approx(e * math.sinh(H) - H, M, abs_=1e-9), \
                f"kepler_h failed M={M} e={e}"
    print("OK test_kepler_h")


def test_rv_elements_roundtrip():
    # ISS-like orbit
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
        # Handle angle wrapping
        if attr in ("raan", "argp", "nu", "i"):
            diff = math.atan2(math.sin(v1 - v2), math.cos(v1 - v2))
            assert abs(diff) < 1e-6, f"{attr}: {v1} vs {v2} (diff {diff})"
        else:
            assert abs(v1 - v2) / max(abs(v1), 1e-9) < 1e-6, f"{attr}: {v1} vs {v2}"
    print("OK test_rv_elements_roundtrip")


def test_propagation_period():
    # Circular orbit: propagate one period, return to start
    a = 7_000_000.0
    elems = OrbitalElements(a=a, e=0.0, i=0, raan=0, argp=0, nu=0, mu=EARTH.mu)
    sv = elements_to_rv(elems, EARTH)
    T = 2 * math.pi * math.sqrt(a**3 / EARTH.mu)
    sv2 = propagate_kepler(sv, EARTH, T)
    r0 = np.linalg.norm(sv.r)
    r1 = np.linalg.norm(sv2.r)
    assert abs(r0 - r1) < 1.0, f"Period propagation failed: {r0} vs {r1}"
    # Check position is close (same point after one period)
    dist = np.linalg.norm(sv.r - sv2.r)
    assert dist < 10.0, f"Position after one period off by {dist} m"
    print("OK test_propagation_period")


def test_rk4_vs_kepler():
    a = 7_000_000.0
    elems = OrbitalElements(a=a, e=0.1, i=math.radians(20), raan=0, argp=0, nu=0, mu=EARTH.mu)
    sv = elements_to_rv(elems, EARTH)
    dt = 1800.0  # 30 min
    sv_k = propagate_kepler(sv, EARTH, dt)
    sv_r = propagate_rk4(sv, EARTH, dt, step=30.0)
    err = np.linalg.norm(sv_k.r - sv_r.r)
    assert err < 1000.0, f"RK4 vs Kepler discrepancy: {err} m"
    print(f"OK test_rk4_vs_kepler (err={err:.1f} m)")


def test_hohmann():
    r1 = 6_700_000.0
    r2 = 42_000_000.0  # GEO-ish
    res = hohmann_transfer(EARTH, r1, r2)
    # Known: GEO transfer Δv ~ 3.9 km/s
    assert 3000 < res.dv_total < 5000, f"Hohmann Δv unexpected: {res.dv_total}"
    assert res.tof > 0
    print(f"OK test_hohmann (dv={res.dv_total:.1f} m/s, tof={res.tof/3600:.1f} h)")


def test_lambert():
    # Lambert: 90° transfer on a circular-orbit geometry.
    # Verify the solution by propagating r1+v1 for `tof` and checking we
    # arrive at r2.  (Lambert does NOT necessarily return the circular
    # velocity unless tof equals the minimum-energy tof.)
    a = 7_000_000.0
    v = math.sqrt(EARTH.mu / a)
    r1 = np.array([a, 0.0, 0.0])
    r2 = np.array([0.0, a, 0.0])  # 90° transfer
    tof = 0.5 * math.pi * math.sqrt(a**3 / EARTH.mu)  # quarter period
    v1, v2 = lambert_izzo(r1, r2, tof, EARTH.mu, prograde=True)
    # Verify by propagation: from (r1, v1), after `tof`, we should reach r2.
    from orbital import StateVector, propagate_rk4
    sv0 = StateVector(r=r1, v=v1)
    sv_f = propagate_rk4(sv0, EARTH, tof, step=10.0)
    err = np.linalg.norm(sv_f.r - r2)
    assert err < 500.0, f"Lambert propagation check failed: {err:.1f} m off"
    # Also check that v2 matches the propagated velocity
    verr = np.linalg.norm(sv_f.v - v2)
    assert verr < 10.0, f"Lambert v2 mismatch: {verr:.2f} m/s"
    print(f"OK test_lambert (|v1|={np.linalg.norm(v1):.1f} m/s, pos_err={err:.1f} m)")


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
    print(f"OK test_ground_track (pts={pts})")


def test_look_angles():
    # Satellite directly above a ground site → elevation should be ~90°
    site_lat = math.radians(40)
    site_lon = 0.0
    alt_sat = 500_000.0  # 500 km above surface
    r_site = EARTH.radius
    # Place satellite on the same radial line above the site (in ECEF)
    r_ecef = np.array([(r_site + alt_sat) * math.cos(site_lat) * math.cos(site_lon),
                       (r_site + alt_sat) * math.cos(site_lat) * math.sin(site_lon),
                       (r_site + alt_sat) * math.sin(site_lat)])
    # GMST=0 → ECI≈ECEF
    el, az, rho = latlon_look_angles(r_ecef, gmst=0.0, site_lat=site_lat, site_lon=site_lon, alt=0.0)
    assert abs(el - math.pi/2) < math.radians(1), f"Zenith elevation expected, got {math.degrees(el):.1f}°"
    assert abs(rho - alt_sat) < 1000.0, f"Range should be ~{alt_sat}, got {rho}"
    print(f"OK test_look_angles (el={math.degrees(el):.1f}°, rho={rho:.1f} m)")


def test_j2():
    r = np.array([7_000_000.0, 0.0, 0.0])
    a = j2_acceleration(r, EARTH)
    # At equatorial radius, J2 accel should be radial inward (x<0)
    assert a[0] < 0
    print(f"OK test_j2 (a={a})")


if __name__ == "__main__":
    test_kepler_e()
    test_kepler_h()
    test_rv_elements_roundtrip()
    test_propagation_period()
    test_rk4_vs_kepler()
    test_hohmann()
    test_lambert()
    test_ground_track()
    test_look_angles()
    test_j2()
    print("\nAll smoke tests passed.")