"""Example 3: Using learning-rate schedulers.

Shows how different LR schedulers affect training dynamics.
"""

import random
from autograd_engine import MLP
from autograd_engine.train import SGD, train
from autograd_engine.schedulers import (
    StepLR, ExponentialLR, CosineAnnealingLR, WarmupLR, LRScheduler,
)


def main():
    print("=== Learning Rate Schedulers ===\n")

    xs = [[0, 0], [0, 1], [1, 0], [1, 1]]
    ys = [0, 1, 1, 0]

    schedulers = [
        ("No scheduler", None),
        ("StepLR (step=50, gamma=0.5)", StepLR(0.1, 50, 0.5)),
        ("ExponentialLR (gamma=0.99)", ExponentialLR(0.1, 0.99)),
        ("CosineAnnealing (T=200)", CosineAnnealingLR(0.1, 200, eta_min=0.001)),
        ("Warmup+Cosine (warmup=20)", WarmupLR(CosineAnnealingLR(0.1, 180), 20)),
    ]

    for name, scheduler in schedulers:
        random.seed(42)
        model = MLP(2, [8, 8, 1], activation="tanh")
        opt = SGD(model.parameters(), lr=0.1, momentum=0.9)
        history = train(model, xs, ys, epochs=200, optimizer=opt,
                         lr_scheduler=scheduler, classification=True, seed=42)
        final_lr = opt.lr
        print(f"{name:35s} -> final_loss={history[-1]:.6f}, final_lr={final_lr:.6f}")

    # Show LR over time for cosine
    print("\nCosine annealing LR schedule:")
    cos = CosineAnnealingLR(0.1, 100, eta_min=0.001)
    for epoch in [0, 25, 50, 75, 100]:
        print(f"  epoch {epoch:3d}: lr={cos.get_lr(epoch):.6f}")


if __name__ == "__main__":
    main()