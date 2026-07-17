#!/usr/bin/env python3
"""Command-line interface for the orbital-mechanics library (v3).

Uses argparse with subcommands.  Run ``python3 cli.py --help`` for
the full list.

Examples
--------
    python3 cli.py hohmann 6678 42164
    python3 cli.py elements 7000 0.01 51.6 0 30 45
    python3 cli.py lambert 7000 0 0 0 7000 0 0 1800
    python3 cli.py propagate 7000 0.01 51.6 0 30 45 3600
    python3 cli.py groundtrack 7000 51.6 600 10
    python3 cli.py j2 7000 0.01 51.6 86400
    python3 cli.py rkf45 7000 0.01 51.6 0 30 45 86400
    python3 cli.py tle examples/iss.tle
    python3 cli.py lagrange earth moon
    python3 cli.py rgt 14 1 51.6
    python3 cli.py config mission.yaml
    python3 cli.py porkchop 7000 0 0 0 7000 0 0 1000 3000
    python3 cli.py visualize 7000 0.5 30 0 0 0
"""
from __future__ import annotations

import argparse
import json
import math
import sys

import numpy as np

sys.path.insert(0, ".")

from orbital import (
    EARTH, MOON, SUN, MARS, VENUS,
    StateVector, OrbitalElements,
    rv_to_elements, elements_to_rv,
    propagate_kepler, propagate_rk4, propagate_cowell,
    propagate_rkf45, propagate_universal, propagate_j2_secular,
    multi_step_propagate,
    hohmann_transfer, bielliptic_transfer, lambert_izzo, compute_dv,
    plane_change_delta_v, combined_plane_change_delta_v,
    minimum_energy_tof, porkchop_data,
    eci_to_ecef, ecef_to_latlon, latlon_look_angles, ground_track,
    j2_acceleration, drag_acceleration,
    solve_kepler_e, solve_kepler_h,
    parse_tle, parse_tle_set,
    lagrange_points, repeat_groundtrack_orbit, frozen_orbit_argp,
    stationkeeping_delta_v,
    visibility_windows, access_summary, sun_position, in_umbra,
    states_to_csv, groundtrack_to_csv, states_to_json,
    ascii_orbit_xy, ascii_ground_track, ascii_porkchop,
    load_config, get_logger, set_log_level,
)
from orbital.bodies import Body

BODIES = {"earth": EARTH, "moon": MOON, "sun": SUN, "mars": MARS, "venus": VENUS}


def _body_arg(name: str) -> Body:
    name = name.lower()
    if name not in BODIES:
        raise argparse.ArgumentTypeError(
            f"Unknown body '{name}'; choose from {list(BODIES)}")
    return BODIES[name]


def cmd_hohmann(args):
    """Hohmann transfer between two circular orbits."""
    r1 = args.r1_km * 1000
    r2 = args.r2_km * 1000
    body = args.body
    res = hohmann_transfer(body, r1, r2)
    print(f"Hohmann Transfer: {r1/1000:.0f} km → {r2/1000:.0f} km ({body.name})")
    print(f"  Δv1 (first burn):  {res.dv1:.2f} m/s")
    print(f"  Δv2 (second burn): {res.dv2:.2f} m/s")
    print(f"  Total Δv:          {res.dv_total:.2f} m/s")
    print(f"  Time of flight:    {res.tof:.1f} s ({res.tof/3600:.2f} h)")


