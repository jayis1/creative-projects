#!/usr/bin/env python3
"""Demo: TLE parsing and ISS orbit visualisation.

Run from the orbital-mechanics directory:
    python3 examples/demo_tle.py
"""
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orbital import (
    parse_tle_set, multi_step_propagate, ground_track,
    propagate_kepler, ascii_orbit_xy, ascii_ground_track,
    visibility_windows, access_summary,
)
import numpy as np


def main():
    with open(os.path.join(os.path.dirname(__file__), "iss.tle")) as f:
        tles = parse_tle_set(f.read())
    tle = tles[0]
    print(f"=== ISS TLE ===\n{tle}")
    elems = tle.to_elements()
    print(f"  a = {elems.a/1000:.1f} km  e = {elems.e:.5f}")
    print(f"  Period = {elems.period/60:.2f} min")

    # Propagate one orbit
    from orbital import elements_to_rv, EARTH
    sv0 = elements_to_rv(elems, EARTH)
    states = multi_step_propagate(sv0, EARTH, elems.period, elems.period / 80)
    print("\n=== Orbit (XY plane) ===")
    print(ascii_orbit_xy(states, title="ISS Orbit (XY projection)"))

    # Ground track
    pts = ground_track(states, EARTH, gmst0=0.0)
    print("\n=== Ground Track ===")
    print(ascii_ground_track(pts, title="ISS Ground Track (1 orbit)"))

    # Visibility from a ground station at 40°N, 0°E
    print("\n=== Visibility from 40°N, 0°E ===")
    passes = visibility_windows(states, math.radians(40), 0,
                                min_elevation=math.radians(5))
    for p in passes:
        print(f"  {access_summary(p)}")
    if not passes:
        print("  No passes above 5° in this time window.")


if __name__ == "__main__":
    main()