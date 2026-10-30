#!/usr/bin/env python3
"""Small-room impulse responses using the rectangular image-source method."""
from __future__ import annotations
import argparse
import json
import math
from dataclasses import dataclass

@dataclass(frozen=True)
class Room:
    dimensions: tuple[float, float, float]
    source: tuple[float, float, float]
    receiver: tuple[float, float, float]
    absorption: tuple[float, float, float, float, float, float]
    speed: float = 343.0


def validate(room: Room) -> None:
    if any(not math.isfinite(v) or v <= 0 for v in room.dimensions):
        raise ValueError("room dimensions must be finite and positive")
    for label, point in (("source", room.source), ("receiver", room.receiver)):
        if len(point) != 3 or any(not math.isfinite(v) or v < 0 or v > room.dimensions[i] for i, v in enumerate(point)):
            raise ValueError(f"{label} must lie inside the room")
    if len(room.absorption) != 6 or any(not math.isfinite(a) or a < 0 or a > 1 for a in room.absorption):
        raise ValueError("six absorption coefficients in [0, 1] are required")
    if not math.isfinite(room.speed) or room.speed <= 0:
        raise ValueError("sound speed must be finite and positive")


def _axis_images(source: float, length: float, order: int):
    # Each integer image index has a corresponding number of wall crossings.
    for image_index in range(-order, order + 1):
        position = 2 * image_index * length + (source if image_index % 2 == 0 else 2 * length - source)
        reflections = abs(image_index)
        yield position, reflections


def impulse_response(room: Room, order: int = 2, duration: float = 0.25, sample_rate: int = 8000):
    """Return (samples, arrivals); arrivals contain time, amplitude, image index."""
    validate(room)
    if not isinstance(order, int) or not 0 <= order <= 20:
        raise ValueError("reflection order must be an integer in [0, 20]")
    if not math.isfinite(duration) or not 0 < duration <= 10:
        raise ValueError("duration must be in (0, 10] seconds")
    if not isinstance(sample_rate, int) or not 100 <= sample_rate <= 192000:
        raise ValueError("sample rate must be an integer in [100, 192000]")
    axes = [_axis_images(room.source[i], room.dimensions[i], order) for i in range(3)]
    sequences = [list(axis) for axis in axes]
    arrivals = []
    dt = 1.0 / sample_rate
    count = math.ceil(duration * sample_rate)
    for ix, (x, rx) in enumerate(sequences[0]):
        for iy, (y, ry) in enumerate(sequences[1]):
            for iz, (z, rz) in enumerate(sequences[2]):
                distance = math.dist((x, y, z), room.receiver)
                time = distance / room.speed
                if time >= duration or distance == 0:
                    continue
                # parity determines which of the two opposing walls was crossed
                hits = (rx, ry, rz)
                coeffs = room.absorption
                gain = 1.0
                for axis, n in enumerate(hits):
                    near, far = (axis * 2, axis * 2 + 1)
                    for bounce in range(n):
                        wall = near if (ix, iy, iz)[axis] % 2 == 0 else far
                        gain *= math.sqrt(1.0 - coeffs[wall])
                amplitude = gain / max(distance, 1e-9)
                arrivals.append((time, amplitude, (ix, iy, iz)))
    arrivals.sort(key=lambda a: (a[0], a[2]))
    samples = [0.0] * count
    for time, amplitude, _ in arrivals:
        index = round(time * sample_rate)
        if 0 <= index < count:
            samples[index] += amplitude
    return samples, arrivals


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--room", nargs=3, type=float, default=(6, 5, 3), metavar=("X", "Y", "Z"))
    parser.add_argument("--source", nargs=3, type=float, default=(1, 1, 1.5))
    parser.add_argument("--receiver", nargs=3, type=float, default=(4, 3, 1.5))
    parser.add_argument("--order", type=int, default=2)
    parser.add_argument("--duration", type=float, default=0.12)
    parser.add_argument("--rate", type=int, default=4000)
    parser.add_argument("--json", action="store_true", help="print arrival records as JSON")
    args = parser.parse_args(argv)
    room = Room(tuple(args.room), tuple(args.source), tuple(args.receiver), (0.2,) * 6)
    try:
        _, arrivals = impulse_response(room, args.order, args.duration, args.rate)
    except ValueError as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps([{"time_s": round(t, 6), "amplitude": round(a, 6), "image": list(i)} for t, a, i in arrivals], indent=2))
    else:
        print(f"room={args.room} m, order={args.order}, arrivals={len(arrivals)}")
        print("time (ms)   amplitude     image")
        for time, amplitude, image in arrivals[:20]:
            print(f"{time*1000:8.2f}   {amplitude:9.5f}   {image}")
        if len(arrivals) > 20:
            print(f"... {len(arrivals)-20} more")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