def cmd_elements(args):
    """Convert orbital elements to a state vector."""
    a = args.a_km * 1000
    e = args.e
    i = math.radians(args.i_deg)
    raan = math.radians(args.raan_deg)
    argp = math.radians(args.argp_deg)
    nu = math.radians(args.nu_deg)
    body = args.body
    elems = OrbitalElements(a=a, e=e, i=i, raan=raan, argp=argp, nu=nu, mu=body.mu)
    sv = elements_to_rv(elems, body)
    print("Orbital Elements → State Vector:")
    print(f"  a={a/1000:.1f} km  e={e:.4f}  i={math.degrees(i):.2f}°  "
          f"Ω={math.degrees(raan):.2f}°  ω={math.degrees(argp):.2f}°  "
          f"ν={math.degrees(nu):.2f}°")
    print(f"  r = [{sv.r[0]:.3f}, {sv.r[1]:.3f}, {sv.r[2]:.3f}] m")
    print(f"  v = [{sv.v[0]:.3f}, {sv.v[1]:.3f}, {sv.v[2]:.3f}] m/s")
    print(f"  |r| = {np.linalg.norm(sv.r)/1000:.3f} km")
    print(f"  |v| = {np.linalg.norm(sv.v):.3f} m/s")
    print(f"  Period = {elems.period:.1f} s ({elems.period/3600:.2f} h)")
    print(f"  Orbit type: {elems.orbit_type}")
    print(f"  Perigee: {elems.perigee/1000:.1f} km  Apogee: "
          f"{elems.apogee/1000:.1f} km")
    elems2 = rv_to_elements(sv, body)
    print(f"  Round-trip: a={elems2.a/1000:.1f} km  e={elems2.e:.4f}  "
          f"i={math.degrees(elems2.i):.2f}°")


def cmd_lambert(args):
    """Solve Lambert's problem."""
    r1 = np.array([args.r1x, args.r1y, args.r1z]) * 1000
    r2 = np.array([args.r2x, args.r2y, args.r2z]) * 1000
    tof = args.tof
    body = args.body
    v1, v2 = lambert_izzo(r1, r2, tof, body.mu, prograde=not args.retrograde)
    print("Lambert's Problem:")
    print(f"  r1 = {r1/1000} km")
    print(f"  r2 = {r2/1000} km")
    print(f"  tof = {tof:.1f} s")
    print(f"  v1 = [{v1[0]:.3f}, {v1[1]:.3f}, {v1[2]:.3f}] m/s  "
          f"(|v1|={np.linalg.norm(v1):.2f})")
    print(f"  v2 = [{v2[0]:.3f}, {v2[1]:.3f}, {v2[2]:.3f}] m/s  "
          f"(|v2|={np.linalg.norm(v2):.2f})")
    sv0 = StateVector(r=r1, v=v1)
    sv_f = propagate_rk4(sv0, body, tof, step=10.0)
    err = np.linalg.norm(sv_f.r - r2)
    print(f"  Propagation check: position error = {err:.1f} m")


def cmd_propagate(args):
    """Propagate an orbit and compare methods."""
    a = args.a_km * 1000
    e = args.e
    i = math.radians(args.i_deg)
    raan = math.radians(args.raan_deg)
    argp = math.radians(args.argp_deg)
    nu = math.radians(args.nu_deg)
    dt = args.dt
    body = args.body
    elems = OrbitalElements(a=a, e=e, i=i, raan=raan, argp=argp, nu=nu, mu=body.mu)
    sv0 = elements_to_rv(elems, body)
    sv_k = propagate_kepler(sv0, body, dt)
    sv_r = propagate_rk4(sv0, body, dt, step=30.0)
    print(f"Propagation (dt={dt:.0f} s, body={body.name}):")
    print(f"  Initial:  r={sv0.r/1000} km, |r|={np.linalg.norm(sv0.r)/1000:.3f} km")
    print(f"  Kepler:   r={sv_k.r/1000} km, |r|={np.linalg.norm(sv_k.r)/1000:.3f} km")
    print(f"  RK4:      r={sv_r.r/1000} km, |r|={np.linalg.norm(sv_r.r)/1000:.3f} km")
    err = np.linalg.norm(sv_k.r - sv_r.r)
    print(f"  Kepler vs RK4 discrepancy: {err:.1f} m")


