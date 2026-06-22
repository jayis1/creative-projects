#!/usr/bin/env python3
"""Demo: train a tiny MLP to learn the XOR truth table."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from autograd_engine import MLP, Value
from autograd_engine.train import train, mean_squared_error


def main() -> int:
    # XOR truth table — 2 inputs, 1 output
    xs = [[0.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 1.0]]
    ys = [0.0, 1.0, 1.0, 0.0]

    model = MLP(2, [4, 4, 1], activation="tanh")
    print("Model:", model)
    print(f"Parameters: {len(model.parameters())}")

    history = train(model, xs, ys, epochs=500, lr=0.1, verbose=True)

    print("\nFinal predictions:")
    for x, y in zip(xs, ys):
        pred = model(x)[0].data
        print(f"  input={x}  target={y}  pred={pred:.4f}")

    final_loss = history[-1]
    print(f"\nFinal loss: {final_loss:.6f}")
    print("PASS" if final_loss < 0.05 else "FAIL")
    return 0 if final_loss < 0.05 else 1


if __name__ == "__main__":
    raise SystemExit(main())