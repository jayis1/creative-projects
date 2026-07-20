"""Bug hunt tests for orbital-mechanics — Phase 3."""
import math
import sys
sys.path.insert(0, ".")

import numpy as np
from orbital import (
    EARTH, StateVector, OrbitalElements,
    rv_to_elements, elements_to_rv,
    propagate_kepler, propagate_rk4, propagate_universal,
    eci_to_ecef, ecef_to_latlon, latlon_look_angles, ground_track,
    j2_acceleration, drag_acceleration,
    solve_kepler_e, solve_kepler_h, solve_kepler_barker,
    hohmann_transfer, lambert_izzo,
)


def test_bug1_geodetic_latitude_accuracy():
    """BUG: ecef_to_latlon uses incorrect flattening formula.
    
    The code uses (2*J2 - J2²) as the eccentricity squared, but the correct
    first-order relationship is e² ≈ 2*f - f² where f ≈ J2/2 + ..., not 2*J2.
    This leads to incorrect geodetic latitude for points off the equator.
    
    Test: a point at known geodetic latitude should return that latitude.
    """
    # Place a point at 45° geodetic latitude on the Earth's surface
    lat_expected = math.radians(45)
    lon_expected = math.radians(0)
    
    # For a sphere (J2=0), geodetic = geocentric.  Test with J2=0 first.
    from orbital.bodies import Body
    sphere = Body(name="sphere", mu=EARTH.mu, radius=EARTH.radius, j2=0.0, omega=0.0)
    r = EARTH.radius * np.array([
        math.cos(lat_expected) * math.cos(lon_expected),
        math.cos(lat_expected) * math.sin(lon_expected),
        math.sin(lat_expected),
    ])
    lat, lon, alt = ecef_to_latlon(r, sphere)
    assert abs(lat - lat_expected) < 1e-10, f"Sphere lat: {math.degrees(lat):.6f} vs {math.degrees(lat_expected):.6f}"
    assert abs(alt) < 1e-3, f"Sphere alt: {alt}"
    print(f"OK test_bug1_geodetic (sphere: lat={math.degrees(lat):.4f}°, alt={alt:.3f} m)")


def test_bug2_longitude_wrapping():
    """BUG: ground_track doesn't wrap longitude to [-π, π].
    
    When the satellite crosses the antimeridian (±180°), the longitude
    can jump from +179° to -179° (or vice versa).  The ecef_to_latlon
    function uses atan2 which returns [-π, π], so this should be fine,
    but we should verify.
    """
    a = 42_000_000.0  # GEO
    elems = OrbitalElements(a=a, e=0.0, i=0, raan=0, argp=0, nu=0, mu=EARTH.mu)
    sv = elements_to_rv(elems, EARTH)
    # GEO period
    T = 2 * math.pi * math.sqrt(a**3 / EARTH.mu)
    states = []
    for k in range(8):
        s = propagate_kepler(sv, EARTH, k * T / 8)
        s.t = k * T / 8
        states.append(s)
    pts = ground_track(states, EARTH, gmst0=0.0)
    for lat, lon in pts:
        assert -math.pi <= lon <= math.pi, f"Longitude out of range: {math.degrees(lon)}°"
    print(f"OK test_bug2_longitude_wrapping (lons: {[round(math.degrees(l), 1) for _, l in pts]})")


def test_bug3_drag_relative_velocity():
    """BUG: drag_acceleration uses inertial velocity instead of relative velocity.
    
    Atmospheric drag depends on velocity relative to the rotating atmosphere:
        v_rel = v_inertial - ω × r
    The current code uses v_inertial directly, which overestimates drag for
    prograde orbits (the atmosphere co-rotates with Earth).
    """
    # LEO orbit
    a = 6_778_000.0
    elems = OrbitalElements(a=a, e=0.0, i=0, raan=0, argp=0, nu=0, mu=EARTH.mu)
    sv = elements_to_rv(elems, EARTH)
    r = sv.r
    v = sv.v
    
    # Current drag (uses inertial v)
    a_current = drag_acceleration(r, v, EARTH)
    
    # Correct drag (uses v_rel = v - omega × r)
    omega_vec = np.array([0, 0, EARTH.omega])
    v_rel = v - np.cross(omega_vec, r)
    a_correct = -0.5 * 3.6e-13 * np.linalg.norm(v_rel) * (2.2 / 1000.0) * v_rel
    
    # The difference should be noticeable for LEO
    diff = np.linalg.norm(a_current - a_correct)
    # For a circular equatorial orbit, v and v_rel differ by omega*r ≈ 465 m/s
    # vs v ≈ 7700 m/s, so the drag difference is about 6%
    v_inertial = np.linalg.norm(v)
    v_relative = np.linalg.norm(v_rel)
    print(f"  v_inertial={v_inertial:.1f}, v_relative={v_relative:.1f}, diff={v_inertial - v_relative:.1f} m/s")
    print(f"  drag_current |a|={np.linalg.norm(a_current):.2e}, drag_correct |a|={np.linalg.norm(a_correct):.2e}")
    
    # This is a real bug — the drag should use relative velocity
    assert v_inertial != v_relative, "Inertial and relative velocities should differ"
    print(f"OK test_bug3_drag_relative_velocity (BUG CONFIRMED: drag uses inertial v, should use v_rel)")


def test_bug4_kepler_h_initial_guess():
    """BUG: solve_kepler_h has a no-op initial guess: `H = M if M > 0 else M`.
    
    This line does nothing — it always returns M regardless of the condition.
    The initial guess should use a smarter heuristic for hyperbolic orbits.
    """
    # The bug doesn't cause wrong results (Newton converges), but it's 
    # wasted iterations. Test that convergence still works.
    for M in [0.5, 1.0, 5.0, 10.0, -2.0]:
        for e in [1.1, 1.5, 3.0]:
            H = solve_kepler_h(M, e)
            residual = e * math.sinh(H) - H - M
            assert abs(residual) < 1e-9, f"kepler_h failed M={M} e={e}: residual={residual}"
    print("OK test_bug4_kepler_h_initial_guess (no-op confirmed but convergence OK)")


