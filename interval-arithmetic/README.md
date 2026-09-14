# Interval Arithmetic

Interval Arithmetic is a pure-Python numerical reliability toolkit for computing conservative bounds when inputs are uncertain. It is useful for validating simulations, propagating measurement error, and checking whether floating-point calculations can cross a safety threshold.

## Quickstart

From this directory:

```bash
PYTHONPATH=. python3 -m interval_arithmetic.cli add 10 0.5 --width 0.1
# {"lower": 10.299999999999999, "upper": 10.700000000000001}
```

The `--width` option turns each number into a closed interval around its center. Division fails clearly when the denominator interval contains zero.

## How it works

`Interval` stores `[lower, upper]` and uses outward rounding (`math.nextafter`) after each operation, so the mathematical result remains enclosed despite ordinary binary floating-point rounding. Addition, subtraction, multiplication, reciprocal-based division, intersection, midpoint, radius, and width are supported. `interval_sum` and `interval_product` fold an iterable without losing the conservative bounds.

## Python API

```python
from interval_arithmetic import Interval

voltage = Interval(4.9, 5.1)
resistance = Interval(99, 101)
current = voltage / resistance
assert 0.048 < current.midpoint() < 0.052
```

## Tests and scope

Run `PYTHONPATH=. python3 -m unittest discover -s tests -v`. The project has no third-party dependencies and is intentionally offline. It currently handles real scalar intervals only; transcendental functions, interval vectors, and dependency-aware expressions are planned enhancements.

## Non-goals

This is not a replacement for arbitrary-precision validated numerics, symbolic algebra, or a probability distribution package. Bounds are conservative, not a statement of likelihood.
