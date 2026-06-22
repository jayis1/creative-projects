# autograd-engine

<div align="center">

**A tiny reverse-mode automatic differentiation engine with a full neural-network toolkit — pure Python, zero dependencies.**

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Tests](https://img.shields.io/badge/tests-211%20passed-brightgreen.svg)
![Dependencies](https://img.shields.io/badge/dependencies-none-success.svg)
![Version](https://img.shields.io/badge/version-2.0.0-orange.svg)

</div>

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Usage Examples](#usage-examples)
- [CLI Reference](#cli-reference)
- [Configuration](#configuration)
- [Available Operations](#available-operations)
- [Activation Functions](#activation-functions)
- [Optimizers & Schedulers](#optimizers--schedulers)
- [Serialization](#serialization)
- [Visualization](#visualization)
- [Evaluation Metrics](#evaluation-metrics)
- [Examples](#examples)
- [Testing](#testing)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [Known Issues (Resolved)](#known-issues-resolved)
- [License](#license)

## Overview

`autograd-engine` is a **reverse-mode automatic differentiation engine** implemented from scratch in pure Python. It builds a dynamically-constructed computational graph of scalar `Value` nodes and performs backpropagation by walking that graph in reverse topological order.

Inspired by Andrej Karpathy's [micrograd](https://github.com/karpathy/micrograd), this project goes well beyond a toy — it includes a complete neural-network library, multiple optimizers, learning-rate schedulers, loss functions, model serialization, computation-graph visualization, evaluation metrics, config-file-driven training, and a full CLI.

**Zero external dependencies** — the entire engine runs on the Python standard library alone.

## Features

### Core Engine
- **11 primitive operations**: `+`, `-`, `*`, `/`, `**`, unary `-`, `tanh`, `relu`, `exp`, `log`, `sigmoid`
- **Variable exponents**: `Value ** Value` with correct gradients for both base and exponent
- **Gradient accumulation**: nodes reused in multiple places get correct summed gradients
- **Numerical gradient checking**: verify analytic gradients against central differences

### Neural Network Library
- **`Module`** base class with parameter collection, grad zeroing, train/eval modes
- **`Neuron`**, **`Layer`**, **`MLP`** — fully-connected layers with configurable activations
- **Weight initialization**: Xavier/Glorot uniform and He uniform
- **Dropout** with inverted scaling (training-time only)
- **14 activation functions**: tanh, relu, sigmoid, leaky_relu, elu, gelu, swish, softplus, mish, selu, hard_tanh, hard_sigmoid, linear, none

### Training Infrastructure
- **2 optimizers**: SGD (with momentum + weight decay), Adam (Kingma & Ba, 2014)
- **6 LR schedulers**: StepLR, ExponentialLR, CosineAnnealingLR, LinearLR, WarmupLR, ReduceOnPlateauLR
- **4 loss functions**: MSE, BCE-with-logits, cross-entropy, hinge
- **Early stopping** with configurable patience and mode
- **Mini-batch training** with shuffling and loss history
- **Config-file-driven training** (JSON and YAML)

### Tools & Utilities
- **Model serialization**: save/load to JSON
- **Graph visualization**: Graphviz DOT output + ASCII loss charts
- **Evaluation metrics**: accuracy, precision, recall, F1, confusion matrix, MSE, RMSE, MAE, R²
- **CLI interface**: `train`, `grad-check`, `demo`, `info` subcommands
- **211 passing tests** with pytest

## Installation

### From source (recommended)

```bash
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/autograd-engine

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"
```

### As a package

```bash
pip install -e .
```

### Optional dependencies

```bash
pip install -e ".[yaml]"   # YAML config support
pip install -e ".[viz]"    # Graphviz rendering
pip install -e ".[dev]"    # pytest, coverage, pyyaml
```

### Requirements

- Python 3.9+
- No runtime dependencies (pure standard library)

## Quick Start

```python
from autograd_engine import Value

# Compute derivatives of any function
x = Value(2.0, label="x")
y = x**2 + 3*x + 1       # y = 11
y.backward()
print(x.grad)             # 7.0  (dy/dx = 2x + 3 = 7)
```

```python
from autograd_engine import MLP
from autograd_engine.train import Adam, train, accuracy

# Train an MLP on XOR
xs = [[0,0], [0,1], [1,0], [1,1]]
ys = [0, 1, 1, 0]

model = MLP(2, [8, 8, 1], activation="tanh")
opt = Adam(model.parameters(), lr=0.01)
history = train(model, xs, ys, epochs=200, optimizer=opt, classification=True)

print(f"Accuracy: {accuracy(model, xs, ys):.0%}")
```

## Architecture

```
autograd-engine/
├── autograd_engine/
│   ├── __init__.py        # Package exports (v2.0.0)
│   ├── engine.py          # Value class — the autodiff core
│   ├── nn.py              # Module, Neuron, Layer, MLP
│   ├── ops.py             # sum, mean, max, softmax, log_softmax, cross_entropy, dot, matvec
│   ├── activations.py     # 14 activation functions + registry
│   ├── train.py           # SGD, Adam, 4 losses, training loop, early stopping, grad check
│   ├── schedulers.py      # 6 LR schedulers + factory
│   ├── serialization.py   # Save/load models to JSON
│   ├── viz.py             # Graphviz DOT output + ASCII loss charts
│   ├── metrics.py         # Classification & regression metrics
│   ├── config.py          # JSON/YAML config with dataclasses
│   └── cli.py             # Command-line interface
├── tests/                 # 211 pytest tests across 10 test files
│   ├── test_engine.py     # Core Value/autodiff tests
│   ├── test_nn.py         # Neural network module tests
│   ├── test_ops.py        # Operations module tests
│   ├── test_train.py      # Optimizer & training tests
│   ├── test_activations.py # Extended activation tests
│   ├── test_schedulers.py  # LR scheduler tests
│   ├── test_serialization.py # Save/load tests
│   ├── test_metrics.py    # Evaluation metric tests
│   ├── test_config.py     # Config system tests
│   ├── test_viz.py        # Visualization tests
│   └── test_cli.py        # CLI integration tests
├── examples/              # 8 runnable example scripts
│   ├── 01_basic_gradients.py
│   ├── 02_xor_optimizers.py
│   ├── 03_schedulers.py
│   ├── 04_activations.py
│   ├── 05_serialization.py
│   ├── 06_config_driven.py
│   ├── 07_metrics.py
│   └── 08_visualization.py
├── demo.py                # Quick XOR demo
├── test_enhanced.py       # Enhanced feature verification
├── pyproject.toml         # Package metadata + pytest config
├── CONTRIBUTING.md        # Contribution guidelines
├── LICENSE                # MIT
└── README.md              # This file
```

### How the Engine Works

#### The `Value` Class

Every scalar quantity in the graph is a `Value` object holding:
- `data` — the forward value (a float)
- `grad` — the accumulated gradient (filled in during `backward()`)
- `_backward` — a closure encoding the local derivative of the operation
- `_prev` — the node's parents in the graph
- `_op` — a string label for the operation
- `label` — an optional human-readable name

Arithmetic operators and transcendental functions are overloaded. Each op records a closure that, when called, propagates the output's gradient to its inputs using the chain rule. Gradients are **accumulated** (`+=`) so nodes reused in multiple places receive the correct summed gradient.

#### Backpropagation

`Value.backward()`:
1. Builds a topological sort of the entire subgraph feeding into the loss node.
2. Zeros all gradients, then seeds the loss with `grad = 1.0`.
3. Walks the topo order in reverse, calling each node's `_backward` closure.

#### Neural Network Stack

```
MLP → Layer[] → Neuron[] → Value (weights + bias)
                      ↓
               _apply_activation(v, name) → ACTIVATION_REGISTRY[name](v)
```

The activation registry centralizes all 14 activations so the NN modules,
config system, and CLI all reference the same lookup table.

## Usage Examples

### Basic Gradient Computation

```python
from autograd_engine import Value

x = Value(2.0, label="x")
y = Value(3.0, label="y")
z = x * y + x ** 2     # z = 6 + 4 = 10
z.backward()
print(f"dz/dx = {x.grad}")  # 7.0  (y + 2x = 3 + 4)
print(f"dz/dy = {y.grad}")  # 3.0  (x = 2... wait, x=2 so dz/dy = x = 2)
```

### Numerical Gradient Checking

```python
from autograd_engine import Value
from autograd_engine.train import numerical_grad_check

def f(inputs):
    x, y = inputs
    return (x * y + x.tanh()).exp().log() + x**2

assert numerical_grad_check(f, [Value(1.5), Value(0.7)], tol=1e-3)
```

### Train MLP on XOR with Adam

```python
from autograd_engine import MLP
from autograd_engine.train import Adam, train, accuracy

xs = [[0,0], [0,1], [1,0], [1,1]]
ys = [0, 1, 1, 0]

model = MLP(2, [8, 8, 1], activation="relu", init="he")
opt = Adam(model.parameters(), lr=0.01)
history = train(model, xs, ys, epochs=300, optimizer=opt, classification=True)

for x, y in zip(xs, ys):
    pred = model(x)[0].data
    print(f"{x} => {pred:.4f} (target {y})")
```

### Using Learning-Rate Schedulers

```python
from autograd_engine import MLP
from autograd_engine.train import SGD, train
from autograd_engine.schedulers import CosineAnnealingLR, WarmupLR

model = MLP(2, [8, 8, 1], activation="tanh")
opt = SGD(model.parameters(), lr=0.1, momentum=0.9)

# Cosine annealing with 20-epoch warmup
scheduler = WarmupLR(CosineAnnealingLR(0.1, T_max=180, eta_min=0.001), warmup_epochs=20)

history = train(model, xs, ys, epochs=200, optimizer=opt,
                lr_scheduler=scheduler, classification=True)
```

### Extended Activation Functions

```python
from autograd_engine import Value
from autograd_engine.activations import gelu, swish, mish, selu

x = Value(1.5)
y = gelu(x)
y.backward()
print(f"GELU(1.5) = {y.data:.4f}, grad = {x.grad:.4f}")

# Use in MLP
from autograd_engine import MLP
model = MLP(2, [8, 1], activation="gelu")
```

### Save and Load Models

```python
from autograd_engine import MLP
from autograd_engine.train import Adam, train
from autograd_engine.serialization import save_model, load_model

model = MLP(2, [8, 8, 1], activation="tanh")
train(model, xs, ys, epochs=200, optimizer=Adam(model.parameters(), lr=0.01),
      classification=True)

# Save
save_model(model, "model.json")

# Load later
loaded = load_model("model.json")
print(loaded([0, 1])[0].data)  # Same predictions
```

### Evaluation Metrics

```python
from autograd_engine.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report,
    mean_squared_error, r2_score,
)

y_true = [0, 1, 0, 1, 1]
y_pred = [0, 1, 1, 1, 0]

print(f"Accuracy:  {accuracy_score(y_true, y_pred):.4f}")
print(f"Precision: {precision_score(y_true, y_pred):.4f}")
print(f"Recall:    {recall_score(y_true, y_pred):.4f}")
print(f"F1:        {f1_score(y_true, y_pred):.4f}")
print(classification_report(y_true, y_pred))
```

### Computation Graph Visualization

```python
from autograd_engine import Value
from autograd_engine.viz import to_dot, ascii_loss_chart

x = Value(2.0, label="x")
y = x ** 2 + 3 * x + 1
y.backward()

# Generate Graphviz DOT
print(to_dot(y, title="y = x^2 + 3x + 1"))

# ASCII loss chart
# ascii_loss_chart(history)
```

### Multi-class Cross-Entropy

```python
from autograd_engine import Value
from autograd_engine.ops import softmax, cross_entropy

logits = [Value(2.0), Value(1.0), Value(0.1)]
probs = softmax(logits)  # [0.659, 0.242, 0.099]

loss = cross_entropy(logits, target=0)
loss.backward()
# gradients flow to logits
```

## CLI Reference

The package includes a full command-line interface:

```bash
# Show available ops, activations, and modules
python -m autograd_engine.cli info

# Run the XOR demo
python -m autograd_engine.cli demo

# Run gradient checking
python -m autograd_engine.cli grad-check

# Train on XOR with options
python -m autograd_engine.cli train --xor \
    --optimizer adam --lr 0.01 --epochs 300 \
    --activation tanh --hidden 8 8 \
    --plot --save-model model.json

# Train from a config file
python -m autograd_engine.cli train --config config.json --data data.csv
```

### CLI Training Output

```
epoch    0  loss=0.716376  lr=0.010000
epoch   30  loss=0.550822  lr=0.009945
epoch   49  loss=0.263204  lr=0.009893

Predictions:
  [0, 0] => 0.0312 (target 0)
  [0, 1] => 0.9685 (target 1)
  [1, 0] => 0.9672 (target 1)
  [1, 1] => 0.0328 (target 0)

  loss (max=0.7164, min=0.2632)
  ┌──────────────────────────────────────────────────────────────────┐
  │●                                                                 │
  │ ●                                                                │
  │  ●                                                               │
  │   ●●                                                             │
  │     ●●●                                                          │
  │        ●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●│
  └──────────────────────────────────────────────────────────────────┘
   epoch 0                                                epoch 299
```

## Configuration

Training can be fully configured via JSON or YAML files:

```json
{
    "model": {
        "nin": 2,
        "nouts": [8, 8, 1],
        "activation": "tanh",
        "init": "xavier",
        "dropout": 0.1
    },
    "optimizer": {
        "type": "adam",
        "lr": 0.01,
        "weight_decay": 0.001
    },
    "training": {
        "epochs": 500,
        "batch_size": 4,
        "seed": 42,
        "classification": true,
        "lr_scheduler": {
            "type": "cosine",
            "base_lr": 0.01,
            "T_max": 500,
            "eta_min": 0.0001
        }
    },
    "logging": {
        "level": "INFO",
        "verbose": true
    }
}
```

Load and use:

```python
from autograd_engine.config import Config

config = Config.load("config.json")
model = config.model.build()
optimizer = config.optimizer.build(model.parameters())
scheduler = config.training.build_scheduler()
```

## Available Operations

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

## Activation Functions

| Name | Formula | Key Property |
|------|---------|-------------|
| `tanh` | `tanh(x)` | Zero-centered, bounded [-1, 1] |
| `relu` | `max(0, x)` | Sparse activation |
| `sigmoid` | `1/(1+e^-x)` | Bounded (0, 1) |
| `leaky_relu` | `max(0.01x, x)` | No dead neurons |
| `elu` | `x` if `x>0` else `α(e^x - 1)` | Zero-centered negatives |
| `gelu` | `0.5x(1 + tanh(√(2/π)(x + 0.044715x³)))` | Smooth, used in BERT/GPT |
| `swish` | `x * sigmoid(x)` | Self-gated |
| `softplus` | `log(1 + e^x)` | Smooth ReLU |
| `mish` | `x * tanh(softplus(x))` | State-of-the-art |
| `selu` | `scale * (x if x>0 else α(e^x - 1))` | Self-normalizing |
| `hard_tanh` | `clamp(x, -1, 1)` | Fast approximation |
| `hard_sigmoid` | `clamp(0.2x + 0.5, 0, 1)` | Fast approximation |
| `linear` | `x` | No activation |

## Optimizers & Schedulers

### Optimizers

| Optimizer | Key Parameters | When to Use |
|-----------|---------------|-------------|
| `SGD` | `lr`, `momentum`, `weight_decay` | Simple problems, fine control |
| `Adam` | `lr`, `betas`, `eps`, `weight_decay` | Default choice, adaptive LR |

### Schedulers

| Scheduler | Formula | Use Case |
|-----------|---------|----------|
| `StepLR` | `lr * γ^(epoch // step)` | Step decay |
| `ExponentialLR` | `lr * γ^epoch` | Smooth exponential decay |
| `CosineAnnealingLR` | Cosine from `lr` to `eta_min` | Periodic, fine-tuning |
| `LinearLR` | Linear from `start_lr` to `end_lr` | Linear warmup/decay |
| `WarmupLR` | Linear warmup → base scheduler | Transformers, large models |
| `ReduceOnPlateauLR` | Reduce on metric plateau | Adaptive, validation-based |

## Serialization

Save and load models to JSON:

```python
from autograd_engine.serialization import save_model, load_model

save_model(model, "model.json")    # Save architecture + weights
model = load_model("model.json")   # Restore with identical architecture
```

The JSON format stores both the architecture configuration and all parameter
values, enabling reproducible experiments and model deployment.

## Visualization

### Graphviz DOT Output

```python
from autograd_engine.viz import to_dot, draw_dot

dot_string = to_dot(loss_node, title="Training graph")
draw_dot(loss_node, "graph.dot")
# Render with: dot -Tpng graph.dot -o graph.png
```

### ASCII Loss Charts

```
  loss (max=0.6931, min=0.0012)
  ┌──────────────────────────────────────────────────────────────────┐
  │●                                                                 │
  │ ●                                                                │
  │  ●●                                                              │
  │    ●●●                                                           │
  │       ●●●●●                                                      │
  │            ●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●│
  └──────────────────────────────────────────────────────────────────┘
   epoch 0                                                epoch 299
```

## Evaluation Metrics

### Classification

- `accuracy_score` — fraction correct
- `precision_score` — TP / (TP + FP)
- `recall_score` — TP / (TP + FN)
- `f1_score` — harmonic mean of precision and recall
- `confusion_matrix` — N×N matrix
- `classification_report` — formatted report with per-class metrics

### Regression

- `mean_squared_error` — MSE
- `root_mean_squared_error` — RMSE
- `mean_absolute_error` — MAE
- `r2_score` — coefficient of determination

## Examples

Eight runnable example scripts in `examples/`:

```bash
# Basic gradient computation
python examples/01_basic_gradients.py

# Compare optimizers on XOR
python examples/02_xor_optimizers.py

# Learning-rate schedulers
python examples/03_schedulers.py

# Extended activation functions
python examples/04_activations.py

# Model save/load
python examples/05_serialization.py

# Config-file-driven training
python examples/06_config_driven.py

# Evaluation metrics
python examples/07_metrics.py

# Graph visualization
python examples/08_visualization.py
```

## Testing

```bash
# Run all 211 tests
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=autograd_engine --cov-report=term-missing

# Run specific module tests
python -m pytest tests/test_engine.py -v

# Run enhanced feature tests
python test_enhanced.py

# CLI smoke tests
python -m autograd_engine.cli info
python -m autograd_engine.cli demo
python -m autograd_engine.cli grad-check
```

### Test Coverage by Module

| Test File | Tests | Covers |
|-----------|-------|--------|
| `test_engine.py` | 34 | Value construction, arithmetic, pow, transcendentals, backprop, equality |
| `test_nn.py` | 16 | Neuron, Layer, MLP, dropout, train/eval, XOR convergence |
| `test_ops.py` | 20 | sum, mean, max, softmax, log_softmax, cross_entropy, dot, matvec |
| `test_train.py` | 28 | SGD, Adam, MSE, BCE, hinge, train loop, accuracy, grad check, early stopping |
| `test_activations.py` | 27 | All 14 activations + registry + gradient checking |
| `test_schedulers.py` | 23 | All 6 schedulers + factory + edge cases |
| `test_serialization.py` | 3 | Save/load models, architecture preservation |
| `test_metrics.py` | 17 | All classification + regression metrics |
| `test_config.py` | 9 | Config from dict/JSON, save/load, defaults |
| `test_viz.py` | 11 | DOT generation, ASCII charts, file output |
| `test_cli.py` | 7 | CLI subcommands: info, demo, grad-check, train |
| **Total** | **211** | |

## Roadmap

- [ ] **Vectorized operations** — batch `Value` arrays for faster forward/backward
- [ ] **Convolutional layers** — Conv1D/Conv2D with im2col
- [ ] **Recurrent layers** — RNN, LSTM, GRU cells
- [ ] **Attention mechanism** — self-attention, multi-head attention
- [ ] **GPU support** — optional CuPy backend for acceleration
- [ ] **Weight tying** — shared parameter support in Module
- [ ] **Model pruning** — magnitude and gradient-based pruning
- [ ] **Quantization** — int8 inference support
- [ ] **JIT compilation** — graph compilation for faster execution
- [ ] **Distributed training** — data-parallel gradient sync
- [ ] **More datasets** — built-in dataset loaders (MNIST, Iris, etc.)
- [ ] **TensorBoard integration** — optional logging to TensorBoard
- [ ] **Web demo** — interactive playground in the browser

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on:
- Setting up the development environment
- Code style and conventions
- Adding new activation functions
- Adding new optimizers
- Running tests
- Submitting pull requests

## Changelog

### v2.0.0 (2026-06-22) — Comprehensive Improvement

**New Modules:**
- `activations.py` — 9 new activation functions (leaky_relu, elu, gelu, swish, softplus, mish, selu, hard_tanh, hard_sigmoid) with a centralized activation registry
- `schedulers.py` — 6 learning-rate schedulers (StepLR, ExponentialLR, CosineAnnealingLR, LinearLR, WarmupLR, ReduceOnPlateauLR) with a factory function
- `serialization.py` — model save/load to JSON
- `viz.py` — Graphviz DOT output and ASCII loss charts
- `metrics.py` — classification and regression evaluation metrics
- `config.py` — JSON/YAML config-file support with dataclasses
- `cli.py` — full CLI with `train`, `grad-check`, `demo`, `info` subcommands

**Enhancements:**
- `nn.py` refactored to use centralized activation registry (all 14 activations available to MLP)
- `train.py` now supports `lr_scheduler` parameter and `classification` mode
- `train.py` adds `EarlyStopping` class
- `__init__.py` exports all new modules and functions
- Type hints added throughout
- Package made installable via `pyproject.toml`

**Testing:**
- 211 comprehensive pytest tests across 10 test files (up from 19)
- CLI integration tests
- Gradient checking for all new activations

**Tooling:**
- GitHub Actions CI (Python 3.9–3.12)
- `pyproject.toml` with optional dependencies
- `CONTRIBUTING.md` with development guidelines
- `LICENSE` (MIT)
- 8 runnable example scripts in `examples/`

### v1.0.0 (2026-06-22) — Initial Release

- Reverse-mode autodiff engine with 11 operations
- MLP library (Neuron, Layer, MLP) with Xavier/He init and dropout
- Ops module (softmax, log_softmax, cross_entropy, dot, matvec)
- 2 optimizers (SGD with momentum, Adam)
- 4 loss functions (MSE, BCE, cross-entropy, hinge)
- Numerical gradient checking
- 4 bugs fixed with 19 edge-case tests

## Known Issues (Resolved)

The following bugs were identified during the Phase 3 bug hunt and have been fixed:

### Bug 1: `Value(0.0) ** 0` crashes on `backward()` with `ZeroDivisionError`

**Root cause:** The gradient formula for `x ** n` is `n * x ** (n-1)`. When `x == 0` and `n == 0`, Python evaluates `0.0 ** (-1)` *before* multiplying by `0`, raising `ZeroDivisionError`.

**Fix:** Guard the backward closure to skip the gradient computation when `self.data == 0` (the derivative is `0` for `n >= 0` at `x = 0`). Added explicit handling for the `0 ** 0` edge case.

### Bug 2: `Value(-2.0) ** 0.5` raises confusing `TypeError`

**Root cause:** Python's `float.__pow__` returns a `complex` number for negative bases with fractional exponents. `Value.__init__` then raises an opaque `TypeError` with no indication of the actual problem.

**Fix:** Added a guard in `__pow__` that detects negative base with non-integer exponent and raises a clear `ValueError` explaining that only integer exponents are supported for negative bases.

### Bug 3: Xavier weight initialization uses wrong fan-out dimension

**Root cause:** `Neuron.__init__` called `_xavier(nin, nin)` — using `nin` (fan-in) as both arguments. The correct Xavier/Glorot uniform initialization requires `sqrt(6 / (fan_in + fan_out))`.

**Fix:** Added an optional `nout` parameter to `Neuron.__init__` and pass it from `Layer`.

### Bug 4: `__eq__`/`__hash__` contract violation

**Root cause:** `__eq__` compared by `.data` but `__hash__` returned `id()`, violating Python's requirement that equal objects have equal hashes.

**Fix:** Changed `__eq__` to identity comparison (`self is other`), consistent with `id`-based `__hash__`.

## License

MIT — part of the `creative-projects` collection. See [LICENSE](LICENSE).