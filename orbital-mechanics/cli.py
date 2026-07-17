#!/usr/bin/env python3
"""CLI demo for the orbital-mechanics library.

Examples
--------
    python3 cli.py hohmann 6678 42164
    python3 cli.py elements 7000 0.01 51.6 0 30 45
    python3 cli.py lambert 7000 0 0 0 7000 0 0 1800
    python3 cli.py propagate 7000 0.01 51.6 0 30 45 3600
    python3 cli.py groundtrack 7000 51.6 600 8
"""
import sys
import math
import numpy as np

sys.path.insert(0, ".")

from orbital import (
    EARTH, StateVector, OrbitalElements,
    rv_to_elements, elements_to_rv,
    propagate_kepler, propagate_rk4, propagate_cowell,
    hohmann_transfer, bielliptic_transfer, lambert_izzo, compute_dv,
    eci_to_ecef, ecef_to_latlon, latlon_look_angles, ground_track,
    j2_acceleration, drag_acceleration,
    solve_kepler_e, solve_kepler_h,
)


def cmd_hohmann(args):
    """hohmann r1_km r2_km — Hohmann transfer between circular orbits."""
    r1 = float(args[0]) * 1000
    r2 = float(args[1]) * 1000
    res = hohmann_transfer(EARTH, r1, r2)
    print(f"Hohmann Transfer: {r1/1000:.0f} km → {r2/1000:.0f} km")
    print(f"  Δv1 (first burn):  {res.dv1:.2f} m/s")
    print(f"  Δv2 (second burn): {res.dv2:.2f} m/s")
    print(f"  Total Δv:          {res.dv_total:.2f} m/s")
    print(f"  Time of flight:    {res.tof:.1f} s ({res.tof/3600:.2f} h)")


def cmd_elements(args):
    """elements a_km e i_deg raan_deg argp_deg nu_deg — convert elements to state vector."""
    a = float(args[0]) * 1000
    e = float(args[1])
    i = math.radians(float(args[2]))
    raan = math.radians(float(args[3]))
    argp = math.radians(float(args[4]))
    nu = math.radians(float(args[5]))
    elems = OrbitalElements(a=a, e=e, i=i, raan=raan, argp=argp, nu=nu, mu=EARTH.mu)
    sv = elements_to_rv(elems, EARTH)
    print(f"Orbital Elements → State Vector:")
    print(f"  a={a/1000:.1f} km  e={e:.4f}  i={math.degrees(i):.2f}°  Ω={math.degrees(raan):.2f}°  ω={math.degrees(argp):.2f}°  ν={math.degrees(nu):.2f}°")
    print(f"  r = [{sv.r[0]:.3f}, {sv.r[1]:.3f}, {sv.r[2]:.3f}] m")
    print(f"  v = [{sv.v[0]:.3f}, {sv.v[1]:.3f}, {sv.v[2]:.3f}] m/s")
    print(f"  |r| = {np.linalg.norm(sv.r)/1000:.3f} km")
    print(f"  |v| = {np.linalg.norm(sv.v):.3f} m/s")
    print(f"  Period = {elems.period:.1f} s ({elems.period/3600:.2f} h)")
    # Round-trip check
    elems2 = rv_to_elements(sv, EARTH)
    print(f"  Round-trip: a={elems2.a/1000:.1f} km  e={elems2.e:.4f}  i={math.degrees(elems2.i):.2f}°")


def cmd_lambert(args):
    """lambert r1_km_x r1_km_y r1_km_z r2_km_x r2_km_y r2_km_z tof_s — solve Lambert's problem."""
    r1 = np.array([float(args[0]), float(args[1]), float(args[2])]) * 1000
    r2 = np.array([float(args[3]), float(args[4]), float(args[5])]) * 1000
    tof = float(args[6])
    v1, v2 = lambert_izzo(r1, r2, tof, EARTH.mu, prograde=True)
    print(f"Lambert's Problem:")
    print(f"  r1 = {r1/1000} km")
    print(f"  r2 = {r2/1000} km")
    print(f"  tof = {tof:.1f} s")
    print(f"  v1 = [{v1[0]:.3f}, {v1[1]:.3f}, {v1[2]:.3f}] m/s  (|v1|={np.linalg.norm(v1):.2f})")
    print(f"  v2 = [{v2[0]:.3f}, {v2[1]:.3f}, {v2[2]:.3f}] m/s  (|v2|={np.linalg.norm(v2):.2f})")
    # Verify by propagation
    sv0 = StateVector(r=r1, v=v1)
    sv_f = propagate_rk4(sv0, EARTH, tof, step=10.0)
    err = np.linalg.norm(sv_f.r - r2)
    print(f"  Propagation check: position error = {err:.1f} m")