def cmd_rkf45(args):
    """Propagate using adaptive RKF45."""
    a = args.a_km * 1000
    e = args.e
    i = math.radians(args.i_deg)
    raan = math.radians(args.raan_deg)
    argp = math.radians(args.argp_deg)
    nu = math.radians(args.nu_deg)
    dt = args.dt
    body = args.body
    elems = OrbitalElements(a=a, e=e, i=i, raan=raan, argp=argp, nu=nu, mu=body.mu)
    sv0 = elements_to_rv(elems, body)
    sv_a = propagate_rkf45(sv0, body, dt, rtol=args.rtol)
    sv_k = propagate_kepler(sv0, body, dt)
    err = np.linalg.norm(sv_a.r - sv_k.r)
    print(f"RKF45 Adaptive Propagation (dt={dt:.0f} s, rtol={args.rtol}):")
    print(f"  Initial:  r={sv0.r/1000} km")
    print(f"  RKF45:    r={sv_a.r/1000} km")
    print(f"  Kepler:   r={sv_k.r/1000} km")
    print(f"  RKF45 vs Kepler discrepancy: {err:.4f} m")


def cmd_groundtrack(args):
    """Generate ground-track points."""
    a = args.a_km * 1000
    i = math.radians(args.i_deg)
    step = args.step_s
    n = args.num_pts
    body = args.body
    elems = OrbitalElements(a=a, e=0.0, i=i, raan=0, argp=0, nu=0, mu=body.mu)
    sv0 = elements_to_rv(elems, body)
    states = []
    for k in range(n):
        s = propagate_kepler(sv0, body, k * step)
        s.t = k * step
        states.append(s)
    pts = ground_track(states, body, gmst0=0.0)
    print(f"Ground Track ({n} points, step={step:.0f} s, body={body.name}):")
    print(f"  {'Lat (°)':>10s}  {'Lon (°)':>10s}")
    for lat, lon in pts:
        print(f"  {math.degrees(lat):10.4f}  {math.degrees(lon):10.4f}")


def cmd_j2(args):
    """J2 perturbation drift analysis."""
    a = args.a_km * 1000
    e = args.e
    i = math.radians(args.i_deg)
    dt = args.dt
    body = args.body
    elems = OrbitalElements(a=a, e=e, i=i, raan=0, argp=0, nu=0, mu=body.mu)
    sv0 = elements_to_rv(elems, body)
    sv_plain = propagate_cowell(sv0, body, dt, step=60.0)
    sv_j2 = propagate_cowell(sv0, body, dt, step=60.0,
                             extra_accel=lambda r, v, t: j2_acceleration(r, body))
    elems_plain = rv_to_elements(sv_plain, body)
    elems_j2 = rv_to_elements(sv_j2, body)
    print(f"J2 Perturbation (dt={dt/3600:.1f} h, body={body.name}):")
    print(f"  Without J2: RAAN={math.degrees(elems_plain.raan):.4f}°  "
          f"argp={math.degrees(elems_plain.argp):.4f}°")
    print(f"  With J2:    RAAN={math.degrees(elems_j2.raan):.4f}°  "
          f"argp={math.degrees(elems_j2.argp):.4f}°")
    print(f"  RAAN drift:  {math.degrees(elems_j2.raan - elems_plain.raan):.6f}°")
    print(f"  argp drift:  {math.degrees(elems_j2.argp - elems_plain.argp):.6f}°")


def cmd_tle(args):
    """Parse a TLE file and print decoded elements."""
    with open(args.file) as f:
        text = f.read()
    tles = parse_tle_set(text)
    if not tles:
        print("No TLE sets found in file.")
        return
    print(f"Parsed {len(tles)} TLE set(s):")
    for tle in tles:
        print(f"\n{tle}")
        elems = tle.to_elements()
        print(f"  a = {elems.a/1000:.1f} km  e = {elems.e:.5f}  "
              f"i = {math.degrees(elems.i):.2f}°")
        print(f"  RAAN = {math.degrees(elems.raan):.2f}°  "
              f"argp = {math.degrees(elems.argp):.2f}°  "
              f"nu = {math.degrees(elems.nu):.2f}°")
        print(f"  Period = {elems.period/60:.2f} min")


