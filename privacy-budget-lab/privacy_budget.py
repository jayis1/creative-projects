"""Small, auditable differential-privacy mechanisms and basic composition."""
from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class PrivacyCost:
    """An (epsilon, delta)-DP guarantee; delta is in [0, 1)."""
    epsilon: float
    delta: float = 0.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.epsilon) or self.epsilon < 0:
            raise ValueError("epsilon must be finite and non-negative")
        if not math.isfinite(self.delta) or not 0 <= self.delta < 1:
            raise ValueError("delta must be finite and in [0, 1)")

    def compose(self, other: "PrivacyCost") -> "PrivacyCost":
        return PrivacyCost(self.epsilon + other.epsilon,
                           min(math.nextafter(1.0, 0.0), self.delta + other.delta))


def clamp_count(value: float, lower: float, upper: float) -> float:
    """Clip one numeric contribution to public bounds."""
    if not all(map(math.isfinite, (value, lower, upper))) or lower > upper:
        raise ValueError("value and ordered bounds must be finite")
    return min(upper, max(lower, value))


def laplace_noise(scale: float, rng: random.Random | None = None) -> float:
    """Draw centered Laplace noise using inverse-CDF sampling."""
    if not math.isfinite(scale) or scale < 0:
        raise ValueError("scale must be finite and non-negative")
    if scale == 0:
        return 0.0
    source = rng or random.SystemRandom()
    # random() may return 0; shifting by half a ULP avoids log(0).
    u = source.random() - 0.5
    if u == 0:
        return 0.0
    return -scale * math.copysign(math.log1p(-2 * abs(u)), u)


def private_sum(values: Iterable[float], *, lower: float, upper: float,
                epsilon: float, rng: random.Random | None = None) -> tuple[float, PrivacyCost]:
    """Release clipped sum for add/remove-one adjacency and L1 sensitivity."""
    if not math.isfinite(epsilon) or epsilon <= 0:
        raise ValueError("epsilon must be finite and positive")
    if not math.isfinite(lower) or not math.isfinite(upper) or lower > upper:
        raise ValueError("finite ordered bounds required")
    clipped = [clamp_count(float(v), lower, upper) for v in values]
    sensitivity = max(abs(lower), abs(upper), abs(upper - lower))
    # For a bounded per-person value under add/remove adjacency, |x| is sensitivity.
    sensitivity = max(abs(lower), abs(upper))
    return sum(clipped) + laplace_noise(sensitivity / epsilon, rng), PrivacyCost(epsilon)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("values", nargs="*", type=float, default=[1, 2, 3, 4])
    parser.add_argument("--lower", type=float, default=0.0)
    parser.add_argument("--upper", type=float, default=10.0)
    parser.add_argument("--epsilon", type=float, default=1.0)
    parser.add_argument("--seed", type=int, help="reproducible demo randomness; not for real private releases")
    args = parser.parse_args(argv)
    rng = random.Random(args.seed) if args.seed is not None else None
    answer, cost = private_sum(args.values, lower=args.lower, upper=args.upper,
                               epsilon=args.epsilon, rng=rng)
    print(json.dumps({"noisy_sum": answer, "epsilon": cost.epsilon,
                      "delta": cost.delta, "contributions": len(args.values)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
