#!/usr/bin/env python3
"""Demo: Hohmann transfer to GEO with porkchop visualisation.

Run from the orbital-mechanics directory:
    python3 examples/demo_hohmann.py
"""
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orbital import (
    EARTH, hohmann_transfer, bielliptic_transfer,
    porkchop_data, ascii_porkchop,
    plane_change_delta_v, combined_plane_change_delta_v,
)
import numpy as np


def main():
    # LEO to GEO Hohmann transfer
    r_leo = 6678e3  # 400 km altitude
    r_geo = 42164e3  # geostationary
    res = hohmann_transfer(EARTH, r_leo, r_geo)
    print("=== Hohmann Transfer: LEO → GEO ===")
    print(f"  Δv1 = {res.dv1:.1f} m/s")
    print(f"  Δv2 = {res.dv2:.1f} m/s")
    print(f"  Total Δv = {res.dv_total:.1f} m/s")
    print(f"  TOF = {res.tof/3600:.2f} hours")

    # Bi-elliptic via 100,000 km
    res_bi = bielliptic_transfer(EARTH, r_leo, r_geo, 100_000e3)
    print(f"\n=== Bi-Elliptic (rb=100,000 km) ===")
    print(f"  Total Δv = {res_bi.dv_total:.1f} m/s")
    print(f"  TOF = {res_bi.tof/3600:.2f} hours")

    # Plane change at GEO speed
    v_geo = math.sqrt(EARTH.mu / r_geo)
    dv_pc = plane_change_delta_v(v_geo, math.radians(28.5))
    print(f"\n=== Plane Change (28.5° at GEO) ===")
    print(f"  Δv = {dv_pc:.1f} m/s")

    # Porkchop plot between two LEO positions
    print("\n=== Porkchop Plot ===")
    r1 = np.array([7000e3, 0, 0])
    r2 = np.array([0, 7000e3, 0])
    data = porkchop_data(EARTH, r1, r2, (1500, 4000), n_tof=30)
    print(ascii_porkchop(data, title="LEO-LEO Porkchop (90° transfer)"))


if __name__ == "__main__":
    main()