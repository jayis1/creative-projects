"""Example 8: Computation graph visualization.

Shows how to generate DOT output and ASCII loss charts.
"""

from autograd_engine import Value
from autograd_engine.train import train
from autograd_engine.viz import to_dot, ascii_loss_chart


def main():
    print("=== Graph Visualization ===\n")

    # Build a computation graph
    x = Value(2.0, label="x")
    y = Value(3.0, label="y")
    z = (x * y + x ** 2).tanh()
    z.label = "z"
    z.backward()

    print("Computation graph (DOT format):")
    print()
    print(to_dot(z, title="z = tanh(x*y + x^2)"))
    print()

    # ASCII loss chart
    print("=== ASCII Loss Chart ===\n")

    xs = [[0, 0], [0, 1], [1, 0], [1, 1]]
    ys = [0, 1, 1, 0]
    from autograd_engine import MLP
    from autograd_engine.train import Adam
    model = MLP(2, [8, 8, 1], activation="tanh")
    opt = Adam(model.parameters(), lr=0.01)
    history = train(model, xs, ys, epochs=100, optimizer=opt,
                     classification=True, seed=42)

    print(ascii_loss_chart(history, width=60, height=15))


if __name__ == "__main__":
    main()