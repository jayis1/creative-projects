"""Example 6: Config-file-driven training.

Shows how to define a full training configuration in JSON and run it.
"""

import json
import tempfile
import os

from autograd_engine.config import Config
from autograd_engine.train import train, accuracy
from autograd_engine.serialization import save_model


CONFIG = {
    "model": {
        "nin": 2,
        "nouts": [8, 8, 1],
        "activation": "tanh",
        "init": "xavier",
        "dropout": 0.0
    },
    "optimizer": {
        "type": "adam",
        "lr": 0.01,
        "weight_decay": 0.0
    },
    "training": {
        "epochs": 300,
        "batch_size": 4,
        "seed": 42,
        "classification": True,
        "lr_scheduler": {
            "type": "cosine",
            "base_lr": 0.01,
            "T_max": 300,
            "eta_min": 0.0001
        }
    },
    "logging": {
        "level": "INFO",
        "verbose": True
    }
}


def main():
    print("=== Config-Driven Training ===\n")

    # Write config to a temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(CONFIG, f, indent=2)
        config_path = f.name

    try:
        # Load config
        config = Config.load(config_path)
        print(f"Loaded config from {config_path}")
        print(f"  Model: nin={config.model.nin}, nouts={config.model.nouts}")
        print(f"  Optimizer: {config.optimizer.type}, lr={config.optimizer.lr}")
        print(f"  Epochs: {config.training.epochs}")
        print(f"  Scheduler: {config.training.lr_scheduler.type}")

        # Build model
        model = config.model.build()
        print(f"\nModel: {model} ({model.num_parameters()} params)")

        # Build optimizer
        optimizer = config.optimizer.build(model.parameters())

        # Build scheduler
        scheduler = config.training.build_scheduler()

        # XOR data
        xs = [[0, 0], [0, 1], [1, 0], [1, 1]]
        ys = [0, 1, 1, 0]

        # Train
        history = train(
            model, xs, ys,
            epochs=config.training.epochs,
            batch_size=config.training.batch_size,
            optimizer=optimizer,
            lr_scheduler=scheduler,
            seed=config.training.seed,
            classification=config.training.classification,
            verbose=config.logging.verbose,
        )

        print(f"\nFinal loss: {history[-1]:.6f}")
        acc = accuracy(model, xs, ys)
        print(f"Accuracy: {acc:.0%}")

    finally:
        os.unlink(config_path)


if __name__ == "__main__":
    main()