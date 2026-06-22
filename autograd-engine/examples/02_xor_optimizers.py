"""Example 2: Training an MLP on XOR with different optimizers.

Compares SGD, SGD+momentum, and Adam on the XOR problem.
"""

import random
from autograd_engine import MLP
from autograd_engine.train import SGD, Adam, train, accuracy


def main():
    print("=== XOR Training: Optimizer Comparison ===\n")

    xs = [[0, 0], [0, 1], [1, 0], [1, 1]]
    ys = [0, 1, 1, 0]

    configs = [
        ("SGD (lr=0.1)", SGD, {"lr": 0.1}),
        ("SGD+momentum (lr=0.05, m=0.9)", SGD, {"lr": 0.05, "momentum": 0.9}),
        ("Adam (lr=0.01)", Adam, {"lr": 0.01}),
        ("Adam (lr=0.005, wd=0.001)", Adam, {"lr": 0.005, "weight_decay": 0.001}),
    ]

    for name, OptClass, opt_kwargs in configs:
        random.seed(42)
        model = MLP(2, [8, 8, 1], activation="tanh")
        opt = OptClass(model.parameters(), **opt_kwargs)
        history = train(model, xs, ys, epochs=200, optimizer=opt,
                         classification=True, seed=42)
        acc = accuracy(model, xs, ys)
        print(f"{name:35s} -> final_loss={history[-1]:.6f}, acc={acc:.0%}")


if __name__ == "__main__":
    main()