def cmd_lagrange(args):
    """Compute Lagrange point positions for a body pair."""
    b1 = _body_arg(args.body1)
    b2 = _body_arg(args.body2)
    pts = lagrange_points(b1, b2)
    print(f"Lagrange Points ({b1.name}-{b2.name} system):")
    for lp in pts:
        r_mag = np.linalg.norm(lp.r)
        print(f"  {lp.name}: r=[{lp.r[0]/1000:.0f}, {lp.r[1]/1000:.0f}, "
              f"{lp.r[2]/1000:.0f}] km  |r|={r_mag/1000:.0f} km")


def cmd_rgt(args):
    """Compute a repeat-ground-track orbit."""
    body = args.body
    rgt = repeat_groundtrack_orbit(body, args.N, args.D,
                                   math.radians(args.i_deg), args.eccentricity)
    print(f"Repeat-Ground-Track Orbit ({body.name}):")
    print(f"  Repeat cycle: {rgt.N_rev} rev / {rgt.D_days} nodal days")
    print(f"  Semi-major axis: {rgt.a/1000:.3f} km")
    print(f"  Altitude: {(rgt.a - body.radius)/1000:.3f} km")
    print(f"  Period: {rgt.period:.2f} s ({rgt.period/60:.2f} min)")
    print(f"  Inclination: {math.degrees(rgt.inclination):.2f}°")


def cmd_frozen(args):
    """Compute frozen-orbit argument of perigee."""
    body = args.body
    a = args.a_km * 1000
    argp = frozen_orbit_argp(body, a, args.e, math.radians(args.i_deg))
    print(f"Frozen Orbit Argument of Perigee ({body.name}):")
    print(f"  a = {a/1000:.1f} km  e = {args.e}  i = {args.i_deg:.2f}°")
    print(f"  ω_frozen = {math.degrees(argp):.4f}° ({argp:.6f} rad)")


def cmd_porkchop(args):
    """Generate porkchop plot data."""
    r1 = np.array([args.r1x, args.r1y, args.r1z]) * 1000
    r2 = np.array([args.r2x, args.r2y, args.r2z]) * 1000
    body = args.body
    data = porkchop_data(body, r1, r2, (args.tof_min, args.tof_max),
                         n_tof=args.n_tof)
    print(f"Porkchop Plot Data ({len(data)} points, body={body.name}):")
    print(f"  {'TOF (s)':>10s}  {'|v1| (m/s)':>12s}  {'|v2| (m/s)':>12s}  "
          f"{'C3 (km²/s²)':>12s}")
    for tof, v1, v2 in data:
        c3 = v1 ** 2 / 1000.0 if v1 != float("inf") else float("inf")
        c3_str = f"{c3:.2f}" if c3 != float("inf") else "—"
        v1_str = f"{v1:.2f}" if v1 != float("inf") else "—"
        v2_str = f"{v2:.2f}" if v2 != float("inf") else "—"
        print(f"  {tof:10.0f}  {v1_str:>12s}  {v2_str:>12s}  {c3_str:>12s}")
    if args.ascii:
        print()
        print(ascii_porkchop(data, title=f"Porkchop ({body.name})"))


def cmd_visualize(args):
    """Render an ASCII orbit visualization."""
    a = args.a_km * 1000
    e = args.e
    i = math.radians(args.i_deg)
    raan = math.radians(args.raan_deg)
    argp = math.radians(args.argp_deg)
    nu = math.radians(args.nu_deg)
    body = args.body
    elems = OrbitalElements(a=a, e=e, i=i, raan=raan, argp=argp, nu=nu, mu=body.mu)
    sv0 = elements_to_rv(elems, body)
    # Propagate one full orbit.
    if elems.is_elliptic:
        states = multi_step_propagate(sv0, body, elems.period,
                                      elems.period / max(args.points, 4))
    else:
        # Hyperbolic — just propagate a fixed duration.
        states = multi_step_propagate(sv0, body, 7200, 60)
    print(ascii_orbit_xy(states, title=f"Orbit XY projection ({body.name}, "
                                       f"e={e}, i={args.i_deg}°)"))
    # Ground track.
    pts = ground_track(states, body, gmst0=0.0)
    print()
    print(ascii_ground_track(pts, title=f"Ground Track ({body.name})"))


