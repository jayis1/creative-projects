# Neural Net Lab

![Python](https://img.shields.io/badge/python-3.10%2B-blue) [![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A dependency-free, inspectable multilayer perceptron for learning neural networks from first principles. It now covers binary and multiclass classification, configurable experiments, model persistence, early stopping, and a production-shaped CLI without hiding the math behind NumPy or a framework.

Maintained by [jayis1](https://github.com/jayis1).

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

Use the diagnostic mode to verify the implementation's backpropagation against
finite-difference numerical gradients before experimenting with a new loss or
activation:

```bash
neural-net-lab --gradient-check --epochs 1
# gradient check max relative error: 1.589e-09
```

A saved model can be evaluated against a labeled CSV or JSONL dataset without retraining:

```bash
neural-net-lab --load xor.json --evaluate examples/xor.csv \
  --target-column label --eval-loss bce
# loss: 0.0008; accuracy: 100.00%; samples: 4
```

Evaluation validates feature and target widths before scoring, and `--threshold`
controls binary classification cutoffs. Add `--report` to print a machine-readable
confusion matrix plus per-class precision, recall, and F1 scores:

```bash
neural-net-lab --load xor.json --evaluate examples/xor.csv \
  --target-column label --eval-loss bce --report
# ... {"confusion_matrix": [[2, 0], [0, 2]], "macro_f1": 1.0, ...}
```

Train on your own numeric CSV (the final column is the target by default), with a
reproducible validation split:

```bash
neural-net-lab --dataset examples/xor.csv --target-column label \
  --config examples/xor.toml --validation-split 0.25 --epochs 500
```

CSV files need a header and numeric columns. Pass comma-separated target columns for one-hot or other vector targets, for example `--target-column class_a,class_b`. JSONL files use one object per line:
`{"features": [0.2, 0.8], "target": [1]}`. Dataset loading is dependency-free,
validates consistent widths, and never mutates the input files.

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

`TrainingHistory.losses` and `val_losses` are epoch-level metrics. Use `clip` for gradient-norm clipping and `patience` with `validation=(x_val, y_val)` for best-checkpoint early stopping. `MLP.classification_report()` provides the same threshold/argmax label rules as `accuracy()` plus confusion-matrix and macro-averaged metrics.

## Architecture

`Layer` owns dense weights, biases, initialization, and activation caches. `MLP` composes layers, performs forward passes, computes MSE/BCE/categorical cross-entropy, and applies reverse-mode chain-rule gradients. `MLP.gradient_check()` provides a finite-difference audit of those gradients for educational debugging. `optim.py` supplies interchangeable SGD and Adam updates. `config.py` validates TOML/JSON experiments; `data.py` provides validated CSV/JSONL loading and deterministic train/validation splitting; `cli.py` is a thin orchestration layer with logging, model inspection, dataset training, and gradient diagnostics.

## Development

```bash
python3 -m pytest -q
python3 -m compileall -q neural_net_lab
```

See [CONTRIBUTING.md](CONTRIBUTING.md). Run the local test and compilation commands above before submitting a change.

## Roadmap

- CSV/JSONL dataset adapters and train/validation splitting (completed)
- Additional optimizers and learning-rate schedules
- Optional NumPy backend for large experiments
- More gradient-checking diagnostics for educational debugging

## Changelog

### 2026-09-23

- Added binary and multiclass classification reports with confusion matrices and macro precision, recall, and F1 metrics.
- Added `--report` to the evaluation CLI for machine-readable JSON output.
- Added regression coverage for report scoring, CLI serialization, and target-shape validation.

### 2026-09-22

- Added multiclass CSV support with comma-separated target columns for one-hot labels.
- Added centralized validation for architecture, optimizer, loss, and training hyperparameters, including CLI overrides.
- Added dataset evaluation for saved models with explicit loss selection and threshold validation.
- Added CLI regression tests for evaluation and model/dataset shape errors.

### 2026-09-21

- Added validated, dependency-free CSV and JSONL dataset adapters.
- Added deterministic train/validation splitting and CLI dataset training flags.
- Added dataset-loader regression tests and a runnable XOR CSV example.

### 2026-09-16

- Added finite-difference gradient checking to audit backpropagation for every weight and bias.
- Corrected the MSE derivative to match the documented `0.5 * squared error` loss.
- Added `--gradient-check` CLI diagnostics and documented the workflow.

### 2026-09-13

- Added stable softmax and categorical cross-entropy for multiclass models.
- Added validated TOML/JSON configuration and CLI model-inspection mode.
- Added logging, type-oriented public contracts, regression tests, and contributor guidance.
- Added multiclass argmax accuracy while retaining binary threshold accuracy.

## Known Issues (Resolved)

- Adam moment state and epsilon placement were corrected.
- Early stopping restores the best validation checkpoint.
- Corrupt model dimensions and malformed JSON now produce `ValueError`.
- Softmax overflow is prevented by max-shifting logits.