def cmd_propagate(args):
    """propagate a_km e i_deg raan_deg argp_deg nu_deg dt_s — propagate an orbit."""
    a = float(args[0]) * 1000
    e = float(args[1])
    i = math.radians(float(args[2]))
    raan = math.radians(float(args[3]))
    argp = math.radians(float(args[4]))
    nu = math.radians(float(args[5]))
    dt = float(args[6])
    elems = OrbitalElements(a=a, e=e, i=i, raan=raan, argp=argp, nu=nu, mu=EARTH.mu)
    sv0 = elements_to_rv(elems, EARTH)
    sv_k = propagate_kepler(sv0, EARTH, dt)
    sv_r = propagate_rk4(sv0, EARTH, dt, step=30.0)
    print(f"Propagation (dt={dt:.0f} s):")
    print(f"  Initial: r={sv0.r/1000} km, |r|={np.linalg.norm(sv0.r)/1000:.3f} km")
    print(f"  Kepler:  r={sv_k.r/1000} km, |r|={np.linalg.norm(sv_k.r)/1000:.3f} km")
    print(f"  RK4:     r={sv_r.r/1000} km, |r|={np.linalg.norm(sv_r.r)/1000:.3f} km")
    err = np.linalg.norm(sv_k.r - sv_r.r)
    print(f"  Kepler vs RK4 discrepancy: {err:.1f} m")


def cmd_groundtrack(args):
    """groundtrack a_km i_deg step_s num_pts — generate ground track points."""
    a = float(args[0]) * 1000
    i = math.radians(float(args[1]))
    step = float(args[2])
    n = int(args[3])
    elems = OrbitalElements(a=a, e=0.0, i=i, raan=0, argp=0, nu=0, mu=EARTH.mu)
    sv0 = elements_to_rv(elems, EARTH)
    states = []
    for k in range(n):
        s = propagate_kepler(sv0, EARTH, k * step)
        s.t = k * step
        states.append(s)
    pts = ground_track(states, EARTH, gmst0=0.0)
    print(f"Ground Track ({n} points, step={step:.0f} s):")
    print(f"  {'Lat (°)':>10s}  {'Lon (°)':>10s}")
    for lat, lon in pts:
        print(f"  {math.degrees(lat):10.4f}  {math.degrees(lon):10.4f}")


def cmd_j2(args):
    """j2 a_km e i_deg dt_s — propagate with J2 perturbation and show drift."""
    a = float(args[0]) * 1000
    e = float(args[1])
    i = math.radians(float(args[2]))
    dt = float(args[3]) if len(args) > 3 else 86400.0  # 1 day default
    elems = OrbitalElements(a=a, e=e, i=i, raan=0, argp=0, nu=0, mu=EARTH.mu)
    sv0 = elements_to_rv(elems, EARTH)
    # Propagate with and without J2
    sv_plain = propagate_cowell(sv0, EARTH, dt, step=60.0)
    sv_j2 = propagate_cowell(sv0, EARTH, dt, step=60.0,
                             extra_accel=lambda r, v, t: j2_acceleration(r, EARTH))
    elems_plain = rv_to_elements(sv_plain, EARTH)
    elems_j2 = rv_to_elements(sv_j2, EARTH)
    print(f"J2 Perturbation (dt={dt/3600:.1f} h):")
    print(f"  Without J2: RAAN={math.degrees(elems_plain.raan):.4f}°  argp={math.degrees(elems_plain.argp):.4f}°")
    print(f"  With J2:    RAAN={math.degrees(elems_j2.raan):.4f}°  argp={math.degrees(elems_j2.argp):.4f}°")
    print(f"  RAAN drift:  {math.degrees(elems_j2.raan - elems_plain.raan):.6f}°")
    print(f"  argp drift:  {math.degrees(elems_j2.argp - elems_plain.argp):.6f}°")


COMMANDS = {
    "hohmann": cmd_hohmann,
    "elements": cmd_elements,
    "lambert": cmd_lambert,
    "propagate": cmd_propagate,
    "groundtrack": cmd_groundtrack,
    "j2": cmd_j2,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        print(f"Available commands: {', '.join(COMMANDS.keys())}")
        sys.exit(1)
    cmd = sys.argv[1]
    args = sys.argv[2:]
    COMMANDS[cmd](args)


if __name__ == "__main__":
    main()