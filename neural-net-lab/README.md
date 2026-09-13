# Neural Net Lab

[![CI](https://github.com/jayis1/creative-projects/actions/workflows/test.yml/badge.svg)](https://github.com/jayis1/creative-projects/actions) ![Python](https://img.shields.io/badge/python-3.10%2B-blue) [![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A dependency-free, inspectable multilayer perceptron for learning neural networks from first principles. It now covers binary and multiclass classification, configurable experiments, model persistence, early stopping, and a production-shaped CLI without hiding the math behind NumPy or a framework.

## Contents

- [Install](#install)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Python API](#python-api)
- [Architecture](#architecture)
- [Development](#development)
- [Roadmap](#roadmap)

## Install

Python 3.10+ is required. The runtime has no third-party dependencies.

```bash
cd neural-net-lab
python3 -m venv .venv && . .venv/bin/activate
python3 -m pip install -e .
```

## Quick start

The CLI trains XOR and prints each prediction:

```bash
python3 -m neural_net_lab.cli --epochs 2000 --loss bce --save xor.json
# or, after installation:
neural-net-lab --config examples/xor.toml --verbose
```

A saved model can be inspected without retraining:

```bash
neural-net-lab --load xor.json
```

Example output (values vary if you change the seed):

```text
final bce loss: 0.0008; accuracy: 100.00%; epochs: 2000
[0, 0] => 0.0004 target 0
[0, 1] => 0.9991 target 1
```

## Configuration

Use TOML (Python 3.11+) or JSON. CLI flags override configuration values.

```toml
sizes = [2, 4, 1]
activations = ["tanh", "sigmoid"]
seed = 7
epochs = 2000
lr = 0.08
batch_size = 4
optimizer = "adam" # adam or sgd
loss = "bce"       # mse, bce, or cross_entropy
clip = 5.0
patience = 300
```

`cross_entropy` pairs with a `softmax` output and one-hot targets, enabling multiclass classification. `bce` pairs with a sigmoid output. Invalid files and incompatible loss/activation combinations fail with actionable `ValueError`s.

## Python API

```python
from neural_net_lab import MLP, Adam
x = [[1, 0], [0, 1]]
y = [[1, 0], [0, 1]]
net = MLP([2, 4, 2], ["tanh", "softmax"], seed=4)
history = net.train(x, y, epochs=300, lr=.08, batch_size=2,
                     optimizer=Adam(), loss_name="cross_entropy")
print(net.predict([1, 0]))       # probability vector
print(net.accuracy(x, y))        # argmax multiclass accuracy
net.save("classifier.json")
restored = MLP.load("classifier.json")
```

`TrainingHistory.losses` and `val_losses` are epoch-level metrics. Use `clip` for gradient-norm clipping and `patience` with `validation=(x_val, y_val)` for best-checkpoint early stopping.

## Architecture

`Layer` owns dense weights, biases, initialization, and activation caches. `MLP` composes layers, performs forward passes, computes MSE/BCE/categorical cross-entropy, and applies reverse-mode chain-rule gradients. Softmax uses a numerically stable max-shift and cross-entropy uses the simplified `prediction - target` gradient. `optim.py` supplies interchangeable SGD and Adam updates. `config.py` validates TOML/JSON experiments; `cli.py` is a thin orchestration layer with logging and model inspection.

## Development

```bash
python3 -m pytest -q
python3 -m compileall -q neural_net_lab
```

See [CONTRIBUTING.md](CONTRIBUTING.md). CI runs the test suite on every push and pull request.

## Roadmap

- CSV/JSONL dataset adapters and train/validation splitting
- Additional optimizers and learning-rate schedules
- Optional NumPy backend for large experiments
- Gradient-checking utility for educational debugging

## Changelog

### 2026-09-13

- Added stable softmax and categorical cross-entropy for multiclass models.
- Added validated TOML/JSON configuration and CLI model-inspection mode.
- Added logging, type-oriented public contracts, CI, contributor guidance, and regression tests.
- Added multiclass argmax accuracy while retaining binary threshold accuracy.

## Known Issues (Resolved)

- Adam moment state and epsilon placement were corrected.
- Early stopping restores the best validation checkpoint.
- Corrupt model dimensions and malformed JSON now produce `ValueError`.
- Softmax overflow is prevented by max-shifting logits.