def cmd_visibility(args):
    """Compute ground-station visibility windows."""
    a = args.a_km * 1000
    i = math.radians(args.i_deg)
    body = args.body
    elems = OrbitalElements(a=a, e=0.0, i=i, raan=0, argp=0, nu=0, mu=body.mu)
    sv0 = elements_to_rv(elems, body)
    states = multi_step_propagate(sv0, body, args.duration, args.step)
    passes = visibility_windows(states, math.radians(args.lat_deg),
                                math.radians(args.lon_deg),
                                min_elevation=math.radians(args.min_el),
                                body=body)
    print(f"Visibility Windows ({len(passes)} passes, body={body.name}):")
    print(f"  Station: lat={args.lat_deg}° lon={args.lon_deg}°  "
          f"min_el={args.min_el}°")
    for p in passes:
        print(f"  {access_summary(p)}")


def cmd_config(args):
    """Run a mission from a config file."""
    cfg = load_config(args.file)
    if args.verbose:
        set_log_level("DEBUG")
    log = get_logger()
    log.info("Loaded config for body=%s", cfg.body.name)
    # Build initial state.
    elems = OrbitalElements(
        a=cfg.satellite.a, e=cfg.satellite.e, i=cfg.satellite.i,
        raan=cfg.satellite.raan, argp=cfg.satellite.argp, nu=cfg.satellite.nu,
        mu=cfg.body.mu,
    )
    sv0 = elements_to_rv(elems, cfg.body)
    print(f"Initial state: {sv0}")
    print(f"  Elements: {elems}")
    # Propagate.
    method = cfg.propagation.method
    dt = cfg.propagation.dt
    if method == "kepler":
        sv_f = propagate_kepler(sv0, cfg.body, dt)
    elif method == "rk4":
        sv_f = propagate_rk4(sv0, cfg.body, dt, step=cfg.propagation.step)
    elif method == "cowell":
        sv_f = propagate_cowell(sv0, cfg.body, dt, step=cfg.propagation.step,
                                extra_accel=lambda r, v, t: j2_acceleration(r, cfg.body))
    elif method == "rkf45":
        sv_f = propagate_rkf45(sv0, cfg.body, dt, rtol=cfg.propagation.rtol)
    elif method == "universal":
        sv_f = propagate_universal(sv0, cfg.body, dt)
    elif method == "j2_secular":
        sv_f = propagate_j2_secular(sv0, cfg.body, dt)
    else:
        raise ValueError(f"Unknown method: {method}")
    print(f"Final state ({method}, dt={dt}s): {sv_f}")
    # Optional outputs.
    if cfg.output.states_csv:
        states = multi_step_propagate(sv0, cfg.body, dt,
                                      max(cfg.propagation.step, 60))
        states_to_csv(states, cfg.body, cfg.output.states_csv)
        print(f"Wrote states CSV → {cfg.output.states_csv}")
    if cfg.output.groundtrack_csv:
        states = multi_step_propagate(sv0, cfg.body, dt,
                                      max(cfg.propagation.step, 60))
        pts = ground_track(states, cfg.body)
        groundtrack_to_csv(pts, cfg.output.groundtrack_csv)
        print(f"Wrote groundtrack CSV → {cfg.output.groundtrack_csv}")


