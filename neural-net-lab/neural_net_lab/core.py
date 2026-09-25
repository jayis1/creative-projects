"""Dependency-free dense neural networks with inspectable backpropagation."""
from __future__ import annotations
import json, math, random
from dataclasses import dataclass
from typing import Any, Sequence


def _act(name: str, x: float) -> tuple[float, float]:
    if name == "relu": return max(0.0, x), 1.0 if x > 0 else 0.0
    if name == "tanh":
        y = math.tanh(x); return y, 1.0 - y * y
    if name == "sigmoid":
        y = 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, x))))
        return y, y * (1.0 - y)
    if name == "linear": return x, 1.0
    if name == "softmax": raise ValueError("softmax is a vector output activation")
    raise ValueError(f"unknown activation: {name}")

@dataclass
class TrainingHistory:
    losses: list[float]
    val_losses: list[float]
    stopped_epoch: int | None = None

class Layer:
    """A fully-connected layer; weights are output-major for readability."""
    def __init__(self, inputs: int, outputs: int, activation="tanh", rng=None):
        if inputs < 1 or outputs < 1: raise ValueError("layer dimensions must be positive")
        if activation not in {"relu", "tanh", "sigmoid", "linear", "softmax"}:
            raise ValueError(f"unknown activation: {activation}")
        if activation == "softmax" and outputs < 2: raise ValueError("softmax needs at least two outputs")
        self.activation = activation; r = rng or random.Random()
        scale = math.sqrt(2 / inputs) if activation == "relu" else math.sqrt(1 / inputs)
        self.w = [[r.gauss(0, scale) for _ in range(inputs)] for _ in range(outputs)]
        self.b = [0.0] * outputs
    def forward(self, x):
        if len(x) != len(self.w[0]): raise ValueError("input width does not match layer")
        z = [sum(a * v for a, v in zip(row, x)) + b for row, b in zip(self.w, self.b)]
        if self.activation == "softmax":
            m = max(z); e = [math.exp(v - m) for v in z]; total = sum(e)
            out = [v / total for v in e]; slopes = [v * (1 - v) for v in out]
        else:
            out, slopes = zip(*(_act(self.activation, v) for v in z)); out, slopes = list(out), list(slopes)
        return out, (list(x), z, slopes)