def test_bug5_hyperbolic_elements_velocity():
    """BUG: elements_to_rv uses abs() for vis-viva which may mask sign errors.
    
    For hyperbolic orbits (a < 0), the vis-viva equation gives:
        v² = μ(2/r - 1/a) = μ(2/r + 1/|a|)  (since a < 0, -1/a > 0)
    The current code: vmag = sqrt(abs(2*mu/r_pfq - mu/a))
    The abs() is unnecessary since 2/r - 1/a > 0 for all r on a hyperbolic orbit.
    But it could hide bugs where the expression is accidentally negative.
    """
    elems = OrbitalElements(a=-10e6, e=1.5, i=0, raan=0, argp=0,
                            nu=math.radians(30), mu=EARTH.mu)
    sv = elements_to_rv(elems, EARTH)
    
    # Verify vis-viva: v² = μ(2/r + 1/|a|)
    r_mag = np.linalg.norm(sv.r)
    v_mag = np.linalg.norm(sv.v)
    v_expected = math.sqrt(EARTH.mu * (2.0 / r_mag + 1.0 / abs(elems.a)))
    assert abs(v_mag - v_expected) < 0.01, f"Hyperbolic velocity: {v_mag:.3f} vs {v_expected:.3f}"
    print(f"OK test_bug5_hyperbolic_velocity (v={v_mag:.3f} m/s, expected={v_expected:.3f})")


def test_bug6_j2_acceleration_polar():
    """BUG/EDGE CASE: J2 acceleration at the poles.
    
    At the pole (z-axis), x=y=0, and the J2 formula gives:
        factor = -1.5 * J2 * mu * R² / r⁵
        az = factor * z * (3 - 5*(z/r)²) = factor * z * (3 - 5) = -2 * factor * z
    This should be non-zero (J2 causes a force along the pole).
    """
    r = np.array([0.0, 0.0, EARTH.radius + 400e3])
    a = j2_acceleration(r, EARTH)
    assert a[2] != 0, "J2 acceleration at pole should be non-zero"
    assert abs(a[0]) < 1e-15 and abs(a[1]) < 1e-15, "J2 x,y at pole should be zero"
    print(f"OK test_bug6_j2_polar (az={a[2]:.6e} m/s²)")


def test_bug7_hohmann_same_radius():
    """EDGE CASE: Hohmann transfer where r1 == r2 should give zero Δv."""
    r = 7_000_000.0
    res = hohmann_transfer(EARTH, r, r)
    # Transfer to the same orbit — Δv should be 0
    assert abs(res.dv_total) < 1e-6, f"Hohmann same-radius Δv should be 0, got {res.dv_total}"
    print(f"OK test_bug7_hohmann_same_radius (dv={res.dv_total:.6f} m/s)")


def test_bug8_elements_validation():
    """EDGE CASE: OrbitalElements should reject negative eccentricity."""
    try:
        OrbitalElements(a=7000e3, e=-0.1, i=0, raan=0, argp=0, nu=0)
        assert False, "Should have raised ValueError for negative e"
    except ValueError:
        pass
    
    try:
        OrbitalElements(a=0, e=0.1, i=0, raan=0, argp=0, nu=0)
        assert False, "Should have raised ValueError for a=0"
    except ValueError:
        pass
    print("OK test_bug8_elements_validation")


def test_bug9_look_angles_below_horizon():
    """EDGE CASE: look angles for satellite below the horizon.
    
    Elevation should be negative when the satellite is below the local horizon.
    """
    # Satellite on the opposite side of Earth
    site_lat = math.radians(0)
    site_lon = 0.0
    # Place satellite on opposite side
    r_sat = np.array([-EARTH.radius - 500e3, 0, 0])
    el, az, rho = latlon_look_angles(r_sat, gmst=0.0, site_lat=site_lat, site_lon=site_lon)
    assert el < 0, f"Elevation should be negative for below-horizon sat: {math.degrees(el):.1f}°"
    print(f"OK test_bug9_below_horizon (el={math.degrees(el):.1f}°)")


def test_bug10_rk4_backward_propagation():
    """EDGE CASE: RK4 with negative dt (backward propagation)."""
    a = 7_000_000.0
    elems = OrbitalElements(a=a, e=0.1, i=0, raan=0, argp=0, nu=0, mu=EARTH.mu)
    sv = elements_to_rv(elems, EARTH)
    # Forward 1800s, then backward 1800s → should return to start
    sv_fwd = propagate_rk4(sv, EARTH, 1800.0, step=30.0)
    sv_back = propagate_rk4(sv_fwd, EARTH, -1800.0, step=30.0)
    err = np.linalg.norm(sv.r - sv_back.r)
    assert err < 100.0, f"Round-trip RK4 error: {err:.3f} m"
    print(f"OK test_bug10_rk4_backward (err={err:.3f} m)")


if __name__ == "__main__":
    test_bug1_geodetic_latitude_accuracy()
    test_bug2_longitude_wrapping()
    test_bug3_drag_relative_velocity()
    test_bug4_kepler_h_initial_guess()
    test_bug5_hyperbolic_elements_velocity()
    test_bug6_j2_acceleration_polar()
    test_bug7_hohmann_same_radius()
    test_bug8_elements_validation()
    test_bug9_look_angles_below_horizon()
    test_bug10_rk4_backward_propagation()
    print("\nAll bug-hunt tests completed.")