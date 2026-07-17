"""CSV / JSON export utilities for orbital state series and ground tracks."""
from __future__ import annotations

import csv
import json
import math
import os
from typing import Iterable, List, Sequence, Tuple

import numpy as np

from .elements import OrbitalElements, StateVector
from .bodies import Body
from .elements import rv_to_elements


def states_to_csv(states: Sequence[StateVector], body: Body, path: str) -> None:
    """Write a time series of state vectors to a CSV file.

    Columns: t, x, y, z, vx, vy, vz, |r|, |v|, a, e, i, raan, argp, nu
    """
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_s", "x_m", "y_m", "z_m", "vx_ms", "vy_ms", "vz_ms",
                    "r_mag_m", "v_mag_ms", "a_m", "e", "i_deg", "raan_deg",
                    "argp_deg", "nu_deg"])
        for s in states:
            try:
                elems = rv_to_elements(s, body)
                row = [
                    s.t, s.r[0], s.r[1], s.r[2], s.v[0], s.v[1], s.v[2],
                    float(np.linalg.norm(s.r)), float(np.linalg.norm(s.v)),
                    elems.a, elems.e, math.degrees(elems.i),
                    math.degrees(elems.raan), math.degrees(elems.argp),
                    math.degrees(elems.nu),
                ]
            except (ValueError, ZeroDivisionError):
                row = [s.t, s.r[0], s.r[1], s.r[2], s.v[0], s.v[1], s.v[2],
                       float(np.linalg.norm(s.r)), float(np.linalg.norm(s.v)),
                       "", "", "", "", "", ""]
            w.writerow(row)


def groundtrack_to_csv(points: Iterable[Tuple[float, float]], path: str) -> None:
    """Write ground-track (lat, lon) pairs to a CSV file."""
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["lat_deg", "lon_deg"])
        for lat, lon in points:
            w.writerow([math.degrees(lat), math.degrees(lon)])


def states_to_json(states: Sequence[StateVector], path: str) -> None:
    """Write a time series of state vectors to a JSON file."""
    out = []
    for s in states:
        out.append({
            "t": s.t,
            "r": s.r.tolist(),
            "v": s.v.tolist(),
        })
    with open(path, "w") as f:
        json.dump(out, f, indent=2)