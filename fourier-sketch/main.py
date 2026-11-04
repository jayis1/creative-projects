#!/usr/bin/env python3
"""Approximate a closed 2D sketch with a truncated discrete Fourier series."""
from __future__ import annotations
import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Term:
    frequency: int
    real: float
    imag: float

    @property
    def amplitude(self) -> float:
        return math.hypot(self.real, self.imag)

def validate_points(points):
    if not isinstance(points, list) or len(points) < 2:
        raise ValueError("points must be a list containing at least two [x, y] pairs")
    result = []
    for i, p in enumerate(points):
        if not isinstance(p, (list, tuple)) or len(p) != 2:
            raise ValueError(f"point {i} must contain exactly x and y")
        x, y = p
        if isinstance(x, bool) or isinstance(y, bool) or not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise ValueError(f"point {i} coordinates must be numbers")
        x, y = float(x), float(y)
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError(f"point {i} coordinates must be finite")
        result.append(complex(x, y))
    return result

def dft(points):
    """Return all DFT coefficients, frequencies in natural signed order."""
    samples = validate_points(points)
    n = len(samples)
    terms = []
    for k in range(n):
        freq = k if k <= n // 2 else k - n
        value = sum(z * complex(math.cos(-2*math.pi*k*j/n), math.sin(-2*math.pi*k*j/n)) for j, z in enumerate(samples)) / n
        terms.append(Term(freq, value.real, value.imag))
    return terms

def reconstruct(terms, count, *, closed=True):
    """Evaluate the selected Fourier terms at count equally spaced times."""
    if isinstance(count, bool) or not isinstance(count, int) or count < 2:
        raise ValueError("count must be an integer >= 2")
    terms = list(terms)
    if not terms:
        raise ValueError("at least one Fourier term is required")
    if any(not isinstance(t, Term) or not all(map(math.isfinite, (t.real, t.imag))) for t in terms):
        raise ValueError("terms must be finite Term values")
    denominator = count if closed else count - 1
    output = []
    for i in range(count):
        t = i / denominator
        z = sum(complex(term.real, term.imag) * complex(math.cos(2*math.pi*term.frequency*t), math.sin(2*math.pi*term.frequency*t)) for term in terms)
        output.append([z.real, z.imag])
    return output

def select_terms(terms, count):
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ValueError("term count must be a positive integer")
    return sorted(terms, key=lambda x: (-x.amplitude, abs(x.frequency), x.frequency))[:count]

def write_svg(points, path, *, width=640, height=480, padding=24):
    """Write a self-contained SVG polyline, scaling even degenerate sketches."""
    pts = validate_points(points)
    for name, value in (("width", width), ("height", height), ("padding", padding)):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    if 2 * padding >= min(width, height):
        raise ValueError("padding must leave a drawable area")
    xs, ys = [p.real for p in pts], [p.imag for p in pts]
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    sx = (width - 2*padding) / (xmax-xmin) if xmax != xmin else 1.0
    sy = (height - 2*padding) / (ymax-ymin) if ymax != ymin else 1.0
    scale = min(sx, sy)
    ox = (width - scale*(xmax-xmin))/2 - scale*xmin
    oy = (height - scale*(ymax-ymin))/2 - scale*ymin
    # SVG's y axis points down; flip the sketch's conventional y axis.
    coords = " ".join(f"{ox+scale*x:.3f},{height-(oy+scale*y):.3f}" for x, y in zip(xs, ys))
    Path(path).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"><polyline fill="none" stroke="#1261a0" stroke-width="2" points="{coords}"/></svg>\n', encoding="utf-8")

def resample_polyline(points, count, *, closed=True):
    """Uniformly resample a stroke by arc length (closed by default for Fourier use)."""
    samples = validate_points(points)
    if not isinstance(closed, bool):
        raise ValueError("closed must be a boolean")
    if isinstance(count, bool) or not isinstance(count, int) or count < 2:
        raise ValueError("resample count must be an integer >= 2")
    segments = list(zip(samples, samples[1:]))
    if closed:
        segments.append((samples[-1], samples[0]))
    lengths = [abs(b-a) for a, b in segments]
    total = sum(lengths)
    if total == 0:
        return [[samples[0].real, samples[0].imag] for _ in range(count)]
    result = []
    for i in range(count):
        distance = total * i / count
        for (a, b), length in zip(segments, lengths):
            if distance <= length or (a, b) == segments[-1]:
                z = a if length == 0 else a + (b-a) * (distance / length)
                result.append([z.real, z.imag])
                break
            distance -= length
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON file containing a points array")
    parser.add_argument("output", type=Path, help="output SVG path")
    parser.add_argument("--terms", type=int, default=12, help="largest Fourier terms to retain")
    parser.add_argument("--samples", type=int, default=400, help="output curve samples")
    parser.add_argument("--resample", type=int, help="uniformly resample input by arc length before analysis")
    args = parser.parse_args(argv)
    try:
        obj = json.loads(args.input.read_text(encoding="utf-8"))
        points = obj["points"] if isinstance(obj, dict) else obj
        if args.resample is not None:
            points = resample_polyline(points, args.resample)
        chosen = select_terms(dft(points), args.terms)
        write_svg(reconstruct(chosen, args.samples), args.output)
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Wrote {args.output} using {len(chosen)} Fourier terms and {args.samples} samples")

if __name__ == "__main__":
    main()
