#!/usr/bin/env python3
"""Command-line interface for the autograd-engine.

Supports:
  - ``train``: Train an MLP on a dataset (CSV or JSON) with configurable
    architecture, optimizer, scheduler, and loss function.
  - ``grad-check``: Run numerical gradient checking on a composed function.
  - ``demo``: Run the built-in XOR demo.
  - ``info``: Print package info and available ops/activations.

Examples
--------
    # Train on XOR with Adam, save model and loss chart
    python3 -m autograd_engine.cli train --xor --optimizer adam --lr 0.01 \
        --epochs 300 --activation tanh --save-model model.json --plot

    # Train from a config file
    python3 -m autograd_engine.cli train --config config.json --data data.csv

    # Gradient check
    python3 -m autograd_engine.cli grad-check

    # Show info
    python3 -m autograd_engine.cli info
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from . import (
    MLP, Value, train as train_fn, accuracy, numerical_grad_check,
    ACTIVATION_REGISTRY, get_activation,
)
from .train import SGD, Adam, mean_squared_error, binary_cross_entropy_with_logits
from .schedulers import get_scheduler, LRScheduler
from .serialization import save_model, load_model
from .viz import ascii_loss_chart
from .config import Config, default_config


# --------------------------------------------------------------------------- #
# dataset helpers
# --------------------------------------------------------------------------- #
def load_csv(path: str | Path) -> Tuple[List[List[float]], List[float]]:
    """Load a CSV file.  Last column is the target, all others are features."""
    xs, ys = [], []
    with open(path, "r", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            vals = [float(v) for v in row]
            xs.append(vals[:-1])
            ys.append(vals[-1])
    return xs, ys


def load_json(path: str | Path) -> Tuple[List[List[float]], List[float]]:
    """Load a JSON file with format ``[{"features": [...], "label": x}, ...]``."""
    data = json.loads(Path(path).read_text())
    xs = [item["features"] for item in data]
    ys = [item["label"] for item in data]
    return xs, ys


def load_dataset(path: Optional[str]) -> Tuple[List[List[float]], List[float]]:
    if path is None:
        return _xor_data()
    p = str(path)
    if p.endswith(".csv"):
        return load_csv(path)
    elif p.endswith(".json"):
        return load_json(path)
    else:
        raise ValueError(f"Unsupported data format: {path} (use .csv or .json)")


def _xor_data() -> Tuple[List[List[float]], List[float]]:
    """The classic XOR dataset."""
    xs = [[0, 0], [0, 1], [1, 0], [1, 1]]
    ys = [0, 1, 1, 0]
    return xs, ys


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #
def cmd_train(args: argparse.Namespace) -> None:
    logger = logging.getLogger("autograd_engine")
    # Ensure logger output goes to stdout so it's captured properly
    if not logger.handlers or not any(
        isinstance(h, logging.StreamHandler) for h in logger.handlers
    ):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S"))
        logger.addHandler(handler)
    elif logger.handlers:
        # Replace existing handler's stream with stdout
        for h in logger.handlers:
            if isinstance(h, logging.StreamHandler):
                h.stream = sys.stdout
    logger.setLevel(logging.INFO)
    if args.config:
        config = Config.load(args.config)
        logger.info(f"Loaded config from {args.config}")
    else:
        config = default_config()
        # Override with CLI args
        if args.xor or args.data is None:
            pass
        if args.epochs:
            config.training.epochs = args.epochs
        if args.lr:
            config.optimizer.lr = args.lr
        if args.optimizer:
            config.optimizer.type = args.optimizer
        if args.activation:
            config.model.activation = args.activation
        if args.hidden:
            config.model.nouts = args.hidden + [config.model.nouts[-1]]
        if args.dropout is not None:
            config.model.dropout = args.dropout
        if args.batch_size:
            config.training.batch_size = args.batch_size
        if args.seed:
            config.training.seed = args.seed
        config.training.classification = True
        config.logging.verbose = True

    # Load data
    xs, ys = load_dataset(args.data)

    # Build model
    if args.data is not None:
        config.model.nin = len(xs[0])
    model = config.model.build()
    logger.info(f"Model: {model} ({model.num_parameters()} parameters)")

    # Build optimizer
    optimizer = config.optimizer.build(model.parameters())

    # Build scheduler
    scheduler = config.training.build_scheduler()

    # Train
    logger.info(f"Training for {config.training.epochs} epochs...")
    history = train_fn(
        model, xs, ys,
        epochs=config.training.epochs,
        batch_size=config.training.batch_size,
        optimizer=optimizer,
        lr_scheduler=scheduler,
        seed=config.training.seed,
        verbose=config.logging.verbose,
        classification=config.training.classification,
    )

    # Results
    final_loss = history[-1]
    logger.info(f"Final loss: {final_loss:.6f}")

    # Accuracy
    acc = accuracy(model, xs, [int(y) for y in ys])
    logger.info(f"Training accuracy: {acc:.2%}")

    # Predictions
    print("\nPredictions:")
    for x, y in zip(xs, ys):
        out = model(x)
        pred = out[0].data if isinstance(out, list) else out.data
        print(f"  {x} => {pred:.4f} (target {y})")

    # Save model
    if args.save_model:
        save_model(model, args.save_model)
        logger.info(f"Model saved to {args.save_model}")

    # Plot
    if args.plot:
        print("\n" + ascii_loss_chart(history))

    # Save config
    if args.save_config:
        config.save(args.save_config)
        logger.info(f"Config saved to {args.save_config}")


def cmd_grad_check(args: argparse.Namespace) -> None:
    """Run numerical gradient checking on a sample function."""
    print("Running numerical gradient checking on f(x,y) = (x*y + x.tanh()).exp().log() + x**2")
    print()

    def f(inputs: List[Value]) -> Value:
        x, y = inputs
        return (x * y + x.tanh()).exp().log() + x ** 2

    test_cases = [
        ([Value(1.5), Value(0.7)], "x=1.5, y=0.7"),
        ([Value(2.0), Value(-1.0)], "x=2.0, y=-1.0"),
        ([Value(0.5), Value(3.0)], "x=0.5, y=3.0"),
    ]

    all_pass = True
    for vals, desc in test_cases:
        # Need fresh Values each time since backward() mutates
        inputs = [Value(v.data) for v in vals]
        result = numerical_grad_check(f, inputs, tol=args.tolerance)
        status = "PASS" if result else "FAIL"
        print(f"  {desc}: {status}")
        if not result:
            all_pass = False

    print()
    if all_pass:
        print("All gradient checks passed! ✓")
    else:
        print("Some gradient checks FAILED! ✗")
        sys.exit(1)


def cmd_demo(args: argparse.Namespace) -> None:
    """Run the XOR demo."""
    print("=== XOR Demo ===\n")
    xs, ys = _xor_data()

    model = MLP(2, [8, 8, 1], activation="tanh")
    opt = Adam(model.parameters(), lr=0.01)
    print(f"Model: {model}")
    print(f"Parameters: {model.num_parameters()}")
    print(f"Training 300 epochs with Adam (lr=0.01)...\n")

    history = train_fn(model, xs, ys, epochs=300, optimizer=opt,
                        classification=True, verbose=True)

    print(f"\nFinal loss: {history[-1]:.6f}")
    acc = accuracy(model, xs, [int(y) for y in ys])
    print(f"Accuracy: {acc:.2%}\n")

    print("Predictions:")
    for x, y in zip(xs, ys):
        pred = model(x)[0].data
        print(f"  {x} => {pred:.4f} (target {y})")

    print("\nLoss chart:")
    print(ascii_loss_chart(history))


def cmd_info(args: argparse.Namespace) -> None:
    """Print package info."""
    from . import __version__
    print(f"autograd-engine v{__version__}")
    print()
    print("Available operations on Value:")
    print("  Arithmetic:  +, -, *, /, **, unary -, reflected ops")
    print("  Transcend.:  tanh, relu, exp, log, sigmoid")
    print()
    print("Available activation functions:")
    for name in sorted(ACTIVATION_REGISTRY):
        print(f"  {name}")
    print()
    print("Modules:")
    print("  engine         — Value class + autodiff core")
    print("  nn             — Module, Neuron, Layer, MLP")
    print("  ops            — sum, mean, max, softmax, cross_entropy, dot, matvec")
    print("  train          — SGD, Adam, losses, training loop, early stopping")
    print("  activations    — extended activation functions")
    print("  schedulers     — LR schedulers (step, cosine, linear, warmup, plateau)")
    print("  serialization  — save/load models to JSON")
    print("  viz            — graph visualization + ASCII loss charts")
    print("  metrics        — classification & regression metrics")
    print("  config         — JSON/YAML config file support")


# --------------------------------------------------------------------------- #
# arg parsing
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autograd-engine",
        description="A tiny reverse-mode autodiff engine with neural network library.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Sub-command to run")

    # train
    p_train = subparsers.add_parser("train", help="Train an MLP on a dataset")
    p_train.add_argument("--config", type=str, default=None,
                          help="Path to a JSON/YAML config file")
    p_train.add_argument("--data", type=str, default=None,
                          help="Path to data file (CSV or JSON). Default: XOR")
    p_train.add_argument("--xor", action="store_true",
                          help="Use the XOR dataset (default if no --data)")
    p_train.add_argument("--epochs", type=int, default=None,
                          help="Number of training epochs")
    p_train.add_argument("--lr", type=float, default=None,
                          help="Learning rate")
    p_train.add_argument("--optimizer", type=str, default=None,
                          choices=["sgd", "adam"],
                          help="Optimizer type")
    p_train.add_argument("--activation", type=str, default=None,
                          help="Activation function for hidden layers")
    p_train.add_argument("--hidden", type=int, nargs="+", default=None,
                          help="Hidden layer sizes (e.g. --hidden 8 8)")
    p_train.add_argument("--dropout", type=float, default=None,
                          help="Dropout probability")
    p_train.add_argument("--batch-size", type=int, default=None,
                          help="Mini-batch size")
    p_train.add_argument("--seed", type=int, default=None,
                          help="Random seed")
    p_train.add_argument("--save-model", type=str, default=None,
                          help="Save trained model to JSON file")
    p_train.add_argument("--save-config", type=str, default=None,
                          help="Save effective config to JSON file")
    p_train.add_argument("--plot", action="store_true",
                          help="Print ASCII loss chart after training")
    p_train.set_defaults(func=cmd_train)

    # grad-check
    p_gc = subparsers.add_parser("grad-check", help="Run numerical gradient checking")
    p_gc.add_argument("--tolerance", type=float, default=1e-4,
                       help="Gradient check tolerance")
    p_gc.set_defaults(func=cmd_grad_check)

    # demo
    p_demo = subparsers.add_parser("demo", help="Run the XOR demo")
    p_demo.set_defaults(func=cmd_demo)

    # info
    p_info = subparsers.add_parser("info", help="Print package info")
    p_info.set_defaults(func=cmd_info)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())