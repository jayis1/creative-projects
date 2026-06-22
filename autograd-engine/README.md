# autograd-engine

A tiny **reverse-mode automatic differentiation engine** implemented from scratch in pure Python, with a small neural-network library (MLP), optimizers, and loss functions built on top of it. No external dependencies — only the standard library.

Inspired by Andrej Karpathy's [micrograd](https://github.com/karpathy/micrograd), this project builds a dynamically-constructed computational graph of scalar `Value` nodes and performs backpropagation by walking that graph in reverse topological order.

## How It Works

### The `Value` class

Every scalar quantity in the graph is a `Value` object holding:

- `data` — the forward value (a float)
- `grad` — the accumulated gradient (filled in during `backward()`)
- `_backward` — a closure encoding the local derivative of the operation that produced this node
- `_prev` — the node's parents in the graph

Arithmetic operators (`+`, `*`, `-`, `/`, `**`, unary `-`) and transcendental functions (`tanh`, `relu`, `exp`, `log`, `sigmoid`) are overloaded. Each op records a closure that, when called, propagates the output's gradient to its inputs using the chain rule. Gradients are **accumulated** (`+=`) so nodes reused in multiple places receive the correct summed gradient.

### Backpropagation

`Value.backward()`:
1. Builds a topological sort of the entire subgraph feeding into the loss node.
2. Zeros all gradients, then seeds the loss with `grad = 1.0`.
3. Walks the topo order in reverse, calling each node's `_backward` closure, accumulating gradients.

### Neural network library

- **`Neuron`** — linear transform + activation (`tanh` / `relu` / `sigmoid` / `linear`)
- **`Layer`** — a fully-connected collection of neurons with optional dropout
- **`MLP`** — stacks layers; the last layer is linear, hidden layers use the chosen activation
- **Weight initialization** — Xavier/Glorot (default) or He init (for ReLU-based nets)
- **Train/eval modes** — dropout is active only in training mode
- **`Module`** base class — parameter collection, grad zeroing, mode toggling

### Operations module (`ops.py`)

Higher-level operations over sequences of `Value` objects:
- `sum_values`, `mean`, `max_value` — reductions
- `softmax`, `log_softmax` — numerically stable via the log-sum-exp trick
- `cross_entropy(logits, target)` — multi-class CE loss
- `dot`, `matvec` — vector/matrix primitives

### Training utilities (`train.py`)

**Loss functions:**
- `mean_squared_error(preds, targets)` — MSE
- `binary_cross_entropy_with_logits(logits, targets)` — numerically stable BCE
- `cross_entropy_loss(logits, target)` — multi-class cross-entropy
- `hinge_loss(preds, targets)` — hinge loss for {-1,+1} targets

**Optimizers:**
- `SGD(params, lr, momentum, weight_decay)` — SGD with momentum and L2 regularization
- `Adam(params, lr, betas, eps, weight_decay)` — Adam optimizer (Kingma & Ba, 2014)

**Utilities:**
- `train(model, xs, ys, ...)` — mini-batch training loop with loss history
- `accuracy(model, xs, ys)` — classification accuracy
- `numerical_grad_check(fn, inputs, ...)` — verify analytic gradients against central differences

## Project Structure

```
autograd-engine/
├── autograd_engine/
│   ├── __init__.py      # package exports
│   ├── engine.py        # Value class + autodiff core (11 ops)
│   ├── nn.py            # Module, Neuron, Layer, MLP (Xavier/He init, dropout)
│   ├── ops.py           # sum, mean, max, softmax, log_softmax, cross_entropy, dot, matvec
│   └── train.py         # SGD, Adam, MSE/BCE/CE/hinge losses, grad check, train loop
├── demo.py              # XOR learning demo (tanh MLP + SGD)
├── test_enhanced.py     # verification of all enhanced features
├── tests/
│   ├── test_engine.py   # engine unit tests
│   ├── test_nn.py       # neural network unit tests
│   ├── test_ops.py      # ops module unit tests
│   └── test_train.py    # optimizer & training tests
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

### Numerical gradient checking

```python
from autograd_engine import Value
from autograd_engine.train import numerical_grad_check

def f(inputs):
    x, y = inputs
    return (x * y + x.tanh()).exp().log() + x**2

assert numerical_grad_check(f, [Value(1.5), Value(0.7)], tol=1e-3)
```

### Train an MLP on XOR (with Adam)

```python
from autograd_engine import MLP
from autograd_engine.train import Adam, train

xs = [[0,0], [0,1], [1,0], [1,1]]
ys = [0, 1, 1, 0]

model = MLP(2, [8, 8, 1], activation="relu", init="he")
opt = Adam(model.parameters(), lr=0.01)
history = train(model, xs, ys, epochs=300, optimizer=opt)

