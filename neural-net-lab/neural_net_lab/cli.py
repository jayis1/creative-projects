"""Command-line experiment runner."""
import argparse, logging
from .config import DEFAULTS, load_config
from .core import MLP
from .optim import Adam, SGD

log = logging.getLogger("neural_net_lab")
XOR_X = [[0, 0], [0, 1], [1, 0], [1, 1]]
XOR_Y = [[0], [1], [1], [0]]

def main(argv=None):
    p = argparse.ArgumentParser(description="Train and inspect a pure-Python MLP (XOR demo by default).")
    p.add_argument("--config", help="TOML or JSON experiment configuration")
    p.add_argument("--load", help="load a JSON model and print predictions")
    p.add_argument("--save", help="write trained model JSON")
    p.add_argument("--epochs", type=int); p.add_argument("--lr", type=float); p.add_argument("--loss", choices=["mse", "bce", "cross_entropy"])
    p.add_argument("--optimizer", choices=["adam", "sgd"]); p.add_argument("--verbose", action="store_true")
    p.add_argument("--gradient-check", action="store_true", help="validate backpropagation with finite differences")
    a = p.parse_args(argv); logging.basicConfig(level=logging.INFO if a.verbose else logging.WARNING, format="%(levelname)s %(message)s")
    if a.load:
        net = MLP.load(a.load)
        for x in XOR_X: print(x, "=>", [round(v, 6) for v in net.predict(x)])
        return 0
    c = load_config(a.config) if a.config else dict(DEFAULTS)
    for key in ("epochs", "lr", "loss", "optimizer"):
        value = getattr(a, key)
        if value is not None: c[key] = value
    net = MLP(c["sizes"], c.get("activations"), c.get("seed", 0)); opt = Adam() if c["optimizer"] == "adam" else SGD()
    log.info("training sizes=%s optimizer=%s loss=%s", c["sizes"], c["optimizer"], c["loss"])
    if a.gradient_check:
        error = net.gradient_check(XOR_X[0], XOR_Y[0], loss_name=c["loss"])
        print(f"gradient check max relative error: {error:.3e}")
    history = net.train(XOR_X, XOR_Y, epochs=c["epochs"], lr=c["lr"], batch_size=c.get("batch_size", 16), optimizer=opt, clip=c.get("clip"), patience=c.get("patience"), loss_name=c["loss"])
    print(f"final {c['loss']} loss: {history.losses[-1]:.6f}; accuracy: {net.accuracy(XOR_X, XOR_Y):.2%}; epochs: {len(history.losses)}")
    for x, y in zip(XOR_X, XOR_Y): print(x, "=>", round(net.predict(x)[0], 4), "target", y[0])
    if a.save: net.save(a.save); log.info("saved model to %s", a.save)
    return 0

if __name__ == "__main__": raise SystemExit(main())