class MLP:
    def __init__(self, sizes: Sequence[int], activations=None, seed=0):
        if len(sizes) < 2 or any(not isinstance(n, int) or isinstance(n, bool) or n < 1 for n in sizes):
            raise ValueError("sizes must contain positive integers")
        acts = list(activations or ["tanh"] * (len(sizes) - 2) + ["sigmoid"])
        if len(acts) != len(sizes) - 1: raise ValueError("one activation per layer required")
        if "softmax" in acts[:-1]: raise ValueError("softmax is only valid on the output layer")
        self.layers = []; rng = random.Random(seed)
        for a, b, act in zip(sizes, sizes[1:], acts): self.layers.append(Layer(a, b, act, rng))
        self.sizes = list(sizes)
    def predict(self, x):
        y = list(map(float, x))
        for layer in self.layers: y, _ = layer.forward(y)
        return y
    def predict_batch(self, xs): return [self.predict(x) for x in xs]
    def _grad(self, x, target, loss_name="mse"):
        acts = [list(map(float, x))]; caches = []
        for layer in self.layers:
            y, cache = layer.forward(acts[-1]); acts.append(y); caches.append(cache)
        if len(target) != len(acts[-1]): raise ValueError("target width does not match output")
        valid = {"mse", "bce", "cross_entropy"}
        if loss_name not in valid: raise ValueError(f"loss must be one of {sorted(valid)}")
        output_act = self.layers[-1].activation
        if loss_name == "bce" and output_act != "sigmoid": raise ValueError("bce requires a sigmoid output layer")
        if loss_name == "cross_entropy" and output_act != "softmax": raise ValueError("cross_entropy requires a softmax output layer")
        y = acts[-1]
        if loss_name in {"bce", "cross_entropy"}: delta = [a - t for a, t in zip(y, target)]
        else: delta = [(a - t) * d for a, t, d in zip(y, target, caches[-1][2])]
        grads = []
        for i in range(len(self.layers) - 1, -1, -1):
            inp, _, slopes = caches[i]
            grads.append(([[delta[o] * inp[j] for j in range(len(inp))] for o in range(len(delta))], delta[:]))
            if i: delta = [sum(self.layers[i].w[o][j] * delta[o] for o in range(len(delta))) * caches[i-1][2][j] for j in range(len(inp))]
        if loss_name == "bce": cost = -sum(t * math.log(max(a, 1e-15)) + (1-t) * math.log(max(1-a, 1e-15)) for a, t in zip(y, target))
        elif loss_name == "cross_entropy": cost = -sum(t * math.log(max(a, 1e-15)) for a, t in zip(y, target))
        else: cost = 0.5 * sum((a-b) ** 2 for a, b in zip(y, target))
        return list(reversed(grads)), cost

    def gradient_check(self, x, target, loss_name="mse", epsilon=1e-6):
        """Compare backpropagation gradients with finite differences.

        This educational diagnostic perturbs every weight and bias for one
        sample, then returns the largest normalized discrepancy. A value near
        zero indicates that the analytic gradients agree with the loss surface.
        """
        if epsilon <= 0:
            raise ValueError("epsilon must be positive")
        analytic, _ = self._grad(x, target, loss_name)
        worst = 0.0
        for layer_index, layer in enumerate(self.layers):
            for output_index, row in enumerate(layer.w):
                for input_index in range(len(row)):
                    original = row[input_index]
                    row[input_index] = original + epsilon
                    plus = self._grad(x, target, loss_name)[1]
                    row[input_index] = original - epsilon
                    minus = self._grad(x, target, loss_name)[1]
                    row[input_index] = original
                    numeric = (plus - minus) / (2 * epsilon)
                    expected = analytic[layer_index][0][output_index][input_index]
                    worst = max(worst, abs(numeric - expected) / max(1e-12, abs(numeric) + abs(expected)))
            for output_index, original in enumerate(layer.b):
                layer.b[output_index] = original + epsilon
                plus = self._grad(x, target, loss_name)[1]
                layer.b[output_index] = original - epsilon
                minus = self._grad(x, target, loss_name)[1]
                layer.b[output_index] = original
                numeric = (plus - minus) / (2 * epsilon)
                expected = analytic[layer_index][1][output_index]
                worst = max(worst, abs(numeric - expected) / max(1e-12, abs(numeric) + abs(expected)))
        return worst

    def train(self, xs, ys, epochs=1000, lr=.1, batch_size=16, optimizer=None, validation=None, shuffle=True, seed=1, clip=None, patience=None, loss_name="mse"):
        if len(xs) != len(ys) or not xs: raise ValueError("xs and ys must be non-empty and equal length")
        if epochs < 1 or lr <= 0 or batch_size < 1 or (clip is not None and clip <= 0) or (patience is not None and patience < 1): raise ValueError("invalid training parameters")
        if validation and (not validation[0] or len(validation[0]) != len(validation[1])): raise ValueError("validation data must be non-empty and aligned")
        rng = random.Random(seed); hist = TrainingHistory([], []); ids = list(range(len(xs))); opt = optimizer
        best, stale, best_weights = float("inf"), 0, None
        for epoch in range(epochs):
            if shuffle: rng.shuffle(ids)
            for start in range(0, len(ids), batch_size):
                sums = [([[0.0] * len(l.w[0]) for _ in l.w], [0.0] * len(l.b)) for l in self.layers]; count = 0
                for k in ids[start:start+batch_size]:
                    gs, _ = self._grad(xs[k], ys[k], loss_name); count += 1
                    for i, (gw, gb) in enumerate(gs):
                        for o in range(len(gw)):
                            for j in range(len(gw[o])): sums[i][0][o][j] += gw[o][j]
                            sums[i][1][o] += gb[o]
                for i, (gw, gb) in enumerate(sums):
                    if clip is not None:
                        norm = math.sqrt(sum(v*v for row in gw for v in row) + sum(v*v for v in gb))
                        if norm > clip: factor = clip / norm; gw = [[v*factor for v in row] for row in gw]; gb = [v*factor for v in gb]
                    (opt.step(self.layers[i], gw, gb, lr, count) if opt else self._apply(self.layers[i], gw, gb, lr, count))
            loss = self.loss(xs, ys, loss_name); current = self.loss(*validation, loss_name=loss_name) if validation else loss
            hist.losses.append(loss); hist.val_losses.append(current if validation else float("nan"))
            if current < best - 1e-12: best, stale = current, 0; best_weights = [([r[:] for r in l.w], l.b[:]) for l in self.layers]
            else: stale += 1
            if patience is not None and stale >= patience:
                hist.stopped_epoch = epoch + 1
                if best_weights:
                    for layer, (w, b) in zip(self.layers, best_weights): layer.w, layer.b = [r[:] for r in w], b[:]
                break
        return hist
    @staticmethod
    def _apply(layer, gw, gb, lr, n):
        for o in range(len(layer.w)):
            for j in range(len(layer.w[o])): layer.w[o][j] -= lr * gw[o][j] / n
            layer.b[o] -= lr * gb[o] / n
    def loss(self, xs, ys, loss_name="mse"):
        if not xs or len(xs) != len(ys): raise ValueError("loss data must be non-empty and aligned")
        return sum(self._grad(x, y, loss_name)[1] for x, y in zip(xs, ys)) / len(xs)
    def accuracy(self, xs, ys, threshold=.5):
        if not xs or len(xs) != len(ys) or not 0 <= threshold <= 1: raise ValueError("accuracy requires aligned data and a valid threshold")
        if len(self.layers[-1].b) == 1: return sum((self.predict(x)[0] >= threshold) == (y[0] >= threshold) for x, y in zip(xs, ys)) / len(xs)
        return sum(max(range(len(p)), key=p.__getitem__) == max(range(len(y)), key=y.__getitem__) for p, y in zip(self.predict_batch(xs), ys)) / len(xs)
    def classification_report(self, xs, ys, threshold=.5) -> dict[str, Any]:
        """Return confusion matrix and macro precision/recall/F1 for classification.

        Labels are thresholded for binary sigmoid outputs and argmaxed for
        multiclass outputs. Empty classes are retained in the matrix and get
        zero precision/recall, making reports comparable across runs.
        """
        if not xs or len(xs) != len(ys) or not 0 <= threshold <= 1:
            raise ValueError("report requires aligned data and a valid threshold")
        classes = len(self.layers[-1].b)
        if any(len(y) != classes for y in ys):
            raise ValueError("target width does not match output")
        if classes == 1:
            actual = [int(y[0] >= threshold) for y in ys]
            predicted = [int(self.predict(x)[0] >= threshold) for x in xs]
            size = 2
        else:
            actual = [max(range(classes), key=y.__getitem__) for y in ys]
            predicted = [max(range(classes), key=self.predict(x).__getitem__) for x in xs]
            size = classes
        matrix = [[0 for _ in range(size)] for _ in range(size)]
        for truth, guess in zip(actual, predicted): matrix[truth][guess] += 1
        scores = []
        for label in range(size):
            tp = matrix[label][label]
            fp = sum(matrix[row][label] for row in range(size)) - tp
            fn = sum(matrix[label]) - tp
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / (tp + fn) if tp + fn else 0.0
            f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
            scores.append({"precision": precision, "recall": recall, "f1": f1, "support": sum(matrix[label])})
        return {"accuracy": self.accuracy(xs, ys, threshold), "confusion_matrix": matrix, "per_class": scores,
                "macro_precision": sum(s["precision"] for s in scores) / size,
                "macro_recall": sum(s["recall"] for s in scores) / size,
                "macro_f1": sum(s["f1"] for s in scores) / size}
    def to_dict(self) -> dict[str, Any]: return {"sizes": self.sizes, "activations": [l.activation for l in self.layers], "weights": [l.w for l in self.layers], "biases": [l.b for l in self.layers]}
    def save(self, path):
        with open(path, "w", encoding="utf8") as f: json.dump(self.to_dict(), f, indent=2)
    @classmethod
    def load(cls, path):
        try:
            with open(path, encoding="utf8") as f: d = json.load(f)
        except (OSError, json.JSONDecodeError) as e: raise ValueError(f"cannot read model: {e}") from e
        if not isinstance(d, dict) or not all(k in d for k in ("sizes", "activations", "weights", "biases")): raise ValueError("invalid model file")
        net = cls(d["sizes"], d["activations"])
        if len(d["weights"]) != len(net.layers) or len(d["biases"]) != len(net.layers): raise ValueError("model layer count mismatch")
        for layer, weights, bias in zip(net.layers, d["weights"], d["biases"]):
            if not isinstance(weights, list) or len(weights) != len(layer.w) or any(not isinstance(row, list) or len(row) != len(layer.w[0]) or any(not isinstance(v, (int, float)) for v in row) for row in weights) or not isinstance(bias, list) or len(bias) != len(layer.b): raise ValueError("invalid model dimensions")
            layer.w, layer.b = weights, bias
        return net
