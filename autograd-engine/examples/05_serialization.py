"""Example 5: Model serialization — save and load.

Shows how to save a trained model to JSON and load it back.
"""

import tempfile
import os

from autograd_engine import MLP
from autograd_engine.train import Adam, train, accuracy
from autograd_engine.serialization import save_model, load_model


def main():
    print("=== Model Serialization ===\n")

    xs = [[0, 0], [0, 1], [1, 0], [1, 1]]
    ys = [0, 1, 1, 0]

    # Train a model
    model = MLP(2, [8, 8, 1], activation="tanh")
    opt = Adam(model.parameters(), lr=0.01)
    train(model, xs, ys, epochs=200, optimizer=opt, classification=True, seed=42)
    acc = accuracy(model, xs, ys)
    print(f"Trained model accuracy: {acc:.0%}")

    # Save
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = os.path.join(tmpdir, "model.json")
        save_model(model, model_path)
        print(f"Model saved to {model_path}")

        # Load
        loaded = load_model(model_path)
        print(f"Model loaded from {model_path}")

        # Verify predictions match
        print("\nPrediction comparison (original vs loaded):")
        for x in xs:
            p1 = model(x)[0].data
            p2 = loaded(x)[0].data
            print(f"  {x} => {p1:.6f} vs {p2:.6f}  (match: {abs(p1-p2) < 1e-10})")

        acc_loaded = accuracy(loaded, xs, ys)
        print(f"\nLoaded model accuracy: {acc_loaded:.0%}")


if __name__ == "__main__":
    main()