"""Example 4: Extended activation functions.

Demonstrates all available activation functions and their gradients.
"""

from autograd_engine import Value
from autograd_engine.activations import (
    leaky_relu, elu, gelu, swish, softplus, mish, selu,
    hard_tanh, hard_sigmoid,
)


def main():
    print("=== Extended Activation Functions ===\n")

    activations = [
        ("leaky_relu", leaky_relu),
        ("elu", elu),
        ("gelu", gelu),
        ("swish", swish),
        ("softplus", softplus),
        ("mish", mish),
        ("selu", selu),
        ("hard_tanh", hard_tanh),
        ("hard_sigmoid", hard_sigmoid),
    ]

    test_vals = [-2.0, -0.5, 0.0, 0.5, 2.0]

    print(f"{'Activation':>15} | " + " | ".join(f"x={v:>5.1f}" for v in test_vals))
    print("-" * 80)

    for name, fn in activations:
        outputs = []
        for xv in test_vals:
            x = Value(xv)
            y = fn(x)
            y.backward()
            outputs.append(f"{y.data:>6.3f}({x.grad:>6.3f})")
        print(f"{name:>15} | " + " | ".join(outputs))

    print("\nFormat: output(gradient)")


if __name__ == "__main__":
    main()