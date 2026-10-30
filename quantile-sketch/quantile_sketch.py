"""Deterministic streaming quantile summaries using the Greenwald-Khanna sketch."""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path


@dataclass
class _Tuple:
    value: float
    g: int
    delta: int


class QuantileSketch:
    """Approximate rank queries in bounded memory (GK epsilon summary)."""
    def __init__(self, epsilon: float = 0.01):
        if not math.isfinite(epsilon) or not 0 < epsilon < 0.5:
            raise ValueError("epsilon must be finite and between 0 and 0.5")
        self.epsilon = epsilon
        self.n = 0
        self._summary: list[_Tuple] = []

    def insert(self, value: float) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("observations must be JSON/Python numbers, not booleans or strings")
        value = float(value)
        if not math.isfinite(value):
            raise ValueError("observations must be finite numbers")
        import bisect
        values = [item.value for item in self._summary]
        index = bisect.bisect_right(values, value)
        self.n += 1
        delta = 0 if index in (0, len(self._summary)) else max(0, math.floor(2 * self.epsilon * self.n) - 1)
        self._summary.insert(index, _Tuple(value, 1, delta))
        if self.n % max(1, int(1 / (2 * self.epsilon))) == 0:
            self._compress()

    def extend(self, values) -> None:
        for value in values:
            self.insert(value)

    def _compress(self) -> None:
        threshold = math.floor(2 * self.epsilon * self.n)
        i = len(self._summary) - 2
        while i > 0:
            left, right = self._summary[i], self._summary[i + 1]
            if left.g + right.g + right.delta <= threshold:
                right.g += left.g
                del self._summary[i]
            i -= 1

    def quantile(self, q: float) -> float:
        if not math.isfinite(q) or not 0 <= q <= 1:
            raise ValueError("q must be finite and in [0, 1]")
        if not self.n:
            raise ValueError("quantile of empty sketch")
        desired = q * (self.n - 1) + 1
        allowance = self.epsilon * self.n
        rank = 0
        previous = self._summary[0].value
        for item in self._summary:
            rank += item.g
            if rank + item.delta > desired + allowance:
                return previous
            previous = item.value
        return self._summary[-1].value

    @property
    def summary_size(self) -> int:
        return len(self._summary)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", help="JSON file containing a numeric array; stdin when omitted")
    parser.add_argument("--epsilon", type=float, default=0.01)
    parser.add_argument("--quantiles", type=float, nargs="+", default=[0, .25, .5, .75, .9, .99, 1])
    parser.add_argument("--demo", action="store_true", help="summarize a deterministic sample")
    parser.add_argument("--jsonl", action="store_true", help="read one JSON number per input line without buffering the stream")
    args = parser.parse_args(argv)
    if args.demo:
        values = [((i * 7919) % 10007) / 100 for i in range(10000)]
    elif args.jsonl:
        values = None
    else:
        try:
            text = Path(args.input).read_text(encoding="utf-8") if args.input else __import__("sys").stdin.read()
            values = json.loads(text)
            if not isinstance(values, list):
                raise ValueError("input JSON must be an array")
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            parser.error(str(exc))
    try:
        sketch = QuantileSketch(args.epsilon)
    except ValueError as exc:
        parser.error(str(exc))
    try:
        if values is None:
            import sys
            stream = Path(args.input).open(encoding="utf-8") if args.input else sys.stdin
            try:
                for line_number, line in enumerate(stream, 1):
                    if line.strip():
                        try:
                            sketch.insert(json.loads(line))
                        except (json.JSONDecodeError, TypeError, ValueError) as exc:
                            raise ValueError(f"invalid JSON number on line {line_number}: {exc}") from exc
            finally:
                if stream is not sys.stdin:
                    stream.close()
        else:
            sketch.extend(values)
        result = {str(q): sketch.quantile(q) for q in args.quantiles}
    except (TypeError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({"count": sketch.n, "summary_size": sketch.summary_size, "quantiles": result}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
