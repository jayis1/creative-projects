"""Command-line experiment runner."""
import argparse, json, logging
from .config import DEFAULTS, load_config, validate_config
from .core import MLP
from .data import load_dataset, train_test_split
from .optim import Adam, SGD

log = logging.getLogger("neural_net_lab")
XOR_X = [[0, 0], [0, 1], [1, 0], [1, 1]]
XOR_Y = [[0], [1], [1], [0]]

def main(argv=None):
    p = argparse.ArgumentParser(description="Train and inspect a pure-Python MLP (XOR demo by default).")
    p.add_argument("--config", help="TOML or JSON experiment configuration")
    p.add_argument("--dataset", help="CSV or JSONL dataset to train instead of XOR")
    p.add_argument("--target-column", help="CSV target column (defaults to the final column)")
    p.add_argument("--validation-split", type=float, metavar="FRACTION", help="reserve a deterministic validation fraction")
    p.add_argument("--load", help="load a JSON model and print XOR predictions")
    p.add_argument("--evaluate", metavar="DATASET", help="evaluate a loaded model on CSV or JSONL data")
    p.add_argument("--report", action="store_true", help="print a JSON classification report during --evaluate")
    p.add_argument("--threshold", type=float, default=0.5, help="binary accuracy threshold for --evaluate")
    p.add_argument("--eval-loss", choices=["mse", "bce", "cross_entropy"], default="mse", help="loss used when evaluating a loaded model")
    p.add_argument("--save", help="write trained model JSON")
    p.add_argument("--epochs", type=int); p.add_argument("--lr", type=float); p.add_argument("--loss", choices=["mse", "bce", "cross_entropy"])
    p.add_argument("--optimizer", choices=["adam", "sgd"]); p.add_argument("--verbose", action="store_true")
    p.add_argument("--gradient-check", action="store_true", help="validate backpropagation with finite differences")
    a = p.parse_args(argv); logging.basicConfig(level=logging.INFO if a.verbose else logging.WARNING, format="%(levelname)s %(message)s")
    if a.load:
        net = MLP.load(a.load)
        if a.evaluate:
            xs, ys = load_dataset(a.evaluate, a.target_column)
            if len(xs[0]) != net.sizes[0] or len(ys[0]) != net.sizes[-1]:
                raise ValueError("evaluation dataset widths do not match the loaded model")
            if not 0 <= a.threshold <= 1:
                raise ValueError("threshold must be between 0 and 1")
            print(f"loss: {net.loss(xs, ys, a.eval_loss):.6f}; accuracy: {net.accuracy(xs, ys, a.threshold):.2%}; samples: {len(xs)}")
            if a.report:
                print(json.dumps(net.classification_report(xs, ys, a.threshold), sort_keys=True))
            return 0
        for x in XOR_X:
            if len(x) != net.sizes[0]:
                raise ValueError("XOR inspection requires a model with two input features; use --evaluate for another dataset")
            print(x, "=>", [round(v, 6) for v in net.predict(x)])
        return 0
    c = load_config(a.config) if a.config else dict(DEFAULTS)
    for key in ("epochs", "lr", "loss", "optimizer"):
        value = getattr(a, key)
        if value is not None: c[key] = value
    c = validate_config(c)
    xs, ys = XOR_X, XOR_Y
    validation = None
    if a.dataset:
        xs, ys = load_dataset(a.dataset, a.target_column)
        if a.validation_split is not None:
            (xs, ys), validation = train_test_split(xs, ys, a.validation_split, seed=c.get("seed", 0))
        sizes = list(c["sizes"])
        if sizes[0] != len(xs[0]) or sizes[-1] != len(ys[0]):
            raise ValueError("dataset feature/target widths must match config sizes")
    net = MLP(c["sizes"], c.get("activations"), c.get("seed", 0)); opt = Adam() if c["optimizer"] == "adam" else SGD()
    log.info("training sizes=%s optimizer=%s loss=%s", c["sizes"], c["optimizer"], c["loss"])
    if a.gradient_check:
        error = net.gradient_check(xs[0], ys[0], loss_name=c["loss"])
        print(f"gradient check max relative error: {error:.3e}")
    history = net.train(xs, ys, epochs=c["epochs"], lr=c["lr"], batch_size=c.get("batch_size", 16), optimizer=opt, validation=validation, clip=c.get("clip"), patience=c.get("patience"), loss_name=c["loss"])
    print(f"final {c['loss']} loss: {history.losses[-1]:.6f}; accuracy: {net.accuracy(xs, ys):.2%}; epochs: {len(history.losses)}")
    if validation:
        print(f"validation loss: {history.val_losses[-1]:.6f}; validation accuracy: {net.accuracy(*validation):.2%}")
    for x, y in zip(xs, ys): print(x, "=>", round(net.predict(x)[0], 4), "target", y[0])
    if a.save: net.save(a.save); log.info("saved model to %s", a.save)
    return 0

if __name__ == "__main__": raise SystemExit(main())
