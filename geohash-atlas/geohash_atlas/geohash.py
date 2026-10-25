"""Geohash encoding, decoding, and neighborhood operations."""
from dataclasses import dataclass

_ALPHABET = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE = {c: i for i, c in enumerate(_ALPHABET)}

@dataclass(frozen=True)
class Bounds:
    south: float
    west: float
    north: float
    east: float


def encode(latitude: float, longitude: float, precision: int = 8) -> str:
    """Encode coordinates as a base-32 geohash of the requested length."""
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("latitude/longitude outside valid range")
    if not isinstance(precision, int) or not 1 <= precision <= 12:
        raise ValueError("precision must be an integer from 1 to 12")
    lat_range, lon_range = [-90.0, 90.0], [-180.0, 180.0]
    bits = (16, 8, 4, 2, 1)
    out, even = [], True
    while len(out) < precision:
        value = 0
        for mask in bits:
            bounds = lon_range if even else lat_range
            coordinate = longitude if even else latitude
            midpoint = (bounds[0] + bounds[1]) / 2
            if coordinate >= midpoint:
                value |= mask
                bounds[0] = midpoint
            else:
                bounds[1] = midpoint
            even = not even
        out.append(_ALPHABET[value])
    return "".join(out)


def decode(code: str) -> Bounds:
    """Return the geographic cell bounds represented by a geohash."""
    if not isinstance(code, str) or not 1 <= len(code) <= 12:
        raise ValueError("geohash must contain 1 to 12 characters")
    if any(c not in _DECODE for c in code):
        raise ValueError("geohash contains an invalid character")
    lat, lon = [-90.0, 90.0], [-180.0, 180.0]
    even = True
    for char in code:
        for mask in (16, 8, 4, 2, 1):
            bounds = lon if even else lat
            midpoint = sum(bounds) / 2
            bounds[0 if _DECODE[char] & mask else 1] = midpoint
            even = not even
    return Bounds(lat[0], lon[0], lat[1], lon[1])
