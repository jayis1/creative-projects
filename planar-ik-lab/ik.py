"""Planar articulated-arm inverse kinematics using damped least squares."""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class Arm:
    lengths: tuple[float, ...]
    angles: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.lengths or len(self.lengths) != len(self.angles):
            raise ValueError("lengths and angles must have the same non-zero size")
        if any(not math.isfinite(x) or x <= 0 for x in self.lengths):
            raise ValueError("link lengths must be finite and positive")
        if any(not math.isfinite(x) for x in self.angles):
            raise ValueError("angles must be finite")

    def joints(self, angles: Sequence[float] | None = None) -> list[tuple[float, float]]:
        qs = self.angles if angles is None else angles
        if len(qs) != len(self.lengths):
            raise ValueError("angle count does not match link count")
        x = y = heading = 0.0
        points = [(x, y)]
        for length, angle in zip(self.lengths, qs):
            heading += angle
            x += length * math.cos(heading)
            y += length * math.sin(heading)
            points.append((x, y))
        return points

    def solve(self, target: tuple[float, float], *, iterations: int = 500,
              tolerance: float = 1e-5, damping: float = 0.05,
              max_step: float = 0.2,
              joint_limits: Sequence[tuple[float, float]] | None = None) -> tuple[tuple[float, ...], float, int]:
        """Return (angles, final error, iterations used), keeping joints unwrapped."""
        if len(target) != 2 or any(not math.isfinite(v) for v in target):
            raise ValueError("target must contain two finite coordinates")
        if iterations < 0 or iterations > 100_000:
            raise ValueError("iterations must be between 0 and 100000")
        if tolerance <= 0 or not math.isfinite(tolerance):
            raise ValueError("tolerance must be finite and positive")
        if damping <= 0 or not math.isfinite(damping):
            raise ValueError("damping must be finite and positive")
        if max_step <= 0 or not math.isfinite(max_step):
            raise ValueError("max_step must be finite and positive")
        q = list(self.angles)
        limits = None
        if joint_limits is not None:
            if len(joint_limits) != len(q):
                raise ValueError("joint_limits must have one pair per link")
            limits = []
            for low, high in joint_limits:
                if not (math.isfinite(low) and math.isfinite(high) and low <= high):
                    raise ValueError("each joint limit must be finite and ordered")
                limits.append((low, high))
            q = [max(lo, min(hi, angle)) for angle, (lo, hi) in zip(q, limits)]
        used = 0
        for used in range(iterations + 1):
            pts = self.joints(q)
            ex, ey = target[0] - pts[-1][0], target[1] - pts[-1][1]
            error = math.hypot(ex, ey)
            if error <= tolerance or used == iterations:
                return tuple(q), error, used
            # Jacobian column for revolute joint i: perpendicular to end-effector radius.
            jx, jy = [], []
            for px, py in pts[:-1]:
                jx.append(-(pts[-1][1] - py))
                jy.append(pts[-1][0] - px)
            # Solve (J J^T + lambda^2 I) z = error, then dq = J^T z.
            a = sum(v * v for v in jx) + damping * damping
            b = sum(x * y for x, y in zip(jx, jy))
            c = sum(v * v for v in jy) + damping * damping
            det = a * c - b * b
            zx, zy = (c * ex - b * ey) / det, (a * ey - b * ex) / det
            for i in range(len(q)):
                delta = jx[i] * zx + jy[i] * zy
                q[i] += max(-max_step, min(max_step, delta))
                if limits is not None:
                    # Clamp after every update so no intermediate pose violates a hard stop.
                    q[i] = max(limits[i][0], min(limits[i][1], q[i]))
        raise AssertionError("unreachable")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lengths", default="1,1,0.7", help="comma-separated link lengths")
    parser.add_argument("--angles", default="0,0,0", help="initial joint angles in radians")
    parser.add_argument("--target", default="1.5,1.2", help="target x,y")
    parser.add_argument("--iterations", type=int, default=500)
    parser.add_argument("--tolerance", type=float, default=1e-5)
    parser.add_argument("--damping", type=float, default=0.05, help="DLS damping factor")
    parser.add_argument("--max-step", type=float, default=0.2, help="maximum joint update in radians")
    parser.add_argument("--joint-limits", help="optional JSON array of [min,max] radian pairs")
    args = parser.parse_args()
    try:
        lengths = tuple(float(x) for x in args.lengths.split(","))
        angles = tuple(float(x) for x in args.angles.split(","))
        target_values = tuple(float(x) for x in args.target.split(","))
        if len(target_values) != 2:
            raise ValueError("target must contain two finite coordinates")
        target = (target_values[0], target_values[1])
        joint_limits = json.loads(args.joint_limits) if args.joint_limits else None
        arm = Arm(lengths, angles)
        result, error, used = arm.solve(
            target, iterations=args.iterations, tolerance=args.tolerance,
            damping=args.damping, max_step=args.max_step,
            joint_limits=joint_limits,
        )
    except (ValueError, OverflowError) as exc:
        parser.error(str(exc))
    print(json.dumps({"angles_radians": result, "joints": arm.joints(result),
                      "error": error, "iterations": used}, indent=2))


if __name__ == "__main__":
    main()
