# autograd-engine

A tiny **reverse-mode automatic differentiation engine** implemented from scratch in pure Python, with a small neural-network library (MLP) built on top of it. No external dependencies — only the standard library.

Inspired by Andrej Karpathy's [micrograd](https://github.com/karpathy/micrograd), this project builds a dynamically-constructed computational graph of scalar `Value` nodes and performs backpropagation by walking that graph in reverse topological order.

## How It Works

### The `Value` class

Every scalar quantity in the graph is a `Value` object holding:

- `data` — the forward value (a float)
- `grad` — the accumulated gradient (filled in during `backward()`)
- `_backward` — a closure encoding the local derivative of the operation that produced this node
- `_prev` — the node's parents in the graph

Arithmetic operators (`+`, `*`, `-`, `/`, `**`, unary `-`) and transcendental functions (`tanh`, `relu`, `exp`, `log`) are overloaded. Each op records a closure that, when called, propagates the output's gradient to its inputs using the chain rule.

### Backpropagation

`Value.backward()`:
1. Builds a topological sort of the entire subgraph feeding into the loss node.
2. Zeros all gradients, then seeds the loss with `grad = 1.0`.
3. Walks the topo order in reverse, calling each node's `_backward` closure, accumulating gradients.

### Neural network library

- **`Neuron`** — linear transform + activation (`tanh` / `relu` / linear)
- **`Layer`** — a fully-connected collection of neurons
- **`MLP`** — stacks layers; the last layer is linear, hidden layers use the chosen activation

### Training utilities

- `mean_squared_error(preds, targets)` — MSE loss as a `Value`
- `SGD` — vanilla stochastic gradient descent optimizer
- `train(model, xs, ys, ...)` — runs a training loop and returns loss history

## Project Structure

```
autograd-engine/
├── autograd_engine/
│   ├── __init__.py      # package exports
│   ├── engine.py        # Value class + autodiff core
│   ├── nn.py            # Neuron, Layer, MLP
│   └── train.py         # SGD optimizer, MSE loss, train loop
├── demo.py              # XOR learning demo
└── README.md
```

## Usage

### Basic gradient computation

```python
from autograd_engine import Value

x = Value(2.0)
y = x**2 + 3*x + 1       # y = 7
y.backward()
print(x.grad)             # 7.0  (dy/dx = 2x+3 = 7)
```

### Train an MLP on XOR

```python
from autograd_engine import MLP
from autograd_engine.train import train

xs = [[0,0], [0,1], [1,0], [1,1]]
ys = [0, 1, 1, 0]

model = MLP(2, [4, 4, 1], activation="tanh")
train(model, xs, ys, epochs=500, lr=0.1)

for x, y in zip(xs, ys):
    print(x, "=>", model(x)[0].data, "(target", y, ")")
```

### Run the demo

```bash
python3 demo.py
```

Output shows the model converging to near-zero loss and correctly predicting all four XOR rows.

## Supported Operations

| Op | Forward | Backward (d/dself) |
|----|---------|---------------------|
| `a + b` | `a.data + b.data` | `1` |
| `a * b` | `a.data * b.data` | `b.data` |
| `a ** n` | `a.data ** n` | `n * a.data**(n-1)` |
| `a / b` | `a * b**-1` | via pow |
| `-a` | `a * -1` | via mul |
| `a.tanh()` | `tanh(a.data)` | `1 - tanh²` |
| `a.relu()` | `max(0, a.data)` | `1 if >0 else 0` |
| `a.exp()` | `exp(a.data)` | `exp(a.data)` |
| `a.log()` | `log(a.data)` | `1 / a.data` |

## License

MIT — part of the `creative-projects` collection.