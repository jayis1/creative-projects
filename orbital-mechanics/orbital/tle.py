"""Two-Line Element (TLE) set parser.

NORAD TLE format::

    1 25544U 98067A   08264.51782528 -.00002182  00000-0 -11606-4 0  2927
    2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537

This module parses the two lines into a :class:`TLE` dataclass with
decoded Keplerian elements and optional SGP4-style mean element rates.

Reference: Kelso, T.S., "Frequently Asked Questions: Two-Line Element Set Format"
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from .bodies import EARTH, Body
from .elements import OrbitalElements


@dataclass
class TLE:
    """Decoded Two-Line Element set."""

    sat_num: int
    classification: str
    intl_desig: str
    epoch_year: int
    epoch_day: float
    ndot: float          # mean motion derivative [rev/day²] (1st derivative)
    nddot: float         # mean motion 2nd derivative [rev/day³]
    bstar: float         # drag term [1/earth radii]
    elset_num: int
    inclination: float   # [rad]
    raan: float          # [rad]
    eccentricity: float
    argp: float          # [rad]
    mean_anomaly: float  # [rad]
    mean_motion: float   # [rev/day]
    rev_num: int
    body: Body = EARTH

    @property
    def epoch(self) -> float:
        """Epoch as fractional year (e.g. 2008.2645)."""
        return 2000 + self.epoch_year if self.epoch_year < 57 else 1900 + self.epoch_year

    @property
    def semi_major_axis(self) -> float:
        """Semi-major axis [m] from mean motion."""
        n = self.mean_motion * 2.0 * math.pi / 86400.0  # rad/s
        return (self.body.mu / n ** 2) ** (1.0 / 3.0)

    def to_elements(self) -> OrbitalElements:
        """Convert to :class:`OrbitalElements` (mean anomaly → true anomaly)."""
        a = self.semi_major_axis
        M = self.mean_anomaly
        # Convert mean anomaly to true anomaly via Kepler (elliptic assumed).
        from .kepler import solve_kepler_e
        from .elements import eccentric_to_true
        E = solve_kepler_e(M, self.eccentricity)
        nu = eccentric_to_true(E, self.eccentricity)
        return OrbitalElements(
            a=a, e=self.eccentricity, i=self.inclination,
            raan=self.raan, argp=self.argp, nu=nu, mu=self.body.mu,
        )

    def __repr__(self) -> str:
        return (f"TLE(sat={self.sat_num}, epoch={self.epoch:.4f}, "
                f"i={math.degrees(self.inclination):.2f}°, "
                f"e={self.eccentricity:.5f}, "
                f"mm={self.mean_motion:.4f} rev/day)")


def parse_tle(line1: str, line2: str, body: Body = EARTH) -> TLE:
    """Parse two TLE lines into a :class:`TLE` object.

    Parameters
    ----------
    line1, line2 : str
        The two TLE lines (with or without a preceding name line).
    body : Body
        Central body (default Earth).

    Raises
    ------
    ValueError
        If the lines are malformed or checksums fail.
    """
    if len(line1) < 68 or len(line2) < 67:
        raise ValueError("TLE lines too short; expected ≥68 and ≥67 chars.")
    if line1[0] != "1":
        raise ValueError(f"Line 1 must start with '1'; got '{line1[0]}'")
    if line2[0] != "2":
        raise ValueError(f"Line 2 must start with '2'; got '{line2[0]}'")

    # Optional checksum validation (modulo-10).
    _check(line1)
    _check(line2)

    sat_num = int(line1[2:7])
    classification = line1[7].strip()
    intl_desig = line1[9:17].strip()
    epoch_year = int(line1[18:20])
    epoch_day = float(line1[20:32])
    # ndot: signed fixed-point, e.g. " .00002182"
    ndot_raw = line1[33:43].strip()
    ndot = float(ndot_raw) if ndot_raw else 0.0
    # nddot: exponential notation with implied decimal point
    nddot_raw = line1[44:52].strip()
    nddot = _parse_exp(nddot_raw) if nddot_raw else 0.0
    bstar_raw = line1[53:61].strip()
    bstar = _parse_exp(bstar_raw) if bstar_raw else 0.0
    elset_num = int(line1[64:68])

    inclination = math.radians(float(line2[8:16]))
    raan = math.radians(float(line2[17:25]))
    # Eccentricity: implied leading decimal point
    eccentricity = float("." + line2[26:33].strip())
    argp = math.radians(float(line2[34:42]))
    mean_anomaly = math.radians(float(line2[43:51]))
    mean_motion = float(line2[52:63])
    rev_num = int(line2[63:68])

    return TLE(
        sat_num=sat_num, classification=classification, intl_desig=intl_desig,
        epoch_year=epoch_year, epoch_day=epoch_day, ndot=ndot, nddot=nddot,
        bstar=bstar, elset_num=elset_num,
        inclination=inclination, raan=raan, eccentricity=eccentricity,
        argp=argp, mean_anomaly=mean_anomaly, mean_motion=mean_motion,
        rev_num=rev_num, body=body,
    )


def parse_tle_set(text: str, body: Body = EARTH) -> list[TLE]:
    """Parse a multi-line string containing one or more TLE sets.

    A name line (starting with a non-digit) preceding each pair is
    tolerated and discarded.
    """
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    tles: list[TLE] = []
    i = 0
    while i < len(lines) - 1:
        if lines[i][0] == "1" and lines[i + 1][0] == "2":
            tles.append(parse_tle(lines[i], lines[i + 1], body))
            i += 2
        else:
            i += 1
    return tles


def _check(line: str) -> None:
    """Validate the TLE modulo-10 checksum (last character)."""
    if not line[-1].isdigit():
        return  # some TLEs drop the checksum
    expected = int(line[-1])
    s = 0
    for ch in line[:-1]:
        if ch == "-":
            s += 1
        elif ch.isdigit():
            s += int(ch)
    if s % 10 != expected:
        raise ValueError(f"TLE checksum failed: computed {s % 10}, expected {expected}")


def _parse_exp(raw: str) -> float:
    """Parse TLE exponential notation: ``NNNNN+N`` → ``0.NNNNN×10^N``.

    The format is 5 digits, a sign, and a 1-digit exponent, with an
    implied decimal point after the first digit.
    """
    raw = raw.strip()
    if len(raw) < 7 or raw[5] not in "+-":
        return 0.0
    mantissa = float(raw[0] + "." + raw[1:5])
    exp = int(raw[5:7])
    return mantissa * (10.0 ** exp)