def cmd_eclipse(args):
    """Check whether a satellite is in Earth's umbra at a given epoch."""
    a = args.a_km * 1000
    e = args.e
    i = math.radians(args.i_deg)
    body = args.body
    elems = OrbitalElements(a=a, e=e, i=i, raan=0, argp=0,
                            nu=math.radians(args.nu_deg), mu=body.mu)
    sv = elements_to_rv(elems, body)
    # Approximate JD from epoch (use 2024-01-01 as reference if not given).
    jd = args.jd if args.jd else 2460310.5  # J2024.0
    r_sun = sun_position(jd)
    shadow = in_umbra(sv.r, r_sun, body)
    print(f"Eclipse Check (ν={args.nu_deg}°, body={body.name}):")
    print(f"  Sat position: {sv.r/1000} km")
    print(f"  Sun position: {r_sun/1e9:.3f} Gm")
    print(f"  In umbra: {shadow}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cli.py",
        description="Orbital mechanics simulator CLI (v3)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="command", required=True)

    # hohmann
    sp = sub.add_parser("hohmann", help="Hohmann transfer between circular orbits")
    sp.add_argument("r1_km", type=float, help="Initial orbit radius [km]")
    sp.add_argument("r2_km", type=float, help="Final orbit radius [km]")
    sp.add_argument("--body", type=_body_arg, default=EARTH, help="Central body")
    sp.set_defaults(func=cmd_hohmann)

    # elements
    sp = sub.add_parser("elements", help="Convert orbital elements to state vector")
    sp.add_argument("a_km", type=float)
    sp.add_argument("e", type=float)
    sp.add_argument("i_deg", type=float)
    sp.add_argument("raan_deg", type=float)
    sp.add_argument("argp_deg", type=float)
    sp.add_argument("nu_deg", type=float)
    sp.add_argument("--body", type=_body_arg, default=EARTH)
    sp.set_defaults(func=cmd_elements)

    # lambert
    sp = sub.add_parser("lambert", help="Solve Lambert's problem")
    sp.add_argument("r1x", type=float); sp.add_argument("r1y", type=float); sp.add_argument("r1z", type=float)
    sp.add_argument("r2x", type=float); sp.add_argument("r2y", type=float); sp.add_argument("r2z", type=float)
    sp.add_argument("tof", type=float, help="Time of flight [s]")
    sp.add_argument("--retrograde", action="store_true")
    sp.add_argument("--body", type=_body_arg, default=EARTH)
    sp.set_defaults(func=cmd_lambert)

    # propagate
    sp = sub.add_parser("propagate", help="Propagate an orbit (Kepler + RK4)")
    sp.add_argument("a_km", type=float)
    sp.add_argument("e", type=float)
    sp.add_argument("i_deg", type=float)
    sp.add_argument("raan_deg", type=float)
    sp.add_argument("argp_deg", type=float)
    sp.add_argument("nu_deg", type=float)
    sp.add_argument("dt", type=float, help="Time increment [s]")
    sp.add_argument("--body", type=_body_arg, default=EARTH)
    sp.set_defaults(func=cmd_propagate)

    # rkf45
    sp = sub.add_parser("rkf45", help="Adaptive RKF45 propagation")
    sp.add_argument("a_km", type=float)
    sp.add_argument("e", type=float)
    sp.add_argument("i_deg", type=float)
    sp.add_argument("raan_deg", type=float)
    sp.add_argument("argp_deg", type=float)
    sp.add_argument("nu_deg", type=float)
    sp.add_argument("dt", type=float)
    sp.add_argument("--rtol", type=float, default=1e-9)
    sp.add_argument("--body", type=_body_arg, default=EARTH)
    sp.set_defaults(func=cmd_rkf45)

    # groundtrack
    sp = sub.add_parser("groundtrack", help="Generate ground-track lat/lon points")
    sp.add_argument("a_km", type=float)
    sp.add_argument("i_deg", type=float)
    sp.add_argument("step_s", type=float)
    sp.add_argument("num_pts", type=int)
    sp.add_argument("--body", type=_body_arg, default=EARTH)
    sp.set_defaults(func=cmd_groundtrack)

    # j2
    sp = sub.add_parser("j2", help="J2 perturbation drift analysis")
    sp.add_argument("a_km", type=float)
    sp.add_argument("e", type=float)
    sp.add_argument("i_deg", type=float)
    sp.add_argument("dt", type=float, nargs="?", default=86400.0)
    sp.add_argument("--body", type=_body_arg, default=EARTH)
    sp.set_defaults(func=cmd_j2)

    # tle
    sp = sub.add_parser("tle", help="Parse a TLE file")
    sp.add_argument("file", help="Path to TLE file")
    sp.set_defaults(func=cmd_tle)

    # lagrange
    sp = sub.add_parser("lagrange", help="Compute Lagrange point positions")
    sp.add_argument("body1", help="Primary body name")
    sp.add_argument("body2", help="Secondary body name")
    sp.set_defaults(func=cmd_lagrange)

    # rgt
    sp = sub.add_parser("rgt", help="Compute repeat-ground-track orbit")
    sp.add_argument("N", type=int, help="Revolutions per repeat cycle")
    sp.add_argument("D", type=int, help="Nodal days per repeat cycle")
    sp.add_argument("i_deg", type=float)
    sp.add_argument("--eccentricity", type=float, default=0.0)
    sp.add_argument("--body", type=_body_arg, default=EARTH)
    sp.set_defaults(func=cmd_rgt)

    # frozen
    sp = sub.add_parser("frozen", help="Compute frozen-orbit argument of perigee")
    sp.add_argument("a_km", type=float)
    sp.add_argument("e", type=float)
    sp.add_argument("i_deg", type=float)
    sp.add_argument("--body", type=_body_arg, default=EARTH)
    sp.set_defaults(func=cmd_frozen)

    # porkchop
    sp = sub.add_parser("porkchop", help="Generate porkchop plot data")
    sp.add_argument("r1x", type=float); sp.add_argument("r1y", type=float); sp.add_argument("r1z", type=float)
    sp.add_argument("r2x", type=float); sp.add_argument("r2y", type=float); sp.add_argument("r2z", type=float)
    sp.add_argument("tof_min", type=float)
    sp.add_argument("tof_max", type=float)
    sp.add_argument("--n-tof", type=int, default=20, dest="n_tof")
    sp.add_argument("--ascii", action="store_true", help="Also print ASCII plot")
    sp.add_argument("--body", type=_body_arg, default=EARTH)
    sp.set_defaults(func=cmd_porkchop)

    # visualize
    sp = sub.add_parser("visualize", help="ASCII orbit + ground-track visualization")
    sp.add_argument("a_km", type=float)
    sp.add_argument("e", type=float)
    sp.add_argument("i_deg", type=float)
    sp.add_argument("raan_deg", type=float, nargs="?", default=0.0)
    sp.add_argument("argp_deg", type=float, nargs="?", default=0.0)
    sp.add_argument("nu_deg", type=float, nargs="?", default=0.0)
    sp.add_argument("--points", type=int, default=80)
    sp.add_argument("--body", type=_body_arg, default=EARTH)
    sp.set_defaults(func=cmd_visualize)

    # visibility
    sp = sub.add_parser("visibility", help="Ground-station visibility windows")
    sp.add_argument("a_km", type=float)
    sp.add_argument("i_deg", type=float)
    sp.add_argument("lat_deg", type=float)
    sp.add_argument("lon_deg", type=float)
    sp.add_argument("duration", type=float, help="Propagation duration [s]")
    sp.add_argument("--step", type=float, default=60.0, dest="step")
    sp.add_argument("--min-el", type=float, default=5.0, dest="min_el")
    sp.add_argument("--body", type=_body_arg, default=EARTH)
    sp.set_defaults(func=cmd_visibility)

    # config
    sp = sub.add_parser("config", help="Run a mission from a config file")
    sp.add_argument("file", help="Path to YAML/JSON/TOML config file")
    sp.add_argument("--verbose", action="store_true")
    sp.set_defaults(func=cmd_config)

    # eclipse
    sp = sub.add_parser("eclipse", help="Check if a satellite is in Earth's umbra")
    sp.add_argument("a_km", type=float)
    sp.add_argument("e", type=float)
    sp.add_argument("i_deg", type=float)
    sp.add_argument("nu_deg", type=float)
    sp.add_argument("--jd", type=float, default=0.0, help="Julian Date")
    sp.add_argument("--body", type=_body_arg, default=EARTH)
    sp.set_defaults(func=cmd_eclipse)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()