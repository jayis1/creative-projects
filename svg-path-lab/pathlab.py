"""Parse and inspect the geometry of SVG path data without third-party packages."""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

_TOKEN = re.compile(r"[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?")
_ARITY = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "Z": 0}


@dataclass(frozen=True)
class Segment:
    kind: str
    points: tuple[tuple[float, float], ...]


def tokenize(data: str) -> list[str]:
    """Tokenize supported SVG path syntax, rejecting every unconsumed character."""
    tokens: list[str] = []
    pos = 0
    while pos < len(data):
        if data[pos].isspace() or data[pos] == ",":
            pos += 1
            continue
        match = _TOKEN.match(data, pos)
        if not match:
            raise ValueError(f"invalid path character at offset {pos}: {data[pos]!r}")
        tokens.append(match.group())
        pos = match.end()
    return tokens


def parse_path(data: str) -> list[Segment]:
    """Parse M/L/H/V/C/S/Q/T/Z, including relative and repeated parameter groups."""
    toks = tokenize(data)
    out: list[Segment] = []
    i, cmd = 0, None
    started = False
    x = y = sx = sy = 0.0
    previous = ""
    last_cubic: tuple[float, float] | None = None
    last_quad: tuple[float, float] | None = None

    def number() -> float:
        nonlocal i
        if i >= len(toks) or toks[i].isalpha():
            raise ValueError("incomplete command parameters")
        value = float(toks[i]); i += 1
        if not math.isfinite(value):
            raise ValueError("coordinates must be finite")
        return value

    while i < len(toks):
        if toks[i].isalpha():
            cmd = toks[i]; i += 1
            if cmd.upper() not in _ARITY:
                raise ValueError(f"unsupported command {cmd!r}")
            if not started and cmd.upper() != "M":
                raise ValueError("path must start with moveto (M)")
        elif cmd is None:
            raise ValueError("path must start with a command")
        assert cmd is not None
        upper, rel = cmd.upper(), cmd.islower()
        if upper == "Z":
            if out:
                out.append(Segment("L", ((x, y), (sx, sy))))
            x, y = sx, sy
            previous, last_cubic, last_quad = "Z", None, None
            cmd = None
            continue
        arity = _ARITY[upper]
        if i >= len(toks) or toks[i].isalpha():
            raise ValueError(f"command {cmd!r} requires parameters")
        while i < len(toks) and not toks[i].isalpha():
            vals = [number() for _ in range(arity)]
            if upper in ("M", "L"):
                nx, ny = vals
                if rel: nx, ny = x + nx, y + ny
                kind = "L"
                if upper == "M" and not started:
                    sx, sy = nx, ny
                    started = True
                else:
                    out.append(Segment(kind, ((x, y), (nx, ny))))
                x, y = nx, ny
                if upper == "M": cmd = "l" if rel else "L"
                last_cubic = last_quad = None
            elif upper == "T":
                nx, ny = vals
                if rel: nx, ny = x + nx, y + ny
                q = (2*x-last_quad[0],2*y-last_quad[1]) if previous in ("Q","T") and last_quad else (x,y)
                out.append(Segment("Q", ((x,y),q,(nx,ny))))
                x,y=nx,ny; last_quad=q; last_cubic=None
            elif upper in ("H", "V"):
                nx = (x + vals[0] if rel else vals[0]) if upper == "H" else x
                ny = (y + vals[0] if rel else vals[0]) if upper == "V" else y
                out.append(Segment("L", ((x, y), (nx, ny))))
                x, y = nx, ny; last_cubic = last_quad = None
            elif upper == "C":
                x1,y1,x2,y2,nx,ny = vals
                if rel: x1,y1,x2,y2,nx,ny = x+x1,y+y1,x+x2,y+y2,x+nx,y+ny
                out.append(Segment("C", ((x,y),(x1,y1),(x2,y2),(nx,ny))))
                x,y=nx,ny; last_cubic=(x2,y2); last_quad=None
            elif upper == "S":
                x2,y2,nx,ny = vals
                if rel: x2,y2,nx,ny = x+x2,y+y2,x+nx,y+ny
                c1 = (2*x-last_cubic[0],2*y-last_cubic[1]) if previous in ("C","S") and last_cubic else (x,y)
                out.append(Segment("C", ((x,y),c1,(x2,y2),(nx,ny))))
                x,y=nx,ny; last_cubic=(x2,y2); last_quad=None
            elif upper == "Q":
                qx,qy,nx,ny=vals
                if rel: qx,qy,nx,ny=x+qx,y+qy,x+nx,y+ny
                out.append(Segment("Q", ((x,y),(qx,qy),(nx,ny))))
                x,y=nx,ny; last_quad=(qx,qy); last_cubic=None
            elif upper == "T":
                nx,ny=vals
                if rel: nx,ny=x+nx,y+ny
                q=(2*x-last_quad[0],2*y-last_quad[1]) if previous in ("Q","T") and last_quad else (x,y)
                out.append(Segment("Q", ((x,y),q,(nx,ny))))
                x,y=nx,ny; last_quad=q; last_cubic=None
            previous = upper
    return out


def _bezier(points: tuple[tuple[float,float], ...], t: float) -> tuple[float,float]:
    u=1-t
    if len(points) == 2:
        (x0,y0),(x1,y1)=points
        return x0+(x1-x0)*t, y0+(y1-y0)*t
    if len(points)==3:
        (x0,y0),(x1,y1),(x2,y2)=points
        return u*u*x0+2*u*t*x1+t*t*x2, u*u*y0+2*u*t*y1+t*t*y2
    (x0,y0),(x1,y1),(x2,y2),(x3,y3)=points
    return u**3*x0+3*u*u*t*x1+3*u*t*t*x2+t**3*x3, u**3*y0+3*u*u*t*y1+3*u*t*t*y2+t**3*y3


def flatten(segments: list[Segment], steps: int = 16) -> list[tuple[float,float]]:
    """Sample curves evenly in parameter space; output includes every segment endpoint."""
    if not isinstance(steps, int) or isinstance(steps, bool) or not 1 <= steps <= 10000:
        raise ValueError("steps must be an integer from 1 to 10000")
    points: list[tuple[float,float]] = []
    for seg in segments:
        if seg.kind == "L":
            if not points: points.append(seg.points[0])
            points.append(seg.points[-1])
        else:
            if not points: points.append(seg.points[0])
            points.extend(_bezier(seg.points,j/steps) for j in range(1,steps+1))
    return points


def analyze(data: str, steps: int = 32) -> dict[str, object]:
    """Return segment count, approximate length, and sampled-curve bounds."""
    segments = parse_path(data)
    pts = flatten(segments, steps)
    if not pts:
        return {"segments": 0, "length": 0.0, "bounds": None}
    length = sum(math.hypot(b[0]-a[0], b[1]-a[1]) for a,b in zip(pts,pts[1:]))
    return {"segments": len(segments), "length": length,
            "bounds": (min(p[0] for p in pts), min(p[1] for p in pts),
                       max(p[0] for p in pts), max(p[1] for p in pts))}


def analyze_svg(source: str, steps: int = 32) -> list[dict[str, object]]:
    """Analyze every SVG <path d=...> in an XML document; do not fetch external resources."""
    try:
        root = ET.fromstring(source)
    except ET.ParseError as exc:
        raise ValueError(f"invalid SVG/XML: {exc}") from exc
    results = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] == "path" and "d" in element.attrib:
            item = analyze(element.attrib["d"], steps)
            item["id"] = element.get("id")
            results.append(item)
    if not results:
        raise ValueError("SVG contains no path elements with a d attribute")
    return results