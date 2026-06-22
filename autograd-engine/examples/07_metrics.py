"""Example 7: Evaluation metrics.

Shows how to use the metrics module for classification and regression.
"""

import random

from autograd_engine import MLP
from autograd_engine.train import train, accuracy
from autograd_engine.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report,
    mean_squared_error, root_mean_squared_error,
    mean_absolute_error, r2_score,
)


def main():
    print("=== Evaluation Metrics ===\n")

    # --- Classification ---
    print("--- Classification Metrics ---\n")

    # Train on XOR
    random.seed(42)
    xs = [[0, 0], [0, 1], [1, 0], [1, 1]]
    ys = [0, 1, 1, 0]

    model = MLP(2, [8, 8, 1], activation="tanh")
    train(model, xs, ys, epochs=200, classification=True, seed=42)

    # Get predictions
    model.eval()
    y_true, y_pred = [], []
    for x, y in zip(xs, ys):
        pred = model(x)[0].data
        label = 1 if pred > 0.5 else 0
        y_true.append(y)
        y_pred.append(label)

    print(f"True labels:      {y_true}")
    print(f"Predicted labels: {y_pred}")
    print()

    print(f"Accuracy:  {accuracy_score(y_true, y_pred):.4f}")
    print(f"Precision: {precision_score(y_true, y_pred):.4f}")
    print(f"Recall:    {recall_score(y_true, y_pred):.4f}")
    print(f"F1 Score:  {f1_score(y_true, y_pred):.4f}")
    print()

    cm = confusion_matrix(y_true, y_pred)
    print("Confusion Matrix:")
    print(f"  Pred:    0    1")
    for i, row in enumerate(cm):
        print(f"  True {i}: {row[0]:>4} {row[1]:>4}")
    print()

    print("Classification Report:")
    print(classification_report(y_true, y_pred))

    # --- Regression ---
    print("\n--- Regression Metrics ---\n")

    y_true_r = [3.0, -0.5, 2.0, 7.0]
    y_pred_r = [2.5, 0.0, 2.0, 8.0]

    print(f"True:      {y_true_r}")
    print(f"Predicted: {y_pred_r}")
    print()
    print(f"MSE:  {mean_squared_error(y_true_r, y_pred_r):.4f}")
    print(f"RMSE: {root_mean_squared_error(y_true_r, y_pred_r):.4f}")
    print(f"MAE:  {mean_absolute_error(y_true_r, y_pred_r):.4f}")
    print(f"R²:   {r2_score(y_true_r, y_pred_r):.4f}")


if __name__ == "__main__":
    main()