for x, y in zip(xs, ys):
    pred = model(x)[0].data
    print(x, "=>", round(pred, 4), "(target", y, ")")
```

### Multi-class classification with cross-entropy

```python
from autograd_engine import Value
from autograd_engine.ops import softmax, cross_entropy

logits = [Value(2.0), Value(1.0), Value(0.1)]
probs = softmax(logits)  # [0.659, 0.242, 0.099]

loss = cross_entropy(logits, target=0)  # class 0 is correct
loss.backward()
# gradients flow to logits
```

### Run the demo

```bash
python3 demo.py
```

### Run the enhanced feature tests

```bash
python3 test_enhanced.py
```

## Supported Operations

| Op | Forward | Backward (d/dself) |
|----|---------|---------------------|
| `a + b` | `a.data + b.data` | `1` |
| `a * b` | `a.data * b.data` | `b.data` |
| `a ** n` | `a.data ** n` | `n * a.data**(n-1)` |
| `a ** v` | `a.data ** v.data` | `v * a^(v-1)` (base) + `a^v * ln(a)` (exp) |
| `a / b` | `a * b**-1` | via pow |
| `-a` | `a * -1` | via mul |
| `a.tanh()` | `tanh(a.data)` | `1 - tanh²` |
| `a.relu()` | `max(0, a.data)` | `1 if >0 else 0` |
| `a.sigmoid()` | `1/(1+e^-x)` | `s * (1-s)` |
| `a.exp()` | `exp(a.data)` | `exp(a.data)` |
| `a.log()` | `log(a.data)` | `1 / a.data` |

## Known Issues (Resolved)

The following bugs were identified during the Phase 3 bug hunt and have been fixed:

### Bug 1: `Value(0.0) ** 0` crashes on `backward()` with `ZeroDivisionError`

**Root cause:** The gradient formula for `x ** n` is `n * x ** (n-1)`. When `x == 0` and `n == 0`, Python evaluates `0.0 ** (-1)` *before* multiplying by `0`, raising `ZeroDivisionError`.

**Fix:** Guard the backward closure to skip the gradient computation when `self.data == 0` (the derivative is `0` for `n >= 0` at `x = 0`). Added explicit handling for the `0 ** 0` edge case.

### Bug 2: `Value(-2.0) ** 0.5` raises confusing `TypeError`

**Root cause:** Python's `float.__pow__` returns a `complex` number for negative bases with fractional exponents. `Value.__init__` then raises an opaque `TypeError: Value data must be a number, got complex` with no indication of the actual problem.

**Fix:** Added a guard in `__pow__` that detects negative base with non-integer exponent and raises a clear `ValueError` explaining that only integer exponents are supported for negative bases.

### Bug 3: Xavier weight initialization uses wrong fan-out dimension

**Root cause:** `Neuron.__init__` called `_xavier(nin, nin)` — using `nin` (fan-in) as both arguments to the Xavier formula. The correct Xavier/Glorot uniform initialization requires `sqrt(6 / (fan_in + fan_out))`, but the code was computing `sqrt(6 / (fan_in + fan_in))`. This made weight initialization scale incorrect for layers where `fan_out != fan_in` (the common case).

**Fix:** Added an optional `nout` parameter to `Neuron.__init__` and pass it from `Layer` (which knows the actual output size). The Xavier formula now uses the correct `(fan_in + fan_out)` denominator.

### Bug 4: `__eq__`/`__hash__` contract violation

**Root cause:** `__eq__` was defined to compare `Value` objects by their `.data` attribute (`a == b` when `a.data == b.data`), but `__hash__` returned `id(self)`. This violated Python's requirement that equal objects must have equal hashes, causing subtle bugs when `Value` objects are used in sets or dictionaries (two equal-by-data objects would hash to different buckets).

**Fix:** Changed `__eq__` to use identity comparison (`self is other`), which is the correct semantics for mutable graph nodes and is consistent with `id`-based `__hash__`. Two `Value` objects are now equal only if they are the same object in memory.

### Additional edge case tests verified

- `relu(0)` backward returns 0 (valid subgradient)
- Division by zero (both `Value` and plain `0`) raises clear `ZeroDivisionError`
- `log()` of non-positive values raises clear `ValueError`
- Gradient accumulation works correctly for reused nodes (`x + x` gives `grad=2`)
- `backward()` correctly zeros stale gradients from previous calls
- Numerical gradient check passes on complex compositions of all ops
- Negative integer exponents work correctly (`Value(4)**-1`)
- Fractional exponents work for positive bases
- MLP validates input length and raises clear `ValueError`
- Softmax outputs sum to exactly 1.0
- Cross-entropy gradient matches softmax − one-hot
- BCE-with-logits gradient matches sigmoid(x) − target
- Both Adam and SGD+momentum converge on XOR

## License

MIT — part of the `creative-projects` collection.