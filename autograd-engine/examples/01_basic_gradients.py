"""Example 1: Basic gradient computation and the chain rule.

Demonstrates how to compute derivatives of arbitrary functions using the
autograd engine.
"""

from autograd_engine import Value


def main():
    print("=== Basic Gradient Computation ===\n")

    # Simple: y = x^2 + 3x + 1, dy/dx = 2x + 3
    x = Value(2.0, label="x")
    y = x ** 2 + 3 * x + 1
    y.backward()
    print(f"y = x^2 + 3x + 1 at x=2: y={y.data:.4f}, dy/dx={x.grad:.4f} (expected 7.0)")

    # Chain rule: y = sin(x^2) approximated via tanh
    x = Value(1.5, label="x")
    y = (x ** 2).tanh()
    y.backward()
    print(f"y = tanh(x^2) at x=1.5: y={y.data:.4f}, dy/dx={x.grad:.4f}")

    # Multi-variable: z = x*y + x^2
    x = Value(3.0, label="x")
    y = Value(4.0, label="y")
    z = x * y + x ** 2
    z.backward()
    print(f"z = x*y + x^2 at x=3, y=4: z={z.data:.4f}")
    print(f"  dz/dx = {x.grad:.4f} (expected 10.0)")
    print(f"  dz/dy = {y.grad:.4f} (expected 3.0)")

    # Using sigmoid
    x = Value(0.5, label="x")
    y = x.sigmoid()
    y.backward()
    print(f"\ny = sigmoid(x) at x=0.5: y={y.data:.4f}, dy/dx={x.grad:.4f}")
    print(f"  (expected y≈0.6225, dy/dx≈0.2350)")


if __name__ == "__main__":
